# Chill Privacy Principles

## Voice Data

Voice data is sensitive biometric data.

Chill must:

- Ask explicit consent before voice enrollment.
- Explain why voice data is processed.
- Store only what is necessary.
- Avoid storing raw audio by default.
- Allow users to delete their voice profile.
- Not sell voice data.
- Provide transparent privacy controls.

## User Rights

Users should be able to:

- Withdraw consent.
- Delete voice data.
- Re-enroll voice.
- Export account data later.
- Delete account.

## Retention

- Keep voice embeddings only while the account is active.
- Delete voice data when the user requests deletion.
- A recording is never stored. Only a one-way digest of a scored recording is
  kept, so it can be recognised as a replay; it is deleted with the voice
  profile, when consent is withdrawn and when the account is deleted.
- Liveness challenge nonces are short-lived and single-use.
- Retain audit logs only as long as necessary for security.

## Communication

Do not claim:

- "Voice login is 100% secure."
- "Chill never makes mistakes."

Instead say:

- "Voice recognition helps Chill recognize you."
- "Additional verification may be required for sensitive actions."
