"""Stronger voice auth (v0.5): replay protection, device binding, challenges.

These exercise the real endpoints. The device-binding test creates a second
device for the same owner directly in the database, because there is no
multi-device-per-owner flow in the API yet.
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.core.tokens import generate_token, hash_token
from app.db.models import Device
from app.main import create_app
from tests.conftest import (
    auth,
    enroll,
    grant_consent,
    make_settings,
    register_device,
    request_challenge,
    sample_audio,
    synth_speech,
    verify,
)

SEEDS = (1, 2, 3, 4, 5)


async def _enrolled(client: AsyncClient) -> tuple[str, str]:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)
    samples = [
        (f"phrase-{index + 1}", sample_audio(seed), 2400)
        for index, seed in enumerate(SEEDS)
    ]
    assert (await enroll(client, token, samples=samples)).status_code == 200
    return token, device["owner_id"]


# --- Replay protection --------------------------------------------------------


async def test_same_recording_cannot_be_used_twice(client: AsyncClient) -> None:
    token, _ = await _enrolled(client)

    first = await verify(client, token, audio=sample_audio(SEEDS[0]))
    assert first.status_code == 200, first.text

    # A fresh challenge, but the identical recording: rejected before scoring.
    second = await verify(client, token, audio=sample_audio(SEEDS[0]))
    assert second.status_code == 422, second.text
    assert second.json()["error"]["code"] == "REPLAY_DETECTED"


async def test_replay_rejection_does_not_count_toward_lockout(
    client: AsyncClient,
) -> None:
    token, _ = await _enrolled(client)

    assert (await verify(client, token, audio=sample_audio(SEEDS[0]))).status_code == 200
    for _ in range(5):
        response = await verify(client, token, audio=sample_audio(SEEDS[0]))
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "REPLAY_DETECTED"

    # No failed attempts were recorded, so a genuine new sample is still scored
    # rather than hitting the lockout.
    scored = await verify(client, token, audio=synth_speech(seed=77, amplitude=0.55))
    assert scored.status_code == 200, scored.text


# --- Device binding -----------------------------------------------------------


async def _add_device_for_owner(app, owner_id: str) -> str:
    """Mint a second device token for an existing owner, as a second phone would."""
    token = generate_token()
    async with app.state.session_factory() as session:
        session.add(
            Device(
                owner_id=owner_id,
                token_hash=hash_token(token, app.state.settings.token_signing_key),
                platform="second-device",
            )
        )
        await session.commit()
    return token


async def test_verification_from_another_device_is_refused(
    client: AsyncClient, app
) -> None:
    token, owner_id = await _enrolled(client)
    other = await _add_device_for_owner(app, owner_id)

    response = await verify(client, other, audio=sample_audio(SEEDS[0]))
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "DEVICE_NOT_BOUND"

    # The bound device still works.
    assert (await verify(client, token, audio=sample_audio(SEEDS[0]))).status_code == 200


async def test_binding_can_be_disabled(tmp_path, app) -> None:
    settings = make_settings(tmp_path, enforce_device_binding=False)
    bound_app = create_app(settings)
    async with bound_app.router.lifespan_context(bound_app):
        transport = ASGITransport(app=bound_app)
        async with AsyncClient(transport=transport, base_url="http://chill.test") as http:
            token, owner_id = await _enrolled(http)
            other = await _add_device_for_owner(bound_app, owner_id)

            # Past the binding check, so the sample is scored normally.
            response = await verify(http, other, audio=sample_audio(SEEDS[0]))
            assert response.status_code == 200, response.text


# --- Challenges ---------------------------------------------------------------


async def test_challenge_nonce_is_returned_and_expires_quickly(
    client: AsyncClient,
) -> None:
    device = await register_device(client)
    token = device["access_token"]

    response = await client.post("/v1/verification/challenge", headers=auth(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["challenge_id"]
    assert len(body["nonce"]) >= 16
    assert body["expires_at"]


async def test_expired_challenge_is_refused(tmp_path, app) -> None:
    settings = make_settings(tmp_path, challenge_ttl_seconds=-1)
    expired_app = create_app(settings)
    async with expired_app.router.lifespan_context(expired_app):
        transport = ASGITransport(app=expired_app)
        async with AsyncClient(transport=transport, base_url="http://chill.test") as http:
            token, _ = await _enrolled(http)
            challenge_id = await request_challenge(http, token)

            response = await verify(
                http, token, audio=sample_audio(SEEDS[0]), challenge_id=challenge_id
            )
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "CHALLENGE_REQUIRED"


async def test_challenge_belongs_to_the_owner(client: AsyncClient, app) -> None:
    token_a, _ = await _enrolled(client)
    token_b, _ = await _enrolled(client)

    # A challenge minted for one owner cannot be used by another.
    challenge_for_a = await request_challenge(client, token_a)
    response = await verify(
        client, token_b, audio=sample_audio(SEEDS[0]), challenge_id=challenge_for_a
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CHALLENGE_REQUIRED"


async def test_challenge_requests_are_rate_limited(tmp_path, app) -> None:
    settings = make_settings(tmp_path, challenge_rate_limit=1)
    limited_app = create_app(settings)
    async with limited_app.router.lifespan_context(limited_app):
        transport = ASGITransport(app=limited_app)
        async with AsyncClient(transport=transport, base_url="http://chill.test") as http:
            device = await register_device(http)
            token = device["access_token"]

            first = await http.post("/v1/verification/challenge", headers=auth(token))
            assert first.status_code == 200

            second = await http.post("/v1/verification/challenge", headers=auth(token))
            assert second.status_code == 429
            assert second.json()["error"]["code"] == "RATE_LIMITED"


async def test_profile_reports_device_binding(client: AsyncClient) -> None:
    token, _ = await _enrolled(client)

    response = await client.get("/v1/profile", headers=auth(token))
    assert response.status_code == 200, response.text
    assert response.json()["device_bound"] is True


# --- Retention ----------------------------------------------------------------


async def test_replay_digests_are_purged_past_the_window(
    client: AsyncClient, app
) -> None:
    from app.core.audio import fingerprint
    from app.services import replay

    token, owner_id = await _enrolled(client)
    assert (await verify(client, token, audio=sample_audio(SEEDS[0]))).status_code == 200

    digest = fingerprint(*_decoded(sample_audio(SEEDS[0])))

    async with app.state.session_factory() as session:
        assert await replay.is_replayed(
            session, owner_id=owner_id, fingerprint=digest
        )

        # A zero-second window drops everything already recorded.
        removed = await replay.purge_expired(session, window_seconds=0)
        await session.commit()
        assert removed >= 1

        assert not await replay.is_replayed(
            session, owner_id=owner_id, fingerprint=digest
        )


def _decoded(audio: bytes):
    """Return (samples, sample_rate) for a WAV, matching how verify fingerprints."""
    from app.core.audio import prepare

    decoded = prepare(audio)
    return decoded.samples, decoded.sample_rate
