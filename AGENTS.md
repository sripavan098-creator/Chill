# Chill Agent Rules

You are building Chill, a personal AI assistant with owner voice recognition.

## Project Rules

- Read docs/PRD.md, docs/TASKS.md, docs/SECURITY.md, and docs/PRIVACY.md first.
- Do not push directly to main.
- Create a feature branch.
- Make small, focused changes.
- Do not invent requirements.
- Do not add background listening.
- Do not store raw audio by default.
- Do not make voice the only authentication method for sensitive actions.
- Always provide fallback authentication.
- Use mock services before real backend services.
- Keep the UI friendly, calm, and accessible.
- Follow design/DESIGN.md.
- Run lint/typecheck/build when available.
- Update docs/TASKS.md after completing work.

## Mobile Rules

- Use React Native + Expo.
- Use TypeScript.
- Use Expo Router.
- Keep components reusable.
- Use StyleSheet or design tokens before adding heavy UI libraries.
- Support loading, error, empty, and retry states.

## Audio Rules (v0.2)

- Record with expo-audio. expo-av is deprecated on SDK 57.
- Write recordings to a temporary cache file only.
- Delete the temporary file before a sample is accepted; never persist raw audio.
- Store only enrollment status (voice enrolled, consent, timestamps) on the device.
- Keep recording logic in `hooks/` and `features/`; screens stay presentational.
- Run `npm test`, `npm run typecheck`, and `npm run lint` before committing.

## Testing Rules (mobile)

- `apps/mobile/__tests__/app.e2e.test.tsx` drives the real Expo Router app end to
  end. Use it as the harness for screen-level work.
- `@testing-library/react-native` v14 `render` is async. `renderRouter` returns
  that promise with the router helpers attached, so `await` it and return it
  inside an object (returning it directly makes `await` unwrap the helpers).
- Import `screen` from `@testing-library/react-native`, not from
  `expo-router/testing-library` (the re-export snapshots an empty placeholder).
- `renderRouter` switches Jest to fake timers. Restore real timers right after
  the first render (`jest.useRealTimers()`) or the mock API's `setTimeout`
  delays never resolve.
- Wrap `fireEvent.press`/`changeText` in `await act(async () => { ... })` so
  React flushes the update before the next assertion.
- Native audio, file system and storage are faked in `jest.setup.ts`; drive them
  through `@/test/mocks/audioMockState`.
- `standard-navigation` must stay in `transformIgnorePatterns` for expo-router's
  testing library to render.

## Security Rules

- No secrets in code.
- No raw audio storage unless explicit consent exists.
- Add rate limiting later for voice attempts.
- Prepare PIN fallback flow.
- Prepare delete voice profile flow.

## Spoken Challenge / Speech-to-Text Rules (v0.5)

- Each verification challenge carries a random phrase (`app/core/phrases.py`).
  The speaker reads it; the recording is transcribed and matched before the
  speaker embedding is computed.
- Matching is lenient: the phrase's distinguishing words must be heard, in any
  order, with wake words ignored. Do not tighten it to exact equality.
- A wrong or mis-heard phrase (`CHALLENGE_PHRASE_MISMATCH`, HTTP 422) must NOT
  count toward the verification lockout.
- Speech-to-text is behind `Transcriber` (`app/core/transcription.py`). The
  default `placeholder` provider is for tests only and must never run in
  production. `CHILL_TRANSCRIPTION_PROVIDER=whisper` selects the real model.
- Backend tests attach a transcript with `attach_transcript(...)` from
  `app.core.transcription` when exercising the verification endpoint, since the
  placeholder cannot recognise the synthetic audio. Tests for the spoken check
  itself pass a wrong transcript to force a mismatch.
- Do not describe spoken challenge-response as liveness detection. It is a
  freshness check, not deepfake or liveness analysis.
