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
- Add liveness checks before production.
- Add replay attack protection.
- Add failed attempt limits (done in v0.3).
- Add device binding later.
- Add audit logs (done in v0.3).

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
