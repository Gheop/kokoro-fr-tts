import re
from collections.abc import Iterator
from typing import Tuple

import numpy as np

# Mots français qu'espeak-ng traite comme anglais.
# On les remplace par des graphies phonétiques que le G2P français gère correctement.
# Layer 1 : corrections text-level pour les vrais mots FR (ex: "dos" → s final muet).
FRENCH_FIXES: dict[str, str] = {
    r"\bdos\b": "deau",
    r"\bpull\b": "pul",
}


def _fix_pronunciation(text: str) -> str:
    """Remplace les mots problématiques avant le passage au G2P."""
    for pattern, replacement in FRENCH_FIXES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


# Layer 2 : mapping IPA anglais → français pour les anglicismes (parking, football, etc.)
# Trié par longueur décroissante pour que les diphthongues soient traitées avant les voyelles.
EN_TO_FR: list[tuple[str, str]] = [
    # Diphthongues (avec tie) — avant les voyelles individuelles
    ("a^ɪ", "aj"),  # price → aille
    ("a^ʊ", "o"),  # mouth → o
    ("e^ɪ", "e"),  # face → é
    ("o^ʊ", "o"),  # goat → o
    ("ə^ʊ", "o"),  # goat variant → o
    ("ɔ^ɪ", "ɔj"),  # choice → oi
    # Voyelles
    ("ɒ", "ɔ"),  # lot → o ouvert
    ("ʊ", "u"),  # foot → ou
    ("ɪ", "i"),  # kit → i
    ("æ", "a"),  # trap → a
    ("ʌ", "a"),  # strut → a
    ("ɑ", "a"),  # bath → a
    ("ɜ", "ɛ"),  # nurse → è
    # Consonnes
    ("θ", "s"),  # thin → s
    ("ð", "z"),  # this → z
    ("ɹ", "ʁ"),  # English r → French r
    # Longueur
    ("ː", ""),  # supprime les marques de longueur
]

# Regex pour détecter les sections en anglais dans la sortie phonemizer.
# Format avec tie='^' : (^e^n)phonèmes(^f^r)
_EN_SWITCH_RE = re.compile(r"\(\^e\^n\)(.*?)\(\^f\^r\)")
# Variante sans tie (au cas où)
_EN_SWITCH_RE_NOTIE = re.compile(r"\(en\)(.*?)\(fr\)")


def _map_en_to_fr(phonemes: str) -> str:
    """Applique le mapping IPA anglais → français sur une section de phonèmes."""
    for old, new in EN_TO_FR:
        phonemes = phonemes.replace(old, new)
    return phonemes


def _fix_en_switches(ps: str) -> str:
    """Détecte et corrige les switches anglais dans la sortie phonemizer.

    espeak-ng bascule certains mots en anglais lors de la phonémisation française.
    Avec language_switch='keep-flags', ces sections sont marquées par (^e^n)...(^f^r).
    On remplace les phonèmes anglais par des approximations françaises.
    """
    # Normaliser les flags avec tie
    ps = _EN_SWITCH_RE.sub(lambda m: _map_en_to_fr(m.group(1)), ps)
    # Nettoyer d'éventuels flags sans tie
    ps = _EN_SWITCH_RE_NOTIE.sub(lambda m: _map_en_to_fr(m.group(1)), ps)
    return ps


class FrenchG2P:
    """G2P français avec détection et correction automatique des switches anglais.

    Drop-in replacement pour EspeakG2P. Utilise language_switch='keep-flags'
    pour préserver les marqueurs (en)...(fr), puis mappe les phonèmes anglais
    vers des phonèmes français.
    """

    def __init__(self) -> None:
        import phonemizer.backend

        self.backend = phonemizer.backend.EspeakBackend(
            language="fr-fr",
            preserve_punctuation=True,
            with_stress=True,
            tie="^",
            language_switch="keep-flags",
        )
        # Mêmes mappings e2m qu'EspeakG2P pour compatibilité Kokoro
        self.e2m = sorted(
            {
                "a^ɪ": "I",
                "a^ʊ": "W",
                "d^z": "ʣ",
                "d^ʒ": "ʤ",
                "e^ɪ": "A",
                "o^ʊ": "O",
                "ə^ʊ": "Q",
                "s^s": "S",
                "t^s": "ʦ",
                "t^ʃ": "ʧ",
                "ɔ^ɪ": "Y",
            }.items()
        )

    def __call__(self, text: str) -> Tuple[str, None]:
        # Angles to curly quotes (same as EspeakG2P)
        text = text.replace("«", chr(8220)).replace("»", chr(8221))
        # Parentheses to angles (protège les parenthèses du texte)
        text = text.replace("(", "«").replace(")", "»")
        ps = self.backend.phonemize([text])
        if not ps:
            return "", None
        ps = ps[0].strip()
        # Corriger les switches anglais AVANT le mapping e2m
        ps = _fix_en_switches(ps)
        # Appliquer les mappings e2m (diphthongues/affricates → tokens Kokoro)
        for old, new in self.e2m:
            ps = ps.replace(old, new)
        # Supprimer les ties restants et les tirets
        ps = ps.replace("^", "")
        ps = ps.replace("-", "")
        # Angles back to parentheses
        ps = ps.replace("«", "(").replace("»", ")")
        return ps, None


class KokoroEngine:
    """Moteur TTS basé sur Kokoro (français, voix ff_siwis)."""

    def __init__(self, voice: str = "ff_siwis", speed: float = 1.0):
        from kokoro import KPipeline

        self.pipeline = KPipeline(lang_code="f", repo_id="hexgrad/Kokoro-82M")
        self.pipeline.g2p = FrenchG2P()
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
