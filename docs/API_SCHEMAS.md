# Flame in Freefall: API Response Schemas

**Generated from [`openapi.json`](openapi.json)** (OpenAPI 3.1.0, API 0.1.0) by `docs/tools/render_api_schemas.py`. Do not edit by hand.
Endpoint behaviour, examples and display rules: [`FRONTEND_API_CONTRACT.md`](FRONTEND_API_CONTRACT.md).

Reading the tables: *Required = yes* means the key is always present. A nullable field (`| null`) is still present, with value `null`, which means "not present or not established" and is never a stand-in for `0`. The only optional keys in responses are those of [`ErrorDetails`](#errordetails).

## 1. Responses by endpoint

| Method | Path | Success | Error statuses (body: [`ErrorResponse`](#errorresponse) unless noted) |
|---|---|---|---|
| GET | `/api/health` | 200 [`HealthResponse`](#healthresponse) | 429, 500, 503 [`HealthResponse`](#healthresponse) |
| GET | `/api/dashboard/counts` | 200 [`DashboardCountsResponse`](#dashboardcountsresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/search` | 200 [`SearchResponse`](#searchresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/documents/{document_id}` | 200 [`DocumentResponse`](#documentresponse) | 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/experiments/{experiment_id}` | 200 [`ExperimentResponse`](#experimentresponse) | 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/evidence/{evidence_id}` | 200 [`EvidenceResponse`](#evidenceresponse) | 400, 401, 403, 404, 429, 500, 503 |
| POST | `/api/analyses` | 202 [`AnalysisResponse`](#analysisresponse) | 400, 401, 403, 413, 415, 422, 429, 500, 503 |
| GET | `/api/analyses` | 200 [`AnalysisListResponse`](#analysislistresponse) | 400, 401, 403, 429, 500, 503 |
| GET | `/api/analyses/{analysis_id}` | 200 [`AnalysisResponse`](#analysisresponse) | 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/analyses/{analysis_id}/artifacts/{artifact_kind}` | 200 `image/png` bytes or `image/jpeg` bytes | 400, 401, 403, 404, 409, 429, 500, 503 |

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
| `input` | [`AnalysisInput`](#analysisinput) | yes |  |
| `pipeline` | [`PipelineInfo`](#pipelineinfo) \| `null` | yes | Null while queued. |
| `result` | [`FlameAnalysisResult`](#flameanalysisresult) \| `null` | yes | Non-null iff status = completed. |
| `interpretation` | [`Interpretation`](#interpretation) | yes |  |
| `artifacts` | [`Artifact`](#artifact)[] | yes | `original` is present from creation; the others appear when status = completed. |
| `warnings` | [`Warning`](#warning)[] | yes |  |
| `failure` | [`AnalysisFailure`](#analysisfailure) \| `null` | yes | Non-null iff status is failed or cancelled. |
| `poll_after_ms` | integer \| `null` (minimum=0) | yes | Suggested delay before the next GET while non-terminal; null when terminal. |

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
| `image_sha256` | string | yes | Lowercase hex SHA-256 of the exact bytes. |
| `original_filename` | string | yes |  |
| `media_type` | `"image/png"` \| `"image/jpeg"` | yes | Media type detected from content (not from the filename or client header). |
| `size_bytes` | integer (minimum=1) | yes |  |
| `width` | integer (minimum=1) | yes | After EXIF orientation. |
| `height` | integer (minimum=1) | yes | After EXIF orientation. |
| `experiment_id` | string (ULID) \| `null` | yes |  |
| `source_file_id` | string \| `null` | yes | files.jsonl file_id the image was taken from, when it comes from the corpus. |
| `frame_index` | integer \| `null` (minimum=0) | yes |  |
| `calibration` | [`Calibration`](#calibration) | yes |  |
| `notes` | string \| `null` | yes |  |

### PipelineInfo

| Field | Type | Required | Description |
|---|---|---|---|
| `pipeline_version` | string | yes | Version of the whole CV pipeline, e.g. `cv-0.1.0`. |
| `preprocessing_version` | string | yes |  |
| `detector` | [`ModelInfo`](#modelinfo) \| `null` | yes |  |
| `segmenter` | [`ModelInfo`](#modelinfo) \| `null` | yes |  |
| `measurement_space` | `"original_oriented_px"` | yes | All pixel coordinates and measurements are in the original image's pixel grid after EXIF orientation, regardless of any internal resize. |

### FlameAnalysisResult

| Field | Type | Required | Description |
|---|---|---|---|
| `detection` | [`Detection`](#detection) | yes |  |
| `segmentation` | [`Segmentation`](#segmentation) \| `null` | yes | Null when detection.status = absent. |
| `measurements` | [`Measurements`](#measurements) | yes |  |
| `quality_flags` | [`QualityFlags`](#qualityflags) | yes |  |
| `observations` | [`Statement`](#statement)[] | yes | Deterministic statements derived from the measurements. |

### Interpretation

Optional AI interpretation. Never alters measurements; displayed separately from them.

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | [`InterpretationStatus`](#interpretationstatus) | yes |  |
| `provider` | `"aura"` \| `null` | yes | Which reasoning layer produced the statements. |
| `model` | string \| `null` | yes | Model identifier reported by the provider. |
| `statements` | [`Statement`](#statement)[] | yes |  |
| `rejected_statement_count` | integer (minimum=0) | yes | Statements dropped by Flame validation (unknown evidence IDs, disallowed claim class, temperature claims). |
| `generated_at` | string (date-time) \| `null` | yes |  |

### Artifact

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | [`ArtifactKind`](#artifactkind) | yes |  |
| `url` | string (uri-reference) | yes | API-relative URL to fetch the bytes: /api/analyses/{analysis_id}/artifacts/{kind}. Never a raw object-storage URL. |
| `media_type` | `"image/png"` \| `"image/jpeg"` | yes | Media type served. |
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

### Calibration

| Field | Type | Required | Description |
|---|---|---|---|
| `state` | [`CalibrationState`](#calibrationstate) | yes |  |
| `scale_px_per_mm` | number \| `null` (exclusiveMinimum=0) | yes |  |
| `scale_source` | string \| `null` | yes | How the scale was established, as supplied by the caller. |

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
| `image` | string (application/octet-stream) | yes | PNG or JPEG, ≤ 10 MiB, ≥ 64×64 px, ≤ 50 megapixels. Type is detected from the bytes. |
| `experiment_id` | string (ULID) | no | Link the image to an existing experiment. Unknown ID → 422 UNKNOWN_EXPERIMENT. |
| `source_file_id` | string | no | File identifier as recorded in datasets/metadata/files.jsonl (`sha256:` + first 16 hex chars). |
| `frame_index` | integer (minimum=0) | no |  |
| `scale_px_per_mm` | number (exclusiveMinimum=0) | no | Optional spatial calibration. Requires scale_source. |
| `scale_source` | string (minLength=1, maxLength=500) | no | How the scale was obtained (e.g. ruler in frame, documented camera geometry). |
| `request_interpretation` | boolean (default=false) | no | Ask for an AURA interpretation after measurements complete. Ignored (status unavailable + warning) when AURA is disabled. |
| `notes` | string (maxLength=2000) | no |  |

## 3. Enums

| Enum | Values | Meaning |
|---|---|---|
| <a id="overallstatus"></a>`OverallStatus` | `healthy`, `degraded`, `unhealthy` | healthy: every service up. degraded: a required service degraded or an optional one down/degraded. unhealthy: a required service down. |
| <a id="errorcode"></a>`ErrorCode` | `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `ROUTE_NOT_FOUND`, `DOCUMENT_NOT_FOUND`, `EXPERIMENT_NOT_FOUND`, `EVIDENCE_NOT_FOUND`, `ANALYSIS_NOT_FOUND`, `ARTIFACT_NOT_FOUND`, `ARTIFACT_NOT_READY`, `PAYLOAD_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE`, `IMAGE_INVALID`, `UNKNOWN_EXPERIMENT`, `RATE_LIMITED`, `DATABASE_UNAVAILABLE`, `STORAGE_UNAVAILABLE`, `SEARCH_UNAVAILABLE`, `MODEL_UNAVAILABLE`, `QUEUE_UNAVAILABLE`, `AURA_UNAVAILABLE`, `INTERNAL_ERROR` | Stable machine-readable error code. The frontend switches on this, never on `message`. |
| <a id="searchresulttype"></a>`SearchResultType` | `document`, `experiment` | document: a matched passage inside a parsed document (carries a page/section locator). experiment: a matched experiment/test record. |
| <a id="documenttype"></a>`DocumentType` | `technical_report`, `publication`, `test_plan`, `requirements`, `final_report`, `thesis`, `dataset_documentation`, `other` | Document classification assigned at ingestion. |
| <a id="searchdomain"></a>`SearchDomain` | `combustion`, `all` | combustion (default) excludes non-combustion sources such as FF-PSI-DSI (DAY2_TASKS domain filter rule). all disables that filter. |
| <a id="retrievalmode"></a>`RetrievalMode` | `lexical`, `hybrid` | lexical: Postgres full-text only (available first). hybrid: lexical + pgvector dense ranks fused. Scores are only comparable within one mode. |
| <a id="textlayer"></a>`TextLayer` | `full`, `partial`, `none`, `unknown` | Whether the original PDF has an extractable text layer. partial: some pages need OCR (see pages_without_text). |
| <a id="gravityregime"></a>`GravityRegime` | `microgravity`, `partial_gravity`, `normal_gravity`, `unknown` | Gravity regime as reported by the source; `unknown` when the source does not state it. |
| <a id="evidencekind"></a>`EvidenceKind` | `document_passage`, `experiment_condition`, `dataset_file`, `image_measurement` | What the evidence points at. |
| <a id="evidenceorigin"></a>`EvidenceOrigin` | `source_evidence`, `calculated_measurement` | source_evidence: content that exists in an upstream NASA/NIST artefact. calculated_measurement: a deterministic, reproducible computation by a versioned Flame pipeline. Model-generated interpretation and inference are NEVER evidence. |
| <a id="extractionmethod"></a>`ExtractionMethod` | `verbatim_text`, `ocr`, `table_parse`, `cv_pipeline`, `manual` | How the evidence content was obtained. |
| <a id="reviewstatus"></a>`ReviewStatus` | `raw`, `machine_extracted`, `human_verified`, `rejected` | Review state (data dictionary: review_status). The UI must visibly distinguish human_verified and must not render rejected evidence as support. |
| <a id="analysistype"></a>`AnalysisType` | `flame_image` | Only single-image flame analysis exists in v0.1. Video/temporal analysis is Weeks 3–6. |
| <a id="analysisstatus"></a>`AnalysisStatus` | `queued`, `processing`, `completed`, `failed`, `cancelled` | Terminal states: completed, failed, cancelled. `cancelled` is set only by the server (shutdown/operator); there is no client cancel endpoint in v0.1. |
| <a id="detectionstatus"></a>`DetectionStatus` | `present`, `absent`, `uncertain` | Whether a flame was detected. |
| <a id="calibrationstate"></a>`CalibrationState` | `absent`, `spatial_scale_provided` | absent: measurements are pixels only. spatial_scale_provided: caller supplied px-per-mm, enabling ESTIMATED physical lengths/areas. No radiometric calibration state exists in v0.1, so temperature is never produced. |
| <a id="servicestatus"></a>`ServiceStatus` | `up`, `degraded`, `down`, `disabled`, `unknown` | disabled: intentionally not configured in this deployment (e.g. AURA in the MVP). unknown: the probe has not run or timed out. |
| <a id="repository"></a>`Repository` | `NASA PSI`, `NASA NTRS`, `NASA Science`, `NASA Open Data`, `NASA GRC FCF`, `Other` | Canonical repository family. Identical to `repository` in datasets/registry/source_registry.schema.json. |
| <a id="locatortype"></a>`LocatorType` | `page`, `section`, `table_row`, `frame`, `file` | What kind of position `Locator` points at (data dictionary: location_type). |
| <a id="conditionorigin"></a>`ConditionOrigin` | `reported`, `derived` | reported: value as written in the source. derived: computed by us (e.g. unit conversion); `value_si` is always derived. |
| <a id="interpretationstatus"></a>`InterpretationStatus` | `not_requested`, `pending`, `completed`, `unavailable`, `failed` | unavailable: AURA disabled or unreachable; the analysis itself still completes. |
| <a id="artifactkind"></a>`ArtifactKind` | `original`, `preprocessed`, `mask`, `overlay` | original: the uploaded bytes, immutable. preprocessed: oriented/colour-converted input to the model. mask: binary flame mask (PNG, original resolution). overlay: original with mask contour drawn (PNG). |
| <a id="warningcode"></a>`WarningCode` | `SCALE_CALIBRATION_ABSENT`, `RADIOMETRIC_CALIBRATION_ABSENT`, `TEMPERATURE_NOT_AVAILABLE`, `EXIF_ORIENTATION_APPLIED`, `COLOR_CONVERTED_TO_RGB`, `LOW_DETECTION_CONFIDENCE`, `MULTIPLE_FLAMES`, `SATURATION_CLIPPING`, `BLUR_DETECTED`, `LOW_LIGHT`, `OCCLUSION`, `QUALITY_CHECK_NOT_IMPLEMENTED`, `INTERPRETATION_UNAVAILABLE`, `INTERPRETATION_STATEMENTS_REJECTED` | Stable warning code. |
| <a id="analysisfailurecode"></a>`AnalysisFailureCode` | `IMAGE_DECODE_FAILED`, `MODEL_UNAVAILABLE`, `PIPELINE_ERROR`, `TIMEOUT`, `CANCELLED` | Why a job ended in failed/cancelled. A no-flame image is NOT a failure: it completes with detection.status = absent. |
| <a id="claimclass"></a>`ClaimClass` | `observed`, `measured`, `estimated`, `inferred`, `hypothesized`, `unsupported` | Scientific interpretation label (MVP plan §10). cv_pipeline statements are observed/measured/estimated only; aura_interpretation statements are inferred/hypothesized/unsupported only. |
| <a id="statementorigin"></a>`StatementOrigin` | `cv_pipeline`, `aura_interpretation` | cv_pipeline: deterministic template text generated from measurements. aura_interpretation: model-generated text, validated by Flame before storage. |
| <a id="measurementclass"></a>`MeasurementClass` | `measured`, `estimated` | measured: computed from validated pixels with a stated method and pixel units. estimated: depends on an assumption/calibration (e.g. caller-supplied scale) and carries uncertainty. |
