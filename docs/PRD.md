# Chill Product Requirements Document

## Product

Chill is a personal AI assistant that recognizes its owner by voice.

## Primary Goal

The assistant must identify the owner using voice enrollment and voice verification.

## MVP Scope

Chill v0.1 includes:

1. Welcome screen.
2. Microphone permission explanation.
3. Voice biometric consent screen.
4. Voice enrollment flow with 5 phrases.
5. Mock voice verification login.
6. PIN fallback placeholder.
7. Assistant home screen.
8. Settings screen with delete voice profile option.

## Non-Goals for v0.1

- Real speaker verification model.
- Always-on wake word.
- Background listening.
- Replacing OS biometrics.
- Unlocking the device.
- Payments.
- Multi-user voice profiles.
- Voice cloning.
- Production backend.

## User Flow

1. User opens Chill.
2. User sees welcome screen.
3. User grants microphone permission.
4. User consents to voice processing.
5. User records 5 enrollment phrases.
6. Chill creates a mock owner voice profile.
7. User can verify with voice using mock verification.
8. If verification fails, Chill shows fallback option.
9. User can delete voice profile in settings.

## Voice Enrollment Phrases

1. "Hey Chill, this is my voice."
2. "Hey Chill, unlock my assistant."
3. "Hey Chill, remember me."
4. "Hey Chill, keep my data private."
5. "Hey Chill, start listening."

## Security Rules

- Voice recognition is not sufficient for high-risk actions.
- Use fallback authentication.
- Store only encrypted voice embeddings later, not raw audio.
- Add attempt limits later.
- Log authentication attempts later.

## Privacy Rules

- Explicit consent is required.
- Voice data can be deleted.
- No selling of voice data.
- Minimal data collection.
- Clear privacy policy.

## v0.6 Scope: Assistant (LLM, STT, TTS, Memory)

Once the owner is verified, Chill can hold a conversation and remember things.

1. Chat with the assistant, with streaming replies.
2. Speech-to-text for dictation. This is not authentication.
3. Text-to-speech replies in the assistant's voice.
4. Long-term personal memory: save, list, search and delete facts.
5. Retrieval-augmented answers: the closest memories are retrieved and used as
   context for the reply.

Non-goals for v0.6: fine-tuning, a hosted vector database, multi-user memory
sharing, and using STT for authentication.

## v0.7 Scope: Action Engine

The assistant can propose actions, under explicit risk rules.

1. A tool registry, where every tool declares a risk level.
2. Low-risk actions run immediately.
3. Medium- and high-risk actions become approval cards and run only on approval.
4. High-risk actions also require an explicit confirmation phrase.
5. Owner-scoped actions, approval TTLs, a pending cap, and an audit trail.
6. The assistant may propose an action from chat; the engine still applies the
   risk rules.

Non-goals for v0.7: arbitrary code execution, tools that touch the operating
system, payments, and any action that bypasses the owner's approval.
