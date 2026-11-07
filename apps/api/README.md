# Flame in Freefall API

> Operational procedures (deploy, migrations, backup/restore, secret rotation, incidents) now live in the [runbook](../../docs/operations/RUNBOOK.md). Offline deployment: [H-6](../../docs/hybrid-ai/PHASE_2_OFFLINE_DEPLOYMENT_GUIDE.md). This file keeps the overview.

The API is a local-first MVP implementing the v0.1 contract in `docs/api/openapi.json`. It persists resources in PostgreSQL, uses Redis/RQ for asynchronous image analysis, and stores originals/derived artifacts in MinIO locally or Railway's S3-compatible bucket in production. Compose enables bearer authentication by default. Each caller should have its own API key: `python -m flame_api.clients create web --scopes read` prints a key once (only its hash is stored); `list` and `revoke NAME` manage them. A `read` key is accepted for `GET`/`HEAD` and `POST /api/chat`, a `write` key for mutations such as analysis uploads. The older `FLAME_READ_API_TOKEN` / `FLAME_WRITE_API_TOKEN` are deprecated but still accepted with the same split; when set they must be distinct and at least 32 characters. Keys and tokens must not be committed or sent in URLs. Every `/api/*` route except `/api/health` is rate-limited per client in Redis (`FLAME_READ_RATE_LIMIT_PER_MINUTE`, `FLAME_WRITE_RATE_LIMIT_PER_MINUTE`, `FLAME_CHAT_RATE_LIMIT_PER_MINUTE`); details in [SECURITY.md](../../docs/operations/SECURITY.md). With `FLAME_ENVIRONMENT=production` the API refuses to start on the local default S3 and database credentials. Compose binds the host API port to loopback. The current separate-project Railway deployment uses public HTTPS with mandatory bearer auth; the write token is never shared with AURA.

## Start locally

1. Install Docker Desktop with Compose.
2. Copy `infrastructure/.env.example` to `infrastructure/.env`, replace local-only passwords and token placeholders, and generate two distinct random API tokens of at least 32 characters.
3. From the repository root, run `docker compose -f infrastructure/compose.yaml up --build`.
4. Open `http://127.0.0.1:8000/api/docs` or `http://localhost:3000` after starting the Next.js app with `npm run dev` in `apps/web`.

For the current AURA Track AP Link 2 deployment, register `https://flame-api-production-e948.up.railway.app/api/openapi.json` as the connector, leave `allow_private_network` disabled, set `read_only_attested: true`, and store only a read-scoped key (`python -m flame_api.clients create aura --scopes read`; the deprecated `FLAME_READ_API_TOKEN` also works) in AURA's credential vault. Never give AURA a write key or the upload token. A same-project private deployment can instead use the private service hostname and `allow_private_network: true`.

Optional Link 1 interpretations are disabled by default. To enable them, set `FLAME_AURA_ENABLED=true`, `FLAME_AURA_BASE_URL=https://aura-ai-production-03a4.up.railway.app`, and the AURA-issued `svc-flame` key as `FLAME_AURA_SERVICE_TOKEN` on both the API and worker. The worker sends only measured results and linked evidence in caller context (the DATA channel), requests local structured output, and validates citations and scientific claim limits before saving it. AURA failures leave the CV analysis completed with an unavailable interpretation. Set `FLAME_AURA_REQUIRE_LOCAL=false` when AURA's only model is a self-hosted GPU Space, which AURA treats as remote; the default `true` makes AURA answer 503 `all_providers_failed` in that setup.

### Dashboard chat

`POST /api/chat` (body `{query, conversation_id?}`, read token) powers the dashboard chat. Flame searches its own corpus, sends the question plus the top passages to the routed model as DATA-channel context (AURA's `context`, or a fenced system message for local models) with tools off, and keeps only citations that were in the retrieved set. No matching evidence means no model call. It answers through the model router (local Ollama/vLLM/llama.cpp or AURA; `docs/hybrid-ai/PHASE_2_HYBRID_AI_ARCHITECTURE.md`) and is limited to `FLAME_CHAT_RATE_LIMIT_PER_MINUTE` (default 30) requests per minute per client (per API process while Redis is unavailable). Since contract 0.2.0 it is in `docs/api/openapi.json`, marked `x-aura-exclude: true` so AURA never compiles it into a tool (ADR-004).

The API container runs Alembic, seeds the source registry and file checksums, and ingests available local PSI PDF/table files on startup. Originals remain under `datasets/raw/`; Compose mounts `datasets/` read-only. Missing raw files are skipped and counted, not downloaded implicitly. Re-run ingestion after new files are acquired with `docker compose -f infrastructure/compose.yaml exec api python -m flame_api.ingest`.

## Data behavior

Search starts with PostgreSQL lexical full-text retrieval. PDF matches carry page evidence; table matches carry row/cell evidence and source checksums. Combustion search excludes `FF-PSI-DSI` by default. The loader preserves original values, leaves unresolved units unset, and does not turn censored/approximate text into fabricated numbers. No vector results are advertised until a persistent embedding index is published.

The CV worker calls the existing `cv/flame_cv.py` pipeline. It enforces the contract's 10 MiB, 64-pixel minimum and 50-megapixel maximum, reports pixel measurements as measured and scale-derived dimensions as estimated, and never produces temperature. Interpretation is disabled unless separately configured.

### Optional Hugging Face CV inference

The local CV pipeline remains the default. To run its image analysis on Hugging Face, deploy the files in `cv/hf_space/` as a private Docker Space, copy `cv/flame_cv.py` into that Space at `cv/flame_cv.py`, and set these variables on both the API and worker:

```text
FLAME_CV_PROVIDER=hf_space
FLAME_CV_HF_SPACE_URL=https://<your-space-subdomain>.hf.space
FLAME_CV_HF_TOKEN=<read-scoped-Hugging-Face-token>
```

`FLAME_CV_HF_TOKEN` is optional for a public Space, but private Spaces are recommended to protect uploaded images. The worker sends only the image and pixel calibration needed for CV; the Space returns the existing analysis and artifacts, which the worker validates and stores as usual. `FLAME_CV_TIMEOUT_S` defaults to 300 seconds for Space cold starts. Setting `FLAME_CV_PROVIDER=local` (or omitting it) keeps inference on the worker. This CV Space is independent of LLM hosting and does not replace or change the AURA/LLM configuration.

## Tests

From the repo root, run `python -m pytest` (both suites), or from `apps/api` run `python -m pytest` (API tests only). The tests use SQLite and mocked queue/storage dependencies; run the Compose stack separately to verify PostgreSQL, MinIO, Redis and the worker together.