# Flame in Freefall: API Response Schemas

**Generated from [`openapi.json`](openapi.json)** (OpenAPI 3.1.0, API 0.8.0) by `docs/tools/render_api_schemas.py`. Do not edit by hand.
Endpoint behaviour, examples and display rules: [`FRONTEND_API_CONTRACT.md`](FRONTEND_API_CONTRACT.md).

Reading the tables: *Required = yes* means the key is always present. A nullable field (`| null`) is still present, with value `null`, which means "not present or not established" and is never a stand-in for `0`. The only optional keys in responses are those of [`ErrorDetails`](#errordetails).

## 1. Responses by endpoint

| Method | Path | Success | Error statuses (body: [`ErrorResponse`](#errorresponse) unless noted) |
|---|---|---|---|
| GET | `/api/health` | 200 [`HealthResponse`](#healthresponse) | 401, 403, 500, 503 [`HealthResponse`](#healthresponse) |
| GET | `/api/dashboard/counts` | 200 [`DashboardCountsResponse`](#dashboardcountsresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/search` | 200 [`SearchResponse`](#searchresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/documents/{document_id}` | 200 [`DocumentResponse`](#documentresponse) | 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/experiments/{experiment_id}` | 200 [`ExperimentResponse`](#experimentresponse) | 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/evidence/{evidence_id}` | 200 [`EvidenceResponse`](#evidenceresponse) | 400, 401, 403, 404, 429, 500, 503 |
| POST | `/api/analyses` | 202 [`AnalysisResponse`](#analysisresponse) | 400, 401, 403, 413, 415, 422, 429, 500, 503 |
| GET | `/api/analyses` | 200 [`AnalysisListResponse`](#analysislistresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/analyses/{analysis_id}` | 200 [`AnalysisResponse`](#analysisresponse) | 400, 401, 403, 404, 429, 500, 503 |
| POST | `/api/analyses/{analysis_id}/cancel` | 200 [`AnalysisResponse`](#analysisresponse)<br>202 [`AnalysisResponse`](#analysisresponse) | 400, 401, 403, 404, 409, 429, 500, 503 |
| GET | `/api/analyses/{analysis_id}/artifacts/{artifact_kind}` | 200 `image/png` bytes or `image/jpeg` bytes | 400, 401, 403, 404, 409, 429, 500, 503 |
| GET | `/api/documents` | 200 [`DocumentListResponse`](#documentlistresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/experiments` | 200 [`ExperimentListResponse`](#experimentlistresponse) | 400, 401, 403, 429, 500, 503 |
| POST | `/api/chat` | 200 [`ChatResponse`](#chatresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/ai/providers` | 200 [`AiProvidersResponse`](#aiprovidersresponse) | 400, 401, 403, 429, 500, 503 |
| PUT | `/api/admin/ai/mode` | 200 [`ModeChangeResponse`](#modechangeresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/admin/files` | 200 [`AdminFileListResponse`](#adminfilelistresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/admin/ingestion-runs` | 200 [`IngestionRunListResponse`](#ingestionrunlistresponse) | 400, 401, 403, 429, 500, 503 |
| POST | `/api/admin/files/{file_id}/reprocess` | 200 [`FileReprocessResponse`](#filereprocessresponse) | 400, 401, 403, 404, 409, 429, 500, 503 |
| PUT | `/api/admin/evidence/{evidence_id}/review` | 200 [`EvidenceReviewResponse`](#evidencereviewresponse) | 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/admin/audit` | 200 [`AuditEventListResponse`](#auditeventlistresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/investigations` | 200 [`InvestigationListResponse`](#investigationlistresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/investigations/{investigation_id}` | 200 [`InvestigationResponse`](#investigationresponse) | 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/insights` | 200 [`InsightListResponse`](#insightlistresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/insights/flex-outcome` | 200 [`FlexOutcomeResponse`](#flexoutcomeresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/graph/entities` | 200 [`GraphEntityListResponse`](#graphentitylistresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/graph/entities/{entity_id}` | 200 [`GraphEntityResponse`](#graphentityresponse) | 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/admin/graph/consistency` | 200 [`GraphConsistencyResponse`](#graphconsistencyresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/scenarios/{scenario_id}/history` | 200 [`ScenarioHistoryResponse`](#scenariohistoryresponse) | 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/insights/suppression-advice` | 200 [`SuppressionAdviceResponse`](#suppressionadviceresponse) | 400, 401, 403, 429, 500, 503 |

## 2. Object schemas

### HealthResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | [`OverallStatus`](#overallstatus) | yes |  |
| `environment` | `"development"` \| `"staging"` \| `"production"` | yes | Deployment environment. |
| `version` | [`VersionInfo`](#versioninfo) | yes |  |
| `knowledge_version` | string \| `null` | yes | Published corpus/knowledge version. Null until the first index publication. |
| `services` | [`HealthServices`](#healthservices) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |
| `ai` | [`AiStatus`](#aistatus) | no | Execution mode and model providers (0.2.0). |

### ErrorResponse

The single error envelope used by every endpoint for every non-2xx status (RFC 7807-style fields per MVP plan §12, wrapped under `error`).

| Field | Type | Required | Description |
|---|---|---|---|
| `error` | [`ErrorBody`](#errorbody) | yes |  |

### DashboardCountsResponse

All counts are exact `COUNT(*)` reads at `meta.generated_at`. On failure the endpoint returns 503, never zeros.

| Field | Type | Required | Description |
|---|---|---|---|
| `documents` | integer (minimum=0) | yes | Published `document` records (parsed NASA/NIST documents). Not raw files: files.jsonl has 121 file records, most of which are data/media, not documents. |
| `experiments` | integer (minimum=0) | yes | `experiment` records (one per test, e.g. a BASS-II test ID) that have at least one ExperimentCondition. |
| `analyses` | integer (minimum=0) | yes | Flame analyses in status `completed`. |
| `analyses_in_progress` | integer (minimum=0) | yes | Flame analyses in status `queued` or `processing`. |
| `chunks` | integer (minimum=0) | yes | All `document_chunk` rows (searchable passages), embedded or not. |
| `indexed_chunks` | integer (minimum=0) | yes | Chunks with a vector in the published vector index (`chunk_embedding` rows of the model named by `vector_index_manifest`). 0 only when no index is published (no manifest row, or not PostgreSQL). Fewer than `chunks` means the index is stale and search runs lexical-only. |
| `knowledge_version` | string \| `null` | yes | Corpus version the document count refers to. |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### SearchResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | yes | The query as received (after trimming). |
| `results` | [`SearchResult`](#searchresult)[] | yes |  |
| `pagination` | [`Pagination`](#pagination) | yes |  |
| `filters` | [`SearchFilters`](#searchfilters) | yes |  |
| `retrieval` | [`RetrievalInfo`](#retrievalinfo) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### DocumentResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `document` | [`Document`](#document) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### ExperimentResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `experiment` | [`Experiment`](#experiment) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### EvidenceResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `evidence` | [`Evidence`](#evidence) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### AnalysisResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `analysis` | [`Analysis`](#analysis) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### AnalysisListResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `items` | [`AnalysisSummary`](#analysissummary)[] | yes |  |
| `pagination` | [`Pagination`](#pagination) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### DocumentListResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `items` | [`DocumentSummary`](#documentsummary)[] | yes |  |
| `pagination` | [`Pagination`](#pagination) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### ExperimentListResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `items` | [`ExperimentSummary`](#experimentsummary)[] | yes |  |
| `pagination` | [`Pagination`](#pagination) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### ChatResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `request_id` | string | yes |  |
| `memory_used` | boolean | yes |  |
| `knowledge_version` | string | yes | `unversioned` until the first publication. |
| `answer` | string (maxLength=4000) | yes |  |
| `sources` | [`ChatSource`](#chatsource)[] | yes |  |
| `cache_hit` | boolean | yes |  |
| `model` | [`ChatModel`](#chatmodel) | yes |  |
| `execution` | [`ExecutionMetadata`](#executionmetadata) \| [`RoutingFailure`](#routingfailure) \| `null` | yes | ExecutionMetadata when a model answered; RoutingFailure when none could (warning generation_unavailable); null when no evidence matched. |
| `warnings` | [`ChatWarning`](#chatwarning)[] | yes |  |

### AiProvidersResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | [`ExecutionMode`](#executionmode) | yes |  |
| `providers` | [`AiProvider`](#aiprovider)[] | yes |  |
| `decisions` | object | yes | Routing decision counters keyed `task\|provider\|outcome`, since process start. |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |
| `mode_source` | [`AiModeSource`](#aimodesource) | no |  |
| `env_mode` | [`ExecutionMode`](#executionmode) | no | FLAME_AI_EXECUTION_MODE as configured; can differ from `mode` only under an audit override. |

### ModeChangeResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `previous_mode` | [`ExecutionMode`](#executionmode) | yes |  |
| `mode` | [`ExecutionMode`](#executionmode) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### AdminFileListResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `items` | [`AdminFile`](#adminfile)[] | yes |  |
| `pagination` | [`Pagination`](#pagination) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### IngestionRunListResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `items` | [`IngestionRun`](#ingestionrun)[] | yes |  |
| `pagination` | [`Pagination`](#pagination) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### FileReprocessResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | [`AdminFile`](#adminfile) | yes |  |
| `audit_event` | [`AuditEvent`](#auditevent) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### EvidenceReviewResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `evidence_id` | string (ULID) | yes |  |
| `previous_review_status` | [`ReviewStatus`](#reviewstatus) \| `null` | yes | Null when the row never had a review_status. |
| `review_status` | [`AdminReviewStatus`](#adminreviewstatus) | yes |  |
| `audit_event` | [`AuditEvent`](#auditevent) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### AuditEventListResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `items` | [`AuditEvent`](#auditevent)[] | yes |  |
| `pagination` | [`Pagination`](#pagination) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### InvestigationListResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `scenario` | [`Scenario`](#scenario) | yes |  |
| `scenarios` | [`Scenario`](#scenario)[] | yes |  |
| `ranking_method` | string | yes |  |
| `items` | [`InvestigationSummary`](#investigationsummary)[] | yes |  |
| `not_acquired` | [`NotAcquiredInvestigation`](#notacquiredinvestigation)[] | yes |  |
| `totals` | object | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |
| `coverage` | [`Coverage`](#coverage) | yes |  |

### InvestigationResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `investigation` | [`InvestigationDetail`](#investigationdetail) | yes |  |
| `scenario` | [`Scenario`](#scenario) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### InsightListResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `scenario` | [`Scenario`](#scenario) | yes |  |
| `items` | [`Insight`](#insight)[] | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### FlexOutcomeResponse

FLEX outcome model estimate (claim class `estimated`). `probabilities` is null outside the applicability domain.

| Field | Type | Required | Description |
|---|---|---|---|
| `input` | object | yes |  |
| `probabilities` | object \| `null` | yes |  |
| `predicted_end_state` | `"Completion"` \| `"Disruption"` \| `"Extinction"` \| `null` | yes |  |
| `applicability` | object | yes |  |
| `similar_tests` | [`FlightTestRef`](#flighttestref)[] | yes |  |
| `similar_tests_end_states` | object | yes |  |
| `o2_sweep` | object[] | yes |  |
| `model` | object | yes |  |
| `claim_class` | string | yes |  |
| `scope` | string | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### GraphEntityListResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `items` | [`GraphEntity`](#graphentity)[] | yes |  |
| `pagination` | [`Pagination`](#pagination) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### GraphEntityResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `entity` | [`GraphEntity`](#graphentity) | yes |  |
| `resolved_from` | string (ULID) \| `null` | yes | The requested ID when it was merged into `entity` (old IDs keep resolving); null otherwise. |
| `neighbourhood` | [`GraphNeighbourhood`](#graphneighbourhood) | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### GraphConsistencyResponse

| Field | Type | Required | Description |
|---|---|---|---|
| `ok` | boolean | yes |  |
| `extractor_version` | string | yes |  |
| `checks` | object | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### ScenarioHistoryResponse

A historical scenario (contract 0.7.0): its cited story, timeline and the data-covered alternative to show after the refusal. Every statement carries NTRS pages.

| Field | Type | Required | Description |
|---|---|---|---|
| `scenario` | [`Scenario`](#scenario) | yes |  |
| `year` | integer | yes |  |
| `story` | string | yes |  |
| `lesson` | string | yes |  |
| `lesson_sources` | [`CitedSource`](#citedsource)[] | yes |  |
| `timeline` | object[] | yes |  |
| `alternative` | object | yes |  |
| `claim_class` | `"cited_history"` | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### SuppressionAdviceResponse

Suppression Advisor output. outcome is recommend, no_clear_winner or no_recommendation; recommended_agent is null unless outcome is recommend.

| Field | Type | Required | Description |
|---|---|---|---|
| `input` | object | yes |  |
| `assumptions` | object | yes |  |
| `outcome` | `"recommend"` \| `"no_clear_winner"` \| `"no_recommendation"` | yes |  |
| `recommended_agent` | `"co2"` \| `"water_mist"` \| `null` | yes |  |
| `confidence` | `"high"` \| `"moderate"` \| `"low"` \| `"none"` | yes |  |
| `basis` | `"thermal_model_comparison"` \| `"relative_only"` \| `"hazard_veto"` \| `"sourced_rule"` \| `"out_of_scope"` | yes |  |
| `why` | string[] | yes |  |
| `what_would_change_it` | string[] | yes |  |
| `decision_sources` | string[] | yes |  |
| `crossover_delivery_fraction` | object \| `null` | yes |  |
| `co2_idlh_volume_m3` | number | yes | Cabin volume below which one CO₂ PFE, well mixed, reaches the CO₂ IDLH. |
| `agents` | object | yes |  |
| `gates` | object | yes |  |
| `evidence` | object[] | yes |  |
| `scope` | string | yes |  |
| `disclaimer` | string | yes |  |
| `meta` | [`ResponseMeta`](#responsemeta) | yes |  |

### VersionInfo

| Field | Type | Required | Description |
|---|---|---|---|
| `api_version` | string | yes | Contract version, same as meta.api_version. |
| `build_id` | string \| `null` | yes | Release/build identifier. |
| `git_sha` | string \| `null` | yes | Commit the running API was built from. |

### HealthServices

Fixed set of service keys so the frontend can render a stable status grid.

| Field | Type | Required | Description |
|---|---|---|---|
| `api` | [`ServiceHealth`](#servicehealth) | yes |  |
| `database` | [`ServiceHealth`](#servicehealth) | yes | PostgreSQL (authoritative store). |
| `vector_index` | [`ServiceHealth`](#servicehealth) | yes | pgvector extension + active chunk index (ADR-002 planned: pgvector before a dedicated vector DB). Same server as `database`, reported separately because it can be absent while Postgres is up. |
| `object_storage` | [`ServiceHealth`](#servicehealth) | yes | S3-compatible store (MinIO locally) for uploads, masks, overlays. |
| `cache` | [`ServiceHealth`](#servicehealth) | yes | Redis (CAG, rate limits, job queue). Optional: failures degrade to recomputation. |
| `cv_model` | [`ServiceHealth`](#servicehealth) | yes | Flame CV pipeline worker (detector/segmenter loaded). |
| `llm` | [`ServiceHealth`](#servicehealth) | yes | Flame's own model router (Ollama/vLLM) used for grounded answers. |
| `aura` | [`ServiceHealth`](#servicehealth) | yes | AURA AI gateway. `disabled` unless FLAME_AURA_ENABLED=true. |

### ResponseMeta

Present on every successful JSON response (MVP plan §12: request_id, server timestamp, API version).

| Field | Type | Required | Description |
|---|---|---|---|
| `request_id` | string | yes | Correlation ID for this request. Echoes the caller's `X-Request-ID` when supplied, otherwise server-generated. Also returned in the `X-Request-ID` response header. |
| `generated_at` | string (date-time) | yes | Server time (UTC) at which the response was produced. |
| `api_version` | string | yes | Semantic version of this API contract. |

### AiStatus

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | [`ExecutionMode`](#executionmode) | yes |  |
| `providers` | [`AiProvider`](#aiprovider)[] | yes |  |
| `mode_source` | [`AiModeSource`](#aimodesource) | no |  |
| `env_mode` | [`ExecutionMode`](#executionmode) | no | FLAME_AI_EXECUTION_MODE as configured; can differ from `mode` only under an audit override. |

### ErrorBody

| Field | Type | Required | Description |
|---|---|---|---|
| `code` | [`ErrorCode`](#errorcode) | yes |  |
| `message` | string | yes | Safe, human-readable summary. |
| `request_id` | string | yes | Same value as the `X-Request-ID` response header. |
| `retryable` | boolean | yes | True when the identical request may succeed later (429, 503). |
| `field_errors` | [`FieldError`](#fielderror)[] | yes | Per-field validation failures; empty for non-validation errors. |
| `details` | [`ErrorDetails`](#errordetails) | yes |  |

### SearchResult

| Field | Type | Required | Description |
|---|---|---|---|
| `result_id` | string | yes | Stable ID of the hit (chunk ID for passages, experiment ID for experiments). Unique within one response. |
| `result_type` | [`SearchResultType`](#searchresulttype) | yes |  |
| `rank` | integer (minimum=1) | yes | 1-based position across all pages. |
| `score` | number | yes | Relevance score from the retriever. Ordinal only; not a probability and not a confidence. |
| `title` | string | yes | Document title or experiment display name. |
| `snippet` | string | yes | Plain-text excerpt (no HTML). Verbatim from the source for document hits. |
| `highlights` | [`TextSpan`](#textspan)[] | yes | Matched-term spans within `snippet`. |
| `source` | [`SourceRef`](#sourceref) | yes |  |
| `document_id` | string (ULID) \| `null` | yes |  |
| `document_type` | [`DocumentType`](#documenttype) \| `null` | yes |  |
| `experiment_id` | string (ULID) \| `null` | yes |  |
| `experiment` | [`SearchResultExperiment`](#searchresultexperiment) \| `null` | yes |  |
| `evidence_id` | string (ULID) \| `null` | yes | Evidence record that backs this hit. Resolve with GET /api/evidence/{evidence_id}. |
| `has_evidence` | boolean | yes | True iff `evidence_id` is non-null. |
| `locator` | [`Locator`](#locator) \| `null` | yes |  |
| `ingested_at` | string (date-time) | yes | When the underlying record was ingested/published. |

### Pagination

| Field | Type | Required | Description |
|---|---|---|---|
| `page` | integer (minimum=1) | yes | 1-based page number that was returned. |
| `page_size` | integer (minimum=1, maximum=100) | yes | Items per page that was applied. |
| `total_items` | integer (minimum=0) | yes | Total matching items across all pages. |
| `total_pages` | integer (minimum=0) | yes | ceil(total_items / page_size); 0 when there are no items. |

### SearchFilters

Echo of the filters the server actually applied, after defaults.

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | [`SearchResultType`](#searchresulttype) \| `null` | yes |  |
| `source_id` | string[] | yes |  |
| `experiment_id` | string \| `null` | yes |  |
| `domain` | [`SearchDomain`](#searchdomain) | yes |  |

### RetrievalInfo

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | [`RetrievalMode`](#retrievalmode) | yes |  |
| `knowledge_version` | string \| `null` | yes |  |
| `index_version` | string \| `null` | yes | Vector index version; null in lexical mode. |
| `searched_but_empty` | boolean | yes | True when the corpus was searched and nothing relevant was found (render as an honest empty state, not an error). |
| `stack_version` | string | yes | Version of the ai/rag search stack that ordered the results (ADR-006), e.g. `flame-search-2.0.0`. |
| `query_rewrite` | [`QueryRewrite`](#queryrewrite) | yes |  |
| `reranking` | [`RerankingInfo`](#rerankinginfo) | yes |  |

### Document

| Field | Type | Required | Description |
|---|---|---|---|
| `document_id` | string (ULID) | yes |  |
| `title` | string | yes |  |
| `document_type` | [`DocumentType`](#documenttype) | yes |  |
| `identifier` | string \| `null` | yes | Report number or upstream identifier, e.g. `NASA/TM-2000-209773` or NTRS `20000034017`. |
| `persistent_identifier` | string \| `null` | yes | Document-level DOI when the document has its own. |
| `source` | [`SourceRef`](#sourceref) | yes |  |
| `file` | [`FileRef`](#fileref) | yes |  |
| `page_count` | integer \| `null` (minimum=0) | yes |  |
| `text_layer` | [`TextLayer`](#textlayer) | yes |  |
| `pages_without_text` | integer[] | yes | Pages flagged for OCR; their text is not searchable yet. |
| `parser_version` | string \| `null` | yes |  |
| `ingested_at` | string (date-time) | yes |  |
| `knowledge_version` | string \| `null` | yes |  |
| `experiment_ids` | string (ULID)[] | yes | Experiments this document is linked to. |
| `evidence_count` | integer (minimum=0) | yes | Evidence records whose target is this document. |

### Experiment

| Field | Type | Required | Description |
|---|---|---|---|
| `experiment_id` | string (ULID) | yes |  |
| `test_id` | string | yes |  |
| `investigation` | string \| `null` | yes | Investigation short name, e.g. BASS-II. |
| `source` | [`SourceRef`](#sourceref) | yes |  |
| `gravity_regime` | [`GravityRegime`](#gravityregime) | yes |  |
| `fuel_or_material` | string \| `null` | yes |  |
| `conditions` | [`ExperimentCondition`](#experimentcondition)[] | yes |  |
| `document_ids` | string (ULID)[] | yes |  |
| `table_file` | [`FileRef`](#fileref) \| `null` | yes |  |

### Evidence

| Field | Type | Required | Description |
|---|---|---|---|
| `evidence_id` | string (ULID) | yes |  |
| `kind` | [`EvidenceKind`](#evidencekind) | yes |  |
| `origin` | [`EvidenceOrigin`](#evidenceorigin) | yes |  |
| `citation` | string | yes | Formatted human-readable citation assembled from stored fields only. |
| `source` | [`SourceRef`](#sourceref) \| `null` | yes | Null only for calculated_measurement evidence. |
| `document_id` | string (ULID) \| `null` | yes |  |
| `experiment_id` | string (ULID) \| `null` | yes |  |
| `analysis_id` | string (ULID) \| `null` | yes |  |
| `file` | [`FileRef`](#fileref) \| `null` | yes | The original (or derived) file the locator applies to. |
| `locator` | [`Locator`](#locator) \| `null` | yes |  |
| `excerpt` | string \| `null` | yes | Verbatim quote from the original at the locator. Null for purely numeric evidence. |
| `value` | [`EvidenceValue`](#evidencevalue) \| `null` | yes |  |
| `measurement_or_claim_type` | string \| `null` | yes | Data dictionary field, e.g. `o2_fraction`, `flame_area_px`. |
| `extraction_method` | [`ExtractionMethod`](#extractionmethod) | yes |  |
| `extraction_confidence` | number \| `null` (minimum=0, maximum=1) | yes | Only when the extraction method itself produced one (e.g. OCR). Null otherwise — never synthesised. |
| `review_status` | [`ReviewStatus`](#reviewstatus) | yes |  |
| `transformation_id` | string \| `null` | yes | Parser/pipeline version that produced this record. |
| `created_at` | string (date-time) | yes |  |
| `knowledge_version` | string \| `null` | yes |  |

### Analysis

| Field | Type | Required | Description |
|---|---|---|---|
| `analysis_id` | string (ULID) | yes |  |
| `analysis_type` | [`AnalysisType`](#analysistype) | yes |  |
| `status` | [`AnalysisStatus`](#analysisstatus) | yes |  |
| `created_at` | string (date-time) | yes |  |
| `updated_at` | string (date-time) | yes |  |
| `started_at` | string (date-time) \| `null` | yes |  |
| `completed_at` | string (date-time) \| `null` | yes |  |
| `cancel_requested_at` | string (date-time) \| `null` | no | When a cancel was requested for a running job (contract 0.6.0). Absent when none was requested. The job stops at its next checkpoint (video) or before storing its result (image), then status becomes `cancelled`. |
| `input` | [`AnalysisInput`](#analysisinput) | yes |  |
| `pipeline` | [`PipelineInfo`](#pipelineinfo) \| `null` | yes | Null while queued. |
| `result` | [`FlameAnalysisResult`](#flameanalysisresult) \| [`FlameVideoAnalysisResult`](#flamevideoanalysisresult) \| `null` | yes | flame_image, non-null iff status = completed. |
| `interpretation` | [`Interpretation`](#interpretation) | yes |  |
| `artifacts` | [`Artifact`](#artifact)[] | yes | `original` is present from creation; the others appear when status = completed. |
| `warnings` | [`Warning`](#warning)[] | yes |  |
| `failure` | [`AnalysisFailure`](#analysisfailure) \| `null` | yes | Non-null iff status is failed or cancelled. |
| `poll_after_ms` | integer \| `null` (minimum=0) | yes | Suggested delay before the next GET while non-terminal; null when terminal. |
| `progress` | [`AnalysisProgress`](#analysisprogress) \| `null` | no | Video jobs only (contract 0.6.0); absent for image analyses. |

### AnalysisSummary

| Field | Type | Required | Description |
|---|---|---|---|
| `analysis_id` | string (ULID) | yes |  |
| `analysis_type` | [`AnalysisType`](#analysistype) | yes |  |
| `status` | [`AnalysisStatus`](#analysisstatus) | yes |  |
| `created_at` | string (date-time) | yes |  |
| `completed_at` | string (date-time) \| `null` | yes |  |
| `original_filename` | string | yes |  |
| `image_sha256` | string | yes | Lowercase hex SHA-256 of the exact bytes. |
| `experiment_id` | string (ULID) \| `null` | yes |  |
| `pipeline_version` | string \| `null` | yes |  |
| `detection_status` | [`DetectionStatus`](#detectionstatus) \| `null` | yes |  |
| `flame_area_px` | number \| `null` | yes | geometry_px.area.value, for list display. |
| `calibration_state` | [`CalibrationState`](#calibrationstate) | yes |  |
| `warning_count` | integer (minimum=0) | yes |  |
| `overlay_url` | string (uri-reference) \| `null` | yes | Overlay artifact URL when completed with a flame; use as thumbnail. |

### DocumentSummary

| Field | Type | Required | Description |
|---|---|---|---|
| `document_id` | string | yes |  |
| `title` | string | yes |  |
| `document_type` | string | yes |  |
| `source` | [`SourceRef`](#sourceref) | yes |  |
| `page_count` | integer \| `null` (minimum=0) | yes |  |
| `text_layer` | string | yes |  |
| `parser_version` | string \| `null` | yes |  |
| `ingested_at` | string (date-time) | yes |  |
| `knowledge_version` | string \| `null` | yes |  |

### ExperimentSummary

| Field | Type | Required | Description |
|---|---|---|---|
| `experiment_id` | string | yes |  |
| `test_id` | string | yes |  |
| `investigation` | string \| `null` | yes |  |
| `source` | [`SourceRef`](#sourceref) | yes |  |
| `gravity_regime` | string | yes |  |
| `fuel_or_material` | string \| `null` | yes |  |
| `condition_count` | integer (minimum=0) | yes |  |

### ChatSource

| Field | Type | Required | Description |
|---|---|---|---|
| `evidence_id` | string | yes |  |
| `document_id` | string | yes |  |
| `title` | string | yes |  |
| `location` | string | yes |  |

### ChatModel

| Field | Type | Required | Description |
|---|---|---|---|
| `provider` | string | yes |  |
| `name` | string | yes |  |
| `version` | string | yes |  |

### ExecutionMetadata

Which provider and model produced a result, and why the router chose it.

| Field | Type | Required | Description |
|---|---|---|---|
| `task` | string (maxLength=64) | yes |  |
| `provider` | string (maxLength=64) | yes |  |
| `runtime` | string (maxLength=64) | yes |  |
| `model` | string \| `null` (maxLength=256) | yes |  |
| `version` | string \| `null` (maxLength=128) | yes |  |
| `locality` | `"local"` \| `"external"` | yes |  |
| `mode` | [`ExecutionMode`](#executionmode) | yes |  |
| `fallback_used` | boolean | yes |  |
| `routing_reason` | string (maxLength=1000) | yes |  |
| `latency_ms` | number (minimum=0) | yes |  |
| `attempts` | object[] (maxItems=16) | yes |  |

### RoutingFailure

Why no model could serve the request (degraded mode).

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | [`ExecutionMode`](#executionmode) | yes |  |
| `reasons` | object[] (maxItems=32) | yes |  |

### AiProvider

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes |  |
| `runtime` | string | yes |  |
| `locality` | `"local"` \| `"external"` | yes |  |
| `capabilities` | `"chat"` \| `"structured"` \| `"embeddings"` \| `"reranking"` \| `"vision"` \| `"video"` \| `"transcription"`[] | yes |  |
| `model` | string \| `null` | yes |  |
| `version` | string \| `null` | yes |  |
| `priority` | integer | yes |  |
| `permitted` | boolean | yes | False when the current mode blocks it (external provider in offline_only). |
| `health` | [`AiProviderHealth`](#aiproviderhealth) | yes |  |
| `circuit` | `"closed"` \| `"open"` \| `"half_open"` | yes |  |

### AdminFile

A file_record as administrators see it: FileRef plus its source, status and quarantine reason. Admin only.

| Field | Type | Required | Description |
|---|---|---|---|
| `file_id` | string | yes | File identifier as recorded in datasets/metadata/files.jsonl (`sha256:` + first 16 hex chars). |
| `source_id` | string (maxLength=64) | yes |  |
| `sha256` | string | yes | Lowercase hex SHA-256 of the exact bytes. |
| `original_filename` | string | yes |  |
| `media_type` | string | yes | Content type recorded at ingestion. |
| `size_bytes` | integer (minimum=0) | yes |  |
| `retrieved_at` | string (date-time) | yes | When the original was mirrored (retrieval_timestamp_utc). |
| `canonical_source_url` | string (uri) \| `null` | yes | Where the original was fetched from (s3:// or PSI API URL). |
| `is_original` | boolean | yes | True for an immutable upstream original; false for a derived artefact. |
| `parent_file_id` | string \| `null` | yes | file_id of the original this artefact was derived from. |
| `status` | [`FileStatus`](#filestatus) | yes |  |
| `quarantine_reason` | string \| `null` | yes | Why ingestion quarantined the file (e.g. checksum_mismatch, unreadable_pdf, encrypted_pdf); null when active. |

### IngestionRun

One ingestion_run row (lineage of what parsed which file bytes).

| Field | Type | Required | Description |
|---|---|---|---|
| `run_id` | string (ULID) | yes |  |
| `source_id` | string (maxLength=64) | yes |  |
| `file_id` | string (maxLength=80) | yes |  |
| `transformation_id` | string (maxLength=80) | yes | Parser version that produced the rows, or `quarantine` for a failed run. |
| `input_sha256` | string | yes |  |
| `started_at` | string (date-time) | yes |  |
| `finished_at` | string (date-time) | yes |  |
| `counts` | object | yes | Per-run counts, or `{reason}` for a quarantine run. |

### AuditEvent

One append-only audit_event row (B6).

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | string (ULID) | yes |  |
| `occurred_at` | string (date-time) | yes |  |
| `actor` | string | yes | `write-token` until per-user admin identities exist (ADR-009 step 2). |
| `action` | string | yes | e.g. `file.reprocess`, `evidence.review`, `ai.mode.changed`. |
| `target_type` | string | yes |  |
| `target_id` | string \| `null` | yes |  |
| `before` | object \| `null` | yes | Values before the change; applying them is the rollback. |
| `after` | object \| `null` | yes | Values after the change, plus the administrator's `note` if one was given. |
| `request_id` | string \| `null` | yes |  |

### Scenario

A cabin atmosphere. Quoted or derived values cite NASA/TM-2008-215260 p. 5; `historical` scenarios (contract 0.7.0, ADR-013) are past atmospheres with a cited story at `GET /api/scenarios/{scenario_id}/history`; `user` is a custom query. `gravity` is the gravity the atmosphere exists in: every flight test in this corpus is microgravity, so any other value is outside the flight data.

| Field | Type | Required | Description |
|---|---|---|---|
| `scenario_id` | string | yes |  |
| `name` | string | yes |  |
| `o2_fraction` | number | yes |  |
| `pressure_kpa` | number | yes |  |
| `ppo2_kpa` | number | yes |  |
| `basis` | `"quoted"` \| `"derived"` \| `"user"` \| `"historical"` | yes |  |
| `note` | string | yes |  |
| `citation` | string \| `null` | yes |  |
| `gravity` | `"microgravity"` \| `"lunar"` \| `"martian"` \| `"earth"` | yes |  |
| `kind` | `"mission"` \| `"historical"` \| `"custom"` | yes |  |

### InvestigationSummary

| Field | Type | Required | Description |
|---|---|---|---|
| `investigation_id` | string | yes |  |
| `acronym` | string \| `null` | yes |  |
| `title` | string | yes |  |
| `status` | `"ingested"` \| `"metadata_only"` | yes |  |
| `flight_platform` | string \| `null` | no |  |
| `hardware` | string \| `null` | no |  |
| `dates` | string \| `null` | no |  |
| `persistent_identifier` | string \| `null` | no |  |
| `license` | string \| `null` | no |  |
| `access_url` | string \| `null` | no |  |
| `source` | [`SourceRef`](#sourceref) \| `null` | no |  |
| `fire_safety_use` | string[] | yes |  |
| `key_variables` | string[] | no |  |
| `key_outputs` | string[] | no |  |
| `objective` | [`CitedText`](#citedtext) \| `null` | no |  |
| `data` | [`InvestigationData`](#investigationdata) | yes |  |
| `coverage_note` | string \| `null` | no |  |
| `relevance` | [`Relevance`](#relevance) \| `null` | yes |  |
| `rank` | integer \| `null` (minimum=1) | no | Position in the scenario ranking (list endpoint only); null when the investigation has no ingested data. |

### NotAcquiredInvestigation

| Field | Type | Required | Description |
|---|---|---|---|
| `investigation_id` | string | yes |  |
| `acronym` | string | yes |  |
| `title` | string | yes |  |
| `note` | string | yes |  |

### Coverage

Scenario-level verdict (contract 0.7.0, ADR-013): does any flight test speak to this atmosphere? The relevance score of each investigation can stay above zero for an atmosphere nobody flew, so the dashboard shows this verdict, the nearest real test and the gap before the ranking. `none` when the scenario's gravity was never flown or no test lies within ±0.03 O2 (and ±25% pressure when recorded); `partial` when 1–4 such tests exist or the atmosphere is outside the flown O2 or pressure range; otherwise `covered` (5 or more).

| Field | Type | Required | Description |
|---|---|---|---|
| `verdict` | `"covered"` \| `"partial"` \| `"none"` | yes |  |
| `headline` | string | yes |  |
| `tests_total` | integer | yes |  |
| `neighbourhood_tests` | integer | yes |  |
| `neighbourhood_by_investigation` | object | yes |  |
| `gravity` | object | yes |  |
| `tested_range` | object | yes |  |
| `nearest_test` | object \| `null` | yes |  |
| `gap` | object \| `null` | yes |  |
| `reasons` | string[] | yes |  |
| `method` | string | yes |  |

### Insight

| Field | Type | Required | Description |
|---|---|---|---|
| `insight_id` | string | yes |  |
| `title` | string | yes |  |
| `kind` | [`InsightKind`](#insightkind) | yes |  |
| `investigations` | string[] | yes |  |
| `statement` | string | yes |  |
| `numbers` | object | yes |  |
| `evidence` | object[] | yes |  |
| `caveats` | string[] | yes |  |

### FlightTestRef

| Field | Type | Required | Description |
|---|---|---|---|
| `experiment_id` | string | yes |  |
| `test_id` | string | yes |  |
| `fuel_or_material` | string \| `null` | no |  |
| `o2_fraction` | number \| `null` | no |  |
| `pressure_kpa` | number \| `null` | no |  |
| `flow_velocity_m_s` | number \| `null` | no |  |
| `end_state` | string \| `null` | no |  |
| `duration_s` | number \| `null` | no |  |
| `end_state_evidence_id` | string \| `null` | no |  |
| `distance` | number | no |  |
| `droplet_diameter_mm` | number | no |  |
| `co2_fraction` | number | no |  |
| `he_fraction` | number | no |  |

### GraphEntity

| Field | Type | Required | Description |
|---|---|---|---|
| `entity_id` | string (ULID) | yes | `stable_ulid(entity_type + ":" + canonical_name)`; stable across rebuilds. |
| `entity_type` | [`GraphEntityType`](#graphentitytype) | yes |  |
| `canonical_name` | string | yes | Lower-cased, whitespace-collapsed name (the resolution key). |
| `display_name` | string | yes | The spelling the source first used. |
| `aliases` | string[] | yes | Other spellings resolved to this entity, including merged entities' names. |
| `properties` | object | yes | Type-specific: `psi_id` (investigation); `experiment_id`, `test_id`, `investigation`, `gravity_regime` (experiment); `unit_si` (condition_variable); `document_id`, `title` (document). |
| `source_id` | string \| `null` | yes |  |
| `evidence_ids` | string (ULID)[] | yes | Evidence that identifies the entity itself (e.g. the test-ID cell). |
| `review_status` | [`GraphReviewStatus`](#graphreviewstatus) | yes |  |
| `merged_into` | string (ULID) \| `null` | yes | Set on an entity merged into another; listings omit merged entities. |
| `knowledge_version` | string \| `null` | yes |  |
| `depth` | integer (minimum=0) | no | Hops from the requested entity (neighbourhood only). |
| `relation_count` | integer (minimum=0) | no | Non-rejected relations touching the entity (listing only). |

### GraphNeighbourhood

| Field | Type | Required | Description |
|---|---|---|---|
| `depth` | integer (minimum=1, maximum=3) | yes |  |
| `predicates` | [`GraphPredicate`](#graphpredicate)[] | yes | Predicates followed; empty means all. |
| `entities` | [`GraphEntity`](#graphentity)[] | yes | The requested entity and the endpoints of the returned edges, nearest first. |
| `edges` | [`GraphEdge`](#graphedge)[] | yes | Edges among reachable entities, nearest first, at most `max_edges`. |
| `truncated` | boolean | yes | True when more edges were reachable than `max_edges`. |
| `reachable_entities` | integer (minimum=1) | yes | Every entity within `depth` hops, including the requested one, before truncation. |
| `reachable_by_type` | object | yes |  |

### GraphConsistencyCheck

| Field | Type | Required | Description |
|---|---|---|---|
| `count` | integer (minimum=0) | yes |  |
| `blocking` | boolean | yes | A blocking check with a non-zero count makes `ok` false; a non-blocking one lists candidates for human review. |
| `examples` | object[] (maxItems=20) | yes |  |

### CitedSource

An NTRS report page. `evidence_id` is the ingested page (null until the report is ingested).

| Field | Type | Required | Description |
|---|---|---|---|
| `source_id` | string | yes |  |
| `page` | integer (minimum=1) | yes |  |
| `quote` | string \| `null` | yes |  |
| `title` | string \| `null` | yes |  |
| `short_name` | string \| `null` | yes |  |
| `access_url` | string \| `null` | yes |  |
| `evidence_id` | string \| `null` | yes |  |

### SuppressionAgentAdvice

| Field | Type | Required | Description |
|---|---|---|---|
| `agent` | `"co2"` \| `"water_mist"` | yes |  |
| `extinguisher` | string | yes |  |
| `charge` | object | yes |  |
| `post_discharge` | object | yes |  |
| `effective_enthalpy_kcal_per_mol_o2` | number \| `null` | yes |  |
| `hazards` | [`SuppressionHazard`](#suppressionhazard)[] | yes |  |
| `hazard_level` | `"red"` \| `"amber"` \| `"green"` \| `"info"` | yes |  |
| `flex_estimate` | object \| `null` | yes | FLEX outcome model for CO₂ (claim class estimated) with nearest flight tests. Null for water mist and for non-FLEX fire types. |
| `thermal_estimate` | object \| `null` | yes | Thermal (effective-enthalpy) model, claim class computed. Null when withheld. |
| `withheld` | string[] | yes | Why a number is not shown. |

### ServiceHealth

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | [`ServiceStatus`](#servicestatus) | yes |  |
| `required` | boolean | yes | True if this service being down makes the overall status `unhealthy`. |
| `latency_ms` | number \| `null` (minimum=0) | yes | Probe round-trip time. Null when the probe did not complete. |
| `checked_at` | string (date-time) \| `null` | yes |  |
| `version` | string \| `null` | yes | Safe version identifier (e.g. pipeline version, model name@version, Postgres major). |
| `message` | string \| `null` | yes | Safe one-line explanation when not `up`. Never contains hosts, DSNs or credentials. |

### FieldError

| Field | Type | Required | Description |
|---|---|---|---|
| `field` | string | yes | Request field, query parameter or form part that failed validation, e.g. `page_size` or `image`. |
| `message` | string | yes | Human-readable reason. |

### ErrorDetails

Typed, optional context. Never contains stack traces, SQL, hostnames or secrets.

| Field | Type | Required | Description |
|---|---|---|---|
| `resource_id` | string \| `null` | no | ID that was not found or was in the wrong state. |
| `limit_bytes` | integer \| `null` | no | Upload size limit, for PAYLOAD_TOO_LARGE. |
| `allowed_media_types` | string[] \| `null` | no | Accepted media types, for UNSUPPORTED_MEDIA_TYPE. |
| `retry_after_s` | integer \| `null` | no | Seconds to wait before retrying, for RATE_LIMITED / *_UNAVAILABLE. Mirrors the `Retry-After` header. |

### TextSpan

Half-open [start, end) UTF-16 code-unit offsets into `snippet`, for highlighting matched terms.

| Field | Type | Required | Description |
|---|---|---|---|
| `start` | integer (minimum=0) | yes |  |
| `end` | integer (minimum=0) | yes |  |

### SourceRef

Projection of one row of datasets/registry/source_registry.csv.

| Field | Type | Required | Description |
|---|---|---|---|
| `source_id` | string | yes | Registry source ID. |
| `title` | string | yes | Canonical source title from the registry. |
| `short_name` | string \| `null` | yes | Short name, e.g. BASS-II. |
| `repository` | [`Repository`](#repository) | yes |  |
| `persistent_identifier` | string \| `null` | yes | DOI or other durable identifier, verbatim from the registry. |
| `license` | string \| `null` | yes | License as recorded in the registry, e.g. CC0-1.0. |
| `access_url` | string (uri) | yes | Human-facing canonical landing page of the source. |

### SearchResultExperiment

Present only when result_type = experiment.

| Field | Type | Required | Description |
|---|---|---|---|
| `test_id` | string | yes | Test identifier as written in the source table, e.g. `B1`. |
| `gravity_regime` | [`GravityRegime`](#gravityregime) | yes |  |
| `fuel_or_material` | string \| `null` | yes |  |

### Locator

A resolvable position inside an original artefact (data dictionary: location_pointer).

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | [`LocatorType`](#locatortype) | yes |  |
| `page` | integer \| `null` (minimum=1) | yes | 1-based physical page number in the original file. |
| `section` | string \| `null` | yes | Section heading path, e.g. `1. INTRODUCTION`. |
| `row` | integer \| `null` (minimum=1) | yes | 1-based data row in a tabular original (header excluded). |
| `frame_index` | integer \| `null` (minimum=0) | yes | 0-based frame index in an image sequence or video. |
| `label` | string | yes | Human-readable rendering of the locator, e.g. `p. 5` or `row 12`. |

### QueryRewrite

The rule-based rewrite kept next to the original query (ADR-006, `ai/rag/query/rewrite.py`): whitespace normalisation and expansion of known abbreviations (ISS, PSI, NTRS), appended in parentheses. Lexical search uses the original query; semantic search embeds the rewritten one.

| Field | Type | Required | Description |
|---|---|---|---|
| `rewritten` | string | yes |  |
| `changed` | boolean | yes | False when the rewrite equals the query. |
| `rules_applied` | string[] | yes | e.g. `expand:iss`, `normalize_whitespace`. |
| `rewriter_version` | string | yes |  |
| `used_for` | `"semantic"` \| `"lexical"`[] | yes |  |

### RerankingInfo

What reranking did (ADR-006). `disabled`: FLAME_RERANKER_ENABLED is false and the order is RRF only. `applied`: a cross-encoder, reached through the model router, reordered the first `depth` fused results (they take over the window's fused scores in their new order, so `score` stays monotonic with `rank`). `unavailable`: reranking was configured but failed, so the RRF order is returned; the search does not fail.

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | `"disabled"` \| `"applied"` \| `"unavailable"` | yes |  |
| `model` | string \| `null` | yes |  |
| `depth` | integer \| `null` (minimum=1) | yes | Size of the reranked window, counted from the first result of page 1. |

### FileRef

Projection of one record of datasets/metadata/files.jsonl.

| Field | Type | Required | Description |
|---|---|---|---|
| `file_id` | string | yes | File identifier as recorded in datasets/metadata/files.jsonl (`sha256:` + first 16 hex chars). |
| `sha256` | string | yes | Lowercase hex SHA-256 of the exact bytes. |
| `original_filename` | string | yes |  |
| `media_type` | string | yes | Content type recorded at ingestion. |
| `size_bytes` | integer (minimum=0) | yes |  |
| `retrieved_at` | string (date-time) | yes | When the original was mirrored (retrieval_timestamp_utc). |
| `canonical_source_url` | string (uri) \| `null` | yes | Where the original was fetched from (s3:// or PSI API URL). |
| `is_original` | boolean | yes | True for an immutable upstream original; false for a derived artefact. |
| `parent_file_id` | string \| `null` | yes | file_id of the original this artefact was derived from. |

### ExperimentCondition

| Field | Type | Required | Description |
|---|---|---|---|
| `variable` | string | yes | Condition name from the data dictionary, e.g. `o2_fraction`, `flow_velocity`. |
| `value_numeric` | number \| `null` | yes | Original numeric value. Null when missing or non-numeric — never 0 for missing. |
| `value_text` | string \| `null` | yes | Original textual value when not numeric. |
| `unit_original` | string \| `null` | yes |  |
| `value_si` | number \| `null` | yes |  |
| `unit_si` | string \| `null` | yes |  |
| `origin` | [`ConditionOrigin`](#conditionorigin) | yes |  |
| `evidence_id` | string (ULID) | yes | Evidence record pointing at the source table row. |

### EvidenceValue

Structured value for table/measurement evidence.

| Field | Type | Required | Description |
|---|---|---|---|
| `numeric` | number \| `null` | yes |  |
| `text` | string \| `null` | yes |  |
| `unit` | string \| `null` | yes |  |

### AnalysisInput

| Field | Type | Required | Description |
|---|---|---|---|
| `image_sha256` | string | yes | Lowercase hex SHA-256 of the exact uploaded bytes (the video file for flame_video; the field name predates video). |
| `original_filename` | string | yes |  |
| `media_type` | `"image/png"` \| `"image/jpeg"` \| `"video/mp4"` \| `"video/quicktime"` \| `"video/x-msvideo"` | yes | Media type detected from content (not from the filename or client header). Video types only for flame_video. |
| `size_bytes` | integer (minimum=1) | yes |  |
| `width` | integer (minimum=1) | yes | After EXIF orientation. |
| `height` | integer (minimum=1) | yes | After EXIF orientation. |
| `experiment_id` | string (ULID) \| `null` | yes |  |
| `source_file_id` | string \| `null` | yes | files.jsonl file_id the image was taken from, when it comes from the corpus. |
| `frame_index` | integer \| `null` (minimum=0) | yes |  |
| `calibration` | [`Calibration`](#calibration) | yes |  |
| `notes` | string \| `null` | yes |  |
| `video` | [`VideoInput`](#videoinput) \| `null` | no | Probe metadata and sampling policy; present only for flame_video (0.3.0). |
| `camera_profile` | string \| `null` | no | The camera_profile the analysis was requested with, or null. Absent on analyses created before it was added. |

### PipelineInfo

| Field | Type | Required | Description |
|---|---|---|---|
| `pipeline_version` | string | yes | Version of the whole CV pipeline, e.g. `cv-0.1.0`. |
| `preprocessing_version` | string | yes |  |
| `detector` | [`ModelInfo`](#modelinfo) \| `null` | yes |  |
| `segmenter` | [`ModelInfo`](#modelinfo) \| `null` | yes |  |
| `measurement_space` | `"original_oriented_px"` | yes | All pixel coordinates and measurements are in the original image's pixel grid after EXIF orientation, regardless of any internal resize. |
| `execution` | [`ExecutionMetadata`](#executionmetadata) \| `null` | no | Which vision provider ran (flame_cv or hf_space) (0.2.0). |

### FlameAnalysisResult

| Field | Type | Required | Description |
|---|---|---|---|
| `detection` | [`Detection`](#detection) | yes |  |
| `segmentation` | [`Segmentation`](#segmentation) \| `null` | yes | Null when detection.status = absent. |
| `measurements` | [`Measurements`](#measurements) | yes |  |
| `quality_flags` | [`QualityFlags`](#qualityflags) | yes |  |
| `observations` | [`Statement`](#statement)[] | yes | Deterministic statements derived from the measurements. |

### FlameVideoAnalysisResult

Result of a flame_video analysis (0.3.0). Pixel units only; no temperature. `audio` (0.7.0) is present only when the deployment runs with FLAME_TRANSCRIPTION_ENABLED=true.

| Field | Type | Required | Description |
|---|---|---|---|
| `video` | object | yes |  |
| `sampling` | object | yes |  |
| `frames` | [`VideoFrameMeasurement`](#videoframemeasurement)[] | yes | Sampled frames in time order; temporal order is preserved. |
| `temporal_summary` | [`VideoTemporalSummary`](#videotemporalsummary) | yes |  |
| `observations` | [`Statement`](#statement)[] | yes |  |
| `audio` | [`VideoAudioTranscript`](#videoaudiotranscript) | no |  |

### Interpretation

Optional AI interpretation. Never alters measurements; displayed separately from them.

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | [`InterpretationStatus`](#interpretationstatus) | yes |  |
| `provider` | string \| `null` (maxLength=64) | yes | Router provider that produced the statements (e.g. aura, ollama, vllm). Null until generated. |
| `model` | string \| `null` | yes | Model identifier reported by the provider. |
| `statements` | [`Statement`](#statement)[] | yes |  |
| `rejected_statement_count` | integer (minimum=0) | yes | Statements dropped by Flame validation (unknown evidence IDs, disallowed claim class, temperature claims). |
| `generated_at` | string (date-time) \| `null` | yes |  |
| `execution` | [`ExecutionMetadata`](#executionmetadata) \| `null` | no | Present once generated (0.2.0). |

### Artifact

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | [`ArtifactKind`](#artifactkind) | yes |  |
| `url` | string (uri-reference) | yes | API-relative URL to fetch the bytes: /api/analyses/{analysis_id}/artifacts/{kind}. Never a raw object-storage URL. |
| `media_type` | `"image/png"` \| `"image/jpeg"` \| `"video/mp4"` \| `"video/quicktime"` \| `"video/x-msvideo"` | yes | Media type served. |
| `sha256` | string | yes | Lowercase hex SHA-256 of the exact bytes. |
| `width` | integer (minimum=1) | yes |  |
| `height` | integer (minimum=1) | yes |  |
| `size_bytes` | integer (minimum=0) | yes |  |

### Warning

| Field | Type | Required | Description |
|---|---|---|---|
| `code` | [`WarningCode`](#warningcode) | yes |  |
| `severity` | `"info"` \| `"warning"` | yes | info: context the user should see; warning: affects how results may be used. |
| `message` | string | yes |  |

### AnalysisFailure

| Field | Type | Required | Description |
|---|---|---|---|
| `code` | [`AnalysisFailureCode`](#analysisfailurecode) | yes |  |
| `message` | string | yes |  |
| `retryable` | boolean | yes |  |

### AnalysisProgress

Video jobs only (ADR-008): sampled frames measured and stored in the job's checkpoint so far. Updated once per checkpoint segment (`FLAME_VIDEO_CHECKPOINT_EVERY_FRAMES`, default 10), not per frame.

| Field | Type | Required | Description |
|---|---|---|---|
| `frames_done` | integer (minimum=0) | yes |  |
| `frames_total` | integer (minimum=0) | yes | Sampled frames this job will measure. |
| `checkpointed_at` | string (date-time) | yes |  |

### AiProviderHealth

| Field | Type | Required | Description |
|---|---|---|---|
| `state` | `"up"` \| `"down"` \| `"degraded"` \| `"unknown"` \| `"blocked"` | yes |  |
| `latency_ms` | number \| `null` (minimum=0) | yes |  |
| `detail` | string \| `null` (maxLength=64) | yes |  |
| `model_present` | boolean \| `null` | yes |  |

### CitedText

NASA ISA-Tab metadata text, verbatim, with the evidence row it came from.

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | yes |  |
| `evidence_id` | string | yes |  |

### InvestigationData

What the investigation's published table covers. A null range means the variable is not recorded in the table (never 0).

| Field | Type | Required | Description |
|---|---|---|---|
| `tests` | integer (minimum=0) | yes |  |
| `o2_fraction` | [`ConditionRange`](#conditionrange) \| `null` | yes |  |
| `o2_approximate` | boolean | no |  |
| `pressure_kpa` | [`ConditionRange`](#conditionrange) \| `null` | yes |  |
| `flow_velocity_m_s` | [`ConditionRange`](#conditionrange) \| `null` | yes |  |
| `fuels_or_materials` | object[] | yes |  |
| `distinct_fuels_or_materials` | integer | no |  |
| `end_states` | object \| `null` | no |  |
| `end_state_recorded` | boolean | yes |  |
| `duration_recorded` | boolean | yes |  |
| `quality_flags` | object | no |  |

### Relevance

Evidence relevance of an investigation to a scenario (not a risk score); formula in `ranking_method`.

| Field | Type | Required | Description |
|---|---|---|---|
| `score` | number (minimum=0, maximum=1) | yes |  |
| `components` | object | yes |  |
| `weights` | object | yes |  |
| `neighbourhood_tests` | integer | yes |  |
| `not_recorded` | string[] | yes |  |
| `explanation` | string[] | yes |  |

### SummarySection

One ISA-Tab section (Objective, Hypothesis, Approach, Research impacts), verbatim, with its evidence row.

| Field | Type | Required | Description |
|---|---|---|---|
| `heading` | string | yes |  |
| `text` | string | yes |  |
| `evidence_id` | string | yes |  |

### GraphEdge

| Field | Type | Required | Description |
|---|---|---|---|
| `relation_id` | string (ULID) | yes |  |
| `subject_id` | string (ULID) | yes |  |
| `predicate` | [`GraphPredicate`](#graphpredicate) | yes |  |
| `object_id` | string (ULID) | yes |  |
| `evidence_id` | string (ULID) \| `null` | yes | The evidence row the edge was read from; resolves at `GET /api/evidence/{evidence_id}`. Null only for `manual` edges. |
| `extraction_method` | `"table_parse"` \| `"nlp_extraction"` \| `"manual"` | yes |  |
| `extractor_version` | string \| `null` | yes |  |
| `confidence` | number \| `null` (minimum=0, maximum=1) | yes | 1.0 for deterministic table parses. |
| `review_status` | [`GraphReviewStatus`](#graphreviewstatus) | yes |  |
| `properties` | object | yes | For `has_condition`: `value_si`, `unit_si`, `value_numeric`, `value_text`, `unit_original`, `origin` of the cell. |

### SuppressionHazard

| Field | Type | Required | Description |
|---|---|---|---|
| `hazard` | string | yes |  |
| `level` | `"red"` \| `"amber"` \| `"green"` \| `"info"` | yes |  |
| `value` | number | no |  |
| `unit` | string | no |  |
| `statement` | string | yes |  |
| `claim_class` | `"reference"` \| `"computed"` | yes |  |
| `sources` | string[] | no |  |

### Calibration

| Field | Type | Required | Description |
|---|---|---|---|
| `state` | [`CalibrationState`](#calibrationstate) | yes |  |
| `scale_px_per_mm` | number \| `null` (exclusiveMinimum=0) | yes |  |
| `scale_source` | string \| `null` | yes | How the scale was established, as supplied by the caller. |

### VideoInput

Video metadata probed synchronously at upload (cv/video_ingestion.py probe_video).

| Field | Type | Required | Description |
|---|---|---|---|
| `container` | `"mp4"` \| `"mov"` \| `"avi"` | yes |  |
| `codec` | string | yes | FourCC reported by the decoder, e.g. avc1. |
| `fps` | number (exclusiveMinimum=0) | yes | Constant frame rate used for timestamps (VFR streams are resampled; see variable_frame_rate). |
| `frame_count` | integer (minimum=1) | yes |  |
| `duration_seconds` | number (minimum=0) | yes |  |
| `variable_frame_rate` | boolean | yes |  |
| `sample_every_n_frames` | integer (minimum=1) | yes |  |
| `max_frames` | integer (minimum=1) | yes |  |

### ModelInfo

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes |  |
| `version` | string | yes |  |
| `artifact_digest` | string \| `null` | yes | Digest of the model weights/package; null for non-learned (classical) stages. |

### Detection

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | [`DetectionStatus`](#detectionstatus) | yes |  |
| `confidence` | number \| `null` (minimum=0, maximum=1) | yes | Detector score. Null for classical (threshold) detectors that produce no calibrated score. The single place detection confidence lives. |
| `bounding_box` | [`BoundingBox`](#boundingbox) \| `null` | yes | Null when status is absent. |

### Segmentation

| Field | Type | Required | Description |
|---|---|---|---|
| `mask_type` | `"binary"` | yes | Mask encoding. |
| `threshold_policy` | string | yes | How the mask was produced, e.g. `otsu-v1` or `prob>=0.5`. |
| `component_count` | integer (minimum=0) | yes | Connected flame components in the mask. |
| `confidence` | number \| `null` (minimum=0, maximum=1) | yes | Segmenter score; null when the method produces none. |
| `contours` | [`Point`](#point)[][] | yes | Outer boundary polygon(s) of each component, simplified to `simplification_tolerance_px`. For client-side overlay toggling. |
| `simplification_tolerance_px` | number (minimum=0) | yes |  |

### Measurements

| Field | Type | Required | Description |
|---|---|---|---|
| `geometry_px` | [`GeometryPx`](#geometrypx) | yes |  |
| `geometry_physical` | [`GeometryPhysical`](#geometryphysical) \| `null` | yes | Present only when calibration.state = spatial_scale_provided. |
| `appearance` | [`Appearance`](#appearance) | yes |  |

### QualityFlags

Image-quality flags (MVP plan §10). Null = the check is not implemented / was not evaluated, which is different from false.

| Field | Type | Required | Description |
|---|---|---|---|
| `blur` | boolean \| `null` | yes |  |
| `saturation_clipping` | boolean \| `null` | yes |  |
| `low_light` | boolean \| `null` | yes |  |
| `multiple_flames` | boolean \| `null` | yes |  |
| `occlusion` | boolean \| `null` | yes |  |
| `scale_absent` | boolean | yes |  |
| `calibration_absent` | boolean | yes | Radiometric calibration absent. Always true in v0.1. |

### Statement

| Field | Type | Required | Description |
|---|---|---|---|
| `statement_id` | string | yes |  |
| `text` | string | yes |  |
| `claim_class` | [`ClaimClass`](#claimclass) | yes |  |
| `origin` | [`StatementOrigin`](#statementorigin) | yes |  |
| `evidence_ids` | string (ULID)[] | yes | Flame evidence IDs supporting the statement. Every ID is verified to exist before the statement is stored; `unsupported` statements have none. |
| `measurement_refs` | string[] | yes | JSON-pointer-style references into `result.measurements`, e.g. `geometry_px/area`. |

### VideoFrameMeasurement

| Field | Type | Required | Description |
|---|---|---|---|
| `frame_index` | integer (minimum=0) | yes | Index in the constant-frame-rate timeline. |
| `source_frame_index` | integer \| `null` (minimum=0) | yes |  |
| `timestamp_s` | number (minimum=0) | yes | frame_index / fps. |
| `source_timestamp_s` | number \| `null` | yes | Container timestamp when usable. |
| `detection_status` | [`DetectionStatus`](#detectionstatus) | yes |  |
| `detection_confidence` | number \| `null` | yes |  |
| `pixel_area` | number \| `null` | yes | Flame mask area in px² (measured). Null when absent or the frame failed. |
| `centroid` | object \| `null` | yes | Mask centroid in px. |
| `error_code` | string \| `null` | yes | CV error for this frame; the frame is then reported as uncertain. |

### VideoTemporalSummary

Thresholds and configuration are in docs/cv/temporal-analysis.md.

| Field | Type | Required | Description |
|---|---|---|---|
| `persistence_rate` | number \| `null` (minimum=0, maximum=1) | yes | Fraction of sampled frames with a detected flame. |
| `flicker_frequency_hz` | number \| `null` | yes | Dominant area oscillation; null when not estimable (see flicker_note). Limited by the sampling rate (Nyquist). |
| `flicker_status` | `"estimated"` \| `"not_estimable"` | yes |  |
| `flicker_note` | string \| `null` | yes |  |
| `area_change_rate_px2_per_s` | object | yes |  |
| `tracking_stability_px2` | number \| `null` | yes | Mean rolling centroid variance in px². Null when not estimable (see tracking_note). |
| `track_sessions` | integer \| `null` (minimum=0) | yes | Null when the sampling interval exceeds the tracking gap (see tracking_note). |
| `classification` | `"measured"` | yes | Deterministic statistics over per-frame pixel measurements; no physical units. |
| `method` | string | yes |  |
| `tracking_note` | string \| `null` | yes | Why tracking metrics are null, e.g. sampled frames are further apart than the 0.5 s tracking gap. |

### VideoAudioTranscript

Operator speech from a flame_video analysis's audio track (0.7.0). Context only: not measurement, not evidence, and not used by AI interpretation.

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | `"no_audio_track"` \| `"silent"` \| `"transcribed"` \| `"no_speech"` \| `"unavailable"` | yes | `silent` means the track exists but its loudest second is at or below -55 dBFS, so no model was run. `unavailable` means transcription could not run (see `failure_code`); the video analysis itself is unaffected. |
| `language` | string \| `null` | yes | Detected language code, e.g. `en`. |
| `duration_s` | number \| `null` (minimum=0) | yes |  |
| `rms_dbfs` | number \| `null` | yes |  |
| `loudest_second_dbfs` | number \| `null` | yes | RMS level of the loudest one-second window of the audio track, in dBFS. |
| `segments` | [`VideoAudioSegment`](#videoaudiosegment)[] | yes | Time-ordered. Empty unless status is `transcribed`. |
| `classification` | `"machine_transcribed"` | yes | Never `measured` and never evidence: this is machine speech-to-text of operator audio. |
| `method` | string | yes |  |
| `note` | string | yes | The caveat to show next to the text. |
| `failure_code` | string \| `null` | yes | Set when status is `unavailable`: a provider error code such as `model_missing`, or `decode_failed`, `no_provider`, `transcription_failed`. |
| `execution` | [`ExecutionMetadata`](#executionmetadata) \| `null` | yes | Which local provider produced the transcript; null when none ran. |

### ConditionRange

| Field | Type | Required | Description |
|---|---|---|---|
| `min` | number | yes |  |
| `max` | number | yes |  |
| `n` | integer (minimum=1) | yes |  |

### BoundingBox

Axis-aligned box in measurement_space pixels (origin top-left).

| Field | Type | Required | Description |
|---|---|---|---|
| `x_min` | number (minimum=0) | yes |  |
| `y_min` | number (minimum=0) | yes |  |
| `x_max` | number (minimum=0) | yes |  |
| `y_max` | number (minimum=0) | yes |  |

### Point

Pixel coordinate in measurement_space.

| Field | Type | Required | Description |
|---|---|---|---|
| `x` | number | yes |  |
| `y` | number | yes |  |

### GeometryPx

Image-plane geometry in pixels. Always present for completed analyses (values null when no flame).

| Field | Type | Required | Description |
|---|---|---|---|
| `area` | [`MeasuredValue`](#measuredvalue) | yes | Flame mask area, unit px2. |
| `width` | [`MeasuredValue`](#measuredvalue) | yes | Mask bounding-box width, unit px. |
| `height` | [`MeasuredValue`](#measuredvalue) | yes | Mask bounding-box height, unit px. |
| `perimeter` | [`MeasuredValue`](#measuredvalue) | yes | Outer contour length, unit px. |
| `centroid` | [`PointMeasurement`](#pointmeasurement) | yes |  |
| `aspect_ratio` | [`MeasuredValue`](#measuredvalue) | yes | height / width, unit ratio. |
| `circularity` | [`MeasuredValue`](#measuredvalue) | yes | 4π·area / perimeter², unit ratio (1 = circle). |

### GeometryPhysical

Projected physical size from the caller-supplied spatial scale. A 2-D projection: not a 3-D flame dimension.

| Field | Type | Required | Description |
|---|---|---|---|
| `area` | [`MeasuredValue`](#measuredvalue) | yes | unit mm2, classification estimated. |
| `width` | [`MeasuredValue`](#measuredvalue) | yes | unit mm, classification estimated. |
| `height` | [`MeasuredValue`](#measuredvalue) | yes | unit mm, classification estimated. |
| `perimeter` | [`MeasuredValue`](#measuredvalue) | yes | unit mm, classification estimated. |

### Appearance

| Field | Type | Required | Description |
|---|---|---|---|
| `color_space` | `"RGB"` | yes | Colour space of the statistics. |
| `mean_r` | [`MeasuredValue`](#measuredvalue) | yes | Mean red channel inside the mask, unit intensity_8bit. |
| `mean_g` | [`MeasuredValue`](#measuredvalue) | yes |  |
| `mean_b` | [`MeasuredValue`](#measuredvalue) | yes |  |
| `mean_intensity` | [`MeasuredValue`](#measuredvalue) | yes | Mean luma inside the mask, unit intensity_8bit. |
| `saturated_fraction` | [`MeasuredValue`](#measuredvalue) | yes | Fraction of mask pixels at sensor maximum in any channel, unit fraction. |
| `physical_interpretation` | `"none"` | yes | Constant. Image-derived colour/intensity statistics are not physical state variables; in particular they are NOT temperature (MVP plan §10). |

### VideoAudioSegment

| Field | Type | Required | Description |
|---|---|---|---|
| `start_s` | number (minimum=0) | yes | Seconds from the start of the audio track. Approximate to a few seconds: voice-activity detection merges speech into long chunks. |
| `end_s` | number (minimum=0) | yes |  |
| `text` | string | yes | Machine speech-to-text. Untrusted text; words can be wrong. |
| `avg_logprob` | number \| `null` | yes | Whisper's average token log-probability for the chunk the segment belongs to; closer to 0 is more confident. |
| `no_speech_prob` | number \| `null` (minimum=0, maximum=1) | yes | Whisper's probability that the chunk is not speech; high values suggest noise. |

### MeasuredValue

| Field | Type | Required | Description |
|---|---|---|---|
| `value` | number \| `null` | yes | Null when not computable for this image (e.g. no flame detected). |
| `unit` | `"px"` \| `"px2"` \| `"mm"` \| `"mm2"` \| `"ratio"` \| `"intensity_8bit"` \| `"fraction"` | yes | Unit of `value`. |
| `classification` | [`MeasurementClass`](#measurementclass) | yes |  |
| `method` | string | yes | Short method identifier, e.g. `mask_pixel_count`, `contour_perimeter_opencv`. |
| `uncertainty` | number \| `null` (minimum=0) | yes | Absolute uncertainty in `unit`, when the method provides one. Never invented. |

### PointMeasurement

| Field | Type | Required | Description |
|---|---|---|---|
| `x` | number \| `null` | yes |  |
| `y` | number \| `null` | yes |  |
| `unit` | `"px"` | yes | Pixel coordinates in measurement_space. |
| `classification` | [`MeasurementClass`](#measurementclass) | yes |  |
| `method` | string | yes |  |

### Request-only schemas

Used in request bodies, never returned.

### AnalysisCreateForm

multipart/form-data body for POST /api/analyses.

| Field | Type | Required | Description |
|---|---|---|---|
| `image` | string (application/octet-stream) | no | PNG or JPEG, ≤ 10 MiB, ≥ 64×64 px, ≤ 50 megapixels. Type is detected from the bytes. Send exactly one of image or video. |
| `experiment_id` | string (ULID) | no | Link the image to an existing experiment. Unknown ID → 422 UNKNOWN_EXPERIMENT. |
| `source_file_id` | string | no | File identifier as recorded in datasets/metadata/files.jsonl (`sha256:` + first 16 hex chars). |
| `frame_index` | integer (minimum=0) | no |  |
| `scale_px_per_mm` | number (exclusiveMinimum=0) | no | Optional spatial calibration. Requires scale_source. |
| `scale_source` | string (minLength=1, maxLength=500) | no | How the scale was obtained (e.g. ruler in frame, documented camera geometry). |
| `request_interpretation` | boolean (default=false) | no | Ask for an AURA interpretation after measurements complete. Ignored (status unavailable + warning) when AURA is disabled. |
| `notes` | string (maxLength=2000) | no |  |
| `video` | string (application/octet-stream) | no | MP4/MOV/AVI (detected from the bytes), H.264/H.265, ≤ 200 MiB (FLAME_MAX_VIDEO_UPLOAD_BYTES), ≤ 600 s. Creates a flame_video analysis (0.3.0). Calibration fields are rejected for video. |
| `sample_every_n_frames` | integer (minimum=1, maximum=10000, default=30) | no | Video only: analyse every N-th frame. |
| `max_frames` | integer (minimum=1, default=300) | no | Video only: cap on sampled frames (≤ FLAME_MAX_VIDEO_FRAMES, default 600). |
| `camera_profile` | string (minLength=1, maxLength=64) | no | Optional fixed-camera profile from `cv/configs/camera_profiles.json` (e.g. `flex-colour`). Its exclusion zones (static bright hardware in that camera's view) are removed before detection; the zones used are reported in the CV result's preprocessing. An unknown name is a 400 VALIDATION_ERROR. |

### ModeChangeRequest

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | [`ExecutionMode`](#executionmode) | yes |  |

### ChatRequest

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string (minLength=1, maxLength=500) | yes |  |
| `conversation_id` | string \| `null` (maxLength=128) | no | Accepted, not yet used server-side (M5). |

### FileReprocessRequest

| Field | Type | Required | Description |
|---|---|---|---|
| `note` | string (maxLength=2000) | no | Free-text reason, kept in the audit event's `after.note`. |

### EvidenceReviewRequest

| Field | Type | Required | Description |
|---|---|---|---|
| `review_status` | [`AdminReviewStatus`](#adminreviewstatus) | yes |  |
| `note` | string (maxLength=2000) | no | Free-text reason, kept in the audit event's `after.note`. |

## 3. Enums

| Enum | Values | Meaning |
|---|---|---|
| <a id="overallstatus"></a>`OverallStatus` | `healthy`, `degraded`, `unhealthy` | healthy: every service up. degraded: a required service degraded or an optional one down/degraded. unhealthy: a required service down. |
| <a id="chatwarning"></a>`ChatWarning` | `no_matching_evidence`, `citations_not_in_retrieved_evidence_removed`, `answer_cites_no_evidence`, `generation_unavailable`, `model_fallback_used`, `answer_values_not_in_cited_evidence`, `answer_withheld_unsupported_values`, `answer_terms_not_in_cited_evidence`, `low_evidence_score` |  |
| <a id="executionmode"></a>`ExecutionMode` | `cloud_preferred`, `local_first`, `offline_only` | Hybrid AI execution mode (Sub-phase 2H). offline_only never contacts an external provider. |
| <a id="aimodesource"></a>`AiModeSource` | `env`, `audit_override` | Where the effective `mode` comes from: `env` is FLAME_AI_EXECUTION_MODE; `audit_override` is the newest `ai.mode.changed` audit event (PUT /api/admin/ai/mode), which wins over env in every process until the next PUT. There is no clear operation yet. |
| <a id="reviewstatus"></a>`ReviewStatus` | `raw`, `machine_extracted`, `human_verified`, `rejected` | Review state (data dictionary: review_status). The UI must visibly distinguish human_verified and must not render rejected evidence as support. |
| <a id="adminreviewstatus"></a>`AdminReviewStatus` | `machine_extracted`, `human_verified`, `rejected` | The ReviewStatus values an administrator may set (`raw` is never a review outcome). |
| <a id="errorcode"></a>`ErrorCode` | `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `ROUTE_NOT_FOUND`, `DOCUMENT_NOT_FOUND`, `EXPERIMENT_NOT_FOUND`, `EVIDENCE_NOT_FOUND`, `ANALYSIS_NOT_FOUND`, `ENTITY_NOT_FOUND`, `ANALYSIS_NOT_CANCELLABLE`, `ARTIFACT_NOT_FOUND`, `ARTIFACT_NOT_READY`, `PAYLOAD_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE`, `IMAGE_INVALID`, `UNKNOWN_EXPERIMENT`, `RATE_LIMITED`, `DATABASE_UNAVAILABLE`, `STORAGE_UNAVAILABLE`, `SEARCH_UNAVAILABLE`, `MODEL_UNAVAILABLE`, `QUEUE_UNAVAILABLE`, `AURA_UNAVAILABLE`, `INTERNAL_ERROR`, `AUTHENTICATION_REQUIRED`, `CHAT_UNAVAILABLE`, `METHOD_NOT_ALLOWED`, `VIDEO_INVALID`, `FILE_NOT_FOUND`, `FILE_NOT_QUARANTINED`, `INVESTIGATION_NOT_FOUND` | Stable machine-readable error code. The frontend switches on this, never on `message`. AURA_UNAVAILABLE is deprecated since 0.2.0: chat now degrades to an evidence-only answer instead. |
| <a id="searchresulttype"></a>`SearchResultType` | `document`, `experiment` | document: a matched passage inside a parsed document (carries a page/section locator). experiment: a matched experiment/test record. |
| <a id="documenttype"></a>`DocumentType` | `technical_report`, `publication`, `test_plan`, `requirements`, `final_report`, `thesis`, `dataset_documentation`, `other` | Document classification assigned at ingestion. |
| <a id="searchdomain"></a>`SearchDomain` | `combustion`, `all` | combustion (default) excludes non-combustion sources such as FF-PSI-DSI (DAY2_TASKS domain filter rule). all disables that filter. |
| <a id="retrievalmode"></a>`RetrievalMode` | `lexical`, `hybrid` | lexical: Postgres full-text only (available first). hybrid: lexical + pgvector dense ranks fused. Scores are only comparable within one mode. |
| <a id="textlayer"></a>`TextLayer` | `full`, `partial`, `none`, `unknown` | Whether the original PDF has an extractable text layer. partial: some pages need OCR (see pages_without_text). |
| <a id="gravityregime"></a>`GravityRegime` | `microgravity`, `partial_gravity`, `normal_gravity`, `unknown` | Gravity regime as reported by the source; `unknown` when the source does not state it. |
| <a id="evidencekind"></a>`EvidenceKind` | `document_passage`, `experiment_condition`, `dataset_file`, `image_measurement`, `video_measurement` | What the evidence points at. |
| <a id="evidenceorigin"></a>`EvidenceOrigin` | `source_evidence`, `calculated_measurement` | source_evidence: content that exists in an upstream NASA/NIST artefact. calculated_measurement: a deterministic, reproducible computation by a versioned Flame pipeline. Model-generated interpretation and inference are NEVER evidence. |
| <a id="extractionmethod"></a>`ExtractionMethod` | `verbatim_text`, `ocr`, `table_parse`, `cv_pipeline`, `manual` | How the evidence content was obtained. |
| <a id="analysistype"></a>`AnalysisType` | `flame_image`, `flame_video` | flame_image: one PNG/JPEG image. flame_video (0.3.0, ADR-005): an MP4/MOV/AVI video analysed on sampled frames with a temporal summary. |
| <a id="analysisstatus"></a>`AnalysisStatus` | `queued`, `processing`, `completed`, `failed`, `cancelled` | Terminal states: completed, failed, cancelled. `cancelled` is set by the server: by `POST /api/analyses/{analysis_id}/cancel` (contract 0.6.0), or by job recovery when a stuck job had a cancel request. |
| <a id="detectionstatus"></a>`DetectionStatus` | `present`, `absent`, `uncertain` | Whether a flame was detected. |
| <a id="calibrationstate"></a>`CalibrationState` | `absent`, `spatial_scale_provided` | absent: measurements are pixels only. spatial_scale_provided: caller supplied px-per-mm, enabling ESTIMATED physical lengths/areas. No radiometric calibration state exists in v0.1, so temperature is never produced. |
| <a id="filestatus"></a>`FileStatus` | `active`, `quarantined` | file_record.status (M9). A quarantined file is kept for review but never parsed or indexed. |
| <a id="insightkind"></a>`InsightKind` | `measured_statistic`, `model_estimate`, `coverage_gap` | measured_statistic: computed from flight-test rows. model_estimate: from the FLEX outcome model (claim class estimated). coverage_gap: what the data does not cover. |
| <a id="graphentitytype"></a>`GraphEntityType` | `investigation`, `experiment`, `fuel`, `condition_variable`, `phenomenon`, `document`, `platform`, `instrument` | E2-6 entity types. `fuel` covers fuels and solid materials, as written in the source tables. `platform` and `instrument` come only from NLP extraction (`extraction_method` `nlp_extraction`, always unreviewed until a person reviews them). |
| <a id="graphreviewstatus"></a>`GraphReviewStatus` | `unreviewed`, `human_verified`, `rejected` |  |
| <a id="graphpredicate"></a>`GraphPredicate` | `part_of`, `uses_fuel`, `has_condition`, `observed`, `describes`, `ran_on`, `measured_with` |  |
| <a id="servicestatus"></a>`ServiceStatus` | `up`, `degraded`, `down`, `disabled`, `unknown` | disabled: intentionally not configured in this deployment (e.g. AURA in the MVP). unknown: the probe has not run or timed out. |
| <a id="repository"></a>`Repository` | `NASA PSI`, `NASA NTRS`, `NASA Science`, `NASA Open Data`, `NASA GRC FCF`, `Other` | Canonical repository family. Identical to `repository` in datasets/registry/source_registry.schema.json. |
| <a id="locatortype"></a>`LocatorType` | `page`, `section`, `table_row`, `frame`, `file` | What kind of position `Locator` points at (data dictionary: location_type). |
| <a id="conditionorigin"></a>`ConditionOrigin` | `reported`, `derived` | reported: value as written in the source. derived: computed by us (e.g. unit conversion); `value_si` is always derived. |
| <a id="interpretationstatus"></a>`InterpretationStatus` | `not_requested`, `pending`, `completed`, `unavailable`, `failed` | unavailable: AURA disabled or unreachable; the analysis itself still completes. |
| <a id="artifactkind"></a>`ArtifactKind` | `original`, `preprocessed`, `mask`, `overlay` | original: the uploaded bytes, immutable. preprocessed: oriented/colour-converted input to the model. mask: binary flame mask (PNG, original resolution). overlay: original with mask contour drawn (PNG). |
| <a id="warningcode"></a>`WarningCode` | `SCALE_CALIBRATION_ABSENT`, `RADIOMETRIC_CALIBRATION_ABSENT`, `TEMPERATURE_NOT_AVAILABLE`, `EXIF_ORIENTATION_APPLIED`, `COLOR_CONVERTED_TO_RGB`, `LOW_DETECTION_CONFIDENCE`, `MULTIPLE_FLAMES`, `SATURATION_CLIPPING`, `BLUR_DETECTED`, `LOW_LIGHT`, `OCCLUSION`, `QUALITY_CHECK_NOT_IMPLEMENTED`, `INTERPRETATION_UNAVAILABLE`, `INTERPRETATION_STATEMENTS_REJECTED`, `JOB_RECOVERED`, `JOB_RESUMED_FROM_CHECKPOINT` | Stable warning code. |
| <a id="analysisfailurecode"></a>`AnalysisFailureCode` | `IMAGE_DECODE_FAILED`, `MODEL_UNAVAILABLE`, `PIPELINE_ERROR`, `TIMEOUT`, `CANCELLED`, `VIDEO_DECODE_FAILED` | Why a job ended in failed/cancelled. A no-flame image is NOT a failure: it completes with detection.status = absent. |
| <a id="claimclass"></a>`ClaimClass` | `observed`, `measured`, `estimated`, `inferred`, `hypothesized`, `unsupported` | Scientific interpretation label (MVP plan §10). cv_pipeline statements are observed/measured/estimated only; aura_interpretation statements are inferred/hypothesized/unsupported only. |
| <a id="statementorigin"></a>`StatementOrigin` | `cv_pipeline`, `aura_interpretation`, `model_interpretation` | cv_pipeline: deterministic template text generated from measurements. aura_interpretation: model-generated text, validated by Flame before storage. model_interpretation: the same, written by a non-AURA model chosen by Flame's router. |
| <a id="measurementclass"></a>`MeasurementClass` | `measured`, `estimated` | measured: computed from validated pixels with a stated method and pixel units. estimated: depends on an assumption/calibration (e.g. caller-supplied scale) and carries uncertainty. |
