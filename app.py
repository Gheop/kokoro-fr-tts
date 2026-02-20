import asyncio
import hashlib
import io
import logging
import pathlib
import struct
import subprocess
import warnings
from collections import OrderedDict

# Supprimer les warnings bruit des dépendances
warnings.filterwarnings("ignore", message=".*dropout option adds dropout.*")
warnings.filterwarnings("ignore", message=".*weight_norm.*is deprecated.*")
warnings.filterwarnings("ignore", message=".*Trying to convert audio.*")
logging.getLogger("phonemizer").setLevel(logging.ERROR)

import gradio as gr  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse  # noqa: E402

from tts_engine import KokoroEngine  # noqa: E402

MAX_INPUT_LENGTH = 750_000
MIN_SPEED = 0.5
MAX_SPEED = 2.0
MAX_QUEUE_SIZE = 3
CACHE_MAX_ENTRIES = 100

try:
    import sounddevice as sd

    sd.query_devices(kind="output")
    _has_audio = True
except Exception:
    _has_audio = False

if _has_audio:
    from audio_player import play_stream  # noqa: E402

_engine: KokoroEngine | None = None
_queue_count = 0
_audio_cache: OrderedDict[str, bytes] = OrderedDict()


def get_engine() -> KokoroEngine:
    global _engine
    if _engine is None:
        _engine = KokoroEngine()
    return _engine


def _cache_key(text: str, voice: str, speed: float, response_format: str) -> str:
    raw = f"{text}|{voice}|{speed}|{response_format}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str) -> bytes | None:
    if key in _audio_cache:
        _audio_cache.move_to_end(key)
        return _audio_cache[key]
    return None


def _cache_put(key: str, data: bytes) -> None:
    _audio_cache[key] = data
    _audio_cache.move_to_end(key)
    while len(_audio_cache) > CACHE_MAX_ENTRIES:
        _audio_cache.popitem(last=False)


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


def _encode_wav(pcm_chunks: list[bytes], sample_rate: int = 24000) -> bytes:
    """Assemble PCM int16 chunks into a complete WAV file."""
    pcm_data = b"".join(pcm_chunks)
    bits = 16
    channels = 1
    block_align = channels * bits // 8
    byte_rate = sample_rate * block_align
    data_size = len(pcm_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits,
        b"data",
        data_size,
    )
    return header + pcm_data


def _encode_audio(pcm_chunks: list[bytes], fmt: str, sample_rate: int = 24000) -> bytes:
    """Encode PCM int16 chunks to the requested format."""
    if fmt == "wav":
        return _encode_wav(pcm_chunks, sample_rate)

    # Reconstruct float32 from int16 for soundfile/ffmpeg
    pcm_data = b"".join(pcm_chunks)
    int16_arr = np.frombuffer(pcm_data, dtype=np.int16)
    float32_arr = int16_arr.astype(np.float32) / 32768.0

    if fmt == "mp3":
        # Use ffmpeg to encode to mp3
        wav_buf = io.BytesIO()
        sf.write(wav_buf, float32_arr, sample_rate, format="WAV", subtype="PCM_16")
        wav_bytes = wav_buf.getvalue()
        result = subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-f", "mp3", "-ab", "192k", "pipe:1"],
            input=wav_bytes,
            capture_output=True,
        )
        return result.stdout

    if fmt == "opus":
        wav_buf = io.BytesIO()
        sf.write(wav_buf, float32_arr, sample_rate, format="WAV", subtype="PCM_16")
        wav_bytes = wav_buf.getvalue()
        result = subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-f", "opus", "-ab", "128k", "pipe:1"],
            input=wav_bytes,
            capture_output=True,
        )
        return result.stdout

    return _encode_wav(pcm_chunks, sample_rate)


_FORMAT_MEDIA_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
}


@app.post("/v1/audio/speech")
async def speech(request: Request):
    global _queue_count

    body = await request.json()
    text = body.get("input", "")
    voice = body.get("voice", "ff_siwis")
    speed = float(body.get("speed", 1.0))
    response_format = body.get("response_format", "wav")

    # --- Validation ---
    if not voice:
        return JSONResponse({"error": "voice must not be empty"}, status_code=422)
    if len(text) > MAX_INPUT_LENGTH:
        return JSONResponse(
            {"error": f"input exceeds {MAX_INPUT_LENGTH} characters"},
            status_code=422,
        )
    if not (MIN_SPEED <= speed <= MAX_SPEED):
        return JSONResponse(
            {"error": f"speed must be between {MIN_SPEED} and {MAX_SPEED}"},
            status_code=422,
        )
    if response_format not in _FORMAT_MEDIA_TYPES:
        return JSONResponse(
            {
                "error": f"response_format must be one of: {', '.join(_FORMAT_MEDIA_TYPES)}"
            },
            status_code=422,
        )

    # --- Queue limit ---
    if _queue_count >= MAX_QUEUE_SIZE:
        return JSONResponse(
            {"error": "server busy, too many pending requests"},
            status_code=503,
        )

    # --- Cache check ---
    key = _cache_key(text, voice, speed, response_format)
    cached = _cache_get(key)
    if cached is not None:
        return Response(
            content=cached,
            media_type=_FORMAT_MEDIA_TYPES[response_format],
        )

    # --- Streaming WAV (default fast path) ---
    if response_format == "wav" and not text:
        # Empty text → header only
        async def empty_stream():
            yield _wav_header()

        return StreamingResponse(empty_stream(), media_type="audio/wav")

    if response_format == "wav":

        async def wav_stream():
            global _queue_count
            _queue_count += 1
            try:
                yield _wav_header()
                async with _engine_lock:
                    engine = get_engine()
                    it = iter(engine.generate_stream(text, voice=voice, speed=speed))
                    sentinel = object()
                    while True:
                        chunk = await asyncio.to_thread(next, it, sentinel)
                        if chunk is sentinel:
                            break
                        pcm = (chunk * 32767).clip(-32768, 32767).astype(np.int16)
                        yield pcm.tobytes()
            finally:
                _queue_count -= 1

        return StreamingResponse(wav_stream(), media_type="audio/wav")

    # --- Non-streaming formats (mp3, opus): collect all chunks then encode ---
    _queue_count += 1
    try:
        pcm_chunks: list[bytes] = []
        async with _engine_lock:
            engine = get_engine()
            it = iter(engine.generate_stream(text, voice=voice, speed=speed))
            sentinel = object()
            while True:
                chunk = await asyncio.to_thread(next, it, sentinel)
                if chunk is sentinel:
                    break
                pcm = (chunk * 32767).clip(-32768, 32767).astype(np.int16)
                pcm_chunks.append(pcm.tobytes())

        encoded = await asyncio.to_thread(_encode_audio, pcm_chunks, response_format)
        _cache_put(key, encoded)
        return Response(
            content=encoded,
            media_type=_FORMAT_MEDIA_TYPES[response_format],
        )
    finally:
        _queue_count -= 1


# Mount Gradio on our FastAPI app — Gradio's catch-all goes last
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--public", action="store_true", help="Écouter sur 0.0.0.0")
    args = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0" if args.public else "127.0.0.1", port=7860)
