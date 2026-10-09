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

- [x] Integrate ECAPA-TDNN (SpeechBrain `spkrec-ecapa-voxceleb`) behind `EmbeddingProvider`.
- [x] Keep the deterministic placeholder provider for the fast default test suite.
- [x] Add voice activity detection and sample quality gating before scoring.
- [x] Add confidence scoring (calibrated bands, `model_version` in the response).
- [x] Decode and embed in the request scope; raw audio is still never persisted.
- [x] Opt-in `speaker` test suite exercising the real model, including end to end.
- [ ] Tune the threshold against real field recordings before beta.

## Milestone 5: Stronger Voice Auth (v0.5)

- [x] Add replay protection (digest of decoded audio; a scored recording is refused).
- [x] Add device binding (profile tied to the enrolling device; `CHILL_ENFORCE_DEVICE_BINDING`).
- [x] Add single-use, time-boxed liveness challenges (`POST /v1/verification/challenge`).
- [x] Tighten rate limits and lockout for production (verification and challenge limits).
- [x] Alembic migration for the new tables and column.
- [x] Tests for replay, device binding, challenges and retention.
- [x] End-to-end smoke tests for the mobile journey (welcome → consent → enrollment → login → fallback → home → settings), driving the real Expo Router app.
- [x] Spoken challenge-response: each challenge carries a random phrase, transcribed and matched before scoring.
- [x] Pluggable speech-to-text (deterministic placeholder for tests; `whisper` for real use).
- [ ] Audio deepfake checks.
- [ ] Tune the threshold against real field recordings before beta.

## Milestone 6: Assistant — LLM, STT, TTS, Memory (v0.6)

- [x] LLM chat endpoint (`POST /v1/assistant/chat`) with conversation history.
- [x] Streaming chat over SSE (`POST /v1/assistant/chat/stream`).
- [x] Pluggable LLM provider: deterministic placeholder for tests, OpenAI-compatible for real use.
- [x] Speech-to-text endpoint (`POST /v1/assistant/transcribe`) for dictation. This is not authentication and never replaces voice verification.
- [x] Text-to-speech endpoint (`POST /v1/assistant/speak`) returning WAV audio.
- [x] Long-term personal memory: `POST/GET/DELETE /v1/assistant/memories` and `POST /v1/assistant/memories/search`.
- [x] Retrieval-augmented chat: the top memories are retrieved and placed in the system prompt as untrusted context.
- [x] Text embeddings stored encrypted (AES-256-GCM), never as plaintext; no embeddings in any response.
- [x] Alembic migration for `chat_messages` and `memories`.
- [x] Account deletion removes chat history and memories.
- [x] Assistant test suite (chat, streaming, memory ranking, STT, TTS, isolation).

## Milestone 7: Action Engine (v0.7)

- [x] Tool registry with explicit risk levels (low / medium / high); unknown tools refused.
- [x] Low-risk actions run immediately; medium- and high-risk actions wait for approval.
- [x] Approval cards: `POST /v1/actions/{id}/approve` and `/deny`, plus listing and lookup.
- [x] Step-up confirmation: a high-risk action also requires typing `CONFIRM`, so voice recognition is never sufficient on its own.
- [x] Approvals expire after a configurable TTL and are capped per owner.
- [x] Actions are owner-scoped: one owner cannot see, approve or run another's action.
- [x] The assistant can propose an action from chat; the engine still applies the risk rules.
- [x] Append-only audit log for requested / approved / denied / executed / failed / rejected.
- [x] Alembic migration for `action_requests`.
- [x] Account deletion removes the owner's actions.
- [x] Action Engine test suite (gating, approvals, confirmation, isolation, chat bridge).

## Milestone 8: Beta Hardening (v0.8)

### Backend

- [x] Client version policy endpoint (`GET /v1/version`), independent of the API version.
- [x] Configurable minimum / latest client version and update URL.
- [x] Request middleware: `X-Request-ID` correlation, declared body-size limit (413), and a generic error envelope that never leaks stack traces.
- [x] Rate limits for action approvals, speech-to-text and feedback.
- [x] Feedback intake (`POST /v1/feedback`, `GET /v1/feedback`) with a kind (general / bug / idea / privacy) and an hourly per-owner cap.
- [x] Shared account-deletion service reused by the account and profile endpoints.
- [x] Alembic migration for feedback reports; account deletion removes them.
- [x] Hardening test suite (payload size, error envelope, rate limits, feedback, account deletion).

### Mobile

- [x] Top-level error boundary with a calm fallback and retry.
- [x] Client version check on launch: update-required blocks, update-recommended is advisory, and the check fails open offline.
- [x] Feedback screen (kind + note, no audio attached) and a plain-language privacy/terms screen with document links.
- [x] Delete account flow behind a second confirmation, clearing profile, consent, memories and the device session.
- [x] Recording calibration guidance (too short / weak / good / strong) on enrollment samples.
- [x] Retry helper and normalized network errors for transient backend failures.
- [x] Backend account-deletion, feedback and version clients behind the existing API facade.
- [x] Tests for the new helpers and screens; the voice orb no longer starves the test renderer.

## Deferred: Deeper Liveness

- [ ] Replay detection beyond exact-match (partial capture, re-recording).
- [ ] Audio deepfake / synthetic-speech checks.
- [ ] Device-binding management (re-bind, unbind, second device).
