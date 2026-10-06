"""Enrollment and profile management.

Enrollment accepts five short audio samples, turns each into an embedding,
averages them into a single owner embedding and stores only the encrypted
average. The raw samples are held in memory for the duration of the request and
are never written to the database.

Deleting the profile is a high-risk action, so it requires an explicit
step-up confirmation (`confirm: "DELETE"`).
"""

from __future__ import annotations

import base64
import binascii
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from sqlalchemy import delete, select

from app.api.consent import latest_consent
from app.api.deps import DeviceDep, SessionDep
from app.core.crypto import EmbeddingCipher
from app.core.errors import (
    ConsentRequiredError,
    IncompleteEnrollmentError,
    NotFoundError,
    ValidationError,
)
from app.core.vectors import pack_vector
from app.db.models import Enrollment, EnrollmentSample, Owner
from app.schemas.voice import (
    DeleteProfileRequest,
    DeleteResponse,
    EnrollmentResponse,
    EnrollRequest,
    ProfileResponse,
)
from app.services import audit

router = APIRouter(tags=["enrollment"])

DELETE_CONFIRMATION = "DELETE"


def _decode_audio(audio_base64: str, phrase_id: str) -> bytes:
    try:
        audio = base64.b64decode(audio_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError(f"Sample '{phrase_id}' is not valid base64 audio.") from exc
    if not audio:
        raise ValidationError(f"Sample '{phrase_id}' is empty.")
    return audio


@router.post("/enrollment", response_model=EnrollmentResponse)
async def create_enrollment(
    payload: EnrollRequest,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> EnrollmentResponse:
    settings = request.app.state.settings
    cipher: EmbeddingCipher = request.app.state.cipher
    provider = request.app.state.embeddings

    consent = await latest_consent(session, device.owner_id)
    if consent is None or not consent.granted:
        await audit.record_event(
            session,
            event="enrollment.rejected",
            outcome="denied",
            owner_id=device.owner_id,
            device_id=device.id,
            detail="consent_missing",
        )
        await session.commit()
        raise ConsentRequiredError("Voice consent is required before enrollment.")

    if len(payload.samples) != settings.required_phrases:
        raise IncompleteEnrollmentError(
            f"Exactly {settings.required_phrases} voice samples are required."
        )

    phrase_ids = [sample.phrase_id for sample in payload.samples]
    if len(set(phrase_ids)) != len(phrase_ids):
        raise ValidationError("Each phrase must be recorded exactly once.")

    for sample in payload.samples:
        if sample.duration_ms < settings.min_sample_ms:
            raise ValidationError(
                f"Sample '{sample.phrase_id}' is too short. "
                f"Hold the phrase for at least {settings.min_sample_ms}ms."
            )
        if sample.duration_ms > settings.max_sample_ms:
            raise ValidationError(f"Sample '{sample.phrase_id}' is too long.")

    # Embed each sample. The raw audio lives only in this loop.
    embeddings: list[list[float]] = []
    sample_rows: list[tuple[str, int, float, bytes]] = []
    for sample in payload.samples:
        audio = _decode_audio(sample.audio_base64, sample.phrase_id)
        embedding = await provider.embed(audio, duration_ms=sample.duration_ms)
        embeddings.append(embedding)
        sample_rows.append(
            (
                sample.phrase_id,
                sample.duration_ms,
                sample.quality,
                cipher.encrypt(pack_vector(embedding)),
            )
        )
        del audio

    owner_embedding = await provider.average(embeddings)
    owner_blob = cipher.encrypt(pack_vector(owner_embedding))

    # Replace any previous enrollment atomically.
    existing = await session.execute(
        select(Enrollment).where(Enrollment.owner_id == device.owner_id)
    )
    enrollment = existing.scalar_one_or_none()
    if enrollment is not None:
        await session.execute(
            delete(EnrollmentSample).where(
                EnrollmentSample.enrollment_id == enrollment.id
            )
        )
        enrollment.phrase_count = len(embeddings)
        enrollment.embedding_dimensions = provider.dimensions
        enrollment.embedding_encrypted = owner_blob
        enrollment.model_version = "placeholder-v0.3"
        enrollment.updated_at = datetime.now(UTC)
    else:
        enrollment = Enrollment(
            owner_id=device.owner_id,
            phrase_count=len(embeddings),
            embedding_dimensions=provider.dimensions,
            embedding_encrypted=owner_blob,
            model_version="placeholder-v0.3",
        )
        session.add(enrollment)
        await session.flush()

    for phrase_id, duration_ms, quality, blob in sample_rows:
        session.add(
            EnrollmentSample(
                enrollment_id=enrollment.id,
                phrase_id=phrase_id,
                duration_ms=duration_ms,
                quality=quality,
                embedding_encrypted=blob,
            )
        )

    owner = await session.get(Owner, device.owner_id)
    assert owner is not None
    if payload.display_name:
        owner.display_name = payload.display_name.strip() or owner.display_name

    await audit.record_event(
        session,
        event="enrollment.created",
        owner_id=device.owner_id,
        device_id=device.id,
        detail=f"phrases={len(embeddings)} model=placeholder-v0.3",
    )
    await session.commit()

    return EnrollmentResponse(
        owner_id=device.owner_id,
        display_name=owner.display_name,
        phrase_count=enrollment.phrase_count,
        embedding_dimensions=enrollment.embedding_dimensions,
        model_version=enrollment.model_version,
        enrolled_at=enrollment.updated_at,
    )


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    session: SessionDep,
    device: DeviceDep,
) -> ProfileResponse:
    owner = await session.get(Owner, device.owner_id)
    if owner is None:
        raise NotFoundError("Owner not found.")

    result = await session.execute(
        select(Enrollment).where(Enrollment.owner_id == device.owner_id)
    )
    enrollment = result.scalar_one_or_none()
    consent = await latest_consent(session, device.owner_id)

    return ProfileResponse(
        owner_id=owner.id,
        display_name=owner.display_name,
        enrolled=enrollment is not None,
        phrase_count=enrollment.phrase_count if enrollment else 0,
        embedding_dimensions=enrollment.embedding_dimensions if enrollment else None,
        model_version=enrollment.model_version if enrollment else None,
        consent_granted=bool(consent and consent.granted),
        consent_policy_version=consent.policy_version if consent else None,
        created_at=owner.created_at,
    )


@router.delete("/profile", response_model=DeleteResponse)
async def delete_profile(
    payload: DeleteProfileRequest,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> DeleteResponse:
    if payload.confirm != DELETE_CONFIRMATION:
        raise ValidationError("Deleting the voice profile requires confirmation.")

    result = await session.execute(
        select(Enrollment.id).where(Enrollment.owner_id == device.owner_id)
    )
    enrollment_ids = result.scalars().all()
    if enrollment_ids:
        await session.execute(
            delete(EnrollmentSample).where(
                EnrollmentSample.enrollment_id.in_(enrollment_ids)
            )
        )
        await session.execute(delete(Enrollment).where(Enrollment.id.in_(enrollment_ids)))

    await audit.record_event(
        session,
        event="profile.deleted",
        owner_id=device.owner_id,
        device_id=device.id,
    )
    await session.commit()
    return DeleteResponse(deleted=True, detail="Voice profile deleted.")
