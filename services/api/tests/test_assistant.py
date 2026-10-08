"""Assistant tests: chat, streaming, memory retrieval and speech.

Everything runs against the real ASGI app. The default LLM, text-embedding and
TTS providers are the deterministic placeholders, so the endpoints are exercised
end to end without a model.
"""

from __future__ import annotations

import base64
import json

from httpx import AsyncClient

from tests.conftest import auth, b64, register_device, synth_speech


async def _device(client: AsyncClient) -> str:
    device = await register_device(client)
    return device["access_token"]


async def test_chat_returns_reply_and_persists_history(client: AsyncClient) -> None:
    token = await _device(client)

    response = await client.post(
        "/v1/assistant/chat", json={"content": "Hello Chill"}, headers=auth(token)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"]["role"] == "assistant"
    assert body["reply"]["content"]
    assert body["model_version"] == "placeholder-llm-v1"
    assert body["used_memory_ids"] == []

    history = await client.get("/v1/assistant/history", headers=auth(token))
    assert history.status_code == 200
    roles = [message["role"] for message in history.json()["messages"]]
    assert roles == ["user", "assistant"]


async def test_chat_rejects_empty_message(client: AsyncClient) -> None:
    token = await _device(client)
    response = await client.post(
        "/v1/assistant/chat", json={"content": ""}, headers=auth(token)
    )
    assert response.status_code == 422


async def test_chat_requires_a_device_token(client: AsyncClient) -> None:
    response = await client.post("/v1/assistant/chat", json={"content": "hi"})
    assert response.status_code == 401


async def test_stream_emits_sse_and_persists_reply(client: AsyncClient) -> None:
    token = await _device(client)

    response = await client.post(
        "/v1/assistant/chat/stream",
        json={"content": "Stream please"},
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = [
        json.loads(line[len("data: ") :])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert events, "expected at least one SSE event"
    assert events[-1]["done"] is True
    assert "".join(event.get("delta", "") for event in events).strip()

    history = await client.get("/v1/assistant/history", headers=auth(token))
    roles = [message["role"] for message in history.json()["messages"]]
    assert roles == ["user", "assistant"]


async def test_memory_crud_and_search_ranking(client: AsyncClient) -> None:
    token = await _device(client)

    created = await client.post(
        "/v1/assistant/memories",
        json={"content": "My favourite tea is jasmine green tea."},
        headers=auth(token),
    )
    assert created.status_code == 200, created.text
    memory_id = created.json()["id"]

    listed = await client.get("/v1/assistant/memories", headers=auth(token))
    assert [item["id"] for item in listed.json()["memories"]] == [memory_id]

    # A query that shares vocabulary should rank the stored memory first.
    found = await client.post(
        "/v1/assistant/memories/search",
        json={"query": "jasmine tea", "top_k": 1},
        headers=auth(token),
    )
    assert found.status_code == 200, found.text
    matches = found.json()["matches"]
    assert matches and matches[0]["id"] == memory_id
    assert matches[0]["similarity"] > 0

    deleted = await client.delete(
        f"/v1/assistant/memories/{memory_id}", headers=auth(token)
    )
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True}

    listed_after = await client.get("/v1/assistant/memories", headers=auth(token))
    assert listed_after.json()["memories"] == []


async def test_memory_search_ignores_other_owners(client: AsyncClient) -> None:
    owner_a = await _device(client)
    owner_b = await _device(client)

    await client.post(
        "/v1/assistant/memories",
        json={"content": "Owner A keeps a red bicycle."},
        headers=auth(owner_a),
    )

    response = await client.post(
        "/v1/assistant/memories/search",
        json={"query": "red bicycle", "top_k": 5},
        headers=auth(owner_b),
    )
    assert response.status_code == 200
    assert response.json()["matches"] == []


async def test_chat_injects_retrieved_memory_ids(client: AsyncClient) -> None:
    token = await _device(client)
    created = await client.post(
        "/v1/assistant/memories",
        json={"content": "I live in Lisbon."},
        headers=auth(token),
    )
    memory_id = created.json()["id"]

    response = await client.post(
        "/v1/assistant/chat",
        json={"content": "Where do I live?"},
        headers=auth(token),
    )
    assert response.status_code == 200
    assert memory_id in response.json()["used_memory_ids"]


async def test_delete_memory_is_scoped_to_owner(client: AsyncClient) -> None:
    owner_a = await _device(client)
    owner_b = await _device(client)
    created = await client.post(
        "/v1/assistant/memories",
        json={"content": "Owner A secret."},
        headers=auth(owner_a),
    )
    memory_id = created.json()["id"]

    response = await client.delete(
        f"/v1/assistant/memories/{memory_id}", headers=auth(owner_b)
    )
    assert response.status_code == 404

    still_there = await client.get("/v1/assistant/memories", headers=auth(owner_a))
    assert [item["id"] for item in still_there.json()["memories"]] == [memory_id]


async def test_transcribe_returns_placeholder_text(client: AsyncClient) -> None:
    token = await _device(client)
    response = await client.post(
        "/v1/assistant/transcribe",
        json={"audio_base64": b64(synth_speech(seed=7))},
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["model_version"] == "placeholder-stt"
    assert body["text"] == ""


async def test_transcribe_rejects_bad_audio(client: AsyncClient) -> None:
    token = await _device(client)
    # Odd-length bytes cannot be a container or 16-bit PCM, so decoding fails.
    response = await client.post(
        "/v1/assistant/transcribe",
        json={"audio_base64": b64(b"\x00\x01\x02")},
        headers=auth(token),
    )
    assert response.status_code == 422


async def test_speak_returns_decodable_audio(client: AsyncClient) -> None:
    token = await _device(client)
    response = await client.post(
        "/v1/assistant/speak",
        json={"text": "Hello from Chill."},
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["content_type"] == "audio/wav"
    assert body["model_version"] == "placeholder-tts-v1"

    audio = base64.b64decode(body["audio_base64"], validate=True)
    assert audio[:4] == b"RIFF"


async def test_account_deletion_removes_assistant_data(client: AsyncClient) -> None:
    token = await _device(client)
    await client.post(
        "/v1/assistant/memories",
        json={"content": "Remember this."},
        headers=auth(token),
    )
    await client.post(
        "/v1/assistant/chat", json={"content": "Hi"}, headers=auth(token)
    )

    response = await client.request(
        "DELETE",
        "/v1/account",
        json={"confirm": "DELETE"},
        headers=auth(token),
    )
    assert response.status_code == 200, response.text

    # The token is gone with the account, so nothing is reachable.
    after = await client.get("/v1/assistant/history", headers=auth(token))
    assert after.status_code == 401
