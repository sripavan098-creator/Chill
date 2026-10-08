"""Assistant endpoints: chat, long-term memory, speech-to-text, text-to-speech.

The chat turn retrieves the owner's most relevant memories, injects them into
the system prompt as untrusted data and streams the model's reply. Only text is
persisted: a transcript is what the owner said or typed, never a recording.

Speech-to-text here is a convenience for dictating a message, distinct from the
spoken-challenge transcriber used for verification. The audio is decoded in the
request scope and discarded; nothing is written.
"""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.actions.tools import describe_tools
from app.api.actions import to_action_out
from app.api.deps import DeviceDep, SessionDep
from app.assistant.action_calls import ActionProposal, extract_action
from app.assistant.prompts import build_system_prompt
from app.core.audio import AudioDecodeError, prepare
from app.core.errors import ChillError, NotFoundError, ValidationError
from app.db.models import ActionRequest, ChatMessage, Memory
from app.schemas.assistant import (
    ChatHistoryResponse,
    ChatMessageIn,
    ChatMessageOut,
    ChatReplyResponse,
    MemoryCreateRequest,
    MemoryListResponse,
    MemoryMatch,
    MemoryOut,
    MemorySearchRequest,
    MemorySearchResponse,
    SpeakRequest,
    SpeakResponse,
    TranscribeRequest,
    TranscribeResponse,
)
from app.services import audit, limits
from app.services import memory as memory_service

router = APIRouter(tags=["assistant"])


