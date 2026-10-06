"""Enrollment and profile tests."""

from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag
from httpx import AsyncClient

from tests.conftest import (
    PHRASES,
    auth,
    b64,
    enroll,
    grant_consent,
    register_device,
    sample_audio,
)


async def test_enrollment_stores_encrypted_embedding_only(client: AsyncClient, app) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)

    response = await enroll(client, token)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["phrase_count"] == 5
    assert body["embedding_dimensions"] == app.state.settings.embedding_dimensions

    # The stored blob must be ciphertext, not the raw embedding bytes.
    from sqlalchemy import select

    from app.core.crypto import EmbeddingCipher
    from app.db.models import Enrollment

    async with app.state.session_factory() as session:
        enrollment = (
            await session.execute(select(Enrollment))
        ).scalar_one()
        blob = enrollment.embedding_encrypted

    assert len(blob) > 12  # nonce + ciphertext
    assert blob[:12] != b"\x00" * 12
    # A wrong key must fail to decrypt, proving the payload is encrypted.
    wrong = EmbeddingCipher(b64(b"x" * 32))
    with pytest.raises(InvalidTag):
        wrong.decrypt(blob)


async def test_enrollment_requires_five_samples(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)

    samples = [
        (f"phrase-{i + 1}", sample_audio(i + 1), 2400)
        for i in range(len(PHRASES[:3]))
    ]
    response = await enroll(client, token, samples=samples)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INCOMPLETE_ENROLLMENT"


async def test_enrollment_rejects_duplicate_phrases(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)

    audio = sample_audio(1)
    samples = [(f"phrase-{i + 1}", audio, 2400) for i in range(len(PHRASES))]
    response = await enroll(client, token, samples=samples)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_enrollment_rejects_short_sample(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)

    samples = [
        (f"phrase-{i + 1}", sample_audio(i + 1), 400)
        for i in range(len(PHRASES))
    ]
    response = await enroll(client, token, samples=samples)
    assert response.status_code == 422


async def test_enrollment_rejects_invalid_base64(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)

    payload = {
        "display_name": "Owner",
        "samples": [
            {
                "phrase_id": f"phrase-{i + 1}",
                "duration_ms": 2200,
                "quality": 0.9,
                "audio_base64": "not base64!!!",
            }
            for i in range(5)
        ],
    }
    response = await client.post("/v1/enrollment", json=payload, headers=auth(token))
    assert response.status_code == 422


async def test_enrollment_is_idempotent_on_reenroll(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)

    assert (await enroll(client, token)).status_code == 200
    assert (await enroll(client, token, display_name="Renamed")).status_code == 200

    profile = await client.get("/v1/profile", headers=auth(token))
    assert profile.json()["display_name"] == "Renamed"
    assert profile.json()["enrolled"] is True


async def test_profile_reports_consent_and_enrollment(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]

    profile = await client.get("/v1/profile", headers=auth(token))
    body = profile.json()
    assert body["enrolled"] is False
    assert body["consent_granted"] is False

    await grant_consent(client, token)
    await enroll(client, token)

    profile = await client.get("/v1/profile", headers=auth(token))
    body = profile.json()
    assert body["enrolled"] is True
    assert body["consent_granted"] is True
    assert body["phrase_count"] == 5


async def test_delete_profile_requires_confirmation(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)
    await enroll(client, token)

    bad = await client.request(
        "DELETE", "/v1/profile", json={"confirm": "yes"}, headers=auth(token)
    )
    assert bad.status_code == 422

    ok = await client.request(
        "DELETE", "/v1/profile", json={"confirm": "DELETE"}, headers=auth(token)
    )
    assert ok.status_code == 200
    assert ok.json()["deleted"] is True

    profile = await client.get("/v1/profile", headers=auth(token))
    assert profile.json()["enrolled"] is False


async def test_enrollment_rejects_empty_sample(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)

    payload = {
        "display_name": "Owner",
        "samples": [
            {
                "phrase_id": f"phrase-{i + 1}",
                "duration_ms": 2200,
                "quality": 0.9,
                "audio_base64": b64(b""),
            }
            for i in range(5)
        ],
    }
    response = await client.post("/v1/enrollment", json=payload, headers=auth(token))
    assert response.status_code == 422
