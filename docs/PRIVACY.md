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

## Assistant, Memory and Actions (v0.6–v0.7)

- Chat text is stored so the conversation can continue, and is deleted with the
  account. Speech-to-text audio is decoded in memory and discarded; only the
  transcript is kept.
- Long-term memory stores the facts the owner chooses to keep, plus an
  encrypted embedding of each. Memories can be listed, searched and deleted
  individually, and are deleted with the account. No embedding is ever returned
  to the client.
- The assistant's spoken replies (text-to-speech) are generated audio, not the
  owner's voice, and carry no biometric data.
- Actions record the tool name, risk level, the arguments the owner approved
  and the result, so the approval card and the audit trail can be shown. The
  owner can review and deny any action that is waiting for approval.

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