def _message_out(message: ChatMessage) -> ChatMessageOut:
    return ChatMessageOut(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def _memory_out(memory: Memory) -> MemoryOut:
    return MemoryOut(
        id=memory.id,
        content=memory.content,
        source=memory.source,
        model_version=memory.model_version,
        created_at=memory.created_at,
    )


async def _load_history(
    session: SessionDep, *, owner_id: str, limit: int
) -> list[ChatMessage]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.owner_id == owner_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    # The query returns newest first; the model needs them oldest first.
    return list(reversed(result.scalars().all()))


async def _retrieve_memories(
    request: Request,
    session: SessionDep,
    *,
    owner_id: str,
    query: str,
) -> list[tuple[Memory, float]]:
    settings = request.app.state.settings
    return await memory_service.search_memories(
        session,
        owner_id=owner_id,
        query=query,
        provider=request.app.state.text_embeddings,
        cipher=request.app.state.cipher,
        top_k=settings.memory_top_k,
        scan_limit=settings.memory_scan_limit,
    )


def _build_messages(history: list[ChatMessage]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in history]


async def request_proposed_action(
    request: Request,
    session: SessionDep,
    *,
    device,
    proposal: ActionProposal,
) -> ActionRequest | None:
    """Hand a model-proposed action to the engine.

    A proposal the engine refuses (unknown tool, bad arguments, rate limit) is
    dropped: the chat still returns the model's prose rather than failing the
    whole turn. The proposal is data, so the risk rules still apply.
    """
    engine = request.app.state.actions
    try:
        return await engine.request_action(
            session,
            owner_id=device.owner_id,
            device_id=device.id,
            tool_name=proposal.tool_name,
            arguments=proposal.arguments,
            summary=proposal.summary,
        )
    except ChillError:
        # The engine has already audited the rejection; keep the conversation.
        return None


@router.post("/assistant/chat", response_model=ChatReplyResponse)
async def chat(
    payload: ChatMessageIn,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> ChatReplyResponse:
    settings = request.app.state.settings
    llm = request.app.state.llm

    await limits.enforce_rate_limit(
        session,
        scope="chat",
        subject=device.id,
        limit=settings.chat_rate_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )

    matches = await _retrieve_memories(
        request, session, owner_id=device.owner_id, query=payload.content
    )
    history = await _load_history(
        session, owner_id=device.owner_id, limit=settings.chat_history_limit
    )

    user_message = ChatMessage(
        owner_id=device.owner_id, role="user", content=payload.content
    )
    session.add(user_message)
    await session.flush()

    tools = describe_tools() if settings.actions_enabled else []
    system_prompt = build_system_prompt(
        memories=[memory.content for memory, _ in matches], tools=tools
    )
    messages = [
        *_build_messages(history),
        {"role": "user", "content": payload.content},
    ]

    chunks: list[str] = []
    async for chunk in llm.stream(system_prompt=system_prompt, messages=messages):
        chunks.append(chunk)
    raw_reply = "".join(chunks).strip()

    # The model may propose an action. The proposal is data: the engine applies
    # the risk rules, so a high-risk proposal still needs approval.
    reply_text, proposal = extract_action(raw_reply)
    action_out = None
    if proposal is not None:
        action = await request_proposed_action(
            request, session, device=device, proposal=proposal
        )
        action_out = to_action_out(action) if action is not None else None

    assistant_message = ChatMessage(
        owner_id=device.owner_id,
        role="assistant",
        content=reply_text,
        model_version=llm.model_version,
    )
    session.add(assistant_message)

    await audit.record_event(
        session,
        event="assistant.chat",
        owner_id=device.owner_id,
        device_id=device.id,
        detail=f"model={llm.model_version} memories={len(matches)}",
    )
    await session.commit()

    return ChatReplyResponse(
        reply=_message_out(assistant_message),
        used_memory_ids=[memory.id for memory, _ in matches],
        model_version=llm.model_version,
        action=action_out,
    )


@router.post("/assistant/chat/stream")
async def chat_stream(
    payload: ChatMessageIn,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> StreamingResponse:
    """Stream the reply as server-sent events.

    Each event is `data: {json}\\n\\n` where the JSON is `{"delta": "..."}`; the
    final event is `{"done": true, "reply_id": "...", "model_version": "..."}`.
    The assistant turn is persisted before the stream ends so a dropped client
    connection does not lose the reply.
    """
    settings = request.app.state.settings
    llm = request.app.state.llm

    await limits.enforce_rate_limit(
        session,
        scope="chat",
        subject=device.id,
        limit=settings.chat_rate_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )

    matches = await _retrieve_memories(
        request, session, owner_id=device.owner_id, query=payload.content
    )
    history = await _load_history(
        session, owner_id=device.owner_id, limit=settings.chat_history_limit
    )
    system_prompt = build_system_prompt(
        memories=[memory.content for memory, _ in matches]
    )
    messages = [
        *_build_messages(history),
        {"role": "user", "content": payload.content},
    ]

    user_message = ChatMessage(
        owner_id=device.owner_id, role="user", content=payload.content
    )
    session.add(user_message)
    await session.flush()
    # Commit the user turn before streaming: the request session stays open, but
    # a client that disconnects mid-stream should still have its message saved.
    await session.commit()

    owner_id = device.owner_id
    device_id = device.id
    session_factory = request.app.state.session_factory

    async def event_stream() -> AsyncIterator[str]:
        chunks: list[str] = []
        async for chunk in llm.stream(system_prompt=system_prompt, messages=messages):
            chunks.append(chunk)
            yield f"data: {json.dumps({'delta': chunk})}\n\n"
        reply_text = "".join(chunks).strip()

        # A fresh session: the request-scoped one may be closed once the
        # response has started streaming.
        async with session_factory() as write_session:
            assistant_message = ChatMessage(
                owner_id=owner_id,
                role="assistant",
                content=reply_text,
                model_version=llm.model_version,
            )
            write_session.add(assistant_message)
            await audit.record_event(
                write_session,
                event="assistant.chat",
                owner_id=owner_id,
                device_id=device_id,
                detail=f"model={llm.model_version} memories={len(matches)}",
            )
            await write_session.commit()
            reply_id = assistant_message.id

        yield "data: " + json.dumps(
            {"done": True, "reply_id": reply_id, "model_version": llm.model_version}
        ) + "\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/assistant/history", response_model=ChatHistoryResponse)
async def history(
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> ChatHistoryResponse:
    settings = request.app.state.settings
    messages = await _load_history(
        session, owner_id=device.owner_id, limit=settings.chat_history_limit
    )
    return ChatHistoryResponse(messages=[_message_out(item) for item in messages])


@router.post("/assistant/memories", response_model=MemoryOut)
async def create_memory(
    payload: MemoryCreateRequest,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> MemoryOut:
    memory = await memory_service.add_memory(
        session,
        owner_id=device.owner_id,
        content=payload.content.strip(),
        provider=request.app.state.text_embeddings,
        cipher=request.app.state.cipher,
        source=payload.source,
    )
    await audit.record_event(
        session,
        event="memory.created",
        owner_id=device.owner_id,
        device_id=device.id,
        detail=f"source={payload.source}",
    )
    await session.commit()
    return _memory_out(memory)


@router.get("/assistant/memories", response_model=MemoryListResponse)
async def list_memories(
    session: SessionDep,
    device: DeviceDep,
) -> MemoryListResponse:
    memories = await memory_service.list_memories(session, owner_id=device.owner_id)
    return MemoryListResponse(memories=[_memory_out(item) for item in memories])


@router.delete("/assistant/memories/{memory_id}")
async def delete_memory(
    memory_id: str,
    session: SessionDep,
    device: DeviceDep,
) -> dict[str, bool]:
    deleted = await memory_service.delete_memory(
        session, owner_id=device.owner_id, memory_id=memory_id
    )
    if not deleted:
        raise NotFoundError("Memory not found.")
    await audit.record_event(
        session,
        event="memory.deleted",
        owner_id=device.owner_id,
        device_id=device.id,
    )
    await session.commit()
    return {"deleted": True}


@router.post("/assistant/memories/search", response_model=MemorySearchResponse)
async def search_memories(
    payload: MemorySearchRequest,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> MemorySearchResponse:
    settings = request.app.state.settings
    top_k = payload.top_k or settings.memory_top_k
    matches = await memory_service.search_memories(
        session,
        owner_id=device.owner_id,
        query=payload.query,
        provider=request.app.state.text_embeddings,
        cipher=request.app.state.cipher,
        top_k=top_k,
        scan_limit=settings.memory_scan_limit,
    )
    return MemorySearchResponse(
        matches=[
            MemoryMatch(id=memory.id, content=memory.content, similarity=round(score, 4))
            for memory, score in matches
        ]
    )


@router.post("/assistant/transcribe", response_model=TranscribeResponse)
async def transcribe(
    payload: TranscribeRequest,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> TranscribeResponse:
    """Transcribe a short recording of the owner's speech.

    The audio is decoded in the request scope and discarded; only the text is
    returned, and it is not stored. This is dictation, not verification: it does
    not identify the speaker and must not be used as an authentication check.
    """
    try:
        audio = base64.b64decode(payload.audio_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError("The sample is not valid base64 audio.") from exc
    if not audio:
        raise ValidationError("The sample is empty.")

    transcriber = request.app.state.transcriber
    try:
        decoded = prepare(audio)
    except AudioDecodeError as exc:
        raise ValidationError("The sample is not decodable audio.") from exc
    finally:
        del audio

    text = await transcriber.transcribe(
        decoded.samples, sample_rate=decoded.sample_rate
    )
    del decoded

    await audit.record_event(
        session,
        event="assistant.transcribed",
        owner_id=device.owner_id,
        device_id=device.id,
        detail=f"stt={transcriber.model_version}",
    )
    await session.commit()
    return TranscribeResponse(text=text, model_version=transcriber.model_version)


@router.post("/assistant/speak", response_model=SpeakResponse)
async def speak(
    payload: SpeakRequest,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> SpeakResponse:
    """Synthesise the assistant's reply as audio.

    The output is the assistant's voice, generated from text; it contains no
    recording of the owner. It is returned inline and not stored.
    """
    tts = request.app.state.tts
    audio = await tts.synthesize(payload.text)
    await audit.record_event(
        session,
        event="assistant.spoke",
        owner_id=device.owner_id,
        device_id=device.id,
        detail=f"tts={tts.model_version}",
    )
    await session.commit()
    return SpeakResponse(
        audio_base64=base64.b64encode(audio).decode(),
        content_type=tts.content_type,
        model_version=tts.model_version,
    )
