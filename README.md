# Chill

Chill is a personal AI assistant that recognizes its owner by voice.

## Current Milestone

Chill v0.5 adds stronger voice authentication:

- Replay protection: a recording that has already been scored is refused, matched by a digest of the decoded audio (never the audio itself)
- Device binding: the voice profile is tied to the device that enrolled it, so a stolen token alone cannot verify from another phone
- Single-use, time-boxed liveness challenges: the client asks for a nonce, says it aloud, and returns it with the recording, so a sample captured before the nonce existed cannot be reused
- Tightened verification and challenge rate limits with the existing failed-attempt lockout

These are real but partial. The challenge is a freshness check, not liveness
detection: a determined attacker can still read the nonce over a replayed
recording. Spoken-phrase challenge-response and audio deepfake detection are
future work. Voice remains one layer, not the security boundary.

Carried over from v0.4: ECAPA-TDNN (SpeechBrain `spkrec-ecapa-voxceleb`)
behind the `EmbeddingProvider` interface, a deterministic placeholder provider
for the fast test suite, voice activity detection and sample quality gating,
and confidence bands.

Carried over from v0.3: the FastAPI service with device-scoped authentication,
consent gating, enrollment, verification, an append-only audit log, and
delete-profile/account endpoints.

## Principles

- Voice recognition is a convenience layer, not the only security layer.
- No raw voice recordings are stored by default.
- Users can delete their voice profile.
- High-risk actions require stronger verification.
- No hidden background listening.
- No misleading security claims.

## Stack

- React Native
- Expo
- TypeScript
- Expo Router
- expo-audio (recording)
- AsyncStorage (local, non-biometric state)
- FastAPI + PostgreSQL (voice backend, v0.3+)
- ECAPA-TDNN speaker verification (v0.4)

## Repository Layout

```text
chill/
├── .github/            # Copilot / agent instructions
├── docs/               # PRD, tasks, security, privacy
├── design/             # Design system
├── apps/mobile/        # Expo + TypeScript mobile app
└── services/api/       # FastAPI voice backend
```

## Getting Started

Mobile:

```bash
cd apps/mobile
npm install
npm run start
```

Useful checks:

```bash
npm run typecheck
npm run lint
npm test
```

Backend:

```bash
cd services/api
docker compose up --build     # or see services/api/README.md
pytest
```

## Status

v0.5 adds stronger voice authentication: replay protection, device binding and
single-use liveness challenges, on top of v0.4's ECAPA-TDNN speaker
verification. The fast test suite runs on the deterministic placeholder
encoder; `pytest -m speaker` runs the real model. See `docs/TASKS.md` for the
current checklist.
