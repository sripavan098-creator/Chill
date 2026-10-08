# Chill

Chill is a personal AI assistant that recognizes its owner by voice.

## Current Milestone

Chill v0.6 turns the verified owner into an assistant, and v0.7 lets it act:

- **Chat** (`/v1/assistant/chat`) and streaming chat over SSE, behind a
  pluggable LLM provider. The default provider is a deterministic offline
  placeholder; set `LLM_PROVIDER=openai` to reach any OpenAI-compatible
  endpoint (OpenAI, Ollama, vLLM).
- **Speech-to-text** (`/v1/assistant/transcribe`) for dictation. This is not
  authentication and never replaces voice verification.
- **Text-to-speech** (`/v1/assistant/speak`) returning WAV audio.
- **Long-term personal memory**: store, list, search and delete facts. The top
  matches are retrieved and placed in the system prompt as untrusted context.
  Text embeddings are stored encrypted, never as plaintext.
- **Action Engine** (v0.7): the assistant can propose tools from a registry
  where each tool carries a risk level. Low-risk tools run immediately;
  medium- and high-risk tools become approval cards and do not run until the
  owner approves them. A high-risk tool additionally requires typing
  `CONFIRM`, so voice recognition is never sufficient on its own. Every
  transition is audited.

Carried over from v0.5, stronger voice authentication:

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
- OpenAI-compatible LLM, STT and TTS providers (v0.6, pluggable)
- Encrypted text embeddings for personal memory (v0.6)
- Risk-gated Action Engine with approvals and audit (v0.7)

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
npm test          # unit, hook and end-to-end journey tests
```

Backend:

```bash
cd services/api
docker compose up --build     # or see services/api/README.md
pytest
```

## Status

v0.6 adds LLM chat, STT, TTS and long-term personal memory on top of the
verified voice profile; v0.7 adds the risk-gated Action Engine with approval
cards and an audit trail. The fast test suite runs entirely on deterministic
placeholder providers; `pytest -m speaker` runs the real ECAPA model. See
`docs/TASKS.md` for the current checklist.
