# API changelog

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | — | 2026-11-07 | L-4, M6 | `docs/api/openapi.json`, `apps/api/flame_api/` |

Semver applies to `docs/api/openapi.json` `info.version`. Breaking changes need a minor bump while we are pre-1.0, an entry here, and one release of deprecation where practical.

## 0.5.0 (2026-11-07)

Additive. Four read-only operations for the fire-safety dashboard (tag **Fire safety**); all use the read scope and AURA's Link 2 dry run compiles them into tools (14 accepted at the pinned AURA revision).

**Added**
- `GET /api/investigations`: every registered combustion investigation with NASA's ISA-Tab objective (cited), the condition envelope of its flight-test table, and an evidence-relevance score for a cabin atmosphere (`scenario` = `iss_nominal` | `pre_eva` | `orion_max_o2` | `lunar_lander_max_o2`, or custom `o2_fraction` + `pressure_kpa`). The scoring formula is returned in `ranking_method`. Investigations named by the challenge but not acquired (SAME) are listed in `not_acquired`.
- `GET /api/investigations/{investigation_id}`: summary sections (objective, hypothesis, approach, research impacts) verbatim with evidence IDs, publications, data envelope, investigation insights, sample tests. 404 `INVESTIGATION_NOT_FOUND`.
- `GET /api/insights`: statements computed from flight-test rows (`measured_statistic`), the FLEX outcome model (`model_estimate`) or coverage checks (`coverage_gap`), each with the evidence IDs it was computed from.
- `GET /api/insights/flex-outcome`: FLEX droplet flame end-state model (claim class `estimated`) with a strict applicability domain (`probabilities: null` plus reasons outside it), the nearest real flight tests with their recorded end state, and an O₂ sweep. Evaluation: `docs/evaluation/reports/flex-outcome-model.md`.
- Schemas `Scenario`, `ConditionRange`, `InvestigationData`, `Relevance`, `CitedText`, `SummarySection`, `InvestigationSummary`, `InvestigationDetail`, `InvestigationListResponse`, `InvestigationResponse`, `NotAcquiredInvestigation`, `InsightKind`, `Insight`, `InsightListResponse`, `FlightTestRef`, `FlexOutcomeResponse`; `ErrorCode.INVESTIGATION_NOT_FOUND`.

**Data**
- The four PSI experimental tables and ISA-Tab metadata are committed, so a fresh clone ingests 840 flight tests and 4 investigation-metadata documents (parser `isatab-investigation-0.1.0`, `document_type: dataset_documentation`).

## 0.4.0 (2026-11-02)

Additive for clients that send a valid token; read the **Changed** items before upgrading a deployment.

**Added**
- Per-client API keys (P2-1, migration `0005_api_clients`): `python -m flame_api.clients {create,list,revoke}` issues `flk_…` keys with `read` and/or `write` scope, stored only as a SHA-256 hash. A key without the needed scope gets **403 `FORBIDDEN`**; an unknown or revoked key gets 401. `FLAME_READ_API_TOKEN` / `FLAME_WRITE_API_TOKEN` still work and are deprecated.
- Admin data operations (P2-8), all write scope, all `x-aura-exclude: true`, every change audited: `GET /api/admin/files`, `GET /api/admin/ingestion-runs`, `POST /api/admin/files/{file_id}/reprocess`, `PUT /api/admin/evidence/{evidence_id}/review`, `GET /api/admin/audit`. New schemas `AdminFile*`, `IngestionRun*`, `AuditEvent*`, `FileReprocess*`, `EvidenceReview*`, `AdminReviewStatus`, `FileStatus`; `ErrorCode` gains `FILE_NOT_FOUND`, `FILE_NOT_QUARANTINED`.
- `DashboardCountsResponse.chunks` and `.indexed_chunks` (P2-10).
- `AiStatus` / `AiProvidersResponse`: optional `mode_source` (`env` | `audit_override`) and `env_mode` (P2-5); schema `AiModeSource`.
- `WarningCode.JOB_RECOVERED` (P2-4): an analysis re-queued by `python -m flame_api.worker recover` after a worker crash.

**Changed**
- Rate limits on every authenticated `/api/*` route, per client (P2-2): `FLAME_READ_RATE_LIMIT_PER_MINUTE` (600), `FLAME_WRITE_RATE_LIMIT_PER_MINUTE` (60), `FLAME_CHAT_RATE_LIMIT_PER_MINUTE` (30, now per client). 429 `RATE_LIMITED` carries `Retry-After` and `details.limit_per_minute` / `retry_after_s`. A rate-limited chat request now gets 429 before any 503 `CHAT_UNAVAILABLE`. Redis down → fail open (chat keeps its in-process ceiling).
- `/api/health` is never rate-limited: its 429 response is removed from the contract; it can return 403 for a key without read scope.
- Every `/api/admin/*` route, **including GETs**, now needs write scope. Before, an admin GET passed with the read token.
- Evidence an administrator rejects is no longer returned by `/api/search` or cited by `/api/chat`; `GET /api/evidence/{id}` still shows it with `review_status: rejected`. Re-ingest keeps `human_verified` / `rejected`.
- Experiment search hits report the real `ingested_at` (migration `0006`; before, the response time). An experiment row with neither an ingestion time nor a table file is left out of search rather than given an invented time.
- `Document.experiment_ids` / `Experiment.document_ids` are filled from evidence that links both; still empty on today's corpus, where no such evidence exists.
- Search ranks lexical candidates in SQL and fetches at most `max(200, 2·page·page_size)` before fusion (P2-3); on PostgreSQL it uses the stored `document_chunk.search_tsv` (migration `0007`). `total_items` and ordering are unchanged.
- Production refuses known local default secrets (S3 `change-me-*`, `flame-local` access key, the `flame` database password) at start-up (P2-6).

