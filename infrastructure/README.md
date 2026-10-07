# Infrastructure

`compose.yaml` provides the private local backend stack: FastAPI, PostgreSQL/pgvector, Redis, MinIO, and the RQ analysis worker. API and dependency ports bind to loopback only. `*.env` files remain untracked; begin with `.env.example` and replace its local-only values before sharing the host.

Start from the repository root with `docker compose -f infrastructure/compose.yaml up --build`. Raw datasets are mounted read-only and are not copied into the application image.
