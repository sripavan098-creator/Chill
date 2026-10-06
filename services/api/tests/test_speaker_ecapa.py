"""Real speaker-verification tests using ECAPA-TDNN.

These are marked `speaker` and skipped unless the `speaker` extra is installed.
They exercise the model that production would use, so they are slower than the
placeholder-backed suite and are not run by default.

Speech is synthesised locally with Piper when a voice model is available, which
keeps the test offline and free of committed audio. Without a voice the tests
skip rather than download one.
"""

from __future__ import annotations

import io
import os
import wave
from pathlib import Path

import numpy as np
import pytest

from app.core.audio import prepare
from app.core.embeddings import EcapaEmbeddingProvider, cosine_similarity

pytestmark = pytest.mark.speaker

# Two different voices: one stands in for the owner, the other for an impostor.
VOICE_A = "lessac"
VOICE_B = "ryan"

PHRASES = [
    "Hey Chill, this is my voice.",
    "Hey Chill, unlock my assistant.",
    "Hey Chill, remember me.",
]


def _piper_voice_path(name: str) -> Path | None:
    """Find a Piper voice in the usual cache locations."""
    candidates = [
        Path(os.environ.get("CHILL_PIPER_DIR", "/tmp/piper")) / f"{name}.onnx",
        Path.home() / ".local/share/piper" / f"{name}.onnx",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _synth(voice_name: str, text: str) -> bytes:
    """Render text with Piper, returning 16-bit mono WAV bytes."""
    model_path = _piper_voice_path(voice_name)
    if model_path is None:
        pytest.skip(f"Piper voice '{voice_name}' is not available")

    from piper import PiperVoice

    voice = PiperVoice.load(str(model_path))
    chunks = [chunk.audio_int16_array for chunk in voice.synthesize(text)]
    if not chunks:
        pytest.skip(f"Piper voice '{voice_name}' produced no audio")
    pcm = np.concatenate(chunks)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(voice.config.sample_rate)
        handle.writeframes(pcm.astype("<i2").tobytes())
    return buffer.getvalue()


@pytest.fixture(scope="module")
def provider() -> EcapaEmbeddingProvider:
    pytest.importorskip("speechbrain", reason="speaker extra is not installed")
    pytest.importorskip("torch", reason="speaker extra is not installed")
    return EcapaEmbeddingProvider(
        cache_dir=os.environ.get("CHILL_MODEL_CACHE_DIR", "./.models"),
        device="cpu",
        dimensions=192,
    )


async def _embed(provider: EcapaEmbeddingProvider, wav: bytes) -> list[float]:
    decoded = prepare(wav)
    return await provider.embed(
        decoded.samples,
        sample_rate=decoded.sample_rate,
        duration_ms=decoded.quality.duration_ms,
    )


async def test_ecapa_embeddings_are_normalised(provider) -> None:
    embedding = await _embed(provider, _synth(VOICE_A, PHRASES[0]))
    assert len(embedding) == 192
    assert cosine_similarity(embedding, embedding) == pytest.approx(1.0, abs=1e-4)


async def test_same_speaker_scores_above_threshold(provider) -> None:
    samples = [_synth(VOICE_A, phrase) for phrase in PHRASES]
    embeddings = [await _embed(provider, wav) for wav in samples]
    centroid = await provider.average(embeddings)

    similarities = [cosine_similarity(e, centroid) for e in embeddings]
    assert min(similarities) > 0.55, similarities


async def test_different_speaker_scores_below_threshold(provider) -> None:
    owner_embeddings = [
        await _embed(provider, _synth(VOICE_A, phrase)) for phrase in PHRASES
    ]
    centroid = await provider.average(owner_embeddings)

    impostor = await _embed(provider, _synth(VOICE_B, PHRASES[0]))
    assert cosine_similarity(impostor, centroid) < 0.55


async def test_average_is_a_unit_vector(provider) -> None:
    embeddings = [
        await _embed(provider, _synth(VOICE_A, phrase)) for phrase in PHRASES
    ]
    centroid = await provider.average(embeddings)
    norm = float(np.linalg.norm(centroid))
    assert norm == pytest.approx(1.0, abs=1e-4)


# --- End to end through the HTTP API -----------------------------------------


@pytest.fixture
async def ecapa_client(tmp_path):
    """The real ASGI app configured with the ECAPA provider."""
    pytest.importorskip("speechbrain", reason="speaker extra is not installed")
    pytest.importorskip("torch", reason="speaker extra is not installed")
    from httpx import ASGITransport, AsyncClient

    from app.core.config import Settings
    from app.main import create_app

    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path}/chill-ecapa.db",
        embedding_provider="ecapa",
        model_cache_dir=os.environ.get("CHILL_MODEL_CACHE_DIR", "./.models"),
        model_device="cpu",
        # The synthetic phrases are short; keep the quality gates permissive so
        # the test exercises the model rather than the gate.
        min_speech_ms=300,
        min_snr_db=3.0,
        verification_rate_limit=50,
        enrollment_rate_limit=50,
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://chill.test") as http:
            yield http


async def test_api_enrollment_and_verification_with_ecapa(ecapa_client) -> None:
    from tests.conftest import auth, b64

    registered = await ecapa_client.post("/v1/devices", json={"platform": "test"})
    token = registered.json()["access_token"]
    headers = auth(token)
    await ecapa_client.put("/v1/consent", json={"granted": True}, headers=headers)

    owner_phrases = [
        "Hey Chill, this is my voice.",
        "Hey Chill, unlock my assistant.",
        "Hey Chill, remember me.",
        "Hey Chill, keep my data private.",
        "Hey Chill, start listening.",
    ]
    samples = [
        {
            "phrase_id": f"phrase-{index + 1}",
            "duration_ms": 2400,
            "quality": 0.9,
            "audio_base64": b64(_synth(VOICE_A, phrase)),
        }
        for index, phrase in enumerate(owner_phrases)
    ]
    enrolled = await ecapa_client.post(
        "/v1/enrollment", json={"display_name": "Owner", "samples": samples}, headers=headers
    )
    assert enrolled.status_code == 200, enrolled.text
    assert enrolled.json()["model_version"] == "ecapa-voxceleb-v1"

    async def submit(audio: bytes):
        challenge = await ecapa_client.post(
            "/v1/verification/challenge", headers=headers
        )
        assert challenge.status_code == 200, challenge.text
        return await ecapa_client.post(
            "/v1/verification",
            json={
                "duration_ms": 2400,
                "audio_base64": b64(audio),
                "challenge_id": challenge.json()["challenge_id"],
            },
            headers=headers,
        )

    # A fresh owner phrase, unseen during enrollment, still verifies.
    genuine = await submit(_synth(VOICE_A, "Hey Chill, it is really me."))
    assert genuine.status_code == 200, genuine.text
    assert genuine.json()["outcome"] == "success", genuine.json()

    # A different speaker is rejected.
    impostor = await submit(_synth(VOICE_B, "Hey Chill, it is really me."))
    assert impostor.status_code == 200, impostor.text
    assert impostor.json()["outcome"] == "failure", impostor.json()
