import numpy as np
import soundfile as sf


def analyze_audio_channels(filepath, window_ms=500, silence_threshold=0.01, overlap_threshold=0.3, correlation_threshold=0.98):
    """
    Détecte si un fichier audio est mono, stéréo dupliqué (mono déguisé),
    ou stéréo avec locuteurs séparés par canal.
    """
    data, samplerate = sf.read(filepath, always_2d=True)
    n_channels = data.shape[1]

    if n_channels == 1:
        return {"type": "mono", "n_channels": 1}

    left, right = data[:, 0], data[:, 1]

    # 1. Les deux canaux sont-ils quasi identiques (mono dupliqué) ?
    correlation = np.corrcoef(left, right)[0, 1]
    if correlation > correlation_threshold:
        return {"type": "stereo_duplicated", "n_channels": 2, "correlation": round(float(correlation), 3)}

    # 2. Activité vocale par fenêtre pour chaque canal (RMS)
    window = int(samplerate * window_ms / 1000)
    n_windows = len(left) // window

    left_active = np.zeros(n_windows, dtype=bool)
    right_active = np.zeros(n_windows, dtype=bool)

    for i in range(n_windows):
        seg_left = left[i * window:(i + 1) * window]
        seg_right = right[i * window:(i + 1) * window]
        left_active[i] = np.sqrt(np.mean(seg_left ** 2)) > silence_threshold
        right_active[i] = np.sqrt(np.mean(seg_right ** 2)) > silence_threshold

    union = left_active | right_active
    both = left_active & right_active
    overlap_ratio = both.sum() / max(1, union.sum())

    result = {
        "type": None,
        "n_channels": 2,
        "correlation": round(float(correlation), 3),
        "overlap_ratio": round(float(overlap_ratio), 3),
        "left_activity_ratio": round(float(left_active.mean()), 3),
        "right_activity_ratio": round(float(right_active.mean()), 3),
    }

    if overlap_ratio < overlap_threshold:
        result["type"] = "stereo_separated_speakers"
    else:
        result["type"] = "stereo_mixed"

    return result


if __name__ == "__main__":
    import sys

    for path in sys.argv[1:]:
        print(path, "->", analyze_audio_channels(path))
