# L-8: Runbook

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Draft (sign-off: any engineer who has dry-run it) | 0.9.0 | 2026-10-12 | M12, §11, 2H | `infrastructure/`, `.railway/`, `apps/api/` |

Every step marked ✅ was executed on the date and commit shown. Unmarked steps are documented but not yet executed in this form, and each needs a dry run (§9).

## 1. Local setup from a clean machine

```bash
git clone https://github.com/FCDS-College/Nasa && cd Nasa
cp infrastructure/.env.example infrastructure/.env
# edit: two distinct random tokens of >= 32 chars, local passwords
python -c "import secrets; print(secrets.token_urlsafe(32))"   # run twice
docker compose -f infrastructure/compose.yaml up --build -d
```

The `api` container runs these, in order: `alembic upgrade head`, `python -m flame_api.seed`, `python -m flame_api.ingest`, then uvicorn.

**Vector index.** Run `docker compose -f infrastructure/compose.yaml exec api python -m flame_api.vector_index build`. This needs the `vector` extra, which the image installs.

**Local LLM.** Set `COMPOSE_PROFILES=local-llm` and `FLAME_OLLAMA_BASE_URL=http://ollama:11434` in `.env`, then run `docker compose -f infrastructure/compose.yaml --profile local-llm-setup run --rm ollama-pull` once while connected.

**Without Docker** ✅ 2026-10-11, working tree of `2afbc37`, PostgreSQL 16 from apt:

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e "apps/api[dev,cv,ingestion,vector]" -r ai/requirements.txt
cd apps/api
export FLAME_DATABASE_URL=postgresql+psycopg://flame:flame@127.0.0.1:5432/flame FLAME_API_AUTH_ENABLED=false PYTHONPATH=$PWD/../..:.
alembic upgrade head && python -m flame_api.seed && python -m flame_api.ingest && python -m flame_api.vector_index build
uvicorn flame_api.main:app --port 8000
```

Result on 2026-10-11:
- `seed` loaded 11 sources, 124 files, 182 image assets and 7 models;
- `ingest` ingested 3 PDF documents (39 pages, 37 chunks), skipped 100 files that are not on disk, and quarantined none;
- the index build embedded 37 chunks.

## 2. Migrations
- **Apply:** `alembic upgrade head` (inside `apps/api`, with `FLAME_DATABASE_URL`).
- **Roll back one:** `alembic downgrade -1`. Migration `0004` drops the Phase 2 tables. **Take a backup first**: they hold audit and publication history.
- ✅ 2026-10-11: on PostgreSQL 16 + pgvector, a fresh `upgrade head`, an upgrade from `main`'s `0003` schema, and `downgrade 0003_vector_index` followed by `upgrade head` all succeeded, with identical final schemas. CI repeats this on every PR.

## 3. Backup and restore

The commands are in [E2-10 §5](../data/OFFLINE_DATA_AND_SYNC.md#5-local-backup-and-restore), shared with H-6. **The restore drill is not yet dated**: it is Pending and is a Week 2 task for Anas (E2).

## 4. Secret rotation
1. Generate new values. Tokens are ≥ 32 characters, and the read and write tokens must differ.
2. Railway: `railway variables set FLAME_READ_API_TOKEN=…` on `flame-api`, and the same for the worker where it applies. Compose: edit `infrastructure/.env`, then `docker compose up -d api worker`.
3. Update every consumer of the read token: the web app's `FLAME_READ_API_TOKEN`, and AURA's credential vault entry for the `flame-api` connector.
4. AURA service key (`FLAME_AURA_SERVICE_TOKEN`): an AURA Super Admin issues a new `svc-flame` key and revokes the old one (AURA runbook §3.5).
5. Verify that `GET /api/health` with the new read token returns 200, and that the old token returns 401.

## 5. Model load and health check (L40S / local)
- **vLLM.** Start with `vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ --port 8001`, set `FLAME_VLLM_BASE_URL=http://<host>:8001`, then check that `GET /api/ai/providers` shows `vllm` as `up` with `model_present: true`.
- **Ollama.** `GET /api/ai/providers` should show `ollama` as `up`. ✅ 2026-10-11, Ollama 0.5.7 with `qwen2.5:3b-instruct-q4_K_M`.
- **Embeddings.** `python -m ai.providers.local.fastembed_embeddings verify --cache-dir …` must print the manifest sha256 (`51f1bd0a…`). ✅ 2026-10-11.

## 6. Railway (`.railway/railway.py`, committed in `780d89b`)

`.railway/railway.py` is Railway infrastructure-as-code (`railway-sdk>=0.2.0`). It defines project `flame-in-freefall-aura` with:
- **Postgres:** `pgvector/pgvector:pg18` with a 5 GB volume.
- **Redis:** with a 5 GB volume.
- **Bucket:** `versatile-bin-Yo7I`.
- **`flame-api`:** built from `apps/api/Dockerfile`; pre-deploy runs `alembic upgrade head && python -m flame_api.seed && python -m flame_api.ingest`; health check `/health/live`.
- **`flame-worker`:** the same image running `rq worker flame-analysis`.

Existing `FLAME_*` variables are kept with `preserve()`.

```bash
pip install -r .railway/requirements.txt
railway config plan      # review
railway config apply
```

**Gaps** (not changed in PR #14):
- `railway.py` doesn't list the new `FLAME_AI_*` / `FLAME_OLLAMA_*` variables. They can be set in the Railway UI and are then preserved.
- There is no vector-index build step.
- Railway Postgres is pg18 while Compose is pg16. The migrations are verified on pg16 only.

## 7. Common incidents

| Symptom | Likely cause | Fix |
|---|---|---|
| Chat returns `generation_unavailable` | No model reachable (`execution.reasons`) | `GET /api/ai/providers`: restart Ollama / check AURA; or check whether the mode blocks AURA |
| `CHAT_UNAVAILABLE` 503 | No LLM provider configured or permitted | Set `FLAME_OLLAMA_BASE_URL` or enable AURA, or leave `offline_only` |
| Search is lexical-only | Index missing or embedder unavailable | `vector_index build`; check the `fastembed` health |
| `aura` circuit `open` | AURA failed 3× | Waits 30 s by itself; check AURA's `/health/ready` |
| Analysis `MODEL_UNAVAILABLE` | Both CV providers failed (HF Space down and OpenCV missing) | Check the worker image has the `cv` extra |
| A file is `quarantined` | Unreadable, encrypted, checksum mismatch, invalid JSON | E2-8 §"inspect failed files" |
| First `seed` loads 0 files | Fixed in PR #14 (sources weren't flushed before the file lookup) | Upgrade |

## 8. Reproducing the demo from a tagged release (MVP §22)

```bash
git checkout v0.1.0-mvp     # see docs/releases/v0.1.0-mvp.md; tag pending approval
docker compose -f infrastructure/compose.yaml up --build
```

## 9. Dry-run record

| Date | Engineer | Commit | Sections | Result |
|---|---|---|---|---|
| 2026-10-11 | Lead (in the CI container, no Docker daemon images) | `2afbc37` working tree | 1 (without Docker), 2, 5 | pass |
| Pending | someone other than the Lead | — | all, from a clean machine | — |

## Known limitations
The Compose path, backup/restore and Railway steps have not been executed in this form. The acceptance criterion "executed from a clean machine by someone other than the Lead" is open.

## Changelog
- 0.9.0 (2026-10-12): first runbook; operational steps moved here from `infrastructure/README.md` and `apps/api/README.md`.
