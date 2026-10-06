# Chill

Chill is a personal AI assistant that recognizes its owner by voice.

## Current Milestone

Chill v0.3 adds the voice backend:

- FastAPI service with device-scoped authentication
- Consent gating: enrollment is rejected without recorded consent
- Enrollment endpoint that stores an encrypted embedding and discards audio
- Verification endpoint with similarity scoring, rate limits and lockout
- Append-only audit log (no biometric payloads)
- Delete voice profile and delete account endpoints
- Mobile client wired to the backend behind `EXPO_PUBLIC_CHILL_API_URL`

The embedding model is a deterministic placeholder until milestone 4.

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

v0.3 adds the FastAPI voice backend and wires the mobile app to it behind a
flag. Verification still uses a placeholder embedding model. See
`docs/TASKS.md` for the current checklist.
