import struct
from unittest.mock import patch

import numpy as np
import pytest
from starlette.testclient import TestClient

from tts_engine import KokoroEngine


def _fake_generate_stream(text, voice=None, speed=None):
    """Yield deux chunks de silence pour simuler le moteur TTS."""
    if not text:
        return
    for _ in range(2):
        yield np.zeros(480, dtype=np.float32)


@pytest.fixture()
def client():
    """Client de test avec le moteur TTS mocké."""
    fake_engine = object.__new__(KokoroEngine)
    fake_engine.sample_rate = 24000
    fake_engine.generate_stream = _fake_generate_stream

    with patch("app.get_engine", return_value=fake_engine):
        import app

        # Reset queue count and cache between tests
        app._queue_count = 0
        app._audio_cache.clear()
        yield TestClient(app.app)


def test_speech_returns_200(client):
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Bonjour"},
    )
    assert response.status_code == 200


def test_speech_content_type(client):
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Bonjour"},
    )
    assert response.headers["content-type"] == "audio/wav"


def test_speech_wav_header(client):
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Bonjour"},
    )
    data = response.content
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WAVE"
    assert data[12:16] == b"fmt "


def test_speech_pcm_format(client):
    """Vérifie que le header WAV indique PCM 16-bit mono 24kHz."""
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Bonjour"},
    )
    data = response.content
    # fmt chunk starts at offset 12, data at offset 20
    audio_format = struct.unpack_from("<H", data, 20)[0]
    channels = struct.unpack_from("<H", data, 22)[0]
    sample_rate = struct.unpack_from("<I", data, 24)[0]
    bits_per_sample = struct.unpack_from("<H", data, 34)[0]
    assert audio_format == 1  # PCM
    assert channels == 1
    assert sample_rate == 24000
    assert bits_per_sample == 16


def test_speech_contains_audio_data(client):
    """Vérifie que la réponse contient des données audio après le header."""
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Bonjour"},
    )
    wav_header_size = 44
    assert len(response.content) > wav_header_size


def test_speech_empty_text(client):
    """Texte vide → header WAV seul, pas de données PCM."""
    response = client.post(
        "/v1/audio/speech",
        json={"input": ""},
    )
    assert response.status_code == 200
    wav_header_size = 44
    assert len(response.content) == wav_header_size


def test_speech_custom_voice(client):
    """Le paramètre voice est accepté sans erreur."""
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Test", "voice": "ff_siwis", "speed": 1.2},
    )
    assert response.status_code == 200


# --- Tests validation ---


def test_speech_text_too_long(client):
    """Texte > 750000 caractères → 422."""
    response = client.post(
        "/v1/audio/speech",
        json={"input": "a" * 750_001},
    )
    assert response.status_code == 422


def test_speech_text_at_limit(client):
    """Texte de exactement 750000 caractères → 200."""
    response = client.post(
        "/v1/audio/speech",
        json={"input": "a" * 750_000},
    )
    assert response.status_code == 200


def test_speech_speed_too_low(client):
    """Speed < 0.5 → 422."""
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Bonjour", "speed": 0.1},
    )
    assert response.status_code == 422


def test_speech_speed_too_high(client):
    """Speed > 2.0 → 422."""
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Bonjour", "speed": 10.0},
    )
    assert response.status_code == 422


def test_speech_speed_at_bounds(client):
    """Speed aux bornes [0.5, 2.0] → 200."""
    for speed in [0.5, 2.0]:
        response = client.post(
            "/v1/audio/speech",
            json={"input": "Bonjour", "speed": speed},
        )
        assert response.status_code == 200


def test_speech_empty_voice(client):
    """Voice vide → 422."""
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Bonjour", "voice": ""},
    )
    assert response.status_code == 422


def test_speech_invalid_format(client):
    """Format inconnu → 422."""
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Bonjour", "response_format": "flac"},
    )
    assert response.status_code == 422


def test_speech_queue_full(client):
    """Quand la queue est pleine → 503."""
    import app

    app._queue_count = 3  # simulate full queue
    response = client.post(
        "/v1/audio/speech",
        json={"input": "Bonjour"},
    )
    assert response.status_code == 503
    app._queue_count = 0
