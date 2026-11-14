# API changelog

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | — | 2026-11-13 | L-4, M6 | `docs/api/openapi.json`, `apps/api/flame_api/` |

Semver applies to `docs/api/openapi.json` `info.version`. Breaking changes need a minor bump while we are pre-1.0, an entry here, and one release of deprecation where practical.

## Unreleased

**Changed**
- `Coverage` verdict `covered` now needs 5 or more neighbouring tests that **record a pressure** within ±25 %. BASS-II and SAFFIRE publish no pressure, so their tests match on O₂ only: they still count in `neighbourhood_tests` and are named in `reasons`, but they make the verdict at most `partial`. Before, 21 % O₂ at 200 kPa was `covered` by 74 tests, 70 of them BASS-II rows without pressure; it is now `partial` ("only 2 record a pressure near it"). The ISS, pre-EVA and Orion presets stay `covered`, the lunar lander stays `partial`, Apollo 1 stays `none`. No shape change.
- `/api/search` and `/api/chat`: under `domain=combustion` (the chat default), a dense-only hit from a non-combustion source is now dropped like a lexical one. Before, it could be returned and cited.

**Added**
- `ChatWarning` value `low_evidence_score` and setting `FLAME_CHAT_ABSTAIN_BELOW` (default unset = off): when set, `/api/chat` returns "too weak to answer from" with the closest sources, calls no model and is not cached, if the best fused score of the search for the whole question is below the value. Calibrate it with `ai.rag.evaluation.run_passage_gold`; no value is recommended until the passage gold set is verified.
- `ChatWarning` value `answer_terms_not_in_cited_evidence` (`/api/chat`): the answer names a fuel, material, oxidizer, instrument or platform (the controlled vocabulary of `ai/rag/nlp/vocab`, with aliases) that none of the cited passages mentions. A weaker signal than a figure: it warns in `warn` and `strict` mode and never withholds the answer; answers with it are not cached.

## 0.8.0 (2026-11-14)

Suppression Advisor (ADR-014, plan `docs/plan/SUPPRESSION_ADVISOR_PLAN.md`). Additive: no existing response changes.

**Added**
- `GET /api/insights/suppression-advice` (`getSuppressionAdvice`, `SuppressionAdviceResponse`, `SuppressionAgentAdvice`, `SuppressionHazard`).
  - A deterministic recommendation between the ISS CO₂ PFE and Fine Water Mist PFE for a cabin.
  - Inputs: fire type, cabin volume, pressure, O₂, background CO₂, temperature, whole-cabin or aimed discharge, and the assumed water delivery fraction.
  - Returns:
    - the post-discharge fire-zone and cabin atmospheres;
    - crew hazards, where a CO₂ discharge reaching the CO₂ IDLH vetoes CO₂;
    - the crossover delivery fraction;
    - for heptane and methanol, the FLEX estimate for CO₂ with its 5 nearest flight tests;
    - a thermal-model probability per agent, when its gates allow.
  - `outcome` is `recommend`, `no_clear_winner` or `no_recommendation`.
  - The absolute water-mist probability is withheld while the thermal model fails the MIST check (see ADR-014).

## 0.7.0 (2026-11-13)

Historical scenarios, a gravity dimension and a scenario-level coverage verdict (ADR-013). The Apollo 1 pure-oxygen atmosphere is the first historical scenario. Response shapes gain **required** fields: clients that validate strictly must take this contract (AURA re-discovery; the `aura-link2-contract` job checks the dry run).

**Added (ADR-013)**
- `Scenario.gravity` (`microgravity | lunar | martian | earth`) and `Scenario.kind` (`mission | historical | custom`); `basis` gains `historical`. Mission scenarios are `microgravity` / `mission`, as before.
- Scenario `apollo1_pad_1967`: 100 % O₂ at 16.7 psia (115.14 kPa), `gravity: earth`, cited to the Apollo 204 Review Board report (FF-NTRS-19930078717 p. 189).
- `InvestigationListResponse.coverage` (schema `Coverage`): `verdict` `covered | partial | none`, headline, reasons, the nearest real flight test with its evidence cells, the gap, the flown ranges and the method. For Apollo 1: `none`, "None of the 1950 flight tests cover this atmosphere." (840 before the ACME, CFI and SAFFIRE-II/III tables below were counted.)
- `GET /api/scenarios/{scenario_id}/history` (`getScenarioHistory`, `ScenarioHistoryResponse`, `CitedSource`): story, lesson, a page-cited timeline and the data-covered alternative scenario (`orion_max_o2`). 404 `SCENARIO_HISTORY_NOT_FOUND` for non-historical scenarios.
- Query parameter `gravity` on `GET /api/investigations`, `GET /api/investigations/{investigation_id}` and `GET /api/insights`, for a custom atmosphere only (400 with a named scenario).

