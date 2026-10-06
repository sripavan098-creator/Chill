"""Shared test fixtures.

Tests run against the real ASGI application over an isolated SQLite database.
Nothing in the application is mocked: the goal is to exercise the same code path
a deployed instance runs, minus Postgres.
"""

from __future__ import annotations

import base64
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


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def make_settings(tmp_path, **overrides) -> Settings:
    defaults = {
        "database_url": f"sqlite+aiosqlite:///{tmp_path}/chill-test.db",
        "verification_threshold": 0.75,
        "max_verification_attempts": 3,
        "verification_rate_limit": 50,
        "enrollment_rate_limit": 50,
        "lockout_seconds": 300,
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


async def enroll(
    client: AsyncClient,
    token: str,
    *,
    samples: list[tuple[str, bytes, int]] | None = None,
    display_name: str | None = "Test owner",
):
    if samples is None:
        samples = [
            (f"phrase-{index + 1}", phrase.encode(), 2200)
            for index, phrase in enumerate(PHRASES)
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
    duration_ms: int = 2200,
):
    """Enroll five phrases that all share the same audio.

    The placeholder encoder is content-addressed, so identical audio collapses to
    a single point and a later sample of that audio matches the centroid. A real
    encoder would not need this; it would recognise the same speaker across
    different phrases.
    """
    samples = [(f"phrase-{index + 1}", audio, duration_ms) for index in range(5)]
    return await enroll(client, token, samples=samples)
