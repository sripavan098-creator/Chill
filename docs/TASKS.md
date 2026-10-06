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

## Milestone 2: Real Audio Recording

- [ ] Add expo-av or react-native-audio-recorder-player.
- [ ] Request microphone permission properly.
- [ ] Record enrollment audio.
- [ ] Show audio level indicator.
- [ ] Handle recording errors.
- [ ] Store enrollment state locally.

## Milestone 3: Voice Backend

- [ ] Create FastAPI service.
- [ ] Add enrollment endpoints.
- [ ] Add verification endpoints.
- [ ] Add consent checks.
- [ ] Add audit logs.
- [ ] Add rate limits.
- [ ] Store encrypted embeddings only.

## Milestone 4: Speaker Verification

- [ ] Integrate ECAPA-TDNN or WeSpeaker.
- [ ] Add voice activity detection.
- [ ] Add liveness/replay checks.
- [ ] Add confidence scoring.
- [ ] Add fallback logic.
