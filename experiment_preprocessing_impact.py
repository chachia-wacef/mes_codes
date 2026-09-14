"""
Expérience : impact du preprocessing sur la qualité de transcription.

Pour chaque audio, compare 4 transcriptions :
  - WhisperX  sur audio brut    (wx_raw)
  - WhisperX  sur audio nettoyé (wx_clean)
  - AWS       sur audio brut    (aws_raw)
  - AWS       sur audio nettoyé (aws_clean)

Prérequis : avoir lancé les 4 transcriptions et sauvegardé les résultats
dans le format attendu :
  [00:00:35 -> 00:02:42] courtier : bla bla bla

Usage :
  python experiment_preprocessing_impact.py <audio.wav> \
      --wx-raw   wx_raw.txt \
      --wx-clean wx_clean.txt \
      --aws-raw  aws_raw.txt \
      --aws-clean aws_clean.txt \
      [--preprocess]   # lance le preprocessing si pas encore fait
"""

import os
import json
import argparse
from pathlib import Path

from audio_preprocessing import preprocess_audio
from audio_transcription_eval import (
    parse_transcription,
    align_segments,
    segment_disagreement,
    semantic_similarity,
    diarization_consistency,
    detect_hallucinations,
    compare_named_entities,
    compare_coverage,
    compare_perplexity_by_speaker,
)


# ---------------------------------------------------------------------------
# Comparaison entre deux transcriptions (wrapper allégé)
# ---------------------------------------------------------------------------

def compare_pair(
    label_a: str,
    label_b: str,
    file_a: str,
    file_b: str,
    audio_duration: float = None,
    use_perplexity: bool = False,
    use_ner: bool = True,
    use_semantic: bool = True,
) -> dict:
    """Compare deux transcriptions et retourne les métriques clés."""
    segs_a = parse_transcription(open(file_a, encoding="utf-8").read())
    segs_b = parse_transcription(open(file_b, encoding="utf-8").read())

    pairs = align_segments(segs_a, segs_b)
    if not pairs:
        return {"error": "Aucun segment aligné trouvé"}

    disagreements = [segment_disagreement(a, b) for a, b in pairs]
    flagged = [d for d in disagreements if d["needs_review"]]

    result = {
        "comparison": f"{label_a} vs {label_b}",
        "total_segments": len(pairs),
        "flagged_segments": len(flagged),
        "flagged_ratio": round(len(flagged) / len(pairs), 3),
        "avg_similarity": round(
            sum(d["similarity"] for d in disagreements) / len(disagreements), 3
        ),
    }

    if use_semantic:
        sem = semantic_similarity(segs_a, segs_b)
        result["avg_semantic_similarity"] = round(
            sum(s["semantic_similarity"] for s in sem) / len(sem), 3
        ) if sem else None

    if use_ner:
        ner = compare_named_entities(segs_a, segs_b)
        if ner:
            result["ner_agreement"] = {
                label: v["agreement_rate"] for label, v in ner.items()
            }

    result["diarization"] = diarization_consistency(segs_a, segs_b)
    result["hallucinations_A"] = len(detect_hallucinations(segs_a))
    result["hallucinations_B"] = len(detect_hallucinations(segs_b))
    result["coverage"] = compare_coverage(segs_a, segs_b, audio_duration)

    if use_perplexity:
        result["perplexity"] = compare_perplexity_by_speaker(segs_a, segs_b)

    return result


# ---------------------------------------------------------------------------
# Résumé synthétique des 4 comparaisons
# ---------------------------------------------------------------------------

