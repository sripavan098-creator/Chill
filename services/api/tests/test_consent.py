"""Consent flow tests: gating, withdrawal and enrollment purge."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import auth, enroll, grant_consent, register_device


async def test_consent_defaults_to_not_granted(client: AsyncClient) -> None:
    device = await register_device(client)
    response = await client.get("/v1/consent", headers=auth(device["access_token"]))
    assert response.status_code == 200
    assert response.json()["granted"] is False


async def test_grant_consent_records_policy_version(client: AsyncClient) -> None:
    device = await register_device(client)
    await grant_consent(client, device["access_token"])

    response = await client.get("/v1/consent", headers=auth(device["access_token"]))
    body = response.json()
    assert body["granted"] is True
    assert body["granted_at"] is not None
    assert body["policy_version"]


async def test_enrollment_requires_consent(client: AsyncClient) -> None:
    device = await register_device(client)
    response = await enroll(client, device["access_token"])

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CONSENT_REQUIRED"


async def test_withdrawing_consent_deletes_enrollment(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)
    assert (await enroll(client, token)).status_code == 200

    withdrawn = await client.put(
        "/v1/consent", json={"granted": False}, headers=auth(token)
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["granted"] is False

    profile = await client.get("/v1/profile", headers=auth(token))
    assert profile.json()["enrolled"] is False


async def test_consent_endpoints_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/v1/consent")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_invalid_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/v1/consent", headers=auth("not-a-real-token"))
    assert response.status_code == 401
