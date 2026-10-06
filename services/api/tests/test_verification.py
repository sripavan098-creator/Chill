"""Verification tests: success, failure, lockout and audit trail."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import (
    auth,
    b64,
    enroll_repeated_audio,
    grant_consent,
    register_device,
)

ENROLLED_AUDIO = b"owner-voice-sample"


async def _enrolled_device(client: AsyncClient) -> str:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)
    assert (await enroll_repeated_audio(client, token, ENROLLED_AUDIO)).status_code == 200
    return token


def _same_voice_audio() -> bytes:
    """Audio identical to the enrollment samples, so similarity is ~1.0."""
    return ENROLLED_AUDIO


async def test_verification_succeeds_for_matching_voice(client: AsyncClient) -> None:
    token = await _enrolled_device(client)

    response = await client.post(
        "/v1/verification",
        json={"duration_ms": 2200, "audio_base64": b64(_same_voice_audio())},
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["outcome"] == "success"
    assert body["similarity"] >= body["threshold"]
    assert body["locked_out"] is False


async def test_verification_fails_for_different_voice(client: AsyncClient) -> None:
    token = await _enrolled_device(client)

    response = await client.post(
        "/v1/verification",
        json={"duration_ms": 2200, "audio_base64": b64(b"a completely different speaker")},
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["outcome"] == "failure"
    assert body["similarity"] < body["threshold"]
    assert body["attempts_remaining"] == 2


async def test_verification_requires_enrollment(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)

    response = await client.post(
        "/v1/verification",
        json={"duration_ms": 2200, "audio_base64": b64(b"hello")},
        headers=auth(token),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ENROLLMENT_REQUIRED"


async def test_repeated_failures_trigger_lockout(client: AsyncClient) -> None:
    token = await _enrolled_device(client)
    payload = {"duration_ms": 2200, "audio_base64": b64(b"wrong speaker audio")}

    for _ in range(3):
        response = await client.post("/v1/verification", json=payload, headers=auth(token))
        assert response.status_code == 200

    locked = await client.post("/v1/verification", json=payload, headers=auth(token))
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "LOCKED_OUT"


async def test_verification_rejects_short_sample(client: AsyncClient) -> None:
    token = await _enrolled_device(client)
    response = await client.post(
        "/v1/verification",
        json={"duration_ms": 200, "audio_base64": b64(b"short")},
        headers=auth(token),
    )
    assert response.status_code == 422


async def test_audit_log_records_enrollment_and_verification(
    client: AsyncClient, app
) -> None:
    token = await _enrolled_device(client)
    await client.post(
        "/v1/verification",
        json={"duration_ms": 2200, "audio_base64": b64(_same_voice_audio())},
        headers=auth(token),
    )

    from sqlalchemy import select

    from app.db.models import AuditLog

    async with app.state.session_factory() as session:
        events = (
            await session.execute(select(AuditLog.event).order_by(AuditLog.created_at))
        ).scalars().all()

    assert "device.registered" in events
    assert "consent.granted" in events
    assert "enrollment.created" in events
    assert "verification.attempt" in events

    # The audit trail must not contain biometric material.
    async with app.state.session_factory() as session:
        details = (
            await session.execute(select(AuditLog.detail))
        ).scalars().all()
    assert all(detail is None or "audio" not in detail for detail in details)
