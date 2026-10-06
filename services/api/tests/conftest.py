"""Shared test fixtures.

Tests run against the real ASGI application over an isolated SQLite database.
Nothing in the application is mocked: the goal is to exercise the same code path
a deployed instance runs, minus Postgres.

The default suite uses the deterministic placeholder encoder, so the audio
fixtures only have to be *valid audio with speech-like structure* — the encoder
is content-addressed. `tests/test_speaker_ecapa.py` runs the real ECAPA model
instead and is opt-in via `pytest -m speaker`.
"""

from __future__ import annotations

import base64
import io
import math
import struct
import wave
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

PHRASES = [
    "phrase-1-voice",
    "phrase-2-unlock",
    "phrase-3-remember",
    "phrase-4-private",
    "phrase-5-listening",
]

SAMPLE_RATE = 16_000


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def synth_speech(
    *,
    seed: int = 0,
    seconds: float = 2.4,
    sample_rate: int = SAMPLE_RATE,
    amplitude: float = 0.6,
    noise: float = 0.01,
) -> bytes:
    """Build a WAV with speech-like structure.

    A voiced harmonic stack with a varying envelope gives the energy-based VAD
    something to find and the placeholder encoder something distinctive. It is
    not real speech and must not be used to judge model accuracy.
    """
    count = int(sample_rate * seconds)
    frames = bytearray()
    phase = 0.0
    for index in range(count):
        t = index / sample_rate
        # Pitch and formant-ish content vary with the seed.
        f0 = 110.0 + seed * 13.0
        value = 0.0
        for harmonic in range(1, 8):
            value += math.sin(2 * math.pi * f0 * harmonic * t) / harmonic
        # Syllable-rate envelope with genuine pauses between phrases, so the
        # energy VAD sees both speech and non-speech frames. The rate is fixed:
        # pauses should not depend on the (seed-selected) pitch.
        envelope = max(0.0, math.sin(2 * math.pi * 3.0 * t)) ** 1.5
        # Deterministic pseudo-noise without pulling in numpy.
        phase = (phase * 1103515245 + 12345) % (2**31)
        jitter = ((phase / (2**31)) - 0.5) * 2.0
        value = value * envelope * amplitude + jitter * noise
        sample = int(max(-1.0, min(1.0, value)) * 32767)
        frames += struct.pack("<h", sample)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(frames))
    return buffer.getvalue()


def silence_wav(seconds: float = 2.0, sample_rate: int = SAMPLE_RATE) -> bytes:
    """A valid WAV with no speech, for quality-rejection tests."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * int(sample_rate * seconds))
    return buffer.getvalue()


def make_settings(tmp_path, **overrides) -> Settings:
    defaults = {
        "database_url": f"sqlite+aiosqlite:///{tmp_path}/chill-test.db",
        # The placeholder encoder is content-addressed, so a fresh take of one
        # enrolled phrase matches exactly one of the five stored samples. Its
        # cosine against the five-sample centroid is ~0.38, while an unrelated
        # speaker sits near 0.05. 0.3 separates the two with margin.
        "verification_threshold": 0.3,
        "max_verification_attempts": 3,
        "verification_rate_limit": 50,
        "enrollment_rate_limit": 50,
        "lockout_seconds": 300,
        # Keep the synthetic fixtures acceptable to the quality gates.
        "min_speech_ms": 300,
        "min_snr_db": 3.0,
    }
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture
async def app(tmp_path):
    settings = make_settings(tmp_path)
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://chill.test") as http:
        yield http


async def register_device(client: AsyncClient, **kwargs) -> dict:
    response = await client.post("/v1/devices", json={"platform": "test", **kwargs})
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def grant_consent(client: AsyncClient, token: str) -> None:
    response = await client.put(
        "/v1/consent", json={"granted": True}, headers=auth(token)
    )
    assert response.status_code == 200, response.text


def sample_audio(seed: int) -> bytes:
    """Distinct, speech-like audio for a phrase."""
    return synth_speech(seed=seed)


async def enroll(
    client: AsyncClient,
    token: str,
    *,
    samples: list[tuple[str, bytes, int]] | None = None,
    display_name: str | None = "Test owner",
):
    if samples is None:
        samples = [
            (f"phrase-{index + 1}", sample_audio(index + 1), 2400)
            for index in range(len(PHRASES))
        ]
    payload = {
        "display_name": display_name,
        "samples": [
            {
                "phrase_id": phrase_id,
                "duration_ms": duration,
                "quality": 0.9,
                "audio_base64": b64(audio),
            }
            for phrase_id, audio, duration in samples
        ],
    }
    return await client.post("/v1/enrollment", json=payload, headers=auth(token))


async def enroll_repeated_audio(
    client: AsyncClient,
    token: str,
    audio: bytes,
    *,
    duration_ms: int = 2400,
):
    """Enroll five phrases that all share the same audio.

    The placeholder encoder is content-addressed, so identical audio collapses to
    a single point and a later sample of that audio matches the centroid. A real
    encoder would not need this; it would recognise the same speaker across
    different phrases.
    """
    samples = [(f"phrase-{index + 1}", audio, duration_ms) for index in range(5)]
    return await enroll(client, token, samples=samples)


async def enroll_default(client: AsyncClient, token: str):
    """Enroll with the standard five distinct phrase samples."""
    return await enroll(client, token)
