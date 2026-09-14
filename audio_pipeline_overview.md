# Pipeline d'évaluation de transcription audio

Comparaison entre **AWS Transcribe** et **WhisperX large-v3**  
Contexte : appels téléphoniques courtier/client (~45 min), détection de fraude financière, français.

---

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                        AUDIO BRUT                               │
│                    (.mp3 / .wav stéréo ou mono)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
       SANS preprocessing     AVEC preprocessing
              │                     │
              │               (audio_preprocessing.py)
              │                     │
              │              ┌──────┴──────────────┐
              │              │  1. Split canaux     │
              │              │  2. Normalisation    │
              │              │  3. Filtre HPF       │
              │              │  4. VAD              │
              │              └──────┬───────────────┘
              │                     │
     ┌────────┴──────┐     ┌────────┴──────┐
     │               │     │               │
     ▼               ▼     ▼               ▼
 WhisperX          AWS  WhisperX          AWS
 large-v3       Transcribe large-v3    Transcribe
     │               │     │               │
  wx_raw.txt   aws_raw.txt wx_clean.txt aws_clean.txt
     │               │     │               │
     └───────┬────────┘     └───────┬───────┘
             │                      │
             └──────────┬───────────┘
                        │
          (experiment_preprocessing_impact.py)
                        │
              ┌─────────┴──────────┐
              │  4 COMPARAISONS    │
              │  wx_raw vs wx_clean│
              │  aws_raw vs clean  │
              │  wx vs aws (raw)   │
              │  wx vs aws (clean) │
              └─────────┬──────────┘
                        │
              (audio_transcription_eval.py)
                        │
                experiment_report.json
```

---

## Format des transcriptions

Les deux systèmes produisent des transcriptions dans ce format :

```
[00:00:35 -> 00:02:42] courtier : bla bla bla
[00:03:05 -> 00:06:17] client : bla bla bla
[00:06:20 -> 00:08:45] courtier : bla bla bla
```

Chaque ligne contient un intervalle temporel, un locuteur identifié, et le texte transcrit.

---

## Fichiers du projet

| Fichier | Rôle |
|---|---|
| `audio_preprocessing.py` | Nettoie les audios avant transcription |
| `audio_transcription_eval.py` | Compare deux transcriptions via 8 métriques |
| `experiment_preprocessing_impact.py` | Orchestre les 4 comparaisons brut/nettoyé |
| `docs/transcription_evaluation_methods.md` | Détail de chaque méthode d'évaluation |

---

## Partie 1 — Preprocessing (`audio_preprocessing.py`)

### Pourquoi preprocesser ?

Les deux systèmes de transcription sont sensibles à :
- **Les déséquilibres de volume** : le courtier (micro proche) est souvent bien plus fort que le client (téléphone)
- **Les silences longs** : WhisperX hallucine sur les passages silencieux (il répète des phrases en boucle)
- **Les basses fréquences parasites** : bruit de fond, ventilation, frottements de micro

Le preprocessing vise à neutraliser ces facteurs pour isoler l'impact réel de chaque système de transcription.

### Pipeline appliqué

#### Étape 1 — Séparation des canaux (stéréo uniquement)

Dans un enregistrement d'appel stéréo, le courtier et le client sont souvent sur des canaux séparés (gauche/droite). Les traiter indépendamment :
- améliore la normalisation du volume (chaque voix à son propre niveau)
- améliore la diarisation (moins de confusion entre les locuteurs)
- réduit les effets de masquage (une voix forte ne cache plus l'autre)

```
Canal gauche → courtier_clean.wav
Canal droit  → client_clean.wav
Fusion       → merged_clean.wav  (fourni aux modèles de transcription)
```

#### Étape 2 — Normalisation du volume (EBU R128)

Normalise chaque canal vers **-23 LUFS**, la norme européenne broadcast pour la parole. Cela garantit que les deux locuteurs ont un volume équilibré dans la transcription finale.

#### Étape 3 — Filtre passe-haut à 80 Hz

Supprime toutes les fréquences inférieures à 80 Hz. La voix humaine commence à ~80-100 Hz ; les fréquences en dessous sont du bruit non vocal (ventilation, vibrations mécaniques, frottements).

#### Étape 4 — Voice Activity Detection (Silero VAD)

Détecte les segments contenant de la parole et supprime les silences longs. Particulièrement important pour des appels de 45 minutes qui contiennent de nombreuses pauses.

**Problème résolu :** WhisperX est connu pour halluciner sur les silences — il répète des phrases en boucle plutôt que de détecter l'absence de parole. La VAD supprime ces zones avant la transcription.

### Usage

```bash
# Fichier unique
python audio_preprocessing.py appel.wav output/

