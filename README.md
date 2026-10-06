# Chill

Chill is a personal AI assistant that recognizes its owner by voice.

## Current Milestone

Chill v0.4 adds real speaker verification:

- ECAPA-TDNN (SpeechBrain `spkrec-ecapa-voxceleb`) behind the `EmbeddingProvider` interface
- Deterministic placeholder provider kept for the fast default test suite
- Voice activity detection and sample quality gating before scoring
- Calibrated confidence bands and `model_version` in the verification response
- Audio decoded and embedded in the request scope; raw audio is still never persisted

Carried over from v0.3: the FastAPI service with device-scoped authentication,
consent gating, enrollment, verification with rate limits and lockout, an
append-only audit log, and delete-profile/account endpoints.

Voice is still one layer, not the security boundary. Liveness, replay
protection and device binding land in v0.5.

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
- FastAPI + PostgreSQL (voice backend, v0.3)
- Speaker verification later

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

v0.4 adds real speaker verification with ECAPA-TDNN, plus voice activity
detection and sample quality gating. The fast test suite runs on the
deterministic placeholder encoder; `pytest -m speaker` runs the real model.
See `docs/TASKS.md` for the current checklist.
