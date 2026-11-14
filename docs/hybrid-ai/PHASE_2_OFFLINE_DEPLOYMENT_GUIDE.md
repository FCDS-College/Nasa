# H-6: Offline deployment guide

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas); storage sections Anas (E2) | Draft (sign-off: the engineer who dry-runs it offline) | 0.9.1 | 2026-11-12 | 2H Tasks 4, 7 | `infrastructure/compose.yaml`, `infrastructure/.env.example`, `apps/api/Dockerfile` |

Linked from the [L-8 runbook](../operations/RUNBOOK.md). Data availability, backup and the sync policy are in [E2-10](../data/OFFLINE_DATA_AND_SYNC.md).

## 1. Hardware prerequisites

| Profile | CPU | RAM | Disk | GPU | What runs |
|---|---|---|---|---|---|
| Minimum (CPU) | 4 cores | 16 GB | 40 GB free | none | Postgres, Redis, MinIO, API, worker, Ollama `qwen2.5:3b` (measured: about 50–78 s per answer) |
| Recommended | 8+ cores | 32 GB | 100 GB | optional | same, faster CPU inference, room for local mirrors |
| GPU | any | 32 GB | 100 GB | L40S 48 GB | add vLLM `Qwen2.5-7B-Instruct-AWQ` (`FLAME_VLLM_BASE_URL`) |

## 2. Storage layout

| Volume / path | Holds | Size (measured where noted) |
|---|---|---|
| `postgres-data` | metadata, evidence, vectors | grows with corpus; ~50 MB for the committed corpus |
| `minio-data` | uploads, masks, overlays | per analysis ~1–10 MB |
| `redis-data` | queue (AOF) | small |
| `model-cache` → `/app/models/fastembed` | embedding model; reranker model (since 2026-11-12) | 67,181,750 B for the embedding model; 90,992,115 B for the reranker's `model.onnx` (m, 2026-11-12) |
| `ollama-models` → `/root/.ollama` | local LLM | 1,929,912,432 B for `qwen2.5:3b` (m) |
| `datasets/raw/` (bind mount, git-ignored) | PSI/DSI mirrors | ~GBs; see E2-10 |

## 3. Images: pull and export while connected

```bash
cd infrastructure
COMPOSE_PROFILES=local-llm docker compose build            # api/worker image includes ai/, cv/, NTRS PDFs
COMPOSE_PROFILES=local-llm docker compose pull postgres redis minio minio-init ollama
docker save -o flame-images.tar \
  pgvector/pgvector:pg16 redis:7-alpine chrislusf/seaweedfs:4.53 \
  amazon/aws-cli@sha256:acc32af784911165a8e78b63950625d174ba79b800a66a436c974689c87cd755 \
  ollama/ollama:0.5.7 flame-in-freefall-api flame-in-freefall-worker
sha256sum flame-images.tar > flame-images.tar.sha256
# On the offline host:
sha256sum -c flame-images.tar.sha256 && docker load -i flame-images.tar
```

## 4. Models: install and verify (with checksums)

Follow [H-3 §2](PHASE_2_LOCAL_MODEL_REGISTRY.md#2-download-and-verification-procedure). The search reranker is on by default (ADR-006), so prepare its model in the same cache while connected, then check it loads offline:

```bash
python -m ai.providers.local.cross_encoder prepare --cache-dir /app/models/fastembed
python -m ai.providers.local.cross_encoder verify  --cache-dir /app/models/fastembed
```

Without it, search falls back to the fused order (`reranking.status = "unavailable"`) and chat answers are not cached; `FLAME_RERANKER_ENABLED=false` turns reranking off instead. Then set:

```text
FLAME_EMBEDDING_OFFLINE=true     # never download; a missing model is reported
FLAME_OLLAMA_BASE_URL=http://ollama:11434
COMPOSE_PROFILES=local-llm
```

`docker run --rm -v flame-in-freefall_model-cache:/m alpine tar cf - /m > model-cache.tar` (and likewise for `ollama-models`) moves prepared volumes to another host. Torch weights for `cv/video_*` research scripts (H-1 row 8) go under `TORCH_HOME` if those scripts are used.

## 5. Environment configuration (names only)

- **Execution:** `FLAME_AI_EXECUTION_MODE=offline_only`.
- **Local models:** `FLAME_OLLAMA_BASE_URL`, `FLAME_OLLAMA_MODEL`, `FLAME_LLM_TIMEOUT_S`, `FLAME_EMBEDDING_CACHE_DIR`, `FLAME_EMBEDDING_OFFLINE`.
- **Keep, but they are blocked in `offline_only`:** `FLAME_AURA_*`, `FLAME_CV_HF_*`.
- **Auth:** `FLAME_READ_API_TOKEN`, `FLAME_WRITE_API_TOKEN`.
- **Storage:** `POSTGRES_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`.

The full list is in `infrastructure/.env.example`.

## 6. First start with no network

1. Remove the default route, or start on an isolated network (`docker network create --internal` for the project network is the strict variant).
2. `docker compose -f infrastructure/compose.yaml up -d`. The API runs migrations, seed and ingest; it never downloads anything.
3. Check `GET /api/ai/providers`:
   - `mode = offline_only`;
   - `ollama`, `fastembed` and `flame_cv` are `up`;
   - `aura` and `hf_space` are `blocked`.
4. Build the index if the cache is present: `docker compose exec api python -m flame_api.vector_index build`.
5. Ask a question through the web app. The answer must show local execution (H-5 S11).

## 7. Backup and restore

The commands and the drill record are in E2-10 §5. They cover PostgreSQL (`pg_dump -Fc`), the MinIO bucket and the model volumes.

## 8. Recovery from a missing or corrupt model

| Symptom (`/api/ai/providers`) | Fix |
|---|---|
| `ollama` down, `model_missing` | `ollama pull` while connected, or restore the `ollama-models` volume tar |
| `fastembed` down, `model_missing` | restore the `model-cache` tar; `verify` must print the manifest's sha256 |
| `ollama` down, `unavailable` | `docker compose restart ollama`; check `docker compose logs ollama` |
| `resource_exhausted` in `execution.reasons` | a smaller model (`FLAME_OLLAMA_MODEL`), or more RAM / a memory limit |

## 9. Reconnection and synchronization
1. Restore the default route.
2. `PUT /api/admin/ai/mode {"mode": "local_first"}` (audited).
3. Circuits half-open on their own after the cooldown.
4. Follow the synchronization policy in E2-10 §6. Nothing local is uploaded automatically.

## Known limitations
- This guide has **not** been dry-run offline yet (H-5 §4); that run sets this to 1.0.0.
- The Compose `ollama` service has no memory limit.

## Changelog
- 0.9.1 (2026-11-12): prepare and verify the reranker model (on by default since PR #30).
- 0.9.0 (2026-10-12): draft.
