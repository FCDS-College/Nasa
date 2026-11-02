# Implementation roadmap (from the 2026-10-30 system audit)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | 1.0.0 | 2026-10-30 | Phase 2 M1, M2, M6, A4, B2/B3, C2, L-8 | see each task |

Evidence for every task is in the [system status audit](../reviews/SYSTEM_STATUS_AUDIT.md) and the [AURA integration audit](../integration/AURA_INTEGRATION_AUDIT.md). **Done** means implemented on branch `claude/nasa-flame-aura-audit-abu89q`, tested, and (where noted) runtime-verified. Details are in the [implementation changelog](../reviews/IMPLEMENTATION_CHANGELOG.md).

## P0: Critical

| ID | Problem | Evidence | Solution | Affected files | Tests / acceptance | Risk | Status |
|---|---|---|---|---|---|---|---|
| P0-1 | CI red on `main`: pytest collects and ruff lints the external drop `tests/eval/Ziad____10/` | baseline: collection error, 23 ruff errors | Exclude the drop from collection and lint (keep the files; they are a reviewed snapshot) | `pytest.ini`, `ruff.toml` | `ruff check .` clean; `python -m pytest` 309 passed, 6 skipped | Low | **Done** |
| P0-2 | Next.js 16.3.8 has unauthenticated RCE advisories | `npm audit` critical | `next` and `eslint-config-next` 16.4.3 | `apps/web/package.json`, lock | `npm audit --omit=dev` 0; lint, typecheck, build pass | Low (patch release) | **Done** |
| P0-3 | Pillow 12.3.0 (39 CVEs) decodes untrusted uploads; capped `<13` | `pip-audit` | `pillow>=13,<14` | `apps/api/pyproject.toml`, `cv/hf_space/requirements.txt`, `requirements.txt` | full suite on 13.0.0; live image analysis re-verified | Low–medium (major version) | **Done** |

## P1: High

