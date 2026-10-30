# System status audit: Flame in Freefall (2026-10-30)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas), audit run by Claude Code | Current | 1.0.0 | 2026-10-30 | M1, M2, M6, A4, L-4, L-12 | `apps/api/`, `apps/web/`, `ai/`, `cv/`, `docs/api/openapi.json` |

Companion documents: [AURA integration audit](../integration/AURA_INTEGRATION_AUDIT.md) · [API integration reference](../integration/API_INTEGRATION_REFERENCE.md) · [Implementation roadmap](../plan/IMPLEMENTATION_ROADMAP.md) · [Implementation changelog](IMPLEMENTATION_CHANGELOG.md) · [Final readiness report](FINAL_SYSTEM_READINESS_REPORT.md).

**Method.** Source code, configuration, tests and runtime behaviour were treated as the truth; plans and earlier reports were not. Every status below names the evidence. "Runtime-verified" means it was exercised against a live stack in this audit: PostgreSQL 16 + pgvector, Redis, an S3 stand-in, uvicorn and an RQ worker (see §3).

## 1. Repository baseline (before any change)

| Item | Value |
|---|---|
| Branch / commit | `claude/nasa-flame-aura-audit-abu89q` at `7340782` (= `main`); clean tree, no submodules, one worktree |
| Layout | `apps/api` (FastAPI, SQLAlchemy, Alembic, RQ), `apps/web` (Next.js 16, React 19), `ai/` (provider contracts, model router, `ai/rag` library), `cv/` (OpenCV image + video pipelines, HF Space), `knowledge/ingestion`, `datasets/`, `infrastructure/compose.yaml`, `.railway/`, `docs/` |
| CI (`.github/workflows/ci.yml`) | ruff, registry validation, `API_SCHEMAS.md` freshness, pytest (both trees), Alembic up/down/up + seed + ingest on pgvector, web lint/typecheck/build, gitleaks. `aura-link2-contract.yml` compiles AURA tools from the contract at a pinned AURA revision. |
| AURA repository | `anasibrahimgnedy-collab/AURA-AI`, reachable, HEAD `6417c43` (inspected read-only) |

### 1.1 Baseline checks

| Check | Result |
|---|---|
| `ruff check .` | **FAIL: 23 errors**, all in `tests/eval/Ziad____10/` (the external drop committed in `1fd1d2d`) |
| `python -m pytest` | **ERROR at collection**: `tests/eval/Ziad____10/.../test_rag_metrics.py` needs a fixture that only exists in the drop. CI on `main` is therefore red. |
| pytest without the drop | 300 passed, 6 skipped (4 eval contract stubs "API backend implementation is pending"; PSI mirror absent; tesseract absent) |
| `validate_registry.py` | 11 sources, 0 problems |
| `render_api_schemas.py --check` | current |
| Web `lint` / `typecheck` / `build` | 0 errors and 5 unused-import warnings / clean / OK |
| Alembic `upgrade head`, `downgrade -1`, `upgrade head` | OK on PostgreSQL 16 + pgvector 0.8 |
| `seed` → `ingest` → `vector_index build` | 11 sources, 124 files, 182 image assets; 3 PDFs, 37 chunks; 0 experiments (raw tables are git-ignored); 37/37 embedded with `bge-small-en-v1.5` |
| `npm audit --omit=dev` | **1 critical**: `next` 16.3.8, including unauthenticated RCE (GHSA-2464-fhr4-w9xw, GHSA-673q-mjm6-r5xr) and a DoS (GHSA-p3m5-59mp-jv5r) |
| `pip-audit` (runtime deps) | **39 known vulnerabilities in `pillow` 12.3.0** (fixed in 13.0.0). Pillow decodes every uploaded image; `pyproject.toml` capped it at `<13`. |
| Docker / compose | Not runnable here (no Docker daemon). Compose file inspected only. |
| gitleaks | Not run (blocked: downloading the binary was not permitted in this environment). CI runs it. |

## 2. Implementation matrix

Status: **COMPLETE** = implemented and verified · **PARTIAL** · **BROKEN** · **MISSING** · **UNVERIFIED**. "→" gives the status after this audit's changes, where it changed.

