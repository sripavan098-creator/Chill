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
- Add liveness checks before production (partial in v0.5, see below).
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

The client asks for a nonce, says it aloud, and returns the challenge id with
the recording. A nonce is bound to the owner, expires after
`CHILL_CHALLENGE_TTL_SECONDS` and is consumed on first use. A recording made
before the nonce existed cannot satisfy it, so a captured sample is harder to
reuse.

This is a freshness check, not liveness detection. A determined attacker can
still read the nonce aloud over a replayed recording. Spoken-phrase
challenge-response and audio deepfake checks are future work (Milestone 6) and
must not be claimed until they are built.

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
  never stores audio, embeddings or similarity scores.
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
