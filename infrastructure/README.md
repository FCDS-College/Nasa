# Infrastructure

> Operational procedures (deploy, migrations, backup/restore, secret rotation, incidents) now live in the [runbook](../docs/operations/RUNBOOK.md). Offline deployment: [H-6](../docs/hybrid-ai/PHASE_2_OFFLINE_DEPLOYMENT_GUIDE.md). This file keeps the overview.

`compose.yaml` provides the private local backend stack: FastAPI, PostgreSQL/pgvector, Redis, MinIO, and the RQ analysis worker. API and dependency ports bind to loopback only. `*.env` files remain untracked; begin with `.env.example` and replace its local-only values before sharing the host.

Start from the repository root with `docker compose -f infrastructure/compose.yaml up --build`. Raw datasets are mounted read-only and are not copied into the application image.

## Railway and AURA

`.railway/railway.py` is the Railway project configuration for the API, worker, PostgreSQL/pgvector, Redis, and object-storage bucket. Install `railway-sdk`, then review with `railway config plan` and apply with `railway config apply`. The API and worker build from `apps/api/Dockerfile`; the API runs migrations, metadata seeding, and ingestion before deployment. The API normalizes Railway's standard `postgresql://` URL to the installed psycopg 3 driver. Railway variables hold connection URLs and object-storage credentials; do not copy secret values into this repository. The raw NASA files are not in Git or the image: attach/ingest the intended dataset in a controlled persistent store before treating research results as complete.

Set `FLAME_API_AUTH_ENABLED=true` and provide distinct, randomly generated `FLAME_READ_API_TOKEN` and `FLAME_WRITE_API_TOKEN` values of at least 32 characters. Only store the read token in AURA's credential vault. Set `FLAME_AURA_ENABLED=true`, `FLAME_AURA_BASE_URL=https://aura-ai-production-03a4.up.railway.app`, and `FLAME_AURA_SERVICE_TOKEN` in the API and worker services to enable optional post-CV interpretations; create the `svc-flame` service key in AURA with access only to `POST /api/v3/chat`.

This deployment uses a separate Railway project from AURA, so Link 2 uses the generated public HTTPS API domain (`flame-api-production-e948.up.railway.app`), not private networking. Authentication is mandatory: AURA receives only the distinct `FLAME_READ_API_TOKEN` with `GET`/`HEAD` access; `FLAME_WRITE_API_TOKEN` stays only in Flame's secret store. Register `/api/openapi.json` in AURA as an OpenAPI connector, keep `allow_private_network` disabled, set `read_only_attested: true`, and store the read token in AURA's credential vault. Obtain Super Admin approval, then discover, compile, evaluate, approve, and deploy the blueprint. Link 1 remains disabled until AURA readiness is healthy and its Super Admin issues the scoped `svc-flame` key; then set that key and `FLAME_AURA_ENABLED=true` in both Flame services. Do not mark the integration proven until the AR-7 live report exists.