| Component | Expected | Status | Evidence | Missing work | Priority |
|---|---|---|---|---|---|
| Backend API | Versioned, contract-first REST | COMPLETE | 15 operations; `test_contract_parity.py` asserts route ↔ `openapi.json` parity; runtime-verified | `meta.api_version` drifted from the contract (said 0.1.0 while the contract was 0.2.0) → fixed | — |
| Frontend dashboard | Real data, honest states | PARTIAL | Health, counts, search, chat, evidence, analysis and history call the API through a server-side proxy (`app/api/[...path]/route.ts`). The **Knowledge page showed hard-coded mock entities with "Verified" badges and citation links to evidence that does not exist** (`lib/api/mockData.ts`) → replaced by an explicit "not available" state. The dashboard hard-codes `indexed_chunks: 0` and empty recent research, coverage and evaluation panels (`client.ts:59`). | Upload UI (deliberately disabled: no write token in the web tier); video display; real dashboard panels | P2 |
| Authentication | Service auth, RBAC | PARTIAL | Two static bearer tokens: read (GET/HEAD and chat) and write (`main.py:83-105`), compared in constant time, ≥32 chars, must differ (`config.py`). No per-user identity, scopes or expiry; ADR-009 (Proposed). | Per-client tokens or OIDC, rotation, scoped AURA token | P2 |
| Document management | Upload → extract → chunk → embed → store | PARTIAL | CLI pipeline `seed`/`ingest`/`vector_index build` is idempotent and runtime-verified (37 chunks). Read and list endpoints exist. **No document upload API**; ingestion is operator-only. | Upload endpoint and job (only if a non-operator workflow needs it) | P3 |
| Experiment management | Experiments with conditions | PARTIAL / UNVERIFIED | Model, list and detail endpoints exist; tests pass on SQLite. 0 experiments in this environment because the PSI tables are git-ignored (`install_datasets.py` downloads ~6 GB). `document_ids` and `experiment_ids` are always `[]` (`main.py:818,840`). Experiment search hits report `ingested_at = now()` (`main.py:488`): a fabricated timestamp. | Dataset install in a runtime env; real cross-links; a true ingestion timestamp | P2 |
| Scientific analysis (image CV) | Upload → queue → CV → artifacts → evidence | COMPLETE | Runtime-verified with NASA ISS and SAFFIRE frames: `completed`, 4 artifacts, `image_measurement` evidence, routed provider `flame_cv`. No temperature field; pixel = measured, scaled = estimated. | — | — |
| Computer vision models | Validated detection | PARTIAL | Otsu/brightness baseline (`cv/flame_cv.py`). CNN and PINN prototypes are unvalidated (`requirements.txt` comment). Detection confidence is heuristic and every result carries `LOW_DETECTION_CONFIDENCE`. | Labelled evaluation set, then a learned detector | P2 |
| Video analysis | Ingest → frames → CV → temporal → persist → API | **MISSING at the API → COMPLETE** | The pipeline (`cv/video_analysis.py`) and router provider (`flame_cv_video`) existed, but there was no endpoint (the dependency audit row 8a said "no API endpoint yet"). Now `POST /api/analyses` with `video` (ADR-005). Runtime-verified on the committed NASA BASS clip (`FF-PSI-25`, 1343 frames, H.264): 40 sampled frames in time order, temporal summary, `video_measurement` evidence. | Video interpretation; overlay artifacts per frame | P3 |
| Audio analysis | Only if scientifically useful | MISSING (justified) | Only a `TranscriptionProvider` contract (`ai/providers/contracts/transcription.py`). The datasets are camera downlinks of combustion; no scientific audio signal was identified. | None. Do not add. | — |
| RAG | Retrieval with citations | PARTIAL | `/api/search`: PostgreSQL full-text plus pgvector, fused with RRF from `ai/rag/retrieval/fusion.py` (runtime: `mode: hybrid`). `/api/chat` grounds on retrieved evidence and drops citations outside it (`generation.py`). The `ai/rag` package (reranker, context builder, citation manager, query rewrite) is **not wired into the API**: ADR-006 is still Proposed. | Accept ADR-006 or retire the duplicate stack; reranker behind `FLAME_RERANKER_ENABLED` | P2 |
| CAG | Answer cache | COMPLETE | `answer_cache.py` keyed on question, knowledge version, instructions and mode; runtime: the repeat question returned `cache_hit: true`. In-memory, per process. | Shared cache for more than one replica | P3 |
| MAG | Session memory | MISSING (API) | `ai/rag/memory/session_mag.py` exists with unit tests; `/api/chat` accepts `conversation_id` but always returns `memory_used: false` (`main.py:621`). | Wire it in, or drop `conversation_id` from the docs | P3 |
| Vector search | pgvector, versioned | COMPLETE | Migration 0003; `vector_index build` publishes a knowledge version; health reports `vector_index: up` with the model | — | — |
| Model evaluation | Reproducible metrics on Flame | **BROKEN** | `docs/reports/REQUIRED_UPDATES_Ziad.md` B1/B3, confirmed: the gold set's locators point to documents that are not in the corpus, and the "baseline" scores `MockRAGSystem` (Recall = MRR = Citation F1 = 0.1842). `docs/evaluation/reports/llm-comparison-2026-10-12.md` is "Scheduled". | Gold set re-annotated against the real corpus (human work), harness pointed at `/api/search` and `/api/chat` | P1 |
| Model ranking | Ranked from recorded results | PARTIAL | `tests/eval/ranking.py` has hard gates and weights (40/40/20), but its inputs are not recorded runs of Flame's models | Depends on evaluation | P2 |
| Admin dashboard | Manage data, jobs, failures | MISSING | Only `PUT /api/admin/ai/mode` (audited, runtime-verified). `docs/data/ADMIN_DATA_OPERATIONS.md` procedures 4, 5 and 7 are raw SQL. No admin UI. | Audited endpoints B2/B3, then UI | P2 |
| Offline AI | Local LLM, embeddings, CV | COMPLETE (runtime) | `offline_only` with a real local model (Qwen2.5-0.5B-Instruct Q4_K_M via llama.cpp): chat answered by `llamacpp`, locality `local`, with citations. FastEmbed with `FLAME_EMBEDDING_OFFLINE=true`; image and video CV local; AURA reported `disabled`. See the readiness report for the shim caveat. | Hardware sizing for a useful model (≥ 3B) | — |
| Model routing / recovery | Fallback, circuit breaker, mode switch | COMPLETE (runtime) | Outage → evidence-only answer with `generation_unavailable`, no generated text; recovery to `llamacpp` ~30 s after restart without an API restart; mode switch audited (`audit_event` before/after) | Gotcha: once any `ai.mode.changed` row exists it overrides `FLAME_AI_EXECUTION_MODE` (`ai_runtime.py:120`). Document it in the runbook. | P2 |
| Database | Schema, constraints, migrations | COMPLETE | 4 migrations, reversible newest; ULID keys; idempotency unique constraint | Backups and a restore drill are Pending (`OFFLINE_DATA_AND_SYNC.md`) | P2 |
| Deployment | Compose, Railway | UNVERIFIED | Compose and Dockerfiles inspected; health checks present; Railway Ollama service exists. Not run: no Docker daemon here. | A clean-machine compose dry run (RUNBOOK L-8) | P1 |
| AURA integration | Controlled, versioned boundary | PARTIAL → mostly COMPLETE | See the [integration audit](../integration/AURA_INTEGRATION_AUDIT.md). Link 2 dry run passes (10 tools, 3 excluded). Two Link 1 defects fixed (422 mapping, idempotency replay). | Deployment-level smoke test with a real AURA connector | P1 |

