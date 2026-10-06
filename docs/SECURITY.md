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
- Store encrypted voice embeddings later.
- Add liveness checks before production.
- Add replay attack protection.
- Add failed attempt limits.
- Add device binding later.
- Add audit logs.

## Mobile Rules

- Use secure storage for tokens.
- Do not log secrets.
- Do not expose embeddings to client.
- Use HTTPS for all backend calls.

## Forbidden Features

- Hidden background listening.
- Silent recording.
- Bypassing OS authentication.
- Replacing device biometrics.
- Claiming 100% security.
