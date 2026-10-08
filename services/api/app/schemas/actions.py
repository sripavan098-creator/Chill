"""Schemas for the Action Engine.

An approval card needs to show the owner exactly what will run, so the request
and response carry the tool name, risk level, a human-readable summary and the
arguments. No secret is ever placed in `arguments` or `result`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ActionRequestIn(BaseModel):
    tool_name: str = Field(min_length=1, max_length=64)
    arguments: dict = Field(default_factory=dict)
    summary: str | None = Field(default=None, max_length=400)


class ActionOut(BaseModel):
    id: str
    tool_name: str
    risk_level: str
    status: str
    summary: str
    arguments: dict
    result: dict | None
    error: str | None
    requires_confirmation: bool
    expires_at: datetime | None
    created_at: datetime
    executed_at: datetime | None


class ActionListResponse(BaseModel):
    actions: list[ActionOut]


class ActionApproveRequest(BaseModel):
    # Required for a high-risk action; must equal "CONFIRM". Ignored otherwise.
    confirm: str | None = Field(default=None, max_length=32)


class ActionToolOut(BaseModel):
    name: str
    description: str
    risk_level: str
    requires_approval: bool
    requires_confirmation: bool
    parameters: list[str]


class ActionToolListResponse(BaseModel):
    tools: list[ActionToolOut]
