# Chill API

FastAPI service for voice enrollment and verification. It stores encrypted
voice embeddings only, and never raw audio.

Speaker verification uses ECAPA-TDNN (SpeechBrain's `spkrec-ecapa-voxceleb`)
behind the `EmbeddingProvider` interface. A deterministic placeholder provider
implements the same interface for the fast default test suite. Select with
`CHILL_EMBEDDING_PROVIDER` (`ecapa` or `placeholder`).

Stronger voice auth (v0.5) adds three layers on top of scoring: replay
protection (a recording that was already scored is refused), device binding
(the profile is tied to the enrolling device) and single-use, time-boxed
challenges. See `docs/SECURITY.md` for what each does and does not cover.

## Layout

```text
services/api/
├── app/
│   ├── api/          # devices, consent, enrollment, verification, account
│   ├── core/         # config, crypto, audio, embeddings, vectors, tokens, errors
│   ├── db/           # SQLAlchemy models and async session
│   ├── schemas/      # request and response models
│   ├── services/     # audit log, rate limits, replay, challenges
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

To run the real speaker encoder, install the extra and point the provider at it.
The model weights download once into `CHILL_MODEL_CACHE_DIR`.

```bash
pip install -e ".[dev,speaker]"
export CHILL_EMBEDDING_PROVIDER=ecapa
```

## Tests

```bash
cd services/api
pip install -e ".[dev]"
pytest        # fast suite on the placeholder encoder
ruff check app tests
```

The `speaker` suite exercises the real ECAPA model and is opt-in:

```bash
pip install -e ".[dev,speaker]"
pytest -m speaker
```

The fast suite runs the real ASGI application against an isolated SQLite
database. No application logic is mocked. The speaker suite synthesises speech
locally with Piper when a voice model is available, and skips otherwise.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/devices` | Register a device, returns an owner-scoped token |
| GET | `/v1/consent` | Read consent status |
| PUT | `/v1/consent` | Grant or withdraw consent |
| POST | `/v1/enrollment` | Submit 5 samples, store the encrypted embedding |
| GET | `/v1/profile` | Enrollment, consent and device-binding status |
| DELETE | `/v1/profile` | Delete the voice profile (`confirm: "DELETE"`) |
| POST | `/v1/verification/challenge` | Issue a single-use, time-boxed nonce |
| POST | `/v1/verification` | Verify a sample against the stored embedding |
| DELETE | `/v1/account` | Delete the owner and all voice data (`confirm: "DELETE"`) |
| GET | `/health` | Liveness check |

## Privacy and security notes

- Audio is used to compute an embedding in memory and then discarded. It is
  never written to disk and never logged.
- Embeddings are encrypted at rest with AES-256-GCM.
- Enrollment is rejected unless consent is on record.
- Verification is rate limited, and repeated failures trigger a lockout.
- A recording that was already scored is refused (replay protection), matched
  by a digest of the decoded audio; the audio itself is never kept.
- The voice profile is bound to the enrolling device by default, and
  verification requires a single-use, time-boxed challenge.
- Deleting the profile or account requires an explicit confirmation token.
- The audit log records event names and outcomes, never biometric payloads.
- `CHILL_ENV=production` refuses to start with the development encryption key.

## Configuration

All settings use the `CHILL_` prefix and are read from the environment or a
`.env` file. See `.env.example` for the full list.