def print_summary(results: dict) -> None:
    print("\n" + "=" * 65)
    print("RÉSUMÉ — IMPACT DU PREPROCESSING")
    print("=" * 65)

    headers = ["Comparaison", "Similarité moy.", "Segments flaggés", "Hallucinations A/B"]
    rows = []
    for key, r in results.items():
        if "error" in r:
            continue
        rows.append([
            r["comparison"],
            f"{r['avg_similarity']:.3f}",
            f"{r['flagged_segments']} ({r['flagged_ratio']:.0%})",
            f"{r['hallucinations_A']} / {r['hallucinations_B']}",
        ])

    col_widths = [max(len(h), max(len(row[i]) for row in rows)) for i, h in enumerate(headers)]
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in col_widths))
    for row in rows:
        print(fmt.format(*row))

    # Conclusions
    print("\nCONCLUSIONS :")

    wx = results.get("wx_raw_vs_clean", {})
    aws = results.get("aws_raw_vs_clean", {})

    if wx and "avg_similarity" in wx:
        impact_wx = wx["avg_similarity"]
        if impact_wx < 0.85:
            print(f"  • Preprocessing améliore WhisperX (similarité={impact_wx:.3f} → divergences notables)")
        else:
            print(f"  • Preprocessing peu d'impact sur WhisperX (similarité={impact_wx:.3f})")

    if aws and "avg_similarity" in aws:
        impact_aws = aws["avg_similarity"]
        if impact_aws < 0.85:
            print(f"  • Preprocessing améliore AWS (similarité={impact_aws:.3f} → divergences notables)")
        else:
            print(f"  • Preprocessing peu d'impact sur AWS (similarité={impact_aws:.3f})")

    best = results.get("wx_clean_vs_aws_clean", {})
    if best and "avg_similarity" in best:
        hall_wx = best.get("hallucinations_A", 0)
        hall_aws = best.get("hallucinations_B", 0)
        sem = best.get("avg_semantic_similarity")
        print(f"  • Après preprocessing : similarité WX vs AWS = {best['avg_similarity']:.3f}"
              + (f", sémantique = {sem:.3f}" if sem else ""))
        if hall_wx > hall_aws:
            print(f"  • WhisperX hallucine plus ({hall_wx} segments) qu'AWS ({hall_aws} segments)")
        elif hall_aws > hall_wx:
            print(f"  • AWS hallucine plus ({hall_aws} segments) que WhisperX ({hall_wx} segments)")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Expérience impact preprocessing sur transcription")
    parser.add_argument("audio", help="Fichier audio original (brut)")
    parser.add_argument("--wx-raw",    required=True, help="Transcription WhisperX  sur audio brut")
    parser.add_argument("--wx-clean",  required=True, help="Transcription WhisperX  sur audio nettoyé")
    parser.add_argument("--aws-raw",   required=True, help="Transcription AWS        sur audio brut")
    parser.add_argument("--aws-clean", required=True, help="Transcription AWS        sur audio nettoyé")
    parser.add_argument("--preprocess", action="store_true",
                        help="Lance le preprocessing de l'audio brut avant comparaison")
    parser.add_argument("--output-dir", default="preprocessed",
                        help="Dossier de sortie pour les fichiers nettoyés (défaut: preprocessed/)")
    parser.add_argument("--duration", type=float, default=None,
                        help="Durée totale de l'audio en secondes (optionnel)")
    parser.add_argument("--no-perplexity", action="store_true",
                        help="Désactive le calcul de perplexité (plus lent)")
    args = parser.parse_args()

    # Preprocessing optionnel
    if args.preprocess:
        print("Lancement du preprocessing...")
        prep_result = preprocess_audio(args.audio, args.output_dir)
        print(f"Fichiers produits : {list(prep_result['files'].values())}")
        print("\nRelancez le script sans --preprocess après avoir généré les transcriptions.")
        return

    # Vérifie que les 4 fichiers existent
    for label, path in [
        ("wx-raw",    args.wx_raw),
        ("wx-clean",  args.wx_clean),
        ("aws-raw",   args.aws_raw),
        ("aws-clean", args.aws_clean),
    ]:
        if not os.path.exists(path):
            print(f"Fichier manquant : {path} ({label})")
            return

    use_ppl = not args.no_perplexity

    print("Lancement des comparaisons...")
    results = {}

    print("\n[1/4] WhisperX  : brut vs nettoyé")
    results["wx_raw_vs_clean"] = compare_pair(
        "WX-raw", "WX-clean", args.wx_raw, args.wx_clean,
        args.duration, use_perplexity=use_ppl
    )

    print("\n[2/4] AWS       : brut vs nettoyé")
    results["aws_raw_vs_clean"] = compare_pair(
        "AWS-raw", "AWS-clean", args.aws_raw, args.aws_clean,
        args.duration, use_perplexity=use_ppl
    )

    print("\n[3/4] WhisperX vs AWS (audio brut)")
    results["wx_vs_aws_raw"] = compare_pair(
        "WX-raw", "AWS-raw", args.wx_raw, args.aws_raw,
        args.duration, use_perplexity=use_ppl
    )

    print("\n[4/4] WhisperX vs AWS (audio nettoyé)")
    results["wx_clean_vs_aws_clean"] = compare_pair(
        "WX-clean", "AWS-clean", args.wx_clean, args.aws_clean,
        args.duration, use_perplexity=use_ppl
    )

    print_summary(results)

    output_path = "experiment_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nRapport détaillé sauvegardé : {output_path}")


if __name__ == "__main__":
    main()