**Changed**
- The scenario model estimate (`flex_model_scenario_estimate`) is refused (`coverage_gap`, no probabilities) when the scenario's gravity is not among the flight tests' regimes. The reason is added to its statement.
- `FlexOutcomeResponse.o2_sweep` extends past the trained O₂ range to a requested O₂ outside it (up to 6 extra points, all `in_domain: false`, `probabilities: null`). For a requested O₂ inside the range, the 12 points are unchanged.
- `Coverage` verdict `partial` also covers an atmosphere outside the flown O₂ or pressure range. (The lunar lander, 34 % O₂ at 62.7 kPa, was `partial` on the four original tables; with the ACME CFI-G flames, flown down to ~43 kPa, it is `covered`: 11 CFI-G and 9 FLEX tests lie near it.)
- Coverage and the investigation list also read the ACME (PSI-10, PSI-159) and CFI (PSI-39) tables for O₂ and pressure, and SAFFIRE-II/III and SAME/SAME-R for flow and duration. ACME inverse flames give no ambient O₂ (their XO₂ is the burner stream). The nearest test is cited to its O₂ and pressure cells for these tables too. For Apollo 1 the nearest test is now a CFI-G normal flame at 39.97 % O₂ (Apollo 1's O₂ is now 2.5× the highest flown; it was 2.9× against FLEX at 34 %).

**Corpus**
- 3 NTRS reports added for the citations (27 in total): FF-NTRS-19930078717 (Apollo 204 Review Board report), FF-NTRS-20170008542 (flame-retardant fibres) and FF-NTRS-20070021223 (Orion ECLSS fire protection).

**Also in this release** (merged after 0.6.0)

**Added**
- Operator speech for video analyses (off by default: nothing changes for a deployment that does not set `FLAME_TRANSCRIPTION_ENABLED=true`).
  - `FlameVideoAnalysisResult.audio` (`VideoAudioTranscript`), optional and present only when `FLAME_TRANSCRIPTION_ENABLED=true`. It holds the speech from the video's audio track, transcribed locally with faster-whisper (`docs/cv/audio-transcription.md`).
    - `status`: `transcribed`, `no_speech`, `silent` (the track exists but its loudest second is at or below -55 dBFS, so no model ran), `no_audio_track`, or `unavailable` (with `failure_code`; the video analysis still completes).
    - `segments[]` (`VideoAudioSegment`): `start_s`, `end_s`, `text`, `avg_logprob`, `no_speech_prob`. Timestamps are approximate to a few seconds.
    - `classification` is always `machine_transcribed`. It is not a measurement and not evidence: no evidence kind, observation or warning code was added, and AI interpretation does not read it. `note` carries the caveat to show beside the text.
  - Settings `FLAME_TRANSCRIPTION_ENABLED` (default `false`), `FLAME_TRANSCRIPTION_MODEL` (default `small`) and `FLAME_TRANSCRIPTION_CACHE_DIR`.
- Migration `0012_chunk_search_tsv_keep`: a stopword-free full-text vector so a question about helium (`He`) can match. Read only when `FLAME_LEXICAL_MODE=or_idf`; no response shape changes.
- Settings `FLAME_LEXICAL_MODE=and|or_idf` and `FLAME_DENSE_GRANULARITY=page|window` (both default to the existing behaviour; no response shape changes) and migration `0011_chunk_window_embedding`. See `docs/ai/retrieval-pipeline.md` §0a–0b.
- `ChatWarning` values `answer_values_not_in_cited_evidence` and `answer_withheld_unsupported_values` (`/api/chat`): a figure in the answer is in none of the cited passages. Setting `ANSWER_SUPPORT_CHECK=warn|strict|off` (default `warn`: warning only; answers with this warning are not cached). `/api/chat` is excluded from AURA's tools.
- Graph entity types `platform` and `instrument`, and predicates `ran_on` and `measured_with` (`GraphEntityType`, `GraphPredicate`). They appear only on edges with `extraction_method` `nlp_extraction` (migration `0010_nlp_record`), which are `unreviewed` co-occurrence associations within one page, each citing that page's evidence. Clients that switch on a predicate or entity type should treat unknown values as "other". `document describes investigation` edges can now also come from NLP (a report naming exactly one investigation on its first page).

**Changed**
- `retrieval.query_rewrite.rewriter_version` is now `1.0.1` (was `1.0.0`). The query rewriter no longer expands `psi` when it directly follows a number (`14.7 psi` is a pressure, not NASA's PSI programme). The shape of the response is unchanged.

## 0.6.0 (2026-11-12)

ADR-006 to 009 built. Additive for read clients; read **Changed** before upgrading a deployment that uses client keys for admin work. AURA's Link 2 dry run at the pinned AURA revision `d696fad`: **16 tools accepted, 10 operations excluded**, exit 0.

**Changed (ADR-009)**
- `/api/admin/*` needs the new **`admin` scope**, reads included. A client key with only `write` scope now gets **403 `FORBIDDEN`** there, where it used to be allowed. Create admin keys with `python -m flame_api.clients create NAME --scopes admin --owner PERSON`; `--owner` is required for admin keys (migration `0008_api_client_owner`). The deprecated `FLAME_WRITE_API_TOKEN` keeps working for admin operations.

**Added (ADR-008)**
- `POST /api/analyses/{analysis_id}/cancel` (write scope, `x-aura-exclude`):
  - a queued analysis becomes `cancelled` (200);
  - a processing one records `cancel_requested_at` and stops at its next checkpoint (202);
  - an already cancelled one returns 200;
  - `completed` or `failed` returns 409 **`ANALYSIS_NOT_CANCELLABLE`**.
- `Analysis.progress` (`AnalysisProgress`: `frames_done`, `frames_total`, `checkpointed_at`) for video jobs, and `Analysis.cancel_requested_at`. Both are optional and absent when they do not apply.
- `WarningCode.JOB_RESUMED_FROM_CHECKPOINT`: a recovered video job resumed from its stored frames (migration `0009_video_checkpoints`).

**Added (ADR-006)**
- `RetrievalInfo.stack_version`, `.query_rewrite` (`QueryRewrite`) and `.reranking` (`RerankingInfo`: `disabled` | `applied` | `unavailable`). They are required: every `/api/search` response now has them.
- Ordering is unchanged with the reranker off (identical top 5 on the 26-question gold set). With `FLAME_RERANKER_ENABLED=true`, the first `FLAME_RERANK_DEPTH` results are reordered by a cross-encoder; `score` stays monotonic with `rank`.

**Default changed after release (no contract change, PR #30)**
- The reranker is **on by default** (`FLAME_RERANKER_ENABLED=true`, depth 10, fastembed ONNX). `/api/search` and chat results are reordered within the first 10, and `retrieval.reranking.status` is now `applied` (or `unavailable` when the model cannot load). Set `FLAME_RERANKER_ENABLED=false` for the previous order.
- The knowledge graph resolves four reviewed spelling variants (E2-6 §0), so `GET /api/graph/entities?type=fuel` lists 55 entities instead of 59.

**Added (ADR-007)**, tag **Knowledge graph**:
- `GET /api/graph/entities` (read scope; AURA tool `api_list_graph_entities`);
- `GET /api/graph/entities/{entity_id}` (read scope; AURA tool `api_get_graph_entity`; 404 **`ENTITY_NOT_FOUND`**);
- `GET /api/admin/graph/consistency` (admin scope, `x-aura-exclude`);
- schemas `GraphEntityType`, `GraphPredicate`, `GraphReviewStatus`, `GraphEntity`, `GraphEdge`, `GraphNeighbourhood`, `GraphEntityListResponse`, `GraphEntityResponse`, `GraphConsistencyCheck`, `GraphConsistencyResponse`.

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
