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
