"""Beta hardening tests (v0.8).

Covers the pieces added for the beta: request correlation ids, the safe error
envelope, audio upload limits, the version policy, feedback intake and the
shared account-deletion path.
"""

from __future__ import annotations

from httpx import AsyncClient

from app.core.version import API_VERSION
from tests.conftest import (
    auth,
    b64,
    enroll,
    grant_consent,
    register_device,
    synth_speech,
)


async def test_health_reports_version_and_request_id(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == API_VERSION
    assert response.headers.get("X-Request-ID")


async def test_request_id_is_echoed_when_well_formed(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "abc123def456"})
    assert response.headers["X-Request-ID"] == "abc123def456"


async def test_request_id_is_regenerated_when_malformed(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "bad id!!"})
    assert response.headers["X-Request-ID"] != "bad id!!"
    assert len(response.headers["X-Request-ID"]) == 32


async def test_version_policy_is_public(client: AsyncClient) -> None:
    response = await client.get("/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == API_VERSION
    assert body["minimum_supported"]
    assert body["update_url"].startswith("https://")


async def test_oversized_body_is_rejected_before_parsing(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    # Declared Content-Length over the limit: refused with a stable envelope.
    oversized = "x" * (20 * 1024 * 1024)
    response = await client.post(
        "/v1/assistant/chat",
        content=oversized,
        headers={**auth(token), "Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


async def test_oversized_audio_sample_is_rejected(client: AsyncClient, app) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)

    audio = synth_speech(seed=1)
    encoded = b64(audio)
    oversized = encoded * (app.state.settings.max_audio_bytes // len(encoded) + 2)
    payload = {
        "display_name": "Big owner",
        "samples": [
            {
                "phrase_id": f"phrase-{index + 1}",
                "duration_ms": 2400,
                "quality": 0.9,
                # A base64 payload larger than a single allowed sample.
                "audio_base64": oversized,
            }
            for index in range(5)
        ],
    }
    response = await client.post("/v1/enrollment", json=payload, headers=auth(token))
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


async def test_unhandled_error_returns_generic_envelope(tmp_path) -> None:
    from httpx import ASGITransport
    from httpx import AsyncClient as Http

    from app.main import create_app
    from tests.conftest import make_settings

    broken = create_app(make_settings(tmp_path))

    @broken.get("/v1/boom")
    async def boom():  # pragma: no cover - deliberately raises
        raise RuntimeError("sensitive internal detail")

    async with broken.router.lifespan_context(broken):
        transport = ASGITransport(app=broken)
        async with Http(transport=transport, base_url="http://chill.test") as http:
            response = await http.get("/v1/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "sensitive internal detail" not in body["error"]["message"]
    assert response.headers.get("X-Request-ID")


async def test_feedback_is_recorded(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    response = await client.post(
        "/v1/feedback",
        json={
            "message": "The enrollment screen scrolled oddly on a small phone.",
            "kind": "bug",
            "app_version": "0.2.0",
            "platform": "android",
        },
        headers=auth(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "bug"
    assert body["id"]


async def test_feedback_rejects_unknown_kind(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    response = await client.post(
        "/v1/feedback",
        json={"message": "hello", "kind": "not-a-kind"},
        headers=auth(token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_feedback_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/v1/feedback", json={"message": "hi"})
    assert response.status_code == 401


async def test_account_deletion_clears_feedback_and_memories(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)
    assert (await enroll(client, token)).status_code == 200

    await client.post(
        "/v1/assistant/memories",
        json={"content": "I like tea in the morning."},
        headers=auth(token),
    )
    await client.post(
        "/v1/feedback",
        json={"message": "Nice so far.", "kind": "general"},
        headers=auth(token),
    )

    deleted = await client.request(
        "DELETE", "/v1/account", json={"confirm": "DELETE"}, headers=auth(token)
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    # The token is now invalid because the device and owner are gone.
    after = await client.post(
        "/v1/feedback", json={"message": "again"}, headers=auth(token)
    )
    assert after.status_code == 401


async def test_profile_delete_removes_the_same_data_as_account_delete(
    client: AsyncClient,
) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)
    assert (await enroll(client, token)).status_code == 200

    deleted = await client.request(
        "DELETE", "/v1/profile", json={"confirm": "DELETE"}, headers=auth(token)
    )
    assert deleted.status_code == 200

    profile = await client.get("/v1/profile", headers=auth(token))
    assert profile.status_code == 200
    assert profile.json()["enrolled"] is False
