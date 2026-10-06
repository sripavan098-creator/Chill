# Chill API

FastAPI service for voice enrollment and verification. It stores encrypted
voice embeddings only, and never raw audio.

The embedding model is a deterministic placeholder. Milestone 4 replaces it
with a real speaker-verification model (ECAPA-TDNN or WeSpeaker) behind the
same `EmbeddingProvider` interface.

## Layout

```text
services/api/
├── app/
│   ├── api/          # devices, consent, enrollment, verification, account
│   ├── core/         # config, crypto, embeddings, vectors, tokens, errors
│   ├── db/           # SQLAlchemy models and async session
│   ├── schemas/      # request and response models
│   ├── services/     # audit log, rate limits
│   └── main.py       # app factory and routers
├── alembic/          # migrations
└── tests/            # pytest suite
```

## Running locally

With Docker (starts Postgres, applies migrations, serves on :8000):

```bash
cd services/api
docker compose up --build
```

Without Docker:

```bash
cd services/api
pip install -e ".[dev]"
cp .env.example .env          # then set CHILL_ENCRYPTION_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

Generate an encryption key:

```bash
python -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"
```

## Tests

```bash
cd services/api
pip install -e ".[dev]"
pytest        # 35 tests
ruff check app tests
```

Tests run the real ASGI application against an isolated SQLite database. No
application logic is mocked.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/devices` | Register a device, returns an owner-scoped token |
| GET | `/v1/consent` | Read consent status |
| PUT | `/v1/consent` | Grant or withdraw consent |
| POST | `/v1/enrollment` | Submit 5 samples, store the encrypted embedding |
| GET | `/v1/profile` | Enrollment and consent status |
| DELETE | `/v1/profile` | Delete the voice profile (`confirm: "DELETE"`) |
| POST | `/v1/verification` | Verify a sample against the stored embedding |
| DELETE | `/v1/account` | Delete the owner and all voice data (`confirm: "DELETE"`) |
| GET | `/health` | Liveness check |

## Privacy and security notes

- Audio is used to compute an embedding in memory and then discarded. It is
  never written to disk and never logged.
- Embeddings are encrypted at rest with AES-256-GCM.
- Enrollment is rejected unless consent is on record.
- Verification is rate limited, and repeated failures trigger a lockout.
- Deleting the profile or account requires an explicit confirmation token.
- The audit log records event names and outcomes, never biometric payloads.
- `CHILL_ENV=production` refuses to start with the development encryption key.

## Configuration

All settings use the `CHILL_` prefix and are read from the environment or a
`.env` file. See `.env.example` for the full list.
