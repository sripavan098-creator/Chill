# Chill Services

Backend services for Chill live here.

- `services/api/` — FastAPI enrollment and verification service (v0.3). See
  `services/api/README.md`. The mobile app uses it only when
  `EXPO_PUBLIC_CHILL_API_URL` is set; otherwise it runs local-only.
- `services/voice/` — Speaker verification model and embedding pipeline (v0.4).
