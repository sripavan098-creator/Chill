# Chill Security Model

## Core Rule

Voice recognition is a convenience layer, not a full security boundary.

## Authentication Layers

1. App profile ownership.
2. Voice owner recognition.
3. PIN or OS biometric fallback.
4. Strong confirmation for high-risk actions.

## High-Risk Actions

The following require more than voice recognition:

- Deleting account
- Deleting voice profile
- Changing authentication settings
- Accessing highly sensitive personal data
- Payments
- Automation that modifies system settings

## Voice Security Rules

- Do not store raw audio by default.
- Store encrypted voice embeddings (AES-256-GCM, done in v0.3).
- Add liveness checks before production (partial in v0.5: spoken challenge-response, see below).
- Add replay attack protection (done in v0.5).
- Add failed attempt limits (done in v0.3).
- Add device binding (done in v0.5).
- Add audit logs (done in v0.3).

## Stronger Voice Auth (v0.5)

Three layers sit on top of similarity scoring. Each is real but partial, and
none of them is liveness detection on its own.

### Replay protection

When a sample is accepted for scoring, a digest of the decoded audio is
recorded. A later submission whose digest matches is refused before it reaches
the encoder. Only the digest is stored, never the audio. The match is exact, so
it catches the direct replay of a previously accepted recording but not a
re-recording of a playback.

### Device binding

Enrollment records the device that submitted the samples. Verification from a
different device is refused (`DEVICE_NOT_BOUND`). A stolen token alone is not
enough to verify from an attacker's phone. Set `CHILL_ENFORCE_DEVICE_BINDING`
to `false` to allow the same owner to verify from a second device. There is no
re-bind or unbind flow yet.

### Single-use challenges

The client asks for a challenge, is shown a phrase, says it aloud, and returns
the challenge id with the recording. A challenge is bound to the owner, expires
after `CHILL_CHALLENGE_TTL_SECONDS` and is consumed on first use. A recording
made before the phrase existed cannot satisfy it, so a captured sample is
harder to reuse.

### Spoken challenge-response

Each challenge carries a random three-word phrase
(`Hey Chill, your code is alpha bravo charlie`). The speaker reads it, and the
recording is transcribed with speech-to-text and compared against the stored
phrase before the speaker embedding is computed. A recording that does not
contain the phrase is refused with `CHALLENGE_PHRASE_MISMATCH` and does **not**
count toward the lockout, so a bad microphone cannot lock an owner out.

Matching is lenient by design: all the phrase's distinguishing words must be
heard, in any order, with the wake words ignored. Strict equality would reject
genuine attempts whenever the recogniser mis-hears an ordinary word, pushing
owners to the PIN fallback.

This is the freshness check described above, strengthened so a blind replay
does not pass. It is still **not liveness detection**: a determined attacker
can read the phrase aloud over a replayed recording, and a cloned voice can say
it in the owner's voice. The transcript is stored for audit (the words the
speaker chose to say, not biometric data). Set
`CHILL_REQUIRE_SPOKEN_CHALLENGE=false` to disable it.

Speech-to-text is pluggable. The default provider is a deterministic
placeholder that returns an empty transcript; it exists for the test suite and
must never run in production. Set `CHILL_TRANSCRIPTION_PROVIDER=whisper` to use
a small faster-whisper model (install the `stt` extra). Audio deepfake
detection and true liveness remain future work and must not be claimed until
they are built.

## Assistant and Memory (v0.6)

- The LLM provider is pluggable. The default is a deterministic offline
  placeholder for the test suite and must never run in production; production
  requires an OpenAI-compatible endpoint and refuses to start without a key.
- Retrieved memories are injected into the system prompt inside an explicit
  untrusted-content boundary. A memory is data the model may read, never an
  instruction it should follow, so a stored note cannot hijack the assistant.
- Text embeddings are stored encrypted (AES-256-GCM), like voice embeddings.
  Embeddings are never returned to the client.
- Speech-to-text (`/v1/assistant/transcribe`) is dictation, not
  authentication. It never authorises anything and never replaces voice
  verification.
- Chat text is stored so the conversation can continue. It is deleted with the
  account.

## Action Engine (v0.7)

The Action Engine is the only path from the assistant to a side effect. Its
rules are enforced server-side, not by the client or the model:

- A tool must be registered. There is no generic "run this code" tool, so the
  registry is the whole surface. An unknown tool is refused and audited.
- Every tool declares a risk level. `low` runs immediately; `medium` and
  `high` are queued as pending approvals and do not run until the owner
  approves them.
- A `high` tool additionally requires typing the exact confirmation phrase
  (`CONFIRM`). Approval alone is not enough, and voice recognition is never
  sufficient for a high-risk action.
- A tool's arguments are validated against its declared parameters before the
  action is created; unknown arguments are refused.
- Actions are owner-scoped. One owner cannot see, approve, deny or run
  another owner's action.
- Approvals expire after a configurable TTL and the number of pending
  approvals per owner is capped.
- A model-proposed action is data, not a command: it goes through the same
  risk rules, and a high-risk proposal from chat still waits for approval.
  Action proposals are honoured on the non-streaming chat endpoint only.
- Every transition (requested, approved, denied, executed, failed, rejected)
  is written to the append-only audit log with the tool name and risk level,
  never the arguments or result payloads.
- Action arguments and results are stored for the approval card and the audit
  trail. A tool must never place a secret in either.

## Backend Rules (v0.3)

- Audio is embedded in memory and discarded; it is never written to disk.
- Embeddings are encrypted at rest. The encryption key comes from the
  environment and is never committed. `CHILL_ENV=production` refuses to start
  with the shared development key.
- Device tokens are stored only as keyed HMAC hashes.
- Enrollment is rejected unless consent is on record. Withdrawing consent
  deletes the stored enrollment.
- Verification is rate limited per owner, and repeated failures trigger a
  time-boxed lockout.
- A scored recording is remembered as a digest so it cannot be replayed; the
  digest is voice-derived, so it is deleted with the enrollment, on consent
  withdrawal and on account deletion.
- Liveness challenges are single-use and time-boxed, and are rate limited
  separately from verification.
- Deleting the voice profile or the account requires an explicit confirmation
  token.
- The audit log stores event names, outcomes and opaque identifiers only. It
  never stores audio, embeddings or similarity scores. A spoken challenge
  stores its phrase and the speech-to-text transcript, which are text the
  speaker chose to say rather than biometric data.
- Embeddings and audio are never returned to the client; responses carry
  scores and statuses only.
- Serve the API over HTTPS. The service itself sets no cookies and keeps no
  server-side sessions.

## Mobile Rules

- Use secure storage for tokens (expo-secure-store; in-memory fallback).
- Do not log secrets.
- Do not expose embeddings to client.
- Use HTTPS for all backend calls.
- Raw audio is uploaded only when a backend is configured, is held in memory
  just long enough to send, and is never persisted.

## Forbidden Features

- Hidden background listening.
- Silent recording.
- Bypassing OS authentication.
- Replacing device biometrics.
- Claiming 100% security.
