import re
import json
import torch
import difflib
import anthropic
import spacy
from collections import Counter
from dataclasses import dataclass
from transformers import GPT2LMHeadModel, GPT2TokenizerFast
from sentence_transformers import SentenceTransformer, util


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Segment:
    start: float  # en secondes
    end: float
    speaker: str
    text: str


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def to_seconds(t: str) -> float:
    h, m, s = map(int, t.split(':'))
    return h * 3600 + m * 60 + s


def parse_transcription(text: str) -> list[Segment]:
    pattern = r'\[(\d{2}:\d{2}:\d{2}) -> (\d{2}:\d{2}:\d{2})\]\s+(\w+)\s*:\s*(.+)'
    segments = []
    for line in text.strip().split('\n'):
        m = re.match(pattern, line)
        if m:
            segments.append(Segment(
                start=to_seconds(m.group(1)),
                end=to_seconds(m.group(2)),
                speaker=m.group(3).strip(),
                text=m.group(4).strip()
            ))
    return segments


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

def align_segments(
    segs_a: list[Segment],
    segs_b: list[Segment],
    min_overlap: float = 0.5
) -> list[tuple[Segment, Segment]]:
    """Retourne les paires de segments qui se chevauchent suffisamment."""
    pairs = []
    for a in segs_a:
        for b in segs_b:
            overlap = min(a.end, b.end) - max(a.start, b.start)
            duration_a = a.end - a.start
            if duration_a > 0 and overlap / duration_a >= min_overlap:
                pairs.append((a, b))
                break
    return pairs


# ---------------------------------------------------------------------------
# Approche 1 : LLM-as-judge
# ---------------------------------------------------------------------------