# Dossier entier (batch)
python audio_preprocessing.py audios/ output/ --batch
```

Produit pour un fichier stéréo :
```
output/
├── appel_channel_L_clean.wav   ← courtier
├── appel_channel_R_clean.wav   ← client
└── appel_merged_clean.wav      ← fusion (à fournir aux modèles)
```

### Dépendances

```bash
pip install soundfile pyloudnorm scipy torch librosa
```

---

## Partie 2 — Évaluation (`audio_transcription_eval.py`)

Compare deux transcriptions via **8 métriques complémentaires**, toutes sans ground truth.

### Étape préliminaire : alignement temporel

Les deux systèmes ne découpent pas l'audio aux mêmes instants. L'alignement se fait par chevauchement temporel : deux segments sont appariés si leur overlap représente ≥ 50% de la durée du segment de référence.

### Méthode 1 — Désaccord lexical

Comparaison mot à mot via SequenceMatcher. Produit un score de similarité (0 à 1) et liste les mots présents dans un système mais absents de l'autre.

**Seuil :** similarité < 0.6 → segment flaggé pour révision.

### Méthode 2 — LLM-as-judge

Un LLM (Claude) arbitre laquelle des deux transcriptions est la plus correcte, **uniquement sur les segments divergents** (similarité < 0.6). Économise les tokens API en ignorant les segments quasi-identiques.

### Méthode 3 — Perplexité par locuteur

Mesure la fluidité linguistique du texte produit par chaque système. Une perplexité plus basse indique un texte plus naturel.  
Modèle utilisé : `asi/gpt-fr-cased-small` (GPT-2 entraîné sur du français).

### Méthode 4 — Similarité sémantique

Compare le sens des segments via embeddings (CamemBERT). Détecte les cas où les deux systèmes disent la même chose avec des mots différents — ce qui n'est pas une erreur.  
Modèle utilisé : `dangvantuan/sentence-camembert-large`.

### Méthode 5 — Cohérence de diarisation

Compare les patterns de prise de parole : ratio de temps par locuteur, nombre de tours, durée moyenne des interventions. Un écart de ratio > 15% entre les deux systèmes indique un désaccord fort sur l'attribution de parole.

### Méthode 6 — Détection d'hallucinations

Détecte les répétitions anormales de n-grams dans les segments WhisperX. Si un trigramme apparaît 3+ fois dans un même segment, c'est probablement une hallucination sur un silence.

### Méthode 7 — Entités nommées (NER)

Extrait et compare les entités critiques : noms de personnes, montants, dates, organisations, pourcentages.  
Un désaccord sur un montant financier est une alerte prioritaire en détection de fraude.

### Méthode 8 — Coverage temporelle

Mesure la proportion de l'audio effectivement couverte par les segments transcrits. Une coverage faible indique des passages manqués.

### Usage

```bash
python audio_transcription_eval.py transcription_A.txt transcription_B.txt [durée_secondes]
```

Produit : `eval_report.json`

### Dépendances

```bash
pip install anthropic transformers torch sentence-transformers spacy
python -m spacy download fr_core_news_sm
```

---

## Partie 3 — Expérience preprocessing (`experiment_preprocessing_impact.py`)

Orchestre les 4 comparaisons pour mesurer l'impact du preprocessing sur chaque système.

### Les 4 comparaisons

| Comparaison | Question à laquelle elle répond |
|---|---|
| `wx_raw` vs `wx_clean` | Le preprocessing améliore-t-il WhisperX ? |
| `aws_raw` vs `aws_clean` | Le preprocessing améliore-t-il AWS ? |
| `wx_raw` vs `aws_raw` | Quel système est meilleur sans preprocessing ? |
| `wx_clean` vs `aws_clean` | Quel système est meilleur après preprocessing ? |

### Workflow complet

**Étape 1 — Preprocessing**

```bash
python experiment_preprocessing_impact.py appel.wav \
    --preprocess \
    --output-dir preprocessed/
