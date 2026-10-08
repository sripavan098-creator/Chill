"""Rate limiting and account deletion tests."""

from __future__ import annotations

from httpx import AsyncClient

from app.core.transcription import attach_transcript
from tests.conftest import (
    auth,
    b64,
    enroll,
    grant_consent,
    make_settings,
    register_device,
    request_challenge_body,
    synth_speech,
)


async def test_verification_rate_limit_returns_429(client: AsyncClient, tmp_path, app) -> None:
    # Rebuild the app with a tight verification limit.
    from app.main import create_app

    settings = make_settings(tmp_path, verification_rate_limit=2, max_verification_attempts=99)
    limited_app = create_app(settings)

    from httpx import ASGITransport

    async with limited_app.router.lifespan_context(limited_app):
        transport = ASGITransport(app=limited_app)
        async with AsyncClient(transport=transport, base_url="http://chill.test") as http:
            device = await register_device(http)
            token = device["access_token"]
            await grant_consent(http, token)
            assert (await enroll(http, token)).status_code == 200

            async def submit(seed: int):
                challenge = await request_challenge_body(http, token)
                with attach_transcript(challenge.get("phrase")):
                    return await http.post(
                        "/v1/verification",
                        json={
                            "duration_ms": 2400,
                            "audio_base64": b64(synth_speech(seed=seed)),
                            "challenge_id": challenge["challenge_id"],
                        },
                        headers=auth(token),
                    )

            assert (await submit(1)).status_code == 200
            assert (await submit(2)).status_code == 200

            blocked = await submit(3)
            assert blocked.status_code == 429
            assert blocked.json()["error"]["code"] == "RATE_LIMITED"
            assert blocked.headers.get("Retry-After") == "60"


async def test_account_deletion_requires_confirmation(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)
    await enroll(client, token)

    bad = await client.request(
        "DELETE", "/v1/account", json={"confirm": "nope"}, headers=auth(token)
    )
    assert bad.status_code == 422

    ok = await client.request(
        "DELETE", "/v1/account", json={"confirm": "DELETE"}, headers=auth(token)
    )
    assert ok.status_code == 200

    # The device token is now useless because the owner is gone.
    after = await client.get("/v1/profile", headers=auth(token))
    assert after.status_code == 401


async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
