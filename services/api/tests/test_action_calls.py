"""Parsing of model-proposed actions, and the chat -> action bridge."""

from __future__ import annotations

import json

from httpx import AsyncClient

from app.assistant.action_calls import extract_action
from tests.conftest import auth, register_device


def test_extract_action_pulls_out_the_block() -> None:
    reply = (
        "Sure, I can remember that.\n\n"
        "```action\n"
        '{"tool_name": "memory.save", "arguments": {"content": "likes tea"}, '
        '"summary": "Save a preference"}\n'
        "```"
    )
    clean, proposal = extract_action(reply)
    assert clean == "Sure, I can remember that."
    assert proposal is not None
    assert proposal.tool_name == "memory.save"
    assert proposal.arguments == {"content": "likes tea"}
    assert proposal.summary == "Save a preference"


def test_extract_action_ignores_a_reply_without_a_block() -> None:
    clean, proposal = extract_action("Just chatting, no action here.")
    assert proposal is None
    assert clean == "Just chatting, no action here."


def test_extract_action_drops_malformed_json() -> None:
    reply = "Here you go.\n```action\n{not valid json}\n```"
    clean, proposal = extract_action(reply)
    assert proposal is None
    # The block is still removed so the owner does not read raw JSON.
    assert "```action" not in clean


def test_extract_action_requires_a_tool_name() -> None:
    reply = '```action\n{"arguments": {"content": "x"}}\n```'
    _clean, proposal = extract_action(reply)
    assert proposal is None


def test_extract_action_rejects_non_object_arguments() -> None:
    reply = '```action\n{"tool_name": "memory.save", "arguments": "drop table"}\n```'
    _clean, proposal = extract_action(reply)
    assert proposal is None


def test_extract_action_keeps_only_the_first_block() -> None:
    reply = (
        '```action\n{"tool_name": "memory.save", "arguments": {"content": "a"}}\n```\n'
        '```action\n{"tool_name": "memory.clear", "arguments": {}}\n```'
    )
    clean, proposal = extract_action(reply)
    assert proposal is not None
    assert proposal.tool_name == "memory.save"
    assert clean == ""


async def test_chat_runs_a_low_risk_proposal(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]

    # The placeholder LLM echoes the user text, so embedding a valid action
    # block in the message drives the whole chat -> engine path.
    block = json.dumps(
        {
            "tool_name": "memory.save",
            "arguments": {"content": "The owner's dog is called Pip."},
            "summary": "Remember the dog's name",
        }
    )
    response = await client.post(
        "/v1/assistant/chat",
        json={"content": f"Remember this please.\n```action\n{block}\n```"},
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["action"] is not None
    assert body["action"]["status"] == "executed"
    assert body["action"]["risk_level"] == "low"
    # The raw JSON block is stripped from the stored reply.
    assert "```action" not in body["reply"]["content"]

    memories = await client.get("/v1/assistant/memories", headers=auth(token))
    contents = [item["content"] for item in memories.json()["memories"]]
    assert "The owner's dog is called Pip." in contents


async def test_chat_queues_a_high_risk_proposal_for_approval(
    client: AsyncClient,
) -> None:
    device = await register_device(client)
    token = device["access_token"]

    block = json.dumps(
        {"tool_name": "voice.delete_profile", "arguments": {}, "summary": "Delete it"}
    )
    response = await client.post(
        "/v1/assistant/chat",
        json={"content": f"Please do it.\n```action\n{block}\n```"},
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["action"] is not None
    # A high-risk proposal never runs from chat; it waits for approval.
    assert body["action"]["status"] == "pending"
    assert body["action"]["risk_level"] == "high"
    assert body["action"]["requires_confirmation"] is True


async def test_chat_survives_a_refused_proposal(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]

    block = json.dumps({"tool_name": "shell.run", "arguments": {"cmd": "ls"}})
    response = await client.post(
        "/v1/assistant/chat",
        json={"content": f"Run this.\n```action\n{block}\n```"},
        headers=auth(token),
    )
    # The unknown tool is refused but the conversation still returns.
    assert response.status_code == 200, response.text
    assert response.json()["action"] is None
