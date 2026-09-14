# Méthodes d'évaluation de transcription audio

Comparaison entre **AWS Transcribe** (système A) et **WhisperX + pyannote** (système B)  
Contexte : appels téléphoniques courtier/client, détection de fraude financière.

---

## Contexte et contraintes

Les transcriptions produites ont le format suivant :

```
[00:00:35 -> 00:02:42] courtier : bla bla bla
[00:03:05 -> 00:06:17] client : bla bla bla
```

Chaque ligne contient :
- un **intervalle temporel** (début → fin)
- un **locuteur** identifié (courtier, client, etc.)
- le **texte transcrit**

**Contrainte principale :** aucune transcription manuelle de référence (ground truth) n'est disponible. Toutes les méthodes ci-dessous fonctionnent donc sans référence.

---

## Étape préliminaire : Parsing et alignement

Avant toute comparaison, les deux fichiers doivent être parsés et leurs segments alignés temporellement.

### Parsing

Chaque ligne est transformée en un objet `Segment` contenant :
- `start` / `end` : timestamps en secondes
- `speaker` : nom du locuteur
- `text` : texte transcrit

### Alignement par chevauchement temporel

Les deux systèmes ne découpent pas l'audio aux mêmes instants. L'alignement se fait par **overlap temporel** : deux segments sont considérés comme correspondants si le chevauchement représente au moins 50 % de la durée du segment A.

```
Segment A : |-----------|
Segment B :      |------------|
Overlap   :      |-------|      ← suffisant si ≥ 50% de A
```

Seules les paires alignées sont comparées dans les méthodes suivantes.

---

## Méthode 1 — LLM-as-judge

### Principe

Un grand modèle de langage (Claude) reçoit les deux transcriptions d'un même passage et choisit laquelle est la plus correcte, sans savoir laquelle provient de quel système.

### Quand l'utiliser

Sur les segments où les deux systèmes divergent fortement (similarité lexicale < 0.6). Cela évite de consommer des tokens API sur des segments identiques.

### Ce que ça évalue

- Fluidité et naturel du langage
- Cohérence sémantique dans un contexte financier
- Absence d'artefacts ou de formulations bizarres

### Sortie

Pour chaque segment divergent :
```json
{
  "winner": "A",
  "confidence": 0.85,
  "raison": "La transcription A mentionne correctement le taux d'intérêt de 3.5%"
}
```

### Limites

- Coût API (tokens) — à limiter aux passages vraiment divergents
- Le LLM ne peut pas entendre l'audio, il juge uniquement le texte
- Biais possible vers un style d'écriture plus formel

---

## Méthode 2 — Taux de désaccord lexical

### Principe

Comparaison mot à mot des segments alignés via l'algorithme de **SequenceMatcher** (Ratcliff/Obershelp). Produit un score de similarité entre 0 (totalement différents) et 1 (identiques).

### Ce que ça évalue

- L'écart brut entre les deux transcriptions
- Les mots présents dans A mais absents de B, et vice versa
- Identification des segments qui nécessitent une écoute humaine

### Seuil de décision

| Score | Interprétation |
|---|---|
| > 0.9 | Quasi-identiques, pas de révision nécessaire |
| 0.6 – 0.9 | Différences mineures, probablement sans impact |
| < 0.6 | Divergence significative → révision ciblée recommandée |

### Sortie

```json
{
  "similarity": 0.43,
  "only_in_A": ["trois", "virgule", "cinq"],
  "only_in_B": ["3.5"],
  "needs_review": true
}
```

### Avantage clé

Permet de **cibler l'écoute humaine** uniquement sur les passages les plus incertains, réduisant drastiquement le temps de révision manuelle.

---

## Méthode 3 — Perplexité par locuteur

### Principe

La **perplexité** mesure à quel point un texte est "surprenant" pour un modèle de langue. Un texte bien transcrit (phrases naturelles, cohérentes) aura une perplexité **plus basse** qu'un texte mal transcrit (mots manquants, mauvaise ponctuation, coupures).

### Formule

```
Perplexité = exp( - (1/N) * Σ log P(mot_i | contexte) )
```

Plus la perplexité est basse, plus le texte est linguistiquement naturel.

### Ce que ça évalue

- Fluidité globale de la transcription par locuteur
- Détection de transcriptions incomplètes ou tronquées
- Comparaison du style de transcription entre les deux systèmes

### Calcul

Le texte de chaque locuteur est reconstitué en concaténant tous ses segments, puis la perplexité est calculée avec un modèle GPT-2.

### Sortie

```
courtier     — A: 124.3 | B: 98.7  → B meilleur
client       — A: 112.5 | B: 135.2 → A meilleur
```

### Modèle utilisé

