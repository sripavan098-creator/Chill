"""Action Engine tests: risk gating, approvals, confirmation and isolation.

Everything runs against the real ASGI app with the placeholder providers.
"""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import auth, register_device


async def _device(client: AsyncClient) -> str:
    device = await register_device(client)
    return device["access_token"]


async def test_tools_registry_exposes_risk_levels(client: AsyncClient) -> None:
    response = await client.get("/v1/actions/tools")
    assert response.status_code == 200, response.text
    tools = {tool["name"]: tool for tool in response.json()["tools"]}
    assert tools["memory.save"]["risk_level"] == "low"
    assert tools["memory.save"]["requires_approval"] is False
    assert tools["memory.clear"]["risk_level"] == "medium"
    assert tools["memory.clear"]["requires_approval"] is True
    assert tools["voice.delete_profile"]["risk_level"] == "high"
    assert tools["voice.delete_profile"]["requires_confirmation"] is True


async def test_low_risk_action_runs_immediately(client: AsyncClient) -> None:
    token = await _device(client)
    response = await client.post(
        "/v1/actions",
        json={
            "tool_name": "memory.save",
            "arguments": {"content": "I prefer tea over coffee."},
            "summary": "Remember a preference",
        },
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "executed"
    assert body["risk_level"] == "low"
    assert body["result"]["memory_id"]

    # The memory is actually there.
    listed = await client.get("/v1/assistant/memories", headers=auth(token))
    contents = [item["content"] for item in listed.json()["memories"]]
    assert "I prefer tea over coffee." in contents


async def test_medium_risk_action_waits_for_approval(client: AsyncClient) -> None:
    token = await _device(client)
    await client.post(
        "/v1/actions",
        json={"tool_name": "memory.save", "arguments": {"content": "keep me"}},
        headers=auth(token),
    )

    created = await client.post(
        "/v1/actions",
        json={"tool_name": "memory.clear", "arguments": {}},
        headers=auth(token),
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["status"] == "pending"
    assert body["risk_level"] == "medium"
    action_id = body["id"]

    # Nothing has been deleted yet.
    listed = await client.get("/v1/assistant/memories", headers=auth(token))
    assert len(listed.json()["memories"]) == 1

    approved = await client.post(
        f"/v1/actions/{action_id}/approve", json={}, headers=auth(token)
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "executed"

    listed_after = await client.get("/v1/assistant/memories", headers=auth(token))
    assert listed_after.json()["memories"] == []


async def test_high_risk_action_requires_confirmation(client: AsyncClient) -> None:
    token = await _device(client)
    created = await client.post(
        "/v1/actions",
        json={"tool_name": "voice.delete_profile", "arguments": {}},
        headers=auth(token),
    )
    assert created.status_code == 200, created.text
    action_id = created.json()["id"]
    assert created.json()["requires_confirmation"] is True

    # Approval without the confirmation phrase is refused.
    refused = await client.post(
        f"/v1/actions/{action_id}/approve", json={}, headers=auth(token)
    )
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "CONFIRMATION_REQUIRED"

    # The action is still pending, not consumed.
    still = await client.get(f"/v1/actions/{action_id}", headers=auth(token))
    assert still.json()["status"] == "pending"

    approved = await client.post(
        f"/v1/actions/{action_id}/approve",
        json={"confirm": "CONFIRM"},
        headers=auth(token),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "executed"


async def test_denied_action_does_not_run(client: AsyncClient) -> None:
    token = await _device(client)
    await client.post(
        "/v1/actions",
        json={"tool_name": "memory.save", "arguments": {"content": "keep me"}},
        headers=auth(token),
    )
    created = await client.post(
        "/v1/actions",
        json={"tool_name": "memory.clear", "arguments": {}},
        headers=auth(token),
    )
    action_id = created.json()["id"]

    denied = await client.post(
        f"/v1/actions/{action_id}/deny", headers=auth(token)
    )
    assert denied.status_code == 200
    assert denied.json()["status"] == "denied"

    listed = await client.get("/v1/assistant/memories", headers=auth(token))
    assert len(listed.json()["memories"]) == 1


async def test_unknown_tool_is_rejected(client: AsyncClient) -> None:
    token = await _device(client)
    response = await client.post(
        "/v1/actions",
        json={"tool_name": "shell.run", "arguments": {"command": "rm -rf /"}},
        headers=auth(token),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACTION_NOT_FOUND"


async def test_unknown_arguments_are_rejected(client: AsyncClient) -> None:
    token = await _device(client)
    response = await client.post(
        "/v1/actions",
        json={
            "tool_name": "memory.save",
            "arguments": {"content": "hi", "path": "/etc/passwd"},
        },
        headers=auth(token),
    )
    assert response.status_code == 422


async def test_actions_are_owner_scoped(client: AsyncClient) -> None:
    owner_a = await _device(client)
    owner_b = await _device(client)
    created = await client.post(
        "/v1/actions",
        json={"tool_name": "memory.clear", "arguments": {}},
        headers=auth(owner_a),
    )
    action_id = created.json()["id"]

    # Owner B cannot see or approve owner A's action.
    hidden = await client.get(f"/v1/actions/{action_id}", headers=auth(owner_b))
    assert hidden.status_code == 404

    refused = await client.post(
        f"/v1/actions/{action_id}/approve", json={}, headers=auth(owner_b)
    )
    assert refused.status_code == 404

    # And it is still pending for owner A.
    still = await client.get(f"/v1/actions/{action_id}", headers=auth(owner_a))
    assert still.json()["status"] == "pending"


async def test_approving_a_settled_action_is_refused(client: AsyncClient) -> None:
    token = await _device(client)
    created = await client.post(
        "/v1/actions",
        json={"tool_name": "memory.save", "arguments": {"content": "once"}},
        headers=auth(token),
    )
    action_id = created.json()["id"]
    assert created.json()["status"] == "executed"

    again = await client.post(
        f"/v1/actions/{action_id}/approve", json={}, headers=auth(token)
    )
    assert again.status_code == 409


async def test_actions_require_a_device_token(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/actions", json={"tool_name": "memory.list", "arguments": {}}
    )
    assert response.status_code == 401
