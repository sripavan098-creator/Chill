# Chill

Chill is a personal AI assistant that recognizes its owner by voice.

## Current Milestone

Chill v0.2 focuses on real audio recording:

- Onboarding and microphone permission (with a denied state)
- Voice biometric consent
- Voice enrollment that records real audio samples
- Duration checks and retry for each of the five phrases
- Temporary recordings deleted before a sample is accepted
- Local enrollment status (no raw audio stored)
- Mock owner verification with success and failure paths
- PIN fallback placeholder
- Privacy settings placeholder

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
- FastAPI later
- PostgreSQL later
- Speaker verification later

## Repository Layout

```text
chill/
├── .github/            # Copilot / agent instructions
├── docs/               # PRD, tasks, security, privacy
├── design/             # Design system
├── apps/mobile/        # Expo + TypeScript mobile app
└── services/           # Backend services (empty until v0.3)
```

## Getting Started

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

## Status

v0.2 records real audio for enrollment, keeps only enrollment status on the
device, and still uses a mock verification model. See `docs/TASKS.md` for the
current checklist.