def llm_judge_segment(seg_a: Segment, seg_b: Segment) -> dict:
    client = anthropic.Anthropic()

    prompt = f"""Tu compares deux transcriptions d'un même passage audio.

Passage [{seg_a.start:.0f}s -> {seg_a.end:.0f}s] — locuteur: {seg_a.speaker}

Transcription A: {seg_a.text}
Transcription B: {seg_b.text}

Contexte: appel entre courtier et client, domaine financier.

Laquelle est plus correcte ? Réponds uniquement en JSON valide:
{{"winner": "A" ou "B" ou "égalité", "confidence": 0.0-1.0, "raison": "..."}}"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"winner": "inconnu", "confidence": 0.0, "raison": raw}


def judge_full_transcription(
    segs_a: list[Segment],
    segs_b: list[Segment]
) -> list[dict]:
    pairs = align_segments(segs_a, segs_b)
    results = []
    for a, b in pairs:
        result = llm_judge_segment(a, b)
        result["start"] = a.start
        result["speaker"] = a.speaker
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Approche 2 : Taux de désaccord par segment
# ---------------------------------------------------------------------------

def segment_disagreement(seg_a: Segment, seg_b: Segment) -> dict:
    words_a = seg_a.text.lower().split()
    words_b = seg_b.text.lower().split()

    matcher = difflib.SequenceMatcher(None, words_a, words_b)
    ratio = matcher.ratio()

    diff = list(difflib.ndiff(words_a, words_b))
    only_a = [w[2:] for w in diff if w.startswith('- ')]
    only_b = [w[2:] for w in diff if w.startswith('+ ')]

    return {
        "start": seg_a.start,
        "end": seg_a.end,
        "speaker": seg_a.speaker,
        "text_a": seg_a.text,
        "text_b": seg_b.text,
        "similarity": round(ratio, 3),
        "only_in_A": only_a,
        "only_in_B": only_b,
        "needs_review": ratio < 0.6,
    }


# ---------------------------------------------------------------------------
# Approche 3 : Perplexité par locuteur
# ---------------------------------------------------------------------------

def load_perplexity_model(model_name: str = "asi/gpt-fr-cased-small"):
    # asi/gpt-fr-cased-small : GPT-2 entraîné sur du texte français
    model = GPT2LMHeadModel.from_pretrained(model_name)
    tokenizer = GPT2TokenizerFast.from_pretrained(model_name)
    model.eval()
    return model, tokenizer


def perplexity(text: str, model, tokenizer) -> float:
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        loss = model(**inputs, labels=inputs["input_ids"]).loss
    return torch.exp(loss).item()


def compare_perplexity_by_speaker(
    segs_a: list[Segment],
    segs_b: list[Segment],
    model=None,
    tokenizer=None
) -> dict:
    if model is None or tokenizer is None:
        model, tokenizer = load_perplexity_model()

    speakers = set(s.speaker for s in segs_a)
    results = {}
    for speaker in speakers:
        text_a = " ".join(s.text for s in segs_a if s.speaker == speaker)
        text_b = " ".join(s.text for s in segs_b if s.speaker == speaker)
        ppl_a = perplexity(text_a, model, tokenizer)
        ppl_b = perplexity(text_b, model, tokenizer)
        results[speaker] = {
            "perplexity_A": round(ppl_a, 2),
            "perplexity_B": round(ppl_b, 2),
            "better": "A" if ppl_a < ppl_b else "B",
        }
        print(f"{speaker:12s} — A: {ppl_a:.1f} | B: {ppl_b:.1f} → {'A' if ppl_a < ppl_b else 'B'} meilleur")
    return results


# ---------------------------------------------------------------------------
# Approche 4 : Similarité sémantique (embeddings)
# ---------------------------------------------------------------------------

def semantic_similarity(
    segs_a: list[Segment],
    segs_b: list[Segment],
    model_name: str = "dangvantuan/sentence-camembert-large"
) -> list[dict]:
    """
    Compare le sens des segments alignés via embeddings.
    Score proche de 1.0 = même sens malgré des mots différents.
    """
    embed_model = SentenceTransformer(model_name)
    pairs = align_segments(segs_a, segs_b)
    results = []
    for a, b in pairs:
        emb_a = embed_model.encode(a.text, convert_to_tensor=True)
        emb_b = embed_model.encode(b.text, convert_to_tensor=True)
        score = float(util.cos_sim(emb_a, emb_b))
        results.append({
            "start": a.start,
            "speaker": a.speaker,
            "text_a": a.text,
            "text_b": b.text,
            "semantic_similarity": round(score, 3),
            "same_meaning": score >= 0.85,
        })
    return results


# ---------------------------------------------------------------------------
# Approche 5 : Cohérence de la diarisation
# ---------------------------------------------------------------------------

def diarization_consistency(
    segs_a: list[Segment],
    segs_b: list[Segment]
) -> dict:
    """
    Compare les patterns de prise de parole entre les deux systèmes.
    """
    def stats(segs):
        speakers = [s.speaker for s in segs]
        durations = {spk: 0.0 for spk in set(speakers)}
        for s in segs:
            durations[s.speaker] += s.end - s.start
        total = sum(durations.values()) or 1
        return {
            "nb_turns": len(segs),
            "nb_speakers": len(set(speakers)),
            "speaker_ratio": {k: round(v / total, 3) for k, v in durations.items()},
            "avg_turn_duration": round(total / len(segs), 2) if segs else 0,
        }

    stats_a = stats(segs_a)
    stats_b = stats(segs_b)

    # écart de ratio par locuteur commun
    speakers = set(stats_a["speaker_ratio"]) & set(stats_b["speaker_ratio"])
    ratio_diff = {
        spk: round(abs(stats_a["speaker_ratio"].get(spk, 0) - stats_b["speaker_ratio"].get(spk, 0)), 3)
        for spk in speakers
    }

    print(f"\nDiarisation — tours A: {stats_a['nb_turns']} | tours B: {stats_b['nb_turns']}")
    for spk, diff in ratio_diff.items():
        flag = " ⚠ désaccord fort" if diff > 0.15 else ""
        print(f"  {spk}: écart ratio = {diff:.3f}{flag}")

    return {
        "system_A": stats_a,
        "system_B": stats_b,
        "speaker_ratio_diff": ratio_diff,
    }


# ---------------------------------------------------------------------------
# Approche 6 : Détection d'hallucinations WhisperX
# ---------------------------------------------------------------------------

def detect_hallucinations(segs: list[Segment], ngram_size: int = 3, threshold: int = 3) -> list[dict]:
    """
    Détecte les répétitions anormales de n-grams dans les segments.
    Whisper hallucine souvent en répétant des phrases sur les silences.
    """
    flagged = []
    for seg in segs:
        words = seg.text.lower().split()
        if len(words) < ngram_size:
            continue
        ngrams = [tuple(words[i:i + ngram_size]) for i in range(len(words) - ngram_size + 1)]
        counts = Counter(ngrams)
        repeated = {" ".join(k): v for k, v in counts.items() if v >= threshold}
        if repeated:
            flagged.append({
                "start": seg.start,
                "speaker": seg.speaker,
                "text": seg.text,
                "repeated_ngrams": repeated,
            })
    return flagged


# ---------------------------------------------------------------------------
# Approche 7 : Cohérence des entités nommées (noms, montants, dates)
# ---------------------------------------------------------------------------

def compare_named_entities(
    segs_a: list[Segment],
    segs_b: list[Segment],
    spacy_model: str = "fr_core_news_sm"
) -> dict:
    """
    Compare les entités nommées extraites par les deux transcriptions.
    Les désaccords sur montants/noms/dates sont critiques en détection de fraude.
    """
    try:
        nlp = spacy.load(spacy_model)
    except OSError:
        print(f"Modèle spaCy '{spacy_model}' non trouvé. Installez-le avec : python -m spacy download {spacy_model}")
        return {}

    def extract_entities(segs):
        full_text = " ".join(s.text for s in segs)
        doc = nlp(full_text)
        entities = {}
        for ent in doc.ents:
            entities.setdefault(ent.label_, []).append(ent.text)
        return entities

    ents_a = extract_entities(segs_a)
    ents_b = extract_entities(segs_b)

    all_labels = set(ents_a) | set(ents_b)
    comparison = {}
    for label in all_labels:
        set_a = set(ents_a.get(label, []))
        set_b = set(ents_b.get(label, []))
        comparison[label] = {
            "only_in_A": list(set_a - set_b),
            "only_in_B": list(set_b - set_a),
            "common": list(set_a & set_b),
            "agreement_rate": round(len(set_a & set_b) / len(set_a | set_b), 3) if set_a | set_b else 1.0,
        }
        if comparison[label]["only_in_A"] or comparison[label]["only_in_B"]:
            print(f"  [{label}] désaccord — seulement A: {comparison[label]['only_in_A']} | seulement B: {comparison[label]['only_in_B']}")

    return comparison


# ---------------------------------------------------------------------------
# Approche 8 : Coverage temporelle
# ---------------------------------------------------------------------------

def temporal_coverage(segs: list[Segment], audio_duration: float = None) -> dict:
    """
    Mesure la proportion de l'audio couverte par les segments transcrits.
    Une faible couverture indique des coupures ou silences ratés.
    """
    if not segs:
        return {"covered_seconds": 0, "coverage_ratio": 0}

    covered = sum(s.end - s.start for s in segs)
    total = audio_duration or segs[-1].end

    return {
        "covered_seconds": round(covered, 2),
        "total_seconds": round(total, 2),
        "coverage_ratio": round(covered / total, 3) if total > 0 else 0,
    }


def compare_coverage(
    segs_a: list[Segment],
    segs_b: list[Segment],
    audio_duration: float = None
) -> dict:
    cov_a = temporal_coverage(segs_a, audio_duration)
    cov_b = temporal_coverage(segs_b, audio_duration)
    print(f"\nCoverage — A: {cov_a['coverage_ratio']:.1%} | B: {cov_b['coverage_ratio']:.1%}")
    return {"system_A": cov_a, "system_B": cov_b}


# ---------------------------------------------------------------------------
# Pipeline complet
# ---------------------------------------------------------------------------

def evaluate(
    file_a: str,
    file_b: str,
    audio_duration: float = None,
    use_llm: bool = True,
    use_perplexity: bool = True,
    use_semantic: bool = True,
    use_ner: bool = True,
    use_hallucination: bool = True,
    use_diarization: bool = True,
    use_coverage: bool = True,
) -> dict:
    """
    file_a : chemin vers la transcription système A (ex: AWS Transcribe)
    file_b : chemin vers la transcription système B (ex: WhisperX)
    audio_duration : durée totale de l'audio en secondes (optionnel)
    """
    segs_a = parse_transcription(open(file_a, encoding="utf-8").read())
    segs_b = parse_transcription(open(file_b, encoding="utf-8").read())

    pairs = align_segments(segs_a, segs_b)
    print(f"{len(pairs)} segments alignés sur {len(segs_a)} (A) / {len(segs_b)} (B)")

    report = {"total_pairs": len(pairs)}

    # Désaccords lexicaux
    disagreements = [segment_disagreement(a, b) for a, b in pairs]
    flagged = [d for d in disagreements if d["needs_review"]]
    print(f"{len(flagged)} segments à réviser manuellement (similarité < 0.6)")
    report["disagreements"] = disagreements
    report["flagged_for_review"] = flagged

    # LLM sur les segments divergents uniquement
    if use_llm and flagged:
        print("Lancement du LLM-as-judge sur les segments divergents...")
        flagged_pairs = [(a, b) for a, b in pairs if segment_disagreement(a, b)["needs_review"]]
        llm_results = []
        for a, b in flagged_pairs:
            judgment = llm_judge_segment(a, b)
            judgment["start"] = a.start
            judgment["speaker"] = a.speaker
            llm_results.append(judgment)
        votes = [r["winner"] for r in llm_results]
        print(f"LLM-as-judge : A gagne {votes.count('A')}x | B gagne {votes.count('B')}x")
        report["llm_judgments"] = llm_results

    # Perplexité
    if use_perplexity:
        print("\nCalcul de la perplexité par locuteur...")
        report["perplexity_by_speaker"] = compare_perplexity_by_speaker(segs_a, segs_b)

    # Similarité sémantique
    if use_semantic:
        print("\nCalcul de la similarité sémantique...")
        report["semantic_similarity"] = semantic_similarity(segs_a, segs_b)

    # Diarisation
    if use_diarization:
        print("\nAnalyse de la cohérence de diarisation...")
        report["diarization"] = diarization_consistency(segs_a, segs_b)

    # Hallucinations (sur B = WhisperX par défaut)
    if use_hallucination:
        print("\nDétection des hallucinations (système B / WhisperX)...")
        report["hallucinations_B"] = detect_hallucinations(segs_b)
        print(f"  {len(report['hallucinations_B'])} segments suspects détectés")

    # Entités nommées
    if use_ner:
        print("\nComparaison des entités nommées...")
        report["named_entities"] = compare_named_entities(segs_a, segs_b)

    # Coverage temporelle
    if use_coverage:
        report["coverage"] = compare_coverage(segs_a, segs_b, audio_duration)

    return report


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python audio_transcription_eval.py <fichier_A> <fichier_B> [durée_audio_secondes]")
        print("  fichier_A : transcription AWS Transcribe")
        print("  fichier_B : transcription WhisperX")
        sys.exit(1)

    duration = float(sys.argv[3]) if len(sys.argv) > 3 else None

    report = evaluate(
        file_a=sys.argv[1],
        file_b=sys.argv[2],
        audio_duration=duration,
        use_llm=True,
        use_perplexity=True,
        use_semantic=True,
        use_ner=True,
        use_hallucination=True,
        use_diarization=True,
        use_coverage=True,
    )

    output_path = "eval_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nRapport sauvegardé dans {output_path}")
