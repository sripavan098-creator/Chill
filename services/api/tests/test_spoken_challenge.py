"""Spoken challenge-response (v0.5).

The default transcriber is the deterministic placeholder, so these tests attach
the transcript directly instead of using a speech model. They verify the
pipeline: the challenge carries a phrase, a wrong phrase is refused before
scoring, and a wrong phrase does not lock the owner out.
"""

from __future__ import annotations

from httpx import AsyncClient

from app.core.transcription import attach_transcript
from tests.conftest import (
    auth,
    b64,
    enroll,
    grant_consent,
    make_settings,
    register_device,
    request_challenge_body,
    sample_audio,
    synth_speech,
)

SEEDS = (1, 2, 3, 4, 5)


async def _enrolled(client: AsyncClient) -> str:
    device = await register_device(client)
    token = device["access_token"]
    await grant_consent(client, token)
    samples = [
        (f"phrase-{index + 1}", sample_audio(seed), 2400)
        for index, seed in enumerate(SEEDS)
    ]
    assert (await enroll(client, token, samples=samples)).status_code == 200
    return token


async def _submit(
    client: AsyncClient, token: str, *, challenge: dict, transcript: str, audio: bytes
):
    with attach_transcript(transcript):
        return await client.post(
            "/v1/verification",
            json={
                "duration_ms": 2400,
                "audio_base64": b64(audio),
                "challenge_id": challenge["challenge_id"],
            },
            headers=auth(token),
        )


# --- Challenge carries a phrase ----------------------------------------------


async def test_challenge_includes_a_phrase_to_say(client: AsyncClient) -> None:
    device = await register_device(client)
    token = device["access_token"]

    body = await request_challenge_body(client, token)
    assert body["challenge_id"]
    assert body["phrase"]
    # The phrase is a real instruction, not the raw nonce.
    assert "code" in body["phrase"].lower()
    assert body["phrase"] != body["nonce"]


async def test_spoken_challenge_can_be_disabled(tmp_path, app) -> None:
    from httpx import ASGITransport
    from httpx import AsyncClient as Http

    from app.main import create_app

    settings = make_settings(tmp_path, require_spoken_challenge=False)
    plain_app = create_app(settings)
    async with plain_app.router.lifespan_context(plain_app):
        transport = ASGITransport(app=plain_app)
        async with Http(transport=transport, base_url="http://chill.test") as http:
            device = await register_device(http)
            token = device["access_token"]
            body = await request_challenge_body(http, token)
            assert body["phrase"] is None


# --- Matching the phrase -----------------------------------------------------


async def test_correct_phrase_verifies_the_speaker(client: AsyncClient) -> None:
    token = await _enrolled(client)
    challenge = await request_challenge_body(client, token)

    response = await _submit(
        client,
        token,
        challenge=challenge,
        transcript=challenge["phrase"],
        audio=sample_audio(SEEDS[0]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["outcome"] == "success"


async def test_wrong_phrase_is_refused_before_scoring(client: AsyncClient) -> None:
    token = await _enrolled(client)
    challenge = await request_challenge_body(client, token)

    # Same (genuine) voice, but the speaker said the wrong words.
    response = await _submit(
        client,
        token,
        challenge=challenge,
        transcript="hey chill your code is totally different words",
        audio=sample_audio(SEEDS[0]),
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "CHALLENGE_PHRASE_MISMATCH"


async def test_misheard_phrase_does_not_lock_the_owner_out(client: AsyncClient) -> None:
    token = await _enrolled(client)

    # A run of mis-transcriptions (bad microphone), then a clean attempt. None
    # of the mismatches should count as failed identity attempts.
    for _ in range(3):
        challenge = await request_challenge_body(client, token)
        response = await _submit(
            client, token, challenge=challenge, transcript="nonsense", audio=sample_audio(SEEDS[0])
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "CHALLENGE_PHRASE_MISMATCH"

    challenge = await request_challenge_body(client, token)
    good = await _submit(
        client,
        token,
        challenge=challenge,
        transcript=challenge["phrase"],
        audio=sample_audio(SEEDS[0]),
    )
    assert good.status_code == 200, good.text
    assert good.json()["outcome"] == "success"


async def test_phrase_mismatch_is_audited(client: AsyncClient, app) -> None:
    token = await _enrolled(client)
    challenge = await request_challenge_body(client, token)
    await _submit(
        client, token, challenge=challenge, transcript="wrong", audio=sample_audio(SEEDS[0])
    )

    from sqlalchemy import select

    from app.db.models import AuditLog, VerificationChallenge

    async with app.state.session_factory() as session:
        events = (
            await session.execute(
                select(AuditLog).where(AuditLog.event == "verification.rejected")
            )
        ).scalars().all()
        assert any("challenge_phrase" in (entry.detail or "") for entry in events)

        stored = (
            await session.execute(
                select(VerificationChallenge).where(
                    VerificationChallenge.id == challenge["challenge_id"]
                )
            )
        ).scalar_one()
        assert stored.heard_text == "wrong"


async def test_transcript_is_committed_for_a_successful_attempt(
    client: AsyncClient, app
) -> None:
    token = await _enrolled(client)
    challenge = await request_challenge_body(client, token)
    await _submit(
        client,
        token,
        challenge=challenge,
        transcript=challenge["phrase"],
        audio=sample_audio(SEEDS[0]),
    )

    from sqlalchemy import select

    from app.db.models import VerificationChallenge

    async with app.state.session_factory() as session:
        stored = (
            await session.execute(
                select(VerificationChallenge).where(
                    VerificationChallenge.id == challenge["challenge_id"]
                )
            )
        ).scalar_one()
        assert stored.heard_text == challenge["phrase"]


# --- Interaction with identity scoring ---------------------------------------


async def test_wrong_speaker_with_the_right_phrase_still_fails(client: AsyncClient) -> None:
    token = await _enrolled(client)
    challenge = await request_challenge_body(client, token)

    # Someone else reads the phrase correctly: the phrase check passes, the
    # identity check does not.
    response = await _submit(
        client,
        token,
        challenge=challenge,
        transcript=challenge["phrase"],
        audio=synth_speech(seed=99, amplitude=0.55),
    )
    assert response.status_code == 200, response.text
    assert response.json()["outcome"] == "failure"
