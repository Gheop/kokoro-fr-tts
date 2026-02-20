from collections.abc import Iterator

import numpy as np
import sounddevice as sd


def play(audio: np.ndarray, sample_rate: int) -> None:
    """Joue l'audio sur les haut-parleurs."""
    if audio.size == 0:
        return
    # Normaliser pour éviter le clipping
    peak = np.max(np.abs(audio))
    if peak > 1.0:
        audio = audio / peak
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


def play_stream(chunks: Iterator[np.ndarray], sample_rate: int) -> list[np.ndarray]:
    """Joue les chunks audio en streaming et renvoie la liste pour concaténation.

    Pas de normalisation per-chunk — le modèle produit du signal cohérent
    en [-1, 1]. Normaliser par chunk provoque des sauts de volume.
    """
    played: list[np.ndarray] = []
    with sd.OutputStream(samplerate=sample_rate, channels=1, dtype="float32") as stream:
        for chunk in chunks:
            chunk = np.asarray(chunk, dtype=np.float32)
            played.append(chunk)
            stream.write(chunk.reshape(-1, 1))
    return played
