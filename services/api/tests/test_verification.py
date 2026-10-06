"""Verification tests: success, failure, lockout and quality guards."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import (
    auth,
    b64,
    enroll,
    grant_consent,
    register_device,
    request_challenge,
    sample_audio,
    silence_wav,
    synth_speech,
    verify,
)

# The placeholder encoder is content-addressed, so the centroid of five
# distinct phrases is spread out. A verification sample that repeats one
# enrolled phrase still lands ~0.38 from the centroid, above the test
# threshold, while an unrelated waveform sits near 0.05.
ENROLLED_SEEDS = (1, 2, 3, 4, 5)


async def _enrolled_device(client: AsyncClient) -> str:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)
    samples = [
        (f"phrase-{index + 1}", sample_audio(seed), 2400)
        for index, seed in enumerate(ENROLLED_SEEDS)
    ]
    assert (await enroll(client, token, samples=samples)).status_code == 200
    return token


def _matching_audio() -> bytes:
    """A fresh take of the enrolled speaker (one of the enrolled seeds)."""
    return sample_audio(ENROLLED_SEEDS[0])


def _different_voice_audio() -> bytes:
    """A speaker whose audio shares nothing with the enrolled samples."""
    return synth_speech(seed=99, amplitude=0.55)


async def test_verification_succeeds_for_matching_voice(client: AsyncClient) -> None:
    token = await _enrolled_device(client)

    response = await verify(client, token, audio=_matching_audio())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["outcome"] == "success"
    assert body["similarity"] >= body["threshold"]
    assert body["locked_out"] is False
    assert body["model_version"] == "placeholder-v0.4"


async def test_verification_fails_for_different_voice(client: AsyncClient) -> None:
    token = await _enrolled_device(client)

    response = await verify(client, token, audio=_different_voice_audio())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["outcome"] == "failure"
    assert body["similarity"] < body["threshold"]
    assert body["attempts_remaining"] == 2


async def test_verification_requires_enrollment(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)

    response = await verify(client, token, audio=_matching_audio())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ENROLLMENT_REQUIRED"


async def test_verification_requires_a_challenge(client: AsyncClient) -> None:
    token = await _enrolled_device(client)

    # No challenge_id: the server must refuse before scoring.
    response = await client.post(
        "/v1/verification",
        json={"duration_ms": 2400, "audio_base64": b64(_matching_audio())},
        headers=auth(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CHALLENGE_REQUIRED"


async def test_verification_rejects_a_used_challenge(client: AsyncClient) -> None:
    token = await _enrolled_device(client)
    challenge_id = await request_challenge(client, token)

    first = await verify(client, token, audio=_matching_audio(), challenge_id=challenge_id)
    assert first.status_code == 200, first.text

    # The same nonce cannot be presented twice.
    second = await verify(
        client, token, audio=_different_voice_audio(), challenge_id=challenge_id
    )
    assert second.status_code == 422
    assert second.json()["error"]["code"] == "CHALLENGE_REQUIRED"


async def test_repeated_failures_trigger_lockout(client: AsyncClient) -> None:
    token = await _enrolled_device(client)

    # Distinct wrong-speaker samples, each scored against the enrolled centroid.
    for index in range(3):
        response = await verify(
            client, token, audio=synth_speech(seed=90 + index, amplitude=0.55)
        )
        assert response.status_code == 200, response.text

    locked = await verify(client, token, audio=synth_speech(seed=200, amplitude=0.55))
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "LOCKED_OUT"


async def test_verification_rejects_short_sample(client: AsyncClient) -> None:
    token = await _enrolled_device(client)
    response = await verify(client, token, audio=_matching_audio(), duration_ms=200)
    assert response.status_code == 422


async def test_verification_rejects_silence(client: AsyncClient) -> None:
    """A valid but speechless recording is a quality rejection, not a failure."""
    token = await _enrolled_device(client)
    response = await verify(client, token, audio=silence_wav())
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SAMPLE_QUALITY"


async def test_quality_rejection_does_not_count_toward_lockout(
    client: AsyncClient,
) -> None:
    token = await _enrolled_device(client)

    for _ in range(5):
        response = await verify(client, token, audio=silence_wav())
        assert response.status_code == 422

    # A good sample still gets scored rather than being locked out.
    good = await verify(client, token, audio=_matching_audio())
    assert good.status_code == 200, good.text


async def test_audit_log_records_enrollment_and_verification(
    client: AsyncClient, app
) -> None:
    token = await _enrolled_device(client)
    await verify(client, token, audio=_matching_audio())

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
