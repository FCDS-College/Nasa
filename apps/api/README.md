# Flame in Freefall API

The API is a local, private-network MVP. It implements the v0.1 contract in `docs/api/openapi.json`, persists resources in PostgreSQL, uses Redis/RQ for asynchronous image analysis, and stores originals/derived artifacts in MinIO. Do not expose the unauthenticated API or upload route to a public network.

## Start locally

1. Install Docker Desktop with Compose.
2. Copy `infrastructure/.env.example` to `infrastructure/.env` and replace the local-only passwords before sharing the machine/network.
3. From the repository root, run `docker compose -f infrastructure/compose.yaml up --build`.
4. Open `http://127.0.0.1:8000/api/docs` or `http://localhost:3000` after starting the Next.js app with `npm run dev` in `apps/web`.

The API container runs Alembic, seeds the source registry and file checksums, and ingests available local PSI PDF/table files on startup. Originals remain under `datasets/raw/`; Compose mounts `datasets/` read-only. Missing raw files are skipped and counted, not downloaded implicitly. Re-run ingestion after new files are acquired with `docker compose -f infrastructure/compose.yaml exec api python -m flame_api.ingest`.

## Data behavior

Search starts with PostgreSQL lexical full-text retrieval. PDF matches carry page evidence; table matches carry row/cell evidence and source checksums. Combustion search excludes `FF-PSI-DSI` by default. The loader preserves original values, leaves unresolved units unset, and does not turn censored/approximate text into fabricated numbers. No vector results are advertised until a persistent embedding index is published.

The CV worker calls the existing `cv/flame_cv.py` pipeline. It enforces the contract's 10 MiB, 64-pixel minimum and 50-megapixel maximum, reports pixel measurements as measured and scale-derived dimensions as estimated, and never produces temperature. Interpretation is disabled unless separately configured.

## Tests

From `apps/api`, run `python -m pip install -e ".[dev,cv,ingestion]"` then `python -m pytest`. The tests use SQLite and mocked queue/storage dependencies; run the Compose stack separately to verify PostgreSQL, MinIO, Redis and the worker together.