## 3. Runtime verification environment

Postgres 16 + pgvector (local cluster), Redis 7, a `moto` S3 server standing in for MinIO, `uvicorn flame_api.main:app` with auth **enabled** (random 48-char tokens), `rq worker flame-analysis`, `next start` for the web proxy, and llama.cpp (llama-cpp-python 0.3 server) with Qwen2.5-0.5B-Instruct Q4_K_M. Workflow results are in the [readiness report §6](FINAL_SYSTEM_READINESS_REPORT.md#6-end-to-end-workflows).

## 4. Security findings

| # | Severity | Finding | Evidence | Status |
|---|---|---|---|---|
| S1 | Critical | Next.js 16.3.8: unauthenticated RCE advisories | `npm audit` | **Fixed**: 16.4.3, `npm audit` 0 |
| S2 | High | Pillow 12.3.0: 39 CVEs in image decoders; uploads are untrusted | `pip-audit` | **Fixed**: `pillow>=13,<14`; 309 tests pass on 13.0.0; live image analysis re-verified |
| S3 | Medium | Static shared tokens; no per-client identity, expiry or rotation; AURA would use the same read token as the web tier | `main.py:83-105`, ADR-009 Proposed | Open (P2) |
| S4 | Medium | Rate limiting only on `/api/chat`, global (not per client) and per process | `main.py:520` | Open (P2) |
| S5 | Low | Non-production defaults (`s3_secret_key="change-me-local-only"`) are not refused when `FLAME_ENVIRONMENT=production` | `config.py:41` | Open (P2) |
| S6 | Low | 405 answered with code `INTERNAL_ERROR` | `main.py` handler | **Fixed**: `METHOD_NOT_ALLOWED` |
| — | OK | Uploads: type sniffed from bytes, size and pixel caps, decompression-bomb guard, EXIF orientation; video now sniffed (ftyp/RIFF), spooled to disk under a cap, probed off the event loop | `analysis.py` | — |
| — | OK | SSRF: provider and AURA base URLs validated as bare origins (https for AURA and the HF Space) | `config.py` validators | — |
| — | OK | Secrets: `SecretStr` throughout; tokens never logged; the web proxy holds the read token server-side, never the write token | `route.ts`, `config.py` | — |
| — | OK | SQL: ORM and bound parameters; raw `text()` filters use bind params | `main.py` search | — |

## 5. Reliability and performance findings

| # | Finding | Evidence | Priority |
|---|---|---|---|
| R1 | `/api/search` loads **every** lexical match into memory, then paginates (`doc_query.all()`). Fine at 37 chunks; O(corpus) at scale. | `main.py:403` | P2 |
| R2 | A worker that dies mid-job leaves the analysis in `processing` forever: `process_*` returns early unless the status is `queued`, so an RQ retry cannot resume it | `worker.py:37,189` | P2 |
| R3 | An unexpected exception in the optional interpretation step marked an already-completed CV analysis as `failed` | `worker.py` (before) | **Fixed** |
| R4 | API unit tests read the persisted AI mode through the real `FLAME_DATABASE_URL`; with a local Postgres holding an `ai.mode.changed` row, 15 tests failed | `conftest.py` | **Fixed** (autouse isolation) |
| R5 | Video tracking metrics were meaningless when sampled frames are further apart than the 0.5 s tracking gap (BASS sample: `track_sessions` 40 for 40 frames) | `cv/temporal_analysis.py` + API mapping | **Fixed**: null plus `tracking_note` |

## 6. Scientific-accuracy review

- **Temperature.** No temperature field exists in the contract. Every analysis carries `TEMPERATURE_NOT_AVAILABLE`. RGB means are labelled `physical_interpretation: "none"`. Correct.
- **Measured vs estimated.** Pixel geometry is `measured`; scale-derived values are `estimated`; model text is `inferred`, `hypothesized` or `unsupported` only, and is never evidence (`EvidenceOrigin`). Video statistics are deterministic over pixel measurements and labelled `measured`, with the method named.
- **Video.** Frames keep their time order and source timestamps. Flicker is refused below the Nyquist rate (BASS run: "sampling rate 1.00 Hz is below the Nyquist rate for 10 Hz"). Calibration is refused for video rather than implied.
- **Generated answers.** Citations outside the retrieved set are dropped, the model identity and locality are returned, and degraded mode says plainly that nothing was generated. A 0.5B local model produced a grounded but weakly relevant answer. That is honest, but not useful science: size offline models at 3B or more (see the readiness report §5).
- **Evaluation numbers** in the repo are not measurements of Flame (§2, Model evaluation). Do not quote them.

## 7. Technical debt

Two retrieval stacks (ADR-006). `AURA_UNAVAILABLE` still in the enum, deprecated. Root-level evaluation scripts (`run_evaluation.py`, `render_report.py`, `generate_presentation.py`, `evaluation_report.json`) score the mock. `tests/eval/Ziad____10/` and `tests/eval/NASA____10.zip` are review snapshots inside the test tree (now excluded from collection; moving them under `docs/reviews/` or out of git is the cleaner fix). `docs/api/FRONTEND_API_CONTRACT.md` and `service-contracts.md` are MVP-era (0.1.0).