`asi/gpt-fr-cased-small` : GPT-2 entraîné exclusivement sur du texte français. Bien adapté au domaine de la transcription d'appels en français.

### Limites

- La perplexité pénalise le vocabulaire technique financier (noms propres, sigles, acronymes)
- Métrique indirecte : un texte fluide n'est pas forcément correct

---

## Méthode 4 — Similarité sémantique (embeddings)

### Principe

Contrairement à la comparaison lexicale (méthode 2), la similarité sémantique compare le **sens** des segments. Deux phrases peuvent avoir des mots différents mais le même sens — cette méthode les identifie comme équivalentes.

### Technique

Chaque segment est encodé en un vecteur de dimension élevée (embedding) par `dangvantuan/sentence-camembert-large`, un modèle de sentence embeddings spécialisé pour le français (basé sur CamemBERT). La **similarité cosinus** entre les deux vecteurs mesure la proximité sémantique.

```
Similarité cosinus = (A · B) / (||A|| × ||B||)
```

Un score proche de **1.0** signifie même sens, proche de **0** signifie sens opposé.

### Ce que ça évalue

- Détecte quand les deux systèmes transcrivent la même idée avec des formulations différentes
- Distingue les vraies erreurs (sens différent) des variations superficielles (synonymes, ordre des mots)
- Complémentaire à la méthode 2 : similarité lexicale basse + similarité sémantique haute = simple reformulation, pas une erreur

### Seuil de décision

| Score sémantique | Interprétation |
|---|---|
| ≥ 0.85 | Même sens — différence superficielle |
| 0.6 – 0.85 | Sens proche mais nuances différentes |
| < 0.6 | Contenu significativement différent |

### Sortie

```json
{
  "semantic_similarity": 0.91,
  "same_meaning": true,
  "text_a": "le taux est de trois virgule cinq pour cent",
  "text_b": "le taux s'élève à 3,5%"
}
```

---

## Méthode 5 — Cohérence de la diarisation

### Principe

La diarisation est l'attribution des segments à des locuteurs (courtier, client). Cette méthode compare les **patterns de prise de parole** entre les deux systèmes : si AWS dit que le courtier parle 70% du temps et WhisperX dit 40%, l'un des deux se trompe.

### Ce que ça évalue

- **Nombre de tours de parole** : un système qui fragmente trop ou trop peu les segments
- **Ratio de temps de parole** par locuteur
- **Durée moyenne des tours** : des tours très courts peuvent indiquer une sur-segmentation
- **Écart de ratio** par locuteur entre les deux systèmes

### Seuil d'alerte

Un écart de ratio > 0.15 (15 points de pourcentage) pour un même locuteur signale un désaccord fort sur l'attribution de parole.

### Sortie

```json
{
  "system_A": {
    "nb_turns": 42,
    "nb_speakers": 2,
    "speaker_ratio": {"courtier": 0.62, "client": 0.38},
    "avg_turn_duration": 18.5
  },
  "system_B": {
    "nb_turns": 38,
    "nb_speakers": 2,
    "speaker_ratio": {"courtier": 0.44, "client": 0.56},
    "avg_turn_duration": 20.3
  },
  "speaker_ratio_diff": {"courtier": 0.18, "client": 0.18}
}
```

### Pertinence fraude

Dans un contexte de détection de fraude, savoir **qui a dit quoi** est critique. Une mauvaise attribution de locuteur peut inverser le sens d'une phrase incriminante.

---

## Méthode 6 — Détection d'hallucinations (WhisperX)

### Principe

Whisper (et WhisperX par extension) est connu pour **halluciner** sur les passages silencieux ou peu audibles : il répète des phrases en boucle plutôt que de détecter le silence. Cette méthode détecte ces répétitions anormales.

### Technique

Comptage des **n-grams** (séquences de N mots consécutifs) dans chaque segment. Si un trigramme apparaît 3 fois ou plus dans un même segment, c'est probablement une hallucination.

### Exemple d'hallucination typique

```
"merci pour votre confiance merci pour votre confiance 
 merci pour votre confiance je vous souhaite"
```

### Ce que ça évalue

- Fiabilité de WhisperX sur les passages à faible signal audio
- Segments à exclure ou à traiter avec précaution
- Qualité globale de la transcription WhisperX

### Sortie

```json
{
  "start": 1523.0,
  "speaker": "client",
  "text": "merci pour votre confiance merci pour votre confiance ...",
  "repeated_ngrams": {
    "merci pour votre": 4,
    "pour votre confiance": 4
  }
}
```

### Note

