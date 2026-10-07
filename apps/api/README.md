# Flame in Freefall API

The API is a local-first MVP implementing the v0.1 contract in `docs/api/openapi.json`. It persists resources in PostgreSQL, uses Redis/RQ for asynchronous image analysis, and stores originals/derived artifacts in MinIO locally or Railway's S3-compatible bucket in production. Compose enables bearer authentication by default: `FLAME_READ_API_TOKEN` is accepted only for `GET`/`HEAD`, while `FLAME_WRITE_API_TOKEN` is required for mutations such as analysis uploads. They must be distinct, at least 32 characters, and must not be committed or sent in URLs. Compose binds the host API port to loopback. The current separate-project Railway deployment uses public HTTPS with mandatory bearer auth; the write token is never shared with AURA.

## Start locally

1. Install Docker Desktop with Compose.
2. Copy `infrastructure/.env.example` to `infrastructure/.env`, replace local-only passwords and token placeholders, and generate two distinct random API tokens of at least 32 characters.
3. From the repository root, run `docker compose -f infrastructure/compose.yaml up --build`.
4. Open `http://127.0.0.1:8000/api/docs` or `http://localhost:3000` after starting the Next.js app with `npm run dev` in `apps/web`.

For the current AURA Track AP Link 2 deployment, register `https://flame-api-production-e948.up.railway.app/api/openapi.json` as the connector, leave `allow_private_network` disabled, set `read_only_attested: true`, and store only `FLAME_READ_API_TOKEN` in AURA's credential vault. Never give AURA the upload token. A same-project private deployment can instead use the private service hostname and `allow_private_network: true`.

Optional Link 1 interpretations are disabled by default. To enable them, set `FLAME_AURA_ENABLED=true`, `FLAME_AURA_BASE_URL=https://aura-ai-production-03a4.up.railway.app`, and the AURA-issued `svc-flame` key as `FLAME_AURA_SERVICE_TOKEN` on both the API and worker. The worker sends only measured results and linked evidence in caller context (the DATA channel), requests local structured output, and validates citations and scientific claim limits before saving it. AURA failures leave the CV analysis completed with an unavailable interpretation.

The API container runs Alembic, seeds the source registry and file checksums, and ingests available local PSI PDF/table files on startup. Originals remain under `datasets/raw/`; Compose mounts `datasets/` read-only. Missing raw files are skipped and counted, not downloaded implicitly. Re-run ingestion after new files are acquired with `docker compose -f infrastructure/compose.yaml exec api python -m flame_api.ingest`.

## Data behavior

Search starts with PostgreSQL lexical full-text retrieval. PDF matches carry page evidence; table matches carry row/cell evidence and source checksums. Combustion search excludes `FF-PSI-DSI` by default. The loader preserves original values, leaves unresolved units unset, and does not turn censored/approximate text into fabricated numbers. No vector results are advertised until a persistent embedding index is published.

The CV worker calls the existing `cv/flame_cv.py` pipeline. It enforces the contract's 10 MiB, 64-pixel minimum and 50-megapixel maximum, reports pixel measurements as measured and scale-derived dimensions as estimated, and never produces temperature. Interpretation is disabled unless separately configured.

## Tests

From `apps/api`, run `python -m pip install -e ".[dev,cv,ingestion]"` then `python -m pytest`. The tests use SQLite and mocked queue/storage dependencies; run the Compose stack separately to verify PostgreSQL, MinIO, Redis and the worker together.