| ID | Problem | Evidence | Solution | Dependencies | Tests / acceptance | Status |
|---|---|---|---|---|---|---|
| P1-1 | Video analysis was not reachable from the API, the dashboard or AURA | dependency audit row 8a; no route | `analysis_type: flame_video` on `/api/analyses` (ADR-005): content sniff, spool to disk under a cap, probe, queue `process_video_analysis`, routed `video.analyze`, temporal summary, `video_measurement` evidence; contract 0.3.0 | `cv/video_analysis.py`, router | 7 new tests incl. real H.264; runtime on NASA BASS video | **Done** |
| P1-2 | Link 1: AURA `422 output_invalid` was not fallback-eligible | `http.py` mapped all 422 to `INVALID_REQUEST` | Map `error: output_invalid` → `INVALID_OUTPUT` | — | `test_aura_schema_failure_is_fallback_eligible` | **Done** |
| P1-3 | Link 1: AURA replays stored <500 answers for 24 h and rejects key reuse with a new body | AURA `idempotency.py:145-151` | Flame key = `<id>:<sha256(body)[:16]>`; cap context text at 2000 | — | `test_idempotency_key_changes_with_the_body_and_context_is_capped` | **Done** (AURA side: AURA-AI #200) |
| P1-4 | Dashboard Knowledge page presented invented "verified" entities and citations | `lib/api/mockData.ts` used by `fetchKnowledge` | Return no entities and show an explicit "not available" state | — | typecheck and build | **Done** |
| P1-5 | Interpretation errors could flip a completed analysis to `failed` | `worker.py` (interpretation ran inside the CV `try`) | Run interpretation after the CV transaction; on any error store `unavailable` | — | `test_unexpected_interpretation_error_keeps_the_image_analysis_completed` | **Done** |
| P1-6 | Model evaluation does not measure Flame: the gold set cites documents that are not in the corpus, and the baseline scores a mock | `REQUIRED_UPDATES_Ziad.md` B1/B3 | Re-annotate the gold set against the registered corpus (`FF-NTRS-*` PDFs, PSI tables); point the harness at `/api/search` and `/api/chat`; record runs per model; rank from recorded runs only | human annotators; dataset install | Recall@k, MRR, citation precision and faithfulness from live runs; report generated, not typed | **Open: needs human annotation** |
| P1-7 | Deployment never dry-run on a clean machine | RUNBOOK L-8 "needs a clean-machine dry run"; no Docker here | `docker compose up` from `infrastructure/`, then the workflows in the readiness report §6 | Docker host | All workflows pass on compose | **Open: needs a Docker host** |
| P1-8 | No end-to-end test with a deployed AURA | no AURA credentials here | Register the Flame connector on AURA (read token), run one agent question that calls `api_search` + `api_get_evidence`; issue a `svc-flame` key and enable Link 1 in staging | AURA SuperAdmin | Agent answer cites Flame evidence IDs; Flame logs show `provider=aura` for one interpretation | **Open: needs AURA access** |

## P2: Medium

| ID | Problem | Solution | Files | Acceptance |
|---|---|---|---|---|
| P2-1 | Static shared tokens; no per-client identity, scopes, expiry | ADR-009: per-client hashed API keys (`aura`, `web`), scope list, `last_used_at`, rotation | `main.py` auth, new table + migration | AURA and the web have distinct revocable keys |
| P2-2 | Rate limit only on chat, global and per process | Per-key token bucket in Redis for all routes; 429 + `Retry-After` | `main.py` middleware | Load test: one client cannot starve another |
| P2-3 | `/api/search` loads every lexical match into memory | Push RRF ordering into SQL, or cap lexical candidates (e.g. 200) before fusion | `main.py:390-445` | p95 stable at 10⁵ chunks |
| P2-4 | Jobs stuck in `processing` after a worker crash | On start-up, re-queue `processing` rows older than the job timeout; let `process_*` resume from `processing` (video already resumes from its checkpoint) | `worker.py`, a `recover` command | Kill the worker mid-job → analysis completes after restart |
| P2-5 | Persisted mode silently overrides `FLAME_AI_EXECUTION_MODE` | Document it in the RUNBOOK; report `mode_source` in `/api/ai/providers` | `ai_runtime.py`, RUNBOOK | Operators can see why the mode differs from env |
| P2-6 | Production accepts local default secrets | Refuse `change-me-*` defaults when `FLAME_ENVIRONMENT=production` | `config.py` | Settings validation test |
| P2-7 | Two retrieval stacks (ADR-006 Proposed) | Decide; wire the `ai/rag` reranker via `rerank` or retire it | `ai/rag`, `main.py` | One stack; benchmark from P1-6 |
| P2-8 | Admin data operations are raw SQL | Audited endpoints for reprocess, review status and quarantine (B2/B3), then UI | new `admin.py` | Every change writes `audit_event` |
| P2-9 | Experiments: fabricated `ingested_at` on search hits; empty `document_ids`/`experiment_ids` | Add `experiment.ingested_at` (migration, backfilled from `ingestion_run.finished_at`); populate the links from evidence | `models.py`, migration, `main.py` | Contract tests with real values |
| P2-10 | Dashboard placeholders (`indexed_chunks: 0`, empty panels) | Add `indexed_chunks` to counts, or hide the panels | `client.ts`, `main.py` | No hard-coded numbers on the dashboard |
| P2-11 | Backups and restore drill Pending | `pg_dump` + MinIO mirror schedule; drill | infra | Restore drill recorded |

### P2 status (2026-11-02)

| ID | Status | Evidence | Left open |
|---|---|---|---|
| P2-1 | **Done** | `flame_api/clients.py`, migration `0005_api_clients`, `test_api_clients.py`; create/list/revoke and scope 403 checked on PostgreSQL | No `rotate` command (create new, deploy, revoke old); no separate `admin` scope, so any `write` key is an admin; legacy env tokens still accepted (deprecated) |
| P2-2 | **Done** | `flame_api/rate_limit.py` (Redis token bucket), per-client isolation tested; live check: client A 200, 200, 429 while client B and the legacy token stayed 200 | Requests that fail authentication (401) are not rate-limited |
| P2-3 | **Done** | SQL-ranked, capped candidates (`fa81ad6`) and stored `search_tsv` (migration `0007`). 100,037 chunks, p95: 0.26–0.49 s for selective queries (was 25–27 s, then ~1.4 s), 0.91 s for a query matching 97 % of chunks (was 31 s, then 12.4 s); totals and top hits unchanged | Migration 0007 rewrites `document_chunk` (26 s at 10^5 rows) |
| P2-4 | **Done** | `python -m flame_api.worker recover`, run at worker start (compose, Railway); 9 tests; real-stack check on PostgreSQL + Redis + S3 stand-in | Runs only at worker start (no periodic sweep). A recovered **video** job restarts at frame 0: its work dir is a temp dir, so the checkpoint never survives. Railway needs `railway config apply` for the new start command |
| P2-5 | **Done** | `mode_source` / `env_mode` on `/api/ai/providers` and `/api/health`; RUNBOOK section | No "clear override" operation; PUT the env value |
| P2-6 | **Done** | Production start-up refuses local default secrets; error names the setting only (`hide_input_in_errors`) | — |
| P2-7 | **Open (decision)** | ADR-006 is Proposed; its owner decides, and acceptance needs the P1-6 benchmark | Blocked on P1-6 |
| P2-8 | **Done** | `flame_api/admin.py`, 5 endpoints, `test_admin_api.py`; rejected evidence excluded from search and chat; re-ingest keeps reviews | No admin UI (the web tier never holds a write key). Procedure 5's manual evidence row stays SQL |
| P2-9 | **Done** | Migration `0006_experiment_ingested_at` with backfill, `test_experiment_provenance.py` | `experiment_ids` / `document_ids` stay empty until ingest writes evidence that links a document and an experiment |
| P2-10 | **Done** | `chunks` / `indexed_chunks` in counts; client panels without a source return `null` | No dashboard page renders these yet (`/` redirects to `/chat`) |
| P2-11 | **Done (local drill)** | `infrastructure/backup/{backup,restore}.sh`; drill 2026-11-02: 21/21 tables and 8/8 S3 objects matched (`OFFLINE_DATA_AND_SYNC.md` §5) | No schedule; `mc mirror` path untested; embeddings not exercised; the Compose/MinIO drill stays Pending |

## P3: Optional

| ID | Item | Why it is deferred |
|---|---|---|
| P3-1 | Wire session memory (MAG) into `/api/chat` | `conversation_id` is accepted but unused; no product need is recorded |
| P3-2 | Shared (Redis) CAG for more than one replica | Single replica today |
| P3-3 | Video interpretation by a model; per-frame overlay artifacts | Measurements first; interpretation needs evaluation |
| P3-4 | Persist search and chat history ("research history") | Needs a privacy decision |
| P3-5 | Move `tests/eval/Ziad____10/` and the zip out of the test tree | Excluded already; cleanup only |
| P3-6 | Remove `AURA_UNAVAILABLE` from `ErrorCode` | Breaking change; coordinate with AURA's compiled tools |
| P3-7 | Audio analysis | No scientific audio signal in the datasets; do not build |

## Order of work

P0-1 → (P0-2, P0-3) → P1-2/P1-3 → P1-1 → P1-4/P1-5 [all done] → P1-7 (Docker host) → P1-8 (AURA staging) → P1-6 (annotation, then evaluation and ranking) → P2-1/P2-2 (needed before any public AURA exposure) → P2-4 → the remaining P2 items.