Cette méthode est appliquée uniquement sur le système B (WhisperX) car AWS Transcribe gère différemment les silences (il les ignore plutôt que d'halluciner).

---

## Méthode 7 — Cohérence des entités nommées (NER)

### Principe

Les entités nommées (noms de personnes, montants, dates, organisations) sont extraites des deux transcriptions via **spaCy** et comparées. Un désaccord sur un montant ou un nom propre est une alerte critique en détection de fraude.

### Types d'entités détectées (modèle français)

| Label spaCy | Type d'entité | Exemple |
|---|---|---|
| `PER` | Personnes | "Jean Dupont" |
| `ORG` | Organisations | "BNP Paribas" |
| `LOC` | Lieux | "Paris" |
| `MONEY` | Montants | "50 000 euros" |
| `DATE` | Dates | "15 mars 2024" |
| `PERCENT` | Pourcentages | "3,5%" |

### Ce que ça évalue

- Accord sur les entités critiques (montants, noms)
- Entités présentes dans A mais manquantes dans B, et vice versa
- Taux d'accord par type d'entité

### Sortie

```json
{
  "MONEY": {
    "only_in_A": ["50 000 euros"],
    "only_in_B": ["cinquante mille euros"],
    "common": ["3,5%"],
    "agreement_rate": 0.5
  },
  "PER": {
    "only_in_A": [],
    "only_in_B": ["M. Dupont"],
    "common": ["Jean"],
    "agreement_rate": 0.67
  }
}
```

### Pertinence fraude

C'est la méthode la plus directement utile pour la détection de fraude : un montant mal transcrit ou un nom manquant peut invalider une analyse. Un faible taux d'accord sur `MONEY` ou `PER` doit déclencher une révision prioritaire.

---

## Méthode 8 — Coverage temporelle

### Principe

Mesure la proportion de la durée totale de l'audio effectivement couverte par les segments transcrits. Un système qui "manque" des passages (silences mal gérés, coupures) aura une couverture inférieure à 100%.

### Formule

```
Coverage = Σ(durée des segments) / durée totale de l'audio
```

### Ce que ça évalue

- Passages non transcrits (silences, chevauchements de parole, bruits)
- Différence de comportement sur les zones ambiguës
- Exhaustivité globale de chaque système

### Sortie

```json
{
  "system_A": {
    "covered_seconds": 3420.5,
    "total_seconds": 3600.0,
    "coverage_ratio": 0.95
  },
  "system_B": {
    "covered_seconds": 3540.2,
    "total_seconds": 3600.0,
    "coverage_ratio": 0.983
  }
}
```

### Interprétation

- Coverage A < Coverage B : AWS Transcribe laisse plus de silences non transcrits
- Coverage proche de 1.0 pour B mais avec hallucinations (méthode 6) : WhisperX remplit les silences par des hallucinations — les deux métriques sont complémentaires

---

## Synthèse et recommandations

### Tableau récapitulatif

| # | Méthode | Ground truth | Coût calcul | Pertinence fraude |
|---|---|---|---|---|
| 1 | LLM-as-judge | Non | Moyen (API) | Haute |
| 2 | Désaccord lexical | Non | Très faible | Moyenne |
| 3 | Perplexité | Non | Moyen (GPU) | Moyenne |
| 4 | Similarité sémantique | Non | Faible | Moyenne |
| 5 | Cohérence diarisation | Non | Très faible | Haute |
| 6 | Détection hallucinations | Non | Très faible | Haute |
| 7 | Entités nommées | Non | Faible | Très haute |
| 8 | Coverage temporelle | Non | Nul | Moyenne |

### Ordre d'exécution recommandé

```
1. Coverage temporelle        → élimine d'emblée le système qui manque trop de passages
2. Détection hallucinations   → signale les segments WhisperX non fiables
3. Cohérence diarisation      → valide l'attribution des locuteurs
4. Entités nommées            → identifie les désaccords critiques (montants, noms)
5. Désaccord lexical          → flag les segments à réviser
6. Similarité sémantique      → filtre les faux positifs du désaccord lexical
7. LLM-as-judge               → arbitre uniquement les segments encore ambigus
8. Perplexité                 → indicateur global de qualité linguistique
```

### Combinaison des signaux

Un segment est **critique** (révision humaine obligatoire) si au moins deux conditions sont réunies :
- Similarité lexicale < 0.6 (méthode 2)
- Similarité sémantique < 0.7 (méthode 4)
- Désaccord sur une entité financière (méthode 7)
- Hallucination détectée dans ce segment (méthode 6)
- Désaccord fort sur le locuteur (méthode 5, écart > 0.15)

---

## Dépendances

```bash
pip install anthropic transformers torch sentence-transformers spacy
python -m spacy download fr_core_news_sm
```

## Usage

```bash
python audio_transcription_eval.py transcription_aws.txt transcription_whisperx.txt [durée_en_secondes]
```

Le rapport est sauvegardé dans `eval_report.json`.
