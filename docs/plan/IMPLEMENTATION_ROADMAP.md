# Implementation roadmap (from the 2026-10-30 system audit)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | 1.1.1 | 2026-11-12 | Phase 2 M1, M2, M6, A4, B2/B3, C2, L-8 | see each task |

Evidence for every task is in the [system status audit](../reviews/SYSTEM_STATUS_AUDIT.md) and the [AURA integration audit](../integration/AURA_INTEGRATION_AUDIT.md). **Done** means implemented on branch `claude/nasa-flame-aura-audit-abu89q`, tested, and (where noted) runtime-verified. Details are in the [implementation changelog](../reviews/IMPLEMENTATION_CHANGELOG.md). Work after 2026-11-02 merged to `main` through the PRs named in [Status update (2026-11-12)](#status-update-2026-11-12).

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
| P1-4 | Dashboard Knowledge page presented invented "verified" entities and citations | `lib/api/mockData.ts` used by `fetchKnowledge` | Return no entities and show an explicit "not available" state | — | typecheck and build | **Done**; superseded 2026-11-12 by the Knowledge Graph page on real data (PR #32) |
| P1-5 | Interpretation errors could flip a completed analysis to `failed` | `worker.py` (interpretation ran inside the CV `try`) | Run interpretation after the CV transaction; on any error store `unavailable` | — | `test_unexpected_interpretation_error_keeps_the_image_analysis_completed` | **Done** |
| P1-6 | Model evaluation does not measure Flame: the gold set cites documents that are not in the corpus, and the baseline scores a mock | `REQUIRED_UPDATES_Ziad.md` B1/B3 | Re-annotate the gold set against the registered corpus (`FF-NTRS-*` PDFs, PSI tables); point the harness at `/api/search` and `/api/chat`; record runs per model; rank from recorded runs only | human annotators; dataset install | Recall@k, MRR, citation precision and faithfulness from live runs; report generated, not typed | **Partly done (retrieval).** Open: human review of the gold set; generated-answer evaluation; per-model ranking |
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
| P2-7 | **Open (decision)** | ADR-006 is Proposed; its owner decides, and acceptance needs the P1-6 benchmark | Blocked on P1-6. **Done 2026-11-12:** see the status update below |
| P2-8 | **Done** | `flame_api/admin.py`, 5 endpoints, `test_admin_api.py`; rejected evidence excluded from search and chat; re-ingest keeps reviews | No admin UI (the web tier never holds a write key). Procedure 5's manual evidence row stays SQL |
| P2-9 | **Done** | Migration `0006_experiment_ingested_at` with backfill, `test_experiment_provenance.py` | `experiment_ids` / `document_ids` stay empty until ingest writes evidence that links a document and an experiment |
| P2-10 | **Done** | `chunks` / `indexed_chunks` in counts; client panels without a source return `null` | No dashboard page renders these yet (`/` redirects to `/chat`) |
| P2-11 | **Done (local drill)** | `infrastructure/backup/{backup,restore}.sh`; drill 2026-11-02: 21/21 tables and 8/8 S3 objects matched (`OFFLINE_DATA_AND_SYNC.md` §5) | No schedule; `mc mirror` path untested; embeddings not exercised; the Compose/MinIO drill stays Pending |

## Status update (2026-11-12)

Changes since the P2 status table of 2026-11-02, which is kept above as dated history. Evidence is in [FINAL_TEST_REPORT.md](../../FINAL_TEST_REPORT.md) (FTR) §8–§10 and the [ADR index](../architecture/adr/README.md).

| ID | Status now | Evidence | Left open |
|---|---|---|---|
| P1-4 | **Superseded.** The "not available" Knowledge page became the Knowledge Graph page (`/knowledge`). It reads the real graph (951 entities, 10,683 edges), and every link opens the table cell it came from. | PR #32; FTR §10: smoke test 9/9 steps | Graph built from tables only: no NLP extraction, no Graph RAG in chat |
| P1-6 | **Partly done (retrieval).** A 26-question gold set (`datasets/evaluation/retrieval_gold_v1.jsonl`), written against the registered corpus. The harness runs against the live `/api/search`. Scores: hit@1 0.88, MRR@10 0.91, recall@5 0.88, with reranking on. | [retrieval-2026-11-12.md](../evaluation/reports/retrieval-2026-11-12.md); FTR §9 | The gold set was written with AI assistance and is not yet human-reviewed (Ziad, Eman). Citation precision, faithfulness and per-model ranking still need a language model, and none was available here |
| P1-7 | Open. | — | No Docker host or Railway access |
| P1-8 | **Open (partly met).** Link 2 ran live once, on Railway on 2026-10-07: an AURA agent answered with real Flame evidence IDs, through 8 compiled tools of an older contract. At contract 0.6.0 only the dry run has been checked: 16 tools accepted, 10 operations excluded, at `d696fad` and AURA `main`. | [integration README](../integration/README.md) §2; AURA `docs/reports/flame-link2-live.md`; FTR §8–§9; AURA-AI #232 | A complete Link 2 report at contract 0.6.0, with every item AURA's runbook §2.6 asks for. Any Link 1 run: no Flame analysis has been interpreted by AURA (`provider=aura`) |
| P2-1 | **Done, and closed the earlier gap.** There is now an `admin` scope for `/api/admin/*`, and a `write` key gets 403 there. Each admin key must name an `--owner` (ADR-009, migration `0008`). | PR #29; `test_api_clients.py`; SECURITY.md 0.7.0 | Still no `rotate` command (create a new key, deploy, revoke the old one). Owners are free text. The deprecated write token keeps its admin rights until it is removed |
| P2-4 | **Done, and closed the earlier gap.** Video jobs checkpoint to `video_checkpoint_frame` every 10 frames and resume after `worker recover`, with a frame-for-frame identical result. `POST /api/analyses/{id}/cancel` was added (ADR-008, migration `0009`). | PR #29; `test_video_checkpoints.py` (8 tests) | Image jobs are not checkpointed (they take seconds). An RQ timeout still fails a video job instead of leaving it to resume. Recovery still runs only at worker start |
| P2-7 | **Done.** ADR-006 was Accepted and built: one `ai/rag` search stack serves `/api/search` and `/api/chat`, and the API's inline ranking is retired. The benchmark gate was met (identical top 5 on all 26 questions). The cross-encoder reranker has been on by default since PR #30. | PR #29, #30; [retrieval-2026-11-12.md](../evaluation/reports/retrieval-2026-11-12.md) | Reranking costs about 0.7 s per search on CPU. Retiring the in-memory `RAGRetrievalPipeline` / `FlameRAGService` is Eman's call |
| P2-9 | Unchanged. | — | Table evidence carries an `experiment_id` but no document, and passage evidence carries a document but no experiment, so `experiment_ids` / `document_ids` are still empty. The knowledge graph now links investigations to their ISA-Tab documents (ADR-007), but these two fields do not read the graph |
| P2-10 | **Partly moot.** `/` no longer redirects to `/chat`: it is the Fire Safety Dashboard. | — | No page renders `chunks` / `indexed_chunks` yet, and `fetchDashboardData` has no caller |

## P3: Optional

| ID | Item | Why it is deferred |
|---|---|---|
| P3-1 | Wire session memory (MAG) into `/api/chat` | `conversation_id` is accepted but unused; no product need is recorded |
| P3-2 | Shared (Redis) CAG for more than one replica | Single replica today |
| P3-3 | Video interpretation by a model; per-frame overlay artifacts | Measurements first; interpretation needs evaluation |
| P3-4 | Persist search and chat history ("research history") | Needs a privacy decision |
| P3-5 | Move `tests/eval/Ziad____10/` and the zip out of the test tree | Excluded already; cleanup only |
| P3-6 | Remove `AURA_UNAVAILABLE` from `ErrorCode` | Breaking change; coordinate with AURA's compiled tools |
| P3-7 | Audio analysis | Reversed 2026-11-13: 11 of 17 BASS-II videos carry operator speech. Built as optional transcription, off by default (`docs/cv/audio-transcription.md`); review, UI and evidence use remain open |

## Order of work

P0-1 → (P0-2, P0-3) → P1-2/P1-3 → P1-1 → P1-4/P1-5 [all done] → P1-7 (Docker host) → P1-8 (AURA staging) → P1-6 (annotation, then evaluation and ranking) → P2-1/P2-2 (needed before any public AURA exposure) → P2-4 → the remaining P2 items.

As of 2026-11-12, every P0, P1-1 to P1-5 and every P2 item except P2-9 and P2-10's dashboard panels are done (P2-11 as a local drill only). P1-6 is partly done. **What is left, in order:**
1. P1-7, the compose dry run (needs a Docker host).
2. P1-8: a live Link 2 run at contract 0.6.0, with a complete report, and a first Link 1 run (needs AURA access).
3. P1-6, human review of the gold set (Ziad, Eman), then generated-answer evaluation with a deployed model.
4. The rest of P2-9, P2-10 and P2-11.

## Changelog
- 1.0.0 (2026-10-30): roadmap from the system audit.
- 1.0.0, amended in place (2026-11-02): the P2 status table. The version was not bumped then.
- 1.1.0 (2026-11-12): status update after the ADR-006 to 009 builds and the Knowledge Graph page (PR #29–#32). Updated: the P1-4 and P1-6 status cells, a pointer from the dated P2-7 row, and the remaining order of work.
- 1.1.1 (2026-11-12): P1-8 corrected. Link 2 ran live once, on 2026-10-07, at an older contract; 1.1.0 had said no live AURA agent had run.
