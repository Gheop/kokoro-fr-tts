import asyncio
import logging
import pathlib
import struct
import warnings

# Supprimer les warnings bruit des dépendances
warnings.filterwarnings("ignore", message=".*dropout option adds dropout.*")
warnings.filterwarnings("ignore", message=".*weight_norm.*is deprecated.*")
warnings.filterwarnings("ignore", message=".*Trying to convert audio.*")
logging.getLogger("phonemizer").setLevel(logging.ERROR)

import gradio as gr  # noqa: E402
import numpy as np  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import HTMLResponse, StreamingResponse  # noqa: E402

from tts_engine import KokoroEngine  # noqa: E402

try:
    import sounddevice as sd

    sd.query_devices(kind="output")
    _has_audio = True
except Exception:
    _has_audio = False

if _has_audio:
    from audio_player import play_stream  # noqa: E402

_engine: KokoroEngine | None = None


def get_engine() -> KokoroEngine:
    global _engine
    if _engine is None:
        _engine = KokoroEngine()
    return _engine


def synthesize(text: str) -> tuple[int, np.ndarray]:
    """Génère l'audio et renvoie l'audio complet pour Gradio. Joue sur les HP si disponible."""
    engine = get_engine()
    sr = engine.sample_rate
    if _has_audio:
        chunks = play_stream(engine.generate_stream(text), sr)
    else:
        chunks = list(engine.generate_stream(text))
    if not chunks:
        return sr, np.array([], dtype=np.float32)
    return sr, np.concatenate(chunks)


# --- Gradio interface ---

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

# --- FastAPI custom routes (registered BEFORE Gradio's catch-all) ---

app = FastAPI()

_engine_lock = asyncio.Lock()
_HERE = pathlib.Path(__file__).parent


def _wav_header(sample_rate: int = 24000, bits: int = 16, channels: int = 1) -> bytes:
    """Header WAV avec taille inconnue (streaming)."""
    block_align = channels * bits // 8
    byte_rate = sample_rate * block_align
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        0xFFFFFFFF,  # taille totale inconnue
        b"WAVE",
        b"fmt ",
        16,  # PCM
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits,
        b"data",
        0xFFFFFFFF,  # taille data inconnue
    )


@app.get("/test", response_class=HTMLResponse)
async def test_page():
    return (_HERE / "test.html").read_text()


@app.post("/v1/audio/speech")
async def speech(request: Request):
    body = await request.json()
    text = body.get("input", "")
    voice = body.get("voice", "ff_siwis")
    speed = float(body.get("speed", 1.0))

    async def audio_stream():
        yield _wav_header()
        async with _engine_lock:
            engine = get_engine()
            it = iter(engine.generate_stream(text, voice=voice, speed=speed))
            sentinel = object()
            while True:
                # Run blocking next() in a thread so the event loop stays free
                # to detect client disconnect between chunks.
                chunk = await asyncio.to_thread(next, it, sentinel)
                if chunk is sentinel:
                    break
                pcm = (chunk * 32767).clip(-32768, 32767).astype(np.int16)
                yield pcm.tobytes()

    return StreamingResponse(audio_stream(), media_type="audio/wav")


# Mount Gradio on our FastAPI app — Gradio's catch-all goes last
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--public", action="store_true", help="Écouter sur 0.0.0.0")
    args = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0" if args.public else "127.0.0.1", port=7860)
