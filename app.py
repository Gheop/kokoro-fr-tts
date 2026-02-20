import logging
import warnings

# Supprimer les warnings bruit des dépendances
warnings.filterwarnings("ignore", message=".*dropout option adds dropout.*")
warnings.filterwarnings("ignore", message=".*weight_norm.*is deprecated.*")
warnings.filterwarnings("ignore", message=".*Trying to convert audio.*")
logging.getLogger("phonemizer").setLevel(logging.ERROR)

import gradio as gr  # noqa: E402
import numpy as np  # noqa: E402

from audio_player import play_stream  # noqa: E402
from tts_engine import KokoroEngine  # noqa: E402

_engine: KokoroEngine | None = None


def get_engine() -> KokoroEngine:
    global _engine
    if _engine is None:
        _engine = KokoroEngine()
    return _engine


def synthesize(text: str) -> tuple[int, np.ndarray]:
    """Génère l'audio en streaming (HP) et renvoie l'audio complet pour Gradio."""
    engine = get_engine()
    sr = engine.sample_rate
    chunks = play_stream(engine.generate_stream(text), sr)
    if not chunks:
        return sr, np.array([], dtype=np.float32)
    return sr, np.concatenate(chunks)


demo = gr.Interface(
    fn=synthesize,
    inputs=gr.Textbox(
        label="Texte",
        placeholder="Entrez le texte en français...",
        lines=4,
    ),
    outputs=gr.Audio(label="Audio généré", type="numpy"),
    title="Text-to-Speech Français",
    description="Synthèse vocale en français avec Kokoro.",
    api_name="predict",
    flagging_mode="never",
)

if __name__ == "__main__":
    demo.launch()