## 0.3.0 (2026-10-30)

All changes are additive; 0.2.0 clients keep working.

**Added**
- Video analyses on the existing resource (ADR-005): `POST /api/analyses` accepts `video` (MP4/MOV/AVI by content, H.264/H.265, ≤ 200 MiB, ≤ 600 s) instead of `image`, with `sample_every_n_frames` (default 30) and `max_frames` (default 300, ≤ `FLAME_MAX_VIDEO_FRAMES`). Exactly one of `image`/`video` is required (`AnalysisCreateForm.oneOf`).
- `AnalysisType` gains `flame_video`; `Analysis.result` may be `FlameVideoAnalysisResult` (`video`, `sampling`, `frames[]` in time order, `temporal_summary`, `observations`). Pixel units only; no temperature; no calibration for video yet.
- `AnalysisInput.video` (`VideoInput`) and video media types on `AnalysisInput.media_type` and `Artifact.media_type` (the `original` artifact of a video is the video).
- `EvidenceKind` gains `video_measurement`; `AnalysisFailureCode` gains `VIDEO_DECODE_FAILED`.
- `ErrorCode` gains `VIDEO_INVALID` and `METHOD_NOT_ALLOWED` (405 used to come back as `INTERNAL_ERROR`).

**Fixed**
- `meta.api_version` returned `0.1.0` although the contract was `0.2.0`; it now equals `info.version` and a test pins the two together.
- `AnalysisSummary.analysis_type` is read from the stored analysis instead of being hard-coded.

**Removal postponed**
- `AURA_UNAVAILABLE` stays in `ErrorCode` for this release (it is not emitted); removing an enum value is a breaking change and needs its own coordinated release with AURA's compiled tools.

## 0.2.0 (2026-10-12, PR #14)

**Added**
- `GET /api/documents`: list with `source_id[]`, `document_type`, `q` (title), `page`, `page_size` ≤ 100 (M6).
- `GET /api/experiments`: list with `source_id[]`, `gravity_regime`, `fuel_or_material`, `investigation`, pagination; each item has `condition_count` (M6).
- `POST /api/chat` is now in the contract (`ChatRequest` / `ChatResponse`), marked `x-aura-exclude: true` (ADR-004).
- `GET /api/ai/providers` (`AiProvidersResponse`): execution mode, providers, health, circuit, decision counters. `x-aura-exclude`.
- `PUT /api/admin/ai/mode` (`ModeChangeRequest` → `ModeChangeResponse`): write token, audited. `x-aura-exclude`.
- `HealthResponse.ai` (optional): `{mode, providers}`.
- `ChatResponse.execution`: `ExecutionMetadata` when a model answered, `RoutingFailure` when none could, `null` when no evidence matched.
- `Interpretation.execution`, `PipelineInfo.execution` (optional).
- `StatementOrigin` gains `model_interpretation`.
- `ErrorCode` gains `AUTHENTICATION_REQUIRED` (the middleware already returned it; contract drift fixed) and `CHAT_UNAVAILABLE`.
- Tag `Admin`.

**Changed**
- `Interpretation.provider` is now any provider name (string ≤ 64, nullable). It was the enum `["aura", null]`. Clients that switched on `"aura"` keep working; new values are `ollama`, `vllm`, `llamacpp`.
- `services.llm` in `/api/health` reflects the router's local language models. Before, it was always `disabled`.
- Chat when no model can answer: **was** `502 AURA_UNAVAILABLE`; **now** `200` with the retrieved `sources`, a fixed explanatory `answer`, and warning `generation_unavailable`. This is a behaviour change for clients that treated 502 as "show retry". The web chat already renders `warnings`.
- `CHAT_UNAVAILABLE` (503) now means "no language model configured or permitted in the current mode", not "AURA disabled".

**Deprecated**
- `AURA_UNAVAILABLE`: no longer emitted by chat. Kept in the enum for one release; to be removed in 0.3.0.

**Fixed**
- `API_SCHEMAS.md` was stale relative to `openapi.json` on `main`; it is regenerated and CI-checked now.

## 0.1.0 (MVP, `e73dcf1`)
The ten MVP operations: health, dashboard counts, search, document, experiment, evidence, analysis create/list/get/artifact.

## Known limitations

- `API_SCHEMAS.md` is generated from `openapi.json` (`python docs/tools/render_api_schemas.py`), so do not hand-edit it. CI runs `--check`.
- Pre-1.0: breaking changes only bump the minor version.
