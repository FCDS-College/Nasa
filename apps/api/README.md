# Flame in Freefall API

The API is a local, private-network MVP. It implements the v0.1 contract in `docs/api/openapi.json`, persists resources in PostgreSQL, uses Redis/RQ for asynchronous image analysis, and stores originals/derived artifacts in MinIO. Compose enables bearer authentication by default: `FLAME_READ_API_TOKEN` is accepted only for `GET`/`HEAD`, while `FLAME_WRITE_API_TOKEN` is required for mutations such as analysis uploads. They must be distinct, at least 32 characters, and must not be committed or sent in URLs. Compose still binds the host API port to loopback; use a private network for AURA and never expose the API publicly.

## Start locally

1. Install Docker Desktop with Compose.
2. Copy `infrastructure/.env.example` to `infrastructure/.env`, replace local-only passwords and token placeholders, and generate two distinct random API tokens of at least 32 characters.
3. From the repository root, run `docker compose -f infrastructure/compose.yaml up --build`.
4. Open `http://127.0.0.1:8000/api/docs` or `http://localhost:3000` after starting the Next.js app with `npm run dev` in `apps/web`.

For AURA Track AP Link 2, configure the AURA OpenAPI connector with only `FLAME_READ_API_TOKEN`, set `read_only_attested: true`, and store the token in AURA's credential vault. Never give AURA the upload token. Both services must be able to reach each other over a private network; the default host loopback binding alone is not a remote connector route.

The API container runs Alembic, seeds the source registry and file checksums, and ingests available local PSI PDF/table files on startup. Originals remain under `datasets/raw/`; Compose mounts `datasets/` read-only. Missing raw files are skipped and counted, not downloaded implicitly. Re-run ingestion after new files are acquired with `docker compose -f infrastructure/compose.yaml exec api python -m flame_api.ingest`.

## Data behavior

Search starts with PostgreSQL lexical full-text retrieval. PDF matches carry page evidence; table matches carry row/cell evidence and source checksums. Combustion search excludes `FF-PSI-DSI` by default. The loader preserves original values, leaves unresolved units unset, and does not turn censored/approximate text into fabricated numbers. No vector results are advertised until a persistent embedding index is published.

The CV worker calls the existing `cv/flame_cv.py` pipeline. It enforces the contract's 10 MiB, 64-pixel minimum and 50-megapixel maximum, reports pixel measurements as measured and scale-derived dimensions as estimated, and never produces temperature. Interpretation is disabled unless separately configured.

## Tests

From `apps/api`, run `python -m pip install -e ".[dev,cv,ingestion]"` then `python -m pytest`. The tests use SQLite and mocked queue/storage dependencies; run the Compose stack separately to verify PostgreSQL, MinIO, Redis and the worker together.