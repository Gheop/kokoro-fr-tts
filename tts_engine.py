import re
from collections.abc import Iterator
from typing import Tuple

import numpy as np

# Mots français qu'espeak-ng traite comme anglais.
# On les remplace par des graphies phonétiques que le G2P français gère correctement.
# Layer 1 : corrections text-level pour les vrais mots FR (ex: "dos" → s final muet).
FRENCH_FIXES: dict[str, str] = {
    # Mots français mal prononcés
    r"\bdos\b": "deau",
    r"\bpull\b": "pul",
    r"\bblockchains?\b": "bloktchène",
    # Sigles — prononciation lettre par lettre
    r"\bAPI\b": "a-pé-i",
    r"\bURL\b": "u-erre-elle",
    r"\bHTML\b": "ache-té-emme-elle",
    r"\bCSS\b": "cé-esse-esse",
    r"\bGPU\b": "gé-pé-u",
    r"\bCPU\b": "cé-pé-u",
    r"\bIA\b": "i-a",
    r"\bSQL\b": "esse-ku-elle",
    r"\bPDF\b": "pé-dé-effe",
    r"\bUSB\b": "u-esse-bé",
    # Anglicismes tech — graphie phonétique française
    r"\bemails?\b": "imèle",
    r"\bsoftware\b": "softwère",
    r"\bhardware\b": "ardwère",
    r"\bstartups?\b": "starteupe",
    r"\bclouds?\b": "claoude",
    r"\bfeedback\b": "fidbak",
    r"\bdeadlines?\b": "dèdlaille",
    r"\bbugs?\b": "beugue",
    r"\bfeatures?\b": "fitcheure",
    r"\btokens?\b": "tokène",
    r"\bstreaming\b": "strimingue",
    r"\bprompts?\b": "prompte",
    r"\bopen\s?source\b": "opène-source",
    r"\bmachine\s?learning\b": "machinn-leurnigne",
    r"\bdeep\s?learning\b": "dip-leurnigne",
}

# Noms propres anglais — case-sensitive pour éviter les faux positifs.
# espeak-ng les lit à la française (ex: "Gates" → /gat/, "Musk" → /mysk/).
PROPER_NAMES: dict[str, str] = {
    # Tech figures — full names (priorité)
    r"\bBill Gates\b": "Bil Guéïtse",
    r"\bElon Musk\b": "Ilone Mosk",
    r"\bSteve Jobs\b": "Stive Djobze",
    r"\bJeff Bezos\b": "Djef Bézosse",
    r"\bMark Zuckerberg\b": "Mark Zokeurbergue",
    r"\bSam Altman\b": "Sam Altmane",
    r"\bTim Cook\b": "Tim Kouk",
    r"\bJensen Huang\b": "Djensène Houang",
    r"\bSundar Pichai\b": "Soundar Pitchaï",
    r"\bLarry Page\b": "Lari Pèïdje",
    r"\bSergey Brin\b": "Sergueï Brine",
    r"\bSatya Nadella\b": "Satia Nadéla",
    r"\bLinus Torvalds\b": "Lineusse Torvalds",
    # Last names seuls (sans ambiguïté)
    r"\bGates\b": "Guéïtse",
    r"\bMusk\b": "Mosk",
    r"\bJobs\b": "Djobze",
    r"\bBezos\b": "Bézosse",
    r"\bZuckerberg\b": "Zokeurbergue",
    r"\bAltman\b": "Altmane",
    r"\bTorvalds\b": "Torvalds",
    # Entreprises tech
    r"\bGoogle\b": "Gougueule",
    r"\bApple\b": "Apeulle",
    r"\bMicrosoft\b": "Maïkrossofte",
    r"\bAmazon\b": "Amazone",
    r"\bOpenAI\b": "Opène-a-aille",
    r"\bSpaceX\b": "Spèïce-X",
    r"\bTesla\b": "Tèsla",
    r"\bNvidia\b": "Ènvidia",
}


def _fix_pronunciation(text: str) -> str:
    """Remplace les mots problématiques avant le passage au G2P."""
    # Noms propres d'abord (case-sensitive, full names avant last names)
    for pattern, replacement in PROPER_NAMES.items():
        text = re.sub(pattern, replacement, text)
    # Mots courants (case-insensitive)
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


# Approximate max tokens per segment to avoid Kokoro rushing long texts.
# Kokoro uses ~1 token per character on average for French.
_MAX_CHARS_PER_SEGMENT = 800  # ~200 tokens, conservative estimate

# Sentence-ending punctuation for splitting
_SENTENCE_END_RE = re.compile(r"(?<=[.!?;])\s+")


def _split_into_segments(
    text: str, max_chars: int = _MAX_CHARS_PER_SEGMENT
) -> list[str]:
    """Split text into segments of ~max_chars at sentence boundaries.

    Returns the original text as a single segment if it's short enough.
    """
    if len(text) <= max_chars:
        return [text]

    sentences = _SENTENCE_END_RE.split(text)
    segments: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)
        if current and current_len + sentence_len > max_chars:
            segments.append(" ".join(current))
            current = [sentence]
            current_len = sentence_len
        else:
            current.append(sentence)
            current_len += sentence_len

    if current:
        segments.append(" ".join(current))

    return segments


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

    def generate_stream(
        self,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
    ) -> Iterator[np.ndarray]:
        """Yield les chunks audio au fur et à mesure de la génération.

        Long texts are split into segments at sentence boundaries to avoid
        Kokoro rushing the output on large inputs.
        """
        text = _fix_pronunciation(text)
        voice = voice or self.voice
        speed = speed if speed is not None else self.speed
        for segment in _split_into_segments(text):
            for _gs, _ps, audio in self.pipeline(segment, voice=voice, speed=speed):
                if audio is not None:
                    yield np.asarray(audio, dtype=np.float32)
