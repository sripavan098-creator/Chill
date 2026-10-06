# Chill

Chill is a personal AI assistant that recognizes its owner by voice.

## Current Milestone

Chill v0.1 focuses on:

- Onboarding
- Microphone permission
- Voice biometric consent
- Voice enrollment UI
- Mock owner verification
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

## Status

Planning and scaffold phase. See `docs/TASKS.md` for the current checklist.
