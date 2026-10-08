"""Schemas for the assistant chat, memory and speech endpoints.

Embeddings and audio never appear in a response. A memory response carries the
text and its id; a chat response carries text only.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.actions import ActionOut


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageOut]


class ChatReplyResponse(BaseModel):
    reply: ChatMessageOut
    # Ids of the memories retrieved for this turn, so the client can show what
    # the answer drew on.
    used_memory_ids: list[str]
    model_version: str
    # The action the assistant proposed, after the engine applied its risk
    # rules. A low-risk action is already executed; a medium- or high-risk one
    # is pending approval.
    action: ActionOut | None = None


class MemoryCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    source: str = Field(default="manual", max_length=32)


class MemoryOut(BaseModel):
    id: str
    content: str
    source: str
    model_version: str
    created_at: datetime


class MemoryListResponse(BaseModel):
    memories: list[MemoryOut]


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class MemoryMatch(BaseModel):
    id: str
    content: str
    # Cosine similarity in [-1, 1]; higher is closer.
    similarity: float


class MemorySearchResponse(BaseModel):
    matches: list[MemoryMatch]


class TranscribeRequest(BaseModel):
    # Base64-encoded audio of the owner's speech. Discarded after decoding.
    audio_base64: str = Field(min_length=1)


class TranscribeResponse(BaseModel):
    text: str
    model_version: str


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class SpeakResponse(BaseModel):
    # Base64 audio in the requested format. This is the assistant's voice, not
    # the owner's, so it carries no biometric data.
    audio_base64: str
    content_type: str
    model_version: str
