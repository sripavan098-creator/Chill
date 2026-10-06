"""Request and response schemas.

The API never returns embeddings or raw audio. `VerificationResponse` carries a
similarity score and a confidence band, not the underlying vector.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RegisterDeviceRequest(BaseModel):
    platform: str = Field(default="unknown", max_length=32)
    label: str | None = Field(default=None, max_length=120)


class RegisterDeviceResponse(BaseModel):
    owner_id: str
    device_id: str
    access_token: str
    created_at: datetime


class ConsentRequest(BaseModel):
    granted: bool
    policy_version: str | None = None


class ConsentResponse(BaseModel):
    granted: bool
    policy_version: str
    granted_at: datetime | None
    withdrawn_at: datetime | None


class EnrollmentSampleIn(BaseModel):
    phrase_id: str = Field(min_length=1, max_length=64)
    duration_ms: int = Field(ge=0)
    quality: float = Field(default=0.0, ge=0.0, le=1.0)
    # Base64-encoded audio for this phrase. Discarded after embedding.
    audio_base64: str = Field(min_length=1)


class EnrollRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    samples: list[EnrollmentSampleIn] = Field(min_length=1)


class EnrollmentResponse(BaseModel):
    owner_id: str
    display_name: str
    phrase_count: int
    embedding_dimensions: int
    model_version: str
    enrolled_at: datetime


class VerifyRequest(BaseModel):
    duration_ms: int = Field(ge=0)
    audio_base64: str = Field(min_length=1)


class VerificationResponse(BaseModel):
    outcome: str
    similarity: float
    confidence: float
    threshold: float
    reason: str
    attempts_remaining: int
    locked_out: bool


class ProfileResponse(BaseModel):
    owner_id: str
    display_name: str
    enrolled: bool
    phrase_count: int
    embedding_dimensions: int | None
    model_version: str | None
    consent_granted: bool
    consent_policy_version: str | None
    created_at: datetime


class DeleteResponse(BaseModel):
    deleted: bool
    detail: str


class DeleteProfileRequest(BaseModel):
    confirm: str = Field(description="Must be exactly 'DELETE'.")


class DeleteAccountRequest(BaseModel):
    confirm: str = Field(description="Must be exactly 'DELETE'.")