```

Produit `preprocessed/appel_merged_clean.wav`.

**Étape 2 — Transcription** (à faire avec vos systèmes existants)

```
appel.wav               → WhisperX large-v3 → wx_raw.txt
appel.wav               → AWS Transcribe    → aws_raw.txt
appel_merged_clean.wav  → WhisperX large-v3 → wx_clean.txt
appel_merged_clean.wav  → AWS Transcribe    → aws_clean.txt
```

**Étape 3 — Comparaison**

```bash
python experiment_preprocessing_impact.py appel.wav \
    --wx-raw   wx_raw.txt   \
    --wx-clean wx_clean.txt \
    --aws-raw  aws_raw.txt  \
    --aws-clean aws_clean.txt \
    --duration 2700
```

### Sortie terminal (exemple)

```
=================================================================
RÉSUMÉ — IMPACT DU PREPROCESSING
=================================================================
Comparaison            Similarité moy.  Segments flaggés  Hallucinations A/B
WX-raw vs WX-clean     0.743            18 (24%)          0 / 3
AWS-raw vs AWS-clean   0.891            4 (5%)            0 / 0
WX-raw vs AWS-raw      0.612            31 (41%)          2 / 0
WX-clean vs AWS-clean  0.834            12 (16%)          0 / 0

CONCLUSIONS :
  • Preprocessing améliore WhisperX (similarité=0.743 → divergences notables)
  • Preprocessing peu d'impact sur AWS (similarité=0.891)
  • Après preprocessing : similarité WX vs AWS = 0.834, sémantique = 0.871
  • WhisperX hallucine plus (3 segments) qu'AWS (0 segments)
```

Produit également : `experiment_report.json` avec le détail complet de chaque comparaison.

---

## Récapitulatif des dépendances

```bash
# Audio processing
pip install soundfile pyloudnorm scipy librosa

# Deep learning
pip install torch transformers sentence-transformers

# NLP
pip install spacy
python -m spacy download fr_core_news_sm

# LLM judge
pip install anthropic

# VAD
# Silero VAD se télécharge automatiquement via torch.hub au premier appel
```

Variable d'environnement requise pour le LLM-as-judge :

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Ordre d'exécution recommandé des métriques

Pour un usage quotidien sur de nombreux fichiers, exécuter dans cet ordre (du plus rapide au plus coûteux) :

```
1. Coverage temporelle        → élimine les transcriptions trop incomplètes
2. Détection hallucinations   → signale les segments WhisperX non fiables
3. Cohérence diarisation      → valide l'attribution des locuteurs
4. Entités nommées            → désaccords critiques (montants, noms)
5. Désaccord lexical          → flags les segments à réviser
6. Similarité sémantique      → filtre les faux positifs du désaccord lexical
7. LLM-as-judge               → arbitre uniquement les segments encore ambigus
8. Perplexité                 → indicateur global de qualité linguistique
```

Un segment est **critique** (priorité de révision maximale) si au moins deux de ces conditions sont vraies :
- Similarité lexicale < 0.6
- Similarité sémantique < 0.7
- Désaccord sur une entité financière (montant, nom)
- Hallucination détectée
- Désaccord fort sur le locuteur (écart ratio > 15%)
