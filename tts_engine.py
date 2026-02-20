import re
from collections.abc import Iterator

import numpy as np

# Mots français qu'espeak-ng traite comme anglais.
# On les remplace par des graphies phonétiques que le G2P français gère correctement.
FRENCH_FIXES: dict[str, str] = {
    r"\bdos\b": "deau",
    r"\bpull\b": "pul",
}


def _fix_pronunciation(text: str) -> str:
    """Remplace les mots problématiques avant le passage au G2P."""
    for pattern, replacement in FRENCH_FIXES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


class KokoroEngine:
    """Moteur TTS basé sur Kokoro (français, voix ff_siwis)."""

    def __init__(self, voice: str = "ff_siwis", speed: float = 1.0):
        from kokoro import KPipeline

        self.pipeline = KPipeline(lang_code="f", repo_id="hexgrad/Kokoro-82M")
        self.voice = voice
        self.speed = speed
        self.sample_rate = 24_000

    def generate(self, text: str) -> tuple[np.ndarray, int]:
        text = _fix_pronunciation(text)
        chunks = []
        for _gs, _ps, audio in self.pipeline(text, voice=self.voice, speed=self.speed):
            if audio is not None:
                chunks.append(audio)
        if not chunks:
            return np.array([], dtype=np.float32), self.sample_rate
        return np.concatenate(chunks), self.sample_rate

    def generate_stream(self, text: str) -> Iterator[np.ndarray]:
        """Yield les chunks audio au fur et à mesure de la génération."""
        text = _fix_pronunciation(text)
        for _gs, _ps, audio in self.pipeline(text, voice=self.voice, speed=self.speed):
            if audio is not None:
                yield np.asarray(audio, dtype=np.float32)
