# H-1: Hybrid AI dependency audit

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review (Princess E3, CV rows: signed 2026-10-14; Anas E2, data rows: pending) | 1.1.0 | 2026-10-14 | 2H Task 1, M1 | `apps/api/flame_api/*`, `ai/`, `cv/`, `apps/web/`, `infrastructure/`, `.github/workflows/` |

**Method.** Every route in `apps/api/flame_api/main.py` and `analysis.py`, the RQ worker (`worker.py`), the ingestion and seed CLIs, `ai/rag`, `cv/`, the web app (`apps/web`), the Compose and Railway configs and the CI workflows were read at commit `2afbc37`. Each outbound network call, model download and container pull is listed below. "Offline today" is the behaviour on branch `ccr-c6a5a263-498la9` (PR #14). The "MVP" column is the behaviour at the audit baseline `e73dcf1`.

## 1. Inventory

| # | Component | File | External endpoint / service | Data sent | MVP offline behaviour | Offline behaviour now | Local path | Prio |
|---|---|---|---|---|---|---|---|---|
| 1 | `/api/chat` generation | `main.py` → `generation.py` | AURA `POST /api/v3/chat` (Railway) | question + ≤16 retrieved passages (DATA channel) | `503 CHAT_UNAVAILABLE` | Answered by a local LLM through the router; with no local LLM, `200` + evidence + `generation_unavailable` | Ollama / vLLM / llama.cpp adapters (`ai/providers/local/`) | P0 ✅ built |
| 2 | Image interpretation | `worker.py` → `generation.interpret_analysis` | AURA `POST /api/v3/chat` | measured values + linked evidence | interpretation `unavailable` | Local LLM; still `unavailable` (CV result kept) when none | as #1 | P0 ✅ built |
| 3 | AURA readiness | `ai/providers/cloud/aura.py` `health` | AURA `GET /health/ready` | none | 2 s timeout per `/api/health` call | Cached and bounded; **never sent** in `offline_only` | — | P0 ✅ |
| 4 | Embeddings (index build + query) | `vector_index.py` → `ai/providers/local/fastembed_embeddings.py` | Hugging Face Hub download of `Qdrant/bge-small-en-v1.5-onnx-Q` on first use | none (download only) | Fails with an empty cache; search falls back to lexical | `FLAME_EMBEDDING_OFFLINE=true` sets `HF_HUB_OFFLINE` and reports `model_missing` instead of downloading. Cache prepared and checksummed while connected (H-3, H-6). | fastembed cache in the `model-cache` volume | P0 ✅ |
| 5 | Embeddings in `ai/rag` | `ai/rag/embeddings/embedding_service.py` | HF Hub download of `sentence-transformers/all-MiniLM-L6-v2` | none | Fails with an empty cache | **Unchanged.** `ai/rag` is not wired into the API (M2, ADR-006). It also uses a *different* model from the API index, so the M2 wiring must switch it to the router's `embed.*` tasks. | router `embed.*` | P1 (with M2, Eman) |
| 6 | Reranking | `ai/rag/reranking/reranker.py`; `ai/providers/local/cross_encoder.py` | HF Hub download (cross-encoder) | none | No cross-encoder exists (score passthrough) | Adapter exists, off by default (`FLAME_RERANKER_ENABLED`) | cached cross-encoder | P1 |
| 7 | CV inference (image) | `worker.py` → router `vision.analyze` | Optional HF Space `POST /api/analyze` | the uploaded image + pixel scale | Local provider works; `hf_space` fails if the Space is unreachable | `hf_space` is never contacted in `offline_only`; when it fails in other modes the router falls back to local `flame_cv` | `ai/providers/local/flame_cv.py` (OpenCV) | P0 ✅ |
| 8 | Video embedding / training | `cv/video_embedding.py`, `cv/video_training.py` | `torchvision` weights download (`weights="DEFAULT"`) | none | Fails with an empty torch cache | Unchanged (research script `cv/video_embedding.py`, not in the API path; `weights="DEFAULT"` only when `weights` is set) | pre-download into `TORCH_HOME` (H-6 §4) | P1 (Princess) |
| 8a | Video analysis (frames, temporal summary) | `ai/providers/local/flame_cv_video.py` → `cv/video_analysis.py` | none (OpenCV, local files only) | — | Works offline | Resumable from `frames.jsonl` when the same `work_dir` is reused; local only, so never blocked | `flame_cv_video` provider (registered for `video.analyze`) | P0 ✅ (API: `POST /api/analyses` with `video`, contract 0.3.0) |
| 9 | Telemetry OCR (video overlays) | `cv/telemetry_ocr.py` | none (local Tesseract binary) | — | Works if Tesseract is installed | Same | — | — |
| 10 | Document OCR | `ingest.py` `_ocr_page` | none (local Tesseract binary) | — | Didn't exist | Works offline. The API image installs `tesseract-ocr` and the `ocr` extra, and CI OCRs a real image-only page. Without them, `ocr.status=unavailable` is recorded. | `apps/api[ocr]` + `tesseract-ocr` (in the image) | P1 ✅ |
| 11 | Data acquisition | `knowledge/ingestion/psi_download.py`, `record_provenance.py`; S3 `nasa-psi` | `psi.nasa.gov`, `s3://nasa-psi` (anonymous) | none | No new data | No new data. Local mirrors (`datasets/raw/`, git-ignored) and committed NTRS PDFs stay usable. Answers show `knowledge_version`. | local mirrors only | — (by design) |
| 12 | NTRS / NIST WebBook | registry rows `FF-NTRS-*`, `FF-NIST-WEBBOOK` | `ntrs.nasa.gov`, `webbook.nist.gov` | none | — | The 3 NTRS PDFs are committed and ingested offline; NIST is reference-only, never fetched | — | — |
| 13 | Frontend fonts | `apps/web/app/layout.tsx` | `fonts.googleapis.com`, `fonts.gstatic.com` | client IP / UA | System-font fallback | **Self-hosted** via `@fontsource-variable/*`, bundled at build | — | P1 ✅ |
| 14 | Frontend → API | `apps/web/app/api/[...path]/route.ts` | `FLAME_API_ORIGIN` (Flame API) | user queries | Works if the API is on the same network | Same; no other web egress | — | — |
| 15 | Auth | `main.py` middleware | none (static bearer tokens) | — | Works offline | Same | — | — |
| 16 | Database / queue / objects | PostgreSQL+pgvector, Redis, MinIO | local containers (Compose) or Railway (cloud) | everything | Compose: works offline; Railway: unreachable | Same; offline deployment = Compose (H-6) | Compose | P0 ✅ |
| 17 | Deployment | `.railway/railway.py` | Railway | — | Unreachable | Railway stays for connected demos (L-8) | Compose on local hardware | — |
| 18 | Container images | `infrastructure/compose.yaml`, Dockerfiles | Docker Hub: `pgvector/pgvector:pg16`, `redis:7-alpine`, `minio/minio`, `minio/mc`, `ollama/ollama:0.5.7`, `python:3.12-slim`, `node:22-alpine` | — | A fresh machine can't start | Pre-pull and `docker save` before going offline (H-6 §3) | image tarballs | P0 (procedure) |
| 19 | Python / npm packages | `pip install`, `npm ci` | PyPI, npm registry, PyTorch CPU index | — | Can't build | Build images while connected; offline hosts load the saved images (H-6) | — | P0 (procedure) |
| 20 | CI | `.github/workflows/*.yml` | GitHub Actions, AURA repo checkout, gitleaks release download | source | n/a | n/a (CI is a connected-only activity) | — | — |
| 21 | Ollama model pull | `compose.yaml` `ollama-pull` | `registry.ollama.ai` | none | — | One-time while connected; the `ollama-models` volume then serves offline | volume backup (H-6) | P0 |
| 22 | Knowledge-version announce | `knowledge_version.py` | local Redis | version event | — | Local only; when Redis is down the PostgreSQL row is still written | — | — |

## 2. Operations that remain online-only

| Operation | Why it can't run offline | Disclosure |
|---|---|---|
| Acquiring new PSI / NTRS / NIST data | The data lives on external servers | Answers carry `knowledge_version`; E2-10 records the last sync time |
| AURA-hosted models and AURA tools (Link 2) | AURA runs on Railway | `services.aura` is `disabled` with the message "AURA is blocked in offline_only mode." |
| HF Space CV | External host | `execution.provider` shows `flame_cv` with `fallback_used` |
| First download of any model or image | Registry access | H-6 preparation checklist |

Flame has no "external research search" feature: it never queries the web at answer time, so scenario 5 of §8.8 reduces to "answers come only from the local corpus and say which knowledge version they used" (H-5 S5).

## 3. Resource requirements of the proposed local models

The models and capabilities are listed in the [H-3 registry](PHASE_2_LOCAL_MODEL_REGISTRY.md). Measured: (m), from this audit's runs. Estimated: (e), from published model sizes; to be replaced by H-7 numbers.

| Capability | Model | Disk | RAM / VRAM | CPU-only | Latency |
|---|---|---|---|---|---|
| Structured answer / interpretation (CPU) | `qwen2.5:3b-instruct-q4_K_M` (Ollama 0.5.7) | 1,929,912,432 B (m) | ~3 GB RAM (e) | yes | 77.8 s cold, 50.0–53.7 s warm for one grounded answer on 4 vCPUs (m, 2026-10-11) |
| Structured answer (GPU) | `Qwen/Qwen2.5-7B-Instruct-AWQ` (vLLM, L40S) | ~5.5 GB (e) | ~8 GB VRAM + KV cache (e) | no | Pending (H-7) |
| Embeddings | `bge-small-en-v1.5` ONNX-Q (fastembed 0.9.0) | 66,465,124 B model; 67,181,750 B cache (m) | ~300 MB (e) | yes | 37 chunks in 9.5 s wall-clock, including model load (m) |
| Reranker | `ms-marco-MiniLM-L-6-v2` | ~90 MB (e) | ~400 MB (e) | yes | Pending |
| CV | `flame_cv` (OpenCV, no weights) | code only | ~0.5 GB per 50 MP image (e) | yes | Pending (Princess's performance doc) |

## 4. Fallback / degraded mode per critical dependency

Every critical AI dependency now has a local alternative or a defined degraded mode. That is the Task 1 acceptance criterion.

| Dependency lost | What still works | Degraded response |
|---|---|---|
| AURA | Chat and interpretation through a local LLM | — |
| AURA and every local LLM | Search, evidence, documents, experiments, CV | Chat: `200`, evidence list, warning `generation_unavailable`. Interpretation: `unavailable`. |
| Embedding model | Lexical search | `retrieval.mode = lexical` |
| HF Space | Local CV | `execution.fallback_used = true` |
| Internet entirely | Everything above in `offline_only` | `services.aura = disabled` |

## Known limitations
- Rows 5 and 6 are not fixed by PR #14. They belong to M2 (Eman). Row 8 is a research script outside the API path; the video path itself is row 8a.
- Row 8a has no HTTP endpoint or worker job yet, so video analysis is reachable only through the router.
- "Offline now" was verified by tests that block sockets, and by a real run with AURA configured but blocked in `offline_only`. It was **not** verified by physically disconnecting a machine. That run is H-5's Pending evidence.
- Python and npm dependencies are not vendored. An offline host relies on pre-built images (H-6).

## Review and sign-off

| Reviewer | Date | Commit | Result |
|---|---|---|---|
| Princess (E3) | 2026-10-14 | `d7adf5e` | Signed for the CV rows (7 to 9, new 8a). All 21 file paths named in §1 exist at this commit. Row 8a added; row 8 corrected. The other rows (AURA, embeddings, data acquisition, infrastructure) were not re-checked beyond path existence. |
| Anas (E2) | — | — | Pending: data rows (11, 12, 22) |

## Changelog
- 1.1.0 (2026-10-14): row 8a (video provider); row 8 and limitations corrected; Princess's review recorded.
- 1.0.0 (2026-10-12): first complete audit, starting from the Phase 2 Plan §7A.3 table and extended to every route, worker, the auth path, the frontend and CI.
