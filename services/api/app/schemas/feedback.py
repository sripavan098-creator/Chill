"""Schemas for in-app feedback and crash reports.

The message is a bounded, free-form note. No schema field carries a device
identifier, location, transcript or biometric value, so a report cannot leak
more than the user typed.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

FEEDBACK_KINDS = ("general", "bug", "crash", "privacy")


class FeedbackRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    kind: str = Field(default="general", max_length=16)
    app_version: str | None = Field(default=None, max_length=32)
    platform: str | None = Field(default=None, max_length=32)


class FeedbackResponse(BaseModel):
    id: str
    kind: str
    created_at: datetime
    detail: str
