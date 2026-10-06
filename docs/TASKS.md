# Chill Tasks

## Milestone 0: Repo Foundation

- [x] Create repository.
- [x] Add README.
- [x] Add AGENTS.md.
- [x] Add docs/PRD.md.
- [x] Add docs/SECURITY.md.
- [x] Add docs/PRIVACY.md.
- [x] Add design/DESIGN.md.

## Milestone 1: Chill Mobile Onboarding UI

- [x] Create Expo app inside apps/mobile.
- [x] Use TypeScript.
- [x] Use Expo Router.
- [x] Create app theme from design/DESIGN.md.
- [x] Create welcome screen.
- [x] Create microphone permission screen.
- [x] Create voice consent screen.
- [x] Create voice enrollment screen.
- [x] Create enrollment success screen.
- [x] Create mock voice login screen.
- [x] Create fallback PIN placeholder screen.
- [x] Create assistant home screen.
- [x] Create settings screen.
- [x] Add delete voice profile button.
- [x] Use mock API client.
- [x] Use mock audio recorder.
- [x] Add navigation flow.
- [x] Add basic accessibility labels.

## Milestone 2: Real Audio Recording (v0.2)

- [x] Use expo-audio (expo-av is deprecated on SDK 57).
- [x] Request microphone permission properly, with a denied state and a settings shortcut.
- [x] Record real enrollment audio to a temporary file.
- [x] Show a recording timer and progress indicator.
- [x] Check recording duration and reject samples that are too short or too long.
- [x] Handle recording errors with retry.
- [x] Delete the temporary recording before the sample is accepted.
- [x] Store enrollment status locally (AsyncStorage), never raw audio.
- [x] Add unit and integration tests for the recording, permission and enrollment flows.

## Milestone 3: Voice Backend (v0.3)

- [x] Create FastAPI service (`services/api`).
- [x] Add enrollment endpoints (5 samples, encrypted embedding).
- [x] Add verification endpoints (similarity scoring, lockout).
- [x] Add consent checks (enrollment gated on recorded consent).
- [x] Add audit logs (append-only, no biometric payloads).
- [x] Add rate limits (fixed-window, DB-backed) and failed-attempt lockout.
- [x] Store encrypted embeddings only (AES-256-GCM; raw audio discarded).
- [x] Delete voice profile and delete account endpoints with step-up confirmation.
- [x] Alembic migration, Dockerfile and docker-compose for local runs.
- [x] Backend test suite (35 tests, real ASGI app over SQLite).
- [x] Mobile client for the backend, behind `EXPO_PUBLIC_CHILL_API_URL`.

## Milestone 4: Speaker Verification (v0.4)

- [ ] Integrate ECAPA-TDNN or WeSpeaker.
- [ ] Add voice activity detection.
- [ ] Add liveness/replay checks.
- [ ] Add confidence scoring.
- [ ] Add fallback logic.
