import os
import torch
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from pathlib import Path
from scipy.signal import butter, sosfilt


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_audio(path: str) -> tuple[np.ndarray, int]:
    """Retourne (signal, sample_rate). Signal shape: (samples,) mono ou (samples, 2) stéréo."""
    signal, sr = sf.read(path, always_2d=False)
    return signal, sr


def save_audio(signal: np.ndarray, sr: int, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, signal, sr)


def is_stereo(signal: np.ndarray) -> bool:
    return signal.ndim == 2 and signal.shape[1] == 2


# ---------------------------------------------------------------------------
# Étape 1 : Séparation des canaux (stéréo uniquement)
# ---------------------------------------------------------------------------

def split_channels(signal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Sépare les deux canaux d'un signal stéréo.
    Dans un enregistrement d'appel, typiquement :
      - canal gauche (index 0) : courtier
      - canal droit  (index 1) : client
    """
    return signal[:, 0], signal[:, 1]


# ---------------------------------------------------------------------------
# Étape 2 : Normalisation du volume (norme EBU R128)
# ---------------------------------------------------------------------------

def normalize_loudness(signal: np.ndarray, sr: int, target_lufs: float = -23.0) -> np.ndarray:
    """
    Normalise le volume vers une cible en LUFS (norme broadcast EBU R128).
    -23 LUFS est le standard européen pour la parole.
    Évite les déséquilibres entre courtier (proche du micro) et client (téléphone).
    """
    meter = pyln.Meter(sr)
    loudness = meter.integrated_loudness(signal)
    if np.isinf(loudness):  # segment trop court ou silencieux
        return signal
    return pyln.normalize.loudness(signal, loudness, target_lufs)


# ---------------------------------------------------------------------------
# Étape 3 : Filtre passe-haut (supprime les basses fréquences non vocales)
# ---------------------------------------------------------------------------

def highpass_filter(signal: np.ndarray, sr: int, cutoff_hz: float = 80.0) -> np.ndarray:
    """
    Supprime les fréquences sous cutoff_hz (bruit de fond basse fréquence,
    vibrations, souffle de climatisation).
    La voix humaine commence à ~80-100 Hz.
    """
    sos = butter(N=4, Wn=cutoff_hz, btype='highpass', fs=sr, output='sos')
    return sosfilt(sos, signal).astype(np.float32)


# ---------------------------------------------------------------------------
# Étape 4 : Voice Activity Detection (supprime les silences longs)
# ---------------------------------------------------------------------------

def load_vad_model():
    """Charge le modèle Silero VAD (téléchargement automatique au premier appel)."""
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        force_reload=False,
        trust_repo=True
    )
    return model, utils


def apply_vad(
    signal: np.ndarray,
    sr: int,
    vad_model,
    vad_utils,
    min_silence_ms: int = 500,
    padding_ms: int = 200,
) -> tuple[np.ndarray, list[dict]]:
    """
    Détecte les segments de parole et supprime les silences.
    Retourne le signal nettoyé et la liste des segments vocaux avec leurs timestamps.

    min_silence_ms : durée minimale d'un silence pour qu'il soit supprimé
    padding_ms     : marge ajoutée avant/après chaque segment vocal
    """
    get_speech_timestamps, _, read_audio, *_ = vad_utils

    # Silero attend du float32 à 16kHz
    if sr != 16000:
        import librosa
        signal_16k = librosa.resample(signal, orig_sr=sr, target_sr=16000)
    else:
        signal_16k = signal.copy()

    signal_tensor = torch.FloatTensor(signal_16k)

    timestamps = get_speech_timestamps(
        signal_tensor,
        vad_model,
        sampling_rate=16000,
        min_silence_duration_ms=min_silence_ms,
        speech_pad_ms=padding_ms,
    )

    # Convertit les timestamps de 16kHz vers le sr original
    ratio = sr / 16000
    segments = []
    chunks = []
    for ts in timestamps:
        start = int(ts['start'] * ratio)
        end = int(ts['end'] * ratio)
        chunks.append(signal[start:end])
        segments.append({
            "start_s": round(ts['start'] / 16000, 3),
            "end_s": round(ts['end'] / 16000, 3),
            "duration_s": round((ts['end'] - ts['start']) / 16000, 3),
        })

    cleaned = np.concatenate(chunks) if chunks else signal
    return cleaned, segments


# ---------------------------------------------------------------------------
# Pipeline complet sur un fichier
# ---------------------------------------------------------------------------

def preprocess_audio(
    input_path: str,
    output_dir: str,
    apply_vad: bool = True,
    target_lufs: float = -23.0,
    highpass_hz: float = 80.0,
) -> dict:
    """
    Applique le pipeline complet de preprocessing sur un fichier audio.

    Pour un fichier stéréo, produit :
      - <nom>_channel_L_clean.wav  (courtier)
      - <nom>_channel_R_clean.wav  (client)
      - <nom>_merged_clean.wav     (fusion des deux canaux nettoyés)

    Pour un fichier mono, produit :
      - <nom>_clean.wav

    Retourne un dict avec les chemins des fichiers produits et les stats VAD.
    """
    signal, sr = load_audio(input_path)
    stem = Path(input_path).stem
    results = {"input": input_path, "sample_rate": sr, "files": {}}

    print(f"\n{'='*60}")
    print(f"Fichier : {Path(input_path).name}")
    print(f"Durée   : {len(signal) / sr / 60:.1f} min | SR: {sr} Hz | {'Stéréo' if is_stereo(signal) else 'Mono'}")

    if is_stereo(signal):
        ch_l, ch_r = split_channels(signal)
        print("Canaux séparés → traitement indépendant")

        channels = {"channel_L": ch_l, "channel_R": ch_r}
        cleaned_channels = {}

        for name, ch in channels.items():
            print(f"\n  Traitement {name}...")
            ch = normalize_loudness(ch, sr, target_lufs)
            ch = highpass_filter(ch, sr, highpass_hz)

            if apply_vad:
                vad_model, vad_utils = load_vad_model()
                ch, segments = apply_vad(ch, sr, vad_model, vad_utils)
                total_speech = sum(s["duration_s"] for s in segments)
                print(f"  VAD : {len(segments)} segments vocaux | {total_speech/60:.1f} min de parole conservés")
                results[f"vad_{name}"] = segments

            out_path = os.path.join(output_dir, f"{stem}_{name}_clean.wav")
            save_audio(ch, sr, out_path)
            cleaned_channels[name] = ch
            results["files"][name] = out_path
            print(f"  Sauvegardé : {out_path}")

        # Fusion stéréo des deux canaux nettoyés
        merged = np.stack([cleaned_channels["channel_L"], cleaned_channels["channel_R"]], axis=1)
        merged_path = os.path.join(output_dir, f"{stem}_merged_clean.wav")
        save_audio(merged, sr, merged_path)
        results["files"]["merged"] = merged_path
        print(f"\n  Fusion stéréo sauvegardée : {merged_path}")

    else:
        print("Fichier mono → traitement unique")
        signal = normalize_loudness(signal, sr, target_lufs)
        signal = highpass_filter(signal, sr, highpass_hz)

        if apply_vad:
            vad_model, vad_utils = load_vad_model()
            signal, segments = apply_vad(signal, sr, vad_model, vad_utils)
            total_speech = sum(s["duration_s"] for s in segments)
            print(f"VAD : {len(segments)} segments vocaux | {total_speech/60:.1f} min conservés")
            results["vad"] = segments

        out_path = os.path.join(output_dir, f"{stem}_clean.wav")
        save_audio(signal, sr, out_path)
        results["files"]["mono"] = out_path
        print(f"Sauvegardé : {out_path}")

    return results


# ---------------------------------------------------------------------------
# Traitement batch d'un dossier
# ---------------------------------------------------------------------------

def preprocess_folder(
    input_dir: str,
    output_dir: str,
    extensions: tuple = (".mp3", ".wav", ".m4a", ".ogg"),
    apply_vad: bool = True,
) -> list[dict]:
    """Applique le preprocessing sur tous les fichiers audio d'un dossier."""
    files = [
        f for f in Path(input_dir).iterdir()
        if f.suffix.lower() in extensions
    ]
    print(f"{len(files)} fichiers audio trouvés dans {input_dir}")

    all_results = []
    for f in sorted(files):
        result = preprocess_audio(str(f), output_dir, apply_vad=apply_vad)
        all_results.append(result)

    return all_results


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 3:
        print("Usage:")
        print("  Fichier unique : python audio_preprocessing.py <fichier_audio> <dossier_sortie>")
        print("  Dossier entier : python audio_preprocessing.py <dossier_entree> <dossier_sortie> --batch")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    batch_mode = "--batch" in sys.argv

    if batch_mode:
        results = preprocess_folder(input_path, output_dir)
    else:
        results = [preprocess_audio(input_path, output_dir)]

    report_path = os.path.join(output_dir, "preprocessing_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nRapport sauvegardé : {report_path}")
