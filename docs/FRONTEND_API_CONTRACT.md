# Flame in Freefall: Frontend API Contract (v0.1.0)

**Audience:** Engineer 4 (frontend) and the Lead (backend). **Status:** contract agreed, **not implemented**.
**Machine-readable source of truth:** [`docs/openapi.json`](openapi.json) (OpenAPI 3.1.0). If this page and the JSON disagree, the JSON wins. Fix the page.
**Every response schema, field by field:** [`docs/API_SCHEMAS.md`](API_SCHEMAS.md) (generated from `openapi.json`).
**Background and evidence:** [`docs/AURA_INTEGRATION_STATUS.md`](AURA_INTEGRATION_STATUS.md).

> **Implementation status.** `apps/api` does not exist yet. No endpoint below is served today. Every
> operation in `openapi.json` carries `x-implementation-status: not_implemented`. Build against the spec
> with a mock server (see §3), and switch to the real API endpoint by endpoint as the Lead ships them.

---

## 1. Endpoint catalogue

| Method | Endpoint | Purpose | Auth | Request | Response | Status codes |
|---|---|---|---|---|---|---|
| GET | `/api/health` | System health and dependency status | none | – | `HealthResponse` | 200, 429, 500, 503 (body is still `HealthResponse`) |
| GET | `/api/dashboard/counts` | Document / experiment / analysis counts | optional bearer | – | `DashboardCountsResponse` | 200, 400, 401, 403, 429, 500, 503 |
| GET | `/api/search` | Search documents and experiments | optional bearer | query: `q`, `type`, `source_id[]`, `experiment_id`, `domain`, `page`, `page_size` | `SearchResponse` | 200, 400, 401, 403, 429, 500, 503 |
| GET | `/api/documents/{document_id}` | Document details and provenance | optional bearer | path: `document_id` | `DocumentResponse` | 200, 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/experiments/{experiment_id}` | Experiment and its conditions (target of experiment search hits) | optional bearer | path: `experiment_id` | `ExperimentResponse` | 200, 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/evidence/{evidence_id}` | Evidence and provenance for one evidence record | optional bearer | path: `evidence_id` | `EvidenceResponse` | 200, 400, 401, 403, 404, 429, 500, 503 |
| POST | `/api/analyses` | Upload an image and start a flame analysis (async) | optional bearer | `multipart/form-data` (`AnalysisCreateForm`) | `AnalysisResponse` (`queued`) | **202**, 400, 401, 403, 413, 415, 422, 429, 500, 503 |
| GET | `/api/analyses` | Analysis history | optional bearer | query: `status[]`, `experiment_id`, `pipeline_version`, `created_from`, `created_to`, `sort`, `page`, `page_size` | `AnalysisListResponse` | 200, 400, 401, 403, 429, 500, 503 |
| GET | `/api/analyses/{analysis_id}` | Analysis status, result, measurements, evidence (polling target) | optional bearer | path: `analysis_id` | `AnalysisResponse` | 200, 400, 401, 403, 404, 429, 500, 503 |
| GET | `/api/analyses/{analysis_id}/artifacts/{artifact_kind}` | Original / preprocessed / mask / overlay image | optional bearer | path: `analysis_id`, `artifact_kind` | `image/png` or `image/jpeg` bytes | 200, 400, 401, 403, 404, **409**, 429, 500, 503 |

That is ten operations on nine paths. Nothing else is in v0.1. Planned endpoints that are **not** in this contract are listed in §6.

### Differences from the MVP plan (§12)

| MVP plan | This contract | Why |
|---|---|---|
| `POST /api/search` | `GET /api/search` | Every filter fits in query parameters. GET makes results linkable and HTTP-cacheable. Nothing was implemented, so the change costs nothing. |
| `POST /api/analysis/image` | `POST /api/analyses` | One REST collection serves upload, history and detail. |
| `GET /api/analysis/{id}` | `GET /api/analyses/{analysis_id}` | Same reason. |
| (none) | `GET /api/dashboard/counts` | The dashboard's three metric cards need one consistent read (DAY2_TASKS §6). |
| (none) | `GET /api/evidence/{evidence_id}` | The Evidence Viewer (MVP plan §13) needs the claim → evidence → source hop as a resource. |
| (none) | `GET /api/analyses/{id}/artifacts/{kind}` | Overlay/mask delivery without exposing object-storage layout. |

---

## 2. Conventions (apply to every endpoint)

| Topic | Rule |
|---|---|
| Base path | `/api`. Call it same-origin. The recommended setup has Next.js rewrite `/api/*` to the API service, so there is no CORS in the browser. |
| JSON style | `snake_case` keys. Timestamps are RFC 3339 UTC (`2026-10-05T09:30:00Z`). Resource IDs are ULIDs (26 chars, Crockford base32). |
| Nullability | Every declared property is **always present**. `null` means "not present or not established" (data dictionary null policy). A missing number is never `0`. Optional appears only in request inputs. |
| Success envelope | Every JSON success body has `meta: { request_id, generated_at, api_version }`. Single resources are wrapped under a named key (`document`, `evidence`, `analysis`, `experiment`). Lists use `items`/`results` + `pagination`. |
| Request ID | Send `X-Request-ID` (≤128 chars, `[A-Za-z0-9._-]`) on every call and log it. The server echoes it in the `X-Request-ID` response header, in `meta.request_id`, and in `error.request_id`. If you don't send one, the server generates it. |
| Auth | Bearer JWT, **optional in v0.1** (development `AuthContext` adapter, MVP plan §12). Send `Authorization: Bearer <token>` when you have one. A later minor version makes it required without changing any route. `/api/health` is always public. |
| Pagination | Offset pages: `page` (1-based, default 1) and `page_size` (default 20; max 50 for search, 100 for history). Response: `pagination: { page, page_size, total_items, total_pages }`. |
| Enums | Closed sets, listed in the spec. Treat an unknown value as a bug and render it raw. Don't crash. |
| Versioning | `info.version` / `meta.api_version` is semver. Adding a field or enum value is a minor bump. Removing or renaming is a major bump plus a new path prefix. |

### 2.1 Error contract

Every non-2xx JSON response has exactly this shape (`ErrorResponse`):

```json
{
  "error": {
    "code": "ANALYSIS_NOT_FOUND",
    "message": "Analysis was not found.",
    "request_id": "req_01J9Z3K8V5Q2N7X4M6R1T0W8YB",
    "retryable": false,
    "field_errors": [],
    "details": { "resource_id": "01J9Z3Q9D3F5H7K9N1R3T5W7Y9" }
  }
}
```

- Switch on `code`, never on `message`.
- `details` is typed and every key in it is optional: `resource_id`, `limit_bytes`, `allowed_media_types`, `retry_after_s`.
- Error bodies never include stack traces, SQL, hostnames, DSNs or secrets.

| `code` | HTTP | When | Retryable |
|---|---|---|---|
| `VALIDATION_ERROR` | 400 / 422 | Bad query/path/form values; `field_errors[]` lists each field | no |
| `UNAUTHORIZED` | 401 | Missing/invalid token (only once auth is enforced) | no |
| `FORBIDDEN` | 403 | Authenticated, not permitted | no |
| `ROUTE_NOT_FOUND` | 404 | Unknown path | no |
| `DOCUMENT_NOT_FOUND` / `EXPERIMENT_NOT_FOUND` / `EVIDENCE_NOT_FOUND` / `ANALYSIS_NOT_FOUND` / `ARTIFACT_NOT_FOUND` | 404 | ID does not exist | no |
| `ARTIFACT_NOT_READY` | 409 | Mask/overlay requested before the analysis completed | yes (`Retry-After`) |
| `PAYLOAD_TOO_LARGE` | 413 | Upload > 10 MiB (`details.limit_bytes`) | no |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Not PNG/JPEG **by content** (`details.allowed_media_types`) | no |
| `IMAGE_INVALID` | 422 | Undecodable, < 64×64 px, or > 50 MP | no |
| `UNKNOWN_EXPERIMENT` | 422 | `experiment_id` on upload does not exist | no |
| `RATE_LIMITED` | 429 | Throttled (`Retry-After`, `details.retry_after_s`) | yes |
| `DATABASE_UNAVAILABLE` / `STORAGE_UNAVAILABLE` / `SEARCH_UNAVAILABLE` / `QUEUE_UNAVAILABLE` / `MODEL_UNAVAILABLE` | 503 | A dependency the request needs is down | yes |
| `AURA_UNAVAILABLE` | 503 | Reserved. **No v0.1 endpoint requires AURA**: AURA being down shows up as a warning on the analysis, never as an HTTP error. | yes |
| `INTERNAL_ERROR` | 500 | Unexpected | no |

An analysis that *runs* and fails is not an HTTP error. It is a `200` with `analysis.status = "failed"` and `analysis.failure.code` set to one of `IMAGE_DECODE_FAILED`, `MODEL_UNAVAILABLE`, `PIPELINE_ERROR`, `TIMEOUT` or `CANCELLED`. An image with no flame is not a failure either. It completes with `detection.status = "absent"`.

---

## 3. Building against the contract before the API exists

```bash
# Types (tested with openapi-typescript 7.13.0 + TypeScript 5.9; TypeScript 6 breaks openapi-typescript 7)
npx openapi-typescript docs/openapi.json -o apps/web/lib/api/schema.d.ts

# Mock server that serves the spec's examples and validates your requests (tested with @stoplight/prism-cli)
npx @stoplight/prism-cli mock -p 4010 docs/openapi.json
#   GET /api/health                → the "degraded" example
#   GET /api/search  (no q)        → 400, as the real API will
```

Use `openapi-fetch` (or any client) over the generated `paths` type. The examples in the spec were validated against their own schemas when the file was generated.

---

## 4. Endpoints

### 4.1 `GET /api/health`: system health

| | |
|---|---|
| **Purpose** | Drives the TopBar status dot and the `/status` page. Replaces the hard-coded "System Online" (DAY2_TASKS §6). |
| **Auth** | None (public). |
| **Headers** | `X-Request-ID` (optional). |
| **Query / path / body** | None. |
| **Response** | `HealthResponse`. **200** when `status` is `healthy` or `degraded`. **503** when `unhealthy`, with the same body. |
| **Pagination** | n/a |
| **Errors** | 429 `RATE_LIMITED`, 500 `INTERNAL_ERROR`. |

`HealthResponse`:

| Field | Type | Notes |
|---|---|---|
| `status` | `"healthy" \| "degraded" \| "unhealthy"` | `unhealthy` if any `required` service is `down`. `degraded` if a required one is degraded or an optional one is down or degraded. |
| `environment` | `"development" \| "staging" \| "production"` | |
| `version` | `{ api_version, build_id \| null, git_sha \| null }` | |
| `knowledge_version` | `string \| null` | Null until the first corpus publication. |
| `services` | object with **fixed keys** `api`, `database`, `vector_index`, `object_storage`, `cache`, `cv_model`, `llm`, `aura` | Each is a `ServiceHealth`. |
| `meta` | `ResponseMeta` | `meta.generated_at` is the health timestamp. |

`ServiceHealth`: `{ status: "up"|"degraded"|"down"|"disabled"|"unknown", required: boolean, latency_ms: number|null, checked_at: datetime|null, version: string|null, message: string|null }`.

- `required` is `true` for `api`, `database` and `object_storage`.
- `disabled` means intentionally not configured. In the MVP that is `aura`, and `llm` until the router exists. Render it neutral grey, not red.
- `unknown` means the probe did not complete. Render it grey.
- There is no separate `vector_db`: by design, vectors live in Postgres via pgvector. `vector_index` reports whether the extension and a published index exist.

**Example request:** `GET /api/health` with `X-Request-ID: web-7f3a`

**Example response (200):**

```json
{
  "status": "degraded",
  "environment": "development",
  "version": { "api_version": "0.1.0", "build_id": null, "git_sha": "695fca8" },
  "knowledge_version": null,
  "services": {
    "api":            { "status": "up",       "required": true,  "latency_ms": 0.4, "checked_at": "2026-10-05T09:30:00Z", "version": "0.1.0", "message": null },
    "database":       { "status": "up",       "required": true,  "latency_ms": 2.1, "checked_at": "2026-10-05T09:30:00Z", "version": "PostgreSQL 16", "message": null },
    "vector_index":   { "status": "down",     "required": false, "latency_ms": null, "checked_at": "2026-10-05T09:30:00Z", "version": null, "message": "No index has been published yet." },
    "object_storage": { "status": "up",       "required": true,  "latency_ms": 3.8, "checked_at": "2026-10-05T09:30:00Z", "version": null, "message": null },
    "cache":          { "status": "up",       "required": false, "latency_ms": 0.9, "checked_at": "2026-10-05T09:30:00Z", "version": null, "message": null },
    "cv_model":       { "status": "unknown",  "required": false, "latency_ms": null, "checked_at": null, "version": null, "message": "CV worker not deployed." },
    "llm":            { "status": "disabled", "required": false, "latency_ms": null, "checked_at": null, "version": null, "message": null },
    "aura":           { "status": "disabled", "required": false, "latency_ms": null, "checked_at": null, "version": null, "message": "FLAME_AURA_ENABLED is false." }
  },
  "meta": { "request_id": "web-7f3a", "generated_at": "2026-10-05T09:30:00Z", "api_version": "0.1.0" }
}
```

**Notes**

- Poll it every 30 s at most.
- If the request itself fails (network error, CORS), show **Unknown**, not Down. You learned nothing about the services.
- `message` is safe to display. It never contains hosts or credentials.

---

### 4.2 `GET /api/dashboard/counts`: dashboard counts

| | |
|---|---|
| **Purpose** | The three metric cards on the dashboard (Documents / Experiments / Analyses). |
| **Auth** | Optional bearer. |
| **Headers** | `X-Request-ID`. |
| **Query / path / body** | None. No filters in v0.1. |
| **Response** | `DashboardCountsResponse` |
| **Pagination** | n/a |
| **Errors** | 503 `DATABASE_UNAVAILABLE`, 429, 500. |

| Field | Type | Exact semantics |
|---|---|---|
| `documents` | integer ≥ 0 | Published `document` records: parsed NASA/NIST documents. **Not** raw files. `files.jsonl` has 121 file records, most of them data or media. |
| `experiments` | integer ≥ 0 | `experiment` records (one per test, e.g. BASS-II `B1`) with at least one `ExperimentCondition`. |
| `analyses` | integer ≥ 0 | Analyses in status `completed`. This matches the card's caption "Completed flame analyses". |
| `analyses_in_progress` | integer ≥ 0 | Analyses in `queued` or `processing`. |
| `knowledge_version` | `string \| null` | Corpus version the document count belongs to. |
| `meta` | `ResponseMeta` | `meta.generated_at` is "as of". |

**Example request:** `GET /api/dashboard/counts`

**Example response:**

```json
{ "documents": 3, "experiments": 129, "analyses": 0, "analyses_in_progress": 0, "knowledge_version": null,
  "meta": { "request_id": "req_01J9Z3K8V5Q2N7X4M6R1T0W8YB", "generated_at": "2026-10-05T09:30:00Z", "api_version": "0.1.0" } }
```

(The numbers are illustrative: 3 NTRS PDFs plus the 129 BASS-II tests once Engineer 2's loaders land.)

**Notes**

- One aggregated call, not three, so the cards share one timestamp and one loading/error state.
- On error the API returns **503, never zeros**. Keep showing `—`.
- The counts are exact `COUNT(*)` reads. No client caching beyond 30 s is needed.

---

### 4.3 `GET /api/search`: research search

| | |
|---|---|
| **Purpose** | Scientific Search screen: ranked document passages and experiment records with locators and evidence links. |
| **Auth** | Optional bearer. |
| **Headers** | `X-Request-ID`. |
| **Body** | None. |

**Query parameters** (only parameters the planned data can support)

| Name | Type | Required | Default | Notes |
|---|---|---|---|---|
| `q` | string, 1–500 | **yes** | – | Search text. |
| `type` | `"document" \| "experiment"` | no | both | |
| `source_id` | string[] (repeat: `?source_id=FF-PSI-25&source_id=FF-PSI-69`) | no | all | Registry IDs (`datasets/registry/source_registry.csv`). Max 20. |
| `experiment_id` | ULID | no | – | Only hits linked to that experiment. |
| `domain` | `"combustion" \| "all"` | no | `combustion` | `combustion` excludes non-combustion sources such as `FF-PSI-DSI` (DAY2_TASKS domain-filter rule). |
| `page` | integer ≥ 1 | no | 1 | |
| `page_size` | integer 1–50 | no | 20 | |

These were left out on purpose:

- `date_from` and `date_to`: no reliable publication dates are captured yet.
- `sort`: relevance is the only meaningful order.

They are additive, so they can join later.

**Response:** `SearchResponse`

| Field | Type | Notes |
|---|---|---|
| `query` | string | As received, trimmed. |
| `results` | `SearchResult[]` | Ordered by `rank`. |
| `pagination` | `Pagination` | |
| `filters` | `SearchFilters` | What the server **actually applied** after defaults. Render it as active filter chips. |
| `retrieval` | `{ mode: "lexical"\|"hybrid", knowledge_version, index_version, searched_but_empty }` | When `searched_but_empty` is true, show "searched, found nothing relevant". That is a real result, not an error. |
| `meta` | `ResponseMeta` | |

`SearchResult`:

| Field | Type | Notes |
|---|---|---|
| `result_id` | string | Unique within the response (chunk ID or experiment ID). Use it as the React key. |
| `result_type` | `"document" \| "experiment"` | |
| `rank` | integer ≥ 1 | Position across all pages. |
| `score` | number | **Ordinal relevance only.** Not a probability, not a confidence. Don't render it as a percentage. Scores are only comparable within one `retrieval.mode`. |
| `title` | string | Document title or experiment display name. |
| `snippet` | string | Plain text, verbatim from the source for document hits. |
| `highlights` | `{start,end}[]` | Half-open UTF-16 offsets into `snippet`. |
| `source` | `SourceRef` | Registry projection: `source_id`, `title`, `short_name`, `repository`, `persistent_identifier` (DOI), `license`, `access_url`. |
| `document_id` | ULID \| null | Set for document hits → `GET /api/documents/{id}`. |
| `document_type` | enum \| null | |
| `experiment_id` | ULID \| null | Set for experiment hits → `GET /api/experiments/{id}`. Also set on document hits that are linked to an experiment. |
| `experiment` | `{ test_id, gravity_regime, fuel_or_material }` \| null | Only for experiment hits. |
| `evidence_id` | ULID \| null | → `GET /api/evidence/{id}`. |
| `has_evidence` | boolean | `evidence_id !== null`. |
| `locator` | `Locator` \| null | `{ type: "page"\|"section"\|"table_row"\|"frame"\|"file", page, section, row, frame_index, label }`. Display `label`. |
| `ingested_at` | datetime | |

**Example request:** `GET /api/search?q=flame%20spread%20low%20gravity%20oxygen&page=1&page_size=20`

**Example response** (the excerpt is real text from `docs/research/20000034017.pdf`, PDF page 5):

```json
{
  "query": "flame spread low gravity oxygen",
  "results": [{
    "result_id": "01J9Z3M2A7D4F6H8K0N2Q4S6T8:v1:4",
    "result_type": "document", "rank": 1, "score": 0.42,
    "title": "Testing and Selection of Fire-Resistant Materials for Spacecraft Use",
    "snippet": "Research shows that flammability and fire-spread rates in low gravity are sensitive to forced convection (ventilation flows) and atmospheric-oxygen concentration.",
    "highlights": [{ "start": 58, "end": 69 }],
    "source": { "source_id": "FF-NTRS-20000034017", "title": "Testing and Selection of Fire-Resistant Materials for Spacecraft Use", "short_name": "NASA/TM-2000-209773", "repository": "NASA NTRS", "persistent_identifier": null, "license": null, "access_url": "https://ntrs.nasa.gov/citations/20000034017" },
    "document_id": "01J9Z3M2A7D4F6H8K0N2Q4S6T8", "document_type": "technical_report",
    "experiment_id": null, "experiment": null,
    "evidence_id": "01J9Z3N5B8C1E3G5J7M9P1R3T5", "has_evidence": true,
    "locator": { "type": "page", "page": 5, "section": "ABSTRACT", "row": null, "frame_index": null, "label": "p. 5" },
    "ingested_at": "2026-10-05T08:00:00Z"
  }],
  "pagination": { "page": 1, "page_size": 20, "total_items": 1, "total_pages": 1 },
  "filters": { "type": null, "source_id": [], "experiment_id": null, "domain": "combustion" },
  "retrieval": { "mode": "lexical", "knowledge_version": "kv-2026-10-05.1", "index_version": null, "searched_but_empty": false },
  "meta": { "request_id": "req_01J9Z3K8V5Q2N7X4M6R1T0W8YB", "generated_at": "2026-10-05T09:30:00Z", "api_version": "0.1.0" }
}
```

**Errors:**

- 400 `VALIDATION_ERROR`: missing `q`, `page_size` > 50, or a bad `source_id` pattern.
- 503 `DATABASE_UNAVAILABLE` or `SEARCH_UNAVAILABLE`.
- 429, 500.

**Notes**

- `FF-NTRS-20000034017` is the *proposed* registry ID. The three NTRS PDFs are not registered yet (DAY2_TASKS §4).
- The first implementation is lexical (Postgres full-text search). `hybrid` arrives with the vector index. The response shape does not change.

---

### 4.4 `GET /api/documents/{document_id}`: document details

| | |
|---|---|
| **Purpose** | Document view and the "document" hop of the evidence trail. |
| **Auth** | Optional bearer. |
| **Path** | `document_id` (ULID). |
| **Response** | `DocumentResponse { document: Document, meta }` |
| **Errors** | 404 `DOCUMENT_NOT_FOUND`, 400 (malformed ID), 503 `DATABASE_UNAVAILABLE`, 429, 500. |

`Document`:

| Field | Type | Notes |
|---|---|---|
| `document_id` | ULID | |
| `title` | string | |
| `document_type` | enum | `technical_report`, `publication`, `test_plan`, `requirements`, `final_report`, `thesis`, `dataset_documentation` or `other`. |
| `identifier` | string \| null | Report number or NTRS ID. |
| `persistent_identifier` | string \| null | Document-level DOI. |
| `source` | `SourceRef` | |
| `file` | `FileRef` | `{ file_id, sha256, original_filename, media_type, size_bytes, retrieved_at, canonical_source_url, is_original, parent_file_id }`, projected from `files.jsonl`. |
| `page_count` | integer \| null | |
| `text_layer` | `"full" \| "partial" \| "none" \| "unknown"` | |
| `pages_without_text` | integer[] | Pages flagged for OCR, e.g. `20080034883.pdf` pp. 14–15. Their text is not searchable yet, so show that. |
| `parser_version` | string \| null | |
| `ingested_at` | datetime | |
| `knowledge_version` | string \| null | |
| `experiment_ids` | ULID[] | |
| `evidence_count` | integer | |

**Example request:** `GET /api/documents/01J9Z3M2A7D4F6H8K0N2Q4S6T8`

**Example response:** in `openapi.json` → `getDocument` → example `ntrsReport`. The sha256 `dc531270…520d` is the real checksum of `docs/research/20000034017.pdf`.

**Notes**

- The "original source" link is `source.access_url` (the landing page). It is deliberately not a direct object-storage URL.
- Page-text endpoints (`/documents/{id}/pages/{n}`) are not in v0.1. The evidence `excerpt` covers the viewer.

---

### 4.5 `GET /api/experiments/{experiment_id}`: experiment details

This is supporting endpoint #7. It is included only because search returns experiment hits and analyses link to experiments, and without it those links would be dead.

| | |
|---|---|
| **Path** | `experiment_id` (ULID). |
| **Response** | `ExperimentResponse { experiment: Experiment, meta }` |
| **Errors** | 404 `EXPERIMENT_NOT_FOUND`, 400, 503, 429, 500. |

`Experiment` has these fields:

- `experiment_id`, `test_id` (e.g. `B1`), `investigation` (e.g. `BASS-II`), `source`
- `gravity_regime`: `microgravity`, `partial_gravity`, `normal_gravity` or `unknown`
- `fuel_or_material`, `conditions[]`, `document_ids[]`, `table_file` (the CSV the row came from)

`ExperimentCondition`: `{ variable, value_numeric|null, value_text|null, unit_original|null, value_si|null, unit_si|null, origin: "reported"|"derived", evidence_id }`. The original value and unit are always kept, and the SI value sits beside them (units policy, `DATA_DICTIONARY.md`).

**Example:** BASS-II test B1 (100 µm PMMA film, initial O₂ 22.2 %, per DAY2_TASKS §4). See the `bassB1` example in the spec.

---

### 4.6 `GET /api/evidence/{evidence_id}`: evidence and provenance

| | |
|---|---|
| **Purpose** | Evidence Viewer. It resolves any `evidence_id` (from a search hit, an experiment condition or an analysis statement) to its source artefact, locator and verbatim content. |
| **Auth** | Optional bearer. |
| **Path** | `evidence_id` (ULID). |
| **Response** | `EvidenceResponse { evidence: Evidence, meta }` |
| **Errors** | 404 `EVIDENCE_NOT_FOUND`, 400, 503 `DATABASE_UNAVAILABLE`, 429, 500. |

**Design decision: evidence is the resource, claims are not.** The data model (MVP plan §9) has an `Evidence` table and no `Claim` table. Claims exist only *inside* the resource that made them. In v0.1 that means the analysis's `observations` and `interpretation.statements`. Each statement carries `evidence_ids[]`, which the frontend resolves through this endpoint. A `GET /api/claims/{id}/evidence` would need a claim store that nobody has planned, so it is not part of v0.1.

`Evidence`:

| Field | Type | Notes |
|---|---|---|
| `evidence_id` | ULID | |
| `kind` | `"document_passage" \| "experiment_condition" \| "dataset_file" \| "image_measurement"` | |
| `origin` | `"source_evidence" \| "calculated_measurement"` | **The only two things that can be evidence.** Model-generated interpretation and inference are never evidence records. |
| `citation` | string | Built only from stored fields. |
| `source` | `SourceRef` \| null | Null only for `calculated_measurement`. |
| `document_id` / `experiment_id` / `analysis_id` | ULID \| null | The target. Exactly the ones that apply are set. |
| `file` | `FileRef` \| null | The artefact the locator applies to, with its sha256. |
| `locator` | `Locator` \| null | page / section / table row / frame. |
| `excerpt` | string \| null | Verbatim quote. |
| `value` | `{ numeric, text, unit }` \| null | For table and measurement evidence. |
| `measurement_or_claim_type` | string \| null | Data-dictionary name, e.g. `o2_fraction`. |
| `extraction_method` | `"verbatim_text" \| "ocr" \| "table_parse" \| "cv_pipeline" \| "manual"` | |
| `extraction_confidence` | number 0–1 \| null | **Only** when the method itself produced a score (OCR). Otherwise null and never synthesised. |
| `review_status` | `"raw" \| "machine_extracted" \| "human_verified" \| "rejected"` | Badge `human_verified` distinctly. **Never** present `rejected` as support. |
| `transformation_id` | string \| null | Parser or pipeline version. |
| `created_at` | datetime | |
| `knowledge_version` | string \| null | |

How the prompt's suggested `source_type` (NASA/NIST/EXPERIMENT/MODEL/OTHER) maps onto this schema:

- `source.repository` gives the publisher: `NASA PSI`, `NASA NTRS`, …
- `kind` gives the experiment-vs-document distinction.
- There is deliberately **no `MODEL` source type**, because model output is not evidence.

**Example request:** `GET /api/evidence/01J9Z3N5B8C1E3G5J7M9P1R3T5`

**Example response** (the excerpt is real text from PDF page 5):

```json
{
  "evidence": {
    "evidence_id": "01J9Z3N5B8C1E3G5J7M9P1R3T5",
    "kind": "document_passage", "origin": "source_evidence",
    "citation": "Friedman, Jackson & Olson, NASA/TM-2000-209773 (2000), p. 5",
    "source": { "source_id": "FF-NTRS-20000034017", "title": "Testing and Selection of Fire-Resistant Materials for Spacecraft Use", "short_name": "NASA/TM-2000-209773", "repository": "NASA NTRS", "persistent_identifier": null, "license": null, "access_url": "https://ntrs.nasa.gov/citations/20000034017" },
    "document_id": "01J9Z3M2A7D4F6H8K0N2Q4S6T8", "experiment_id": null, "analysis_id": null,
    "file": { "file_id": "sha256:dc531270ffb646b2", "sha256": "dc531270ffb646b26503955afb0c1df7bcc47482bbfed4a3d6b922de9629520d", "original_filename": "20000034017.pdf", "media_type": "application/pdf", "size_bytes": 1297410, "retrieved_at": "2026-10-03T20:00:38Z", "canonical_source_url": null, "is_original": true, "parent_file_id": null },
    "locator": { "type": "page", "page": 5, "section": "ABSTRACT", "row": null, "frame_index": null, "label": "p. 5" },
    "excerpt": "Research shows that flammability and fire-spread rates in low gravity are sensitive to forced convection (ventilation flows) and atmospheric-oxygen concentration.",
    "value": null, "measurement_or_claim_type": null,
    "extraction_method": "verbatim_text", "extraction_confidence": null, "review_status": "machine_extracted",
    "transformation_id": "pymupdf-pages-0.1.0", "created_at": "2026-10-05T08:00:00Z", "knowledge_version": "kv-2026-10-05.1"
  },
  "meta": { "request_id": "req_01J9Z3K8V5Q2N7X4M6R1T0W8YB", "generated_at": "2026-10-05T09:30:00Z", "api_version": "0.1.0" }
}
```

**Notes**

- Trace path to render: statement → evidence (`excerpt`/`value` + `review_status`) → document (`document_id`) → page (`locator.label`) → original (`file.sha256`, `source.access_url`).
- `retrieved_at` above is the date the PDF was committed. The real retrieval time and URL aren't recorded yet, because the PDFs aren't in `files.jsonl`.

---

### 4.7 `POST /api/analyses`: upload a flame image (asynchronous)

| | |
|---|---|
| **Purpose** | Start a flame analysis. |
| **Auth** | Optional bearer. |
| **Headers** | `X-Request-ID`. `Idempotency-Key` (optional, 8–128 chars): resending within 24 h returns the original 202 instead of creating a second analysis. Use it on every submit to make double-clicks safe. |
| **Content type** | `multipart/form-data` |
| **Behaviour** | Validates synchronously, stores the original, enqueues, and returns **202** with the analysis in `queued`. Never returns a finished result. See §5. |

**Form fields** (`AnalysisCreateForm`)

| Field | Type | Required | Validation / meaning |
|---|---|---|---|
| `image` | file | **yes** | PNG or JPEG, **detected from bytes** (not the filename or part header). ≤ 10 MiB (matches the existing intake code in `origin/Princess:cv/CVmodel.ipynb`). ≥ 64×64 px, ≤ 50 megapixels. EXIF orientation is applied; the original bytes are kept unchanged. |
| `experiment_id` | ULID | no | Must exist, else 422 `UNKNOWN_EXPERIMENT`. |
| `source_file_id` | `sha256:` + 16 hex | no | The `files.jsonl` `file_id` the image came from, for provenance when it comes from the corpus. |
| `frame_index` | integer ≥ 0 | no | Frame within that source sequence or video. |
| `scale_px_per_mm` | number > 0 | no | Spatial calibration. Enables `geometry_physical` (classed `estimated`). Requires `scale_source`. |
| `scale_source` | string 1–500 | if scale is given | How the scale was established. Stored verbatim. |
| `request_interpretation` | boolean | no (default `false`) | Ask for an AURA interpretation after measurements. When AURA is disabled you get `interpretation.status = "unavailable"` plus a warning. The analysis still completes. |
| `notes` | string ≤ 2000 | no | |

There is no temperature or radiometric calibration input in v0.1, so no field can lead to a temperature value. TIFF and BMP (the FLEX originals) are not accepted yet: bit depth and mono-vs-RGB handling are still open in the image-intake spec.

**Response (202):** `AnalysisResponse`, with `Location: /api/analyses/{analysis_id}` and `Retry-After: 1`.

**Example request**

```bash
curl -X POST /api/analyses \
  -H "X-Request-ID: web-91c2" -H "Idempotency-Key: 6b0f3c1e-upload-1" \
  -F "image=@flame.png;type=image/png" \
  -F "experiment_id=01J9Z3P7C2E4G6J8M0Q2S4V6X8" \
  -F "request_interpretation=false"
```

**Example response (202)**

```json
{
  "analysis": {
    "analysis_id": "01J9Z3Q9D3F5H7K9N1R3T5W7Y9", "analysis_type": "flame_image", "status": "queued",
    "created_at": "2026-10-05T09:30:00Z", "updated_at": "2026-10-05T09:30:00Z", "started_at": null, "completed_at": null,
    "input": { "image_sha256": "4f1c…3f2a", "original_filename": "example.png", "media_type": "image/png", "size_bytes": 354891, "width": 640, "height": 480,
               "experiment_id": null, "source_file_id": null, "frame_index": null,
               "calibration": { "state": "absent", "scale_px_per_mm": null, "scale_source": null }, "notes": null },
    "pipeline": null, "result": null,
    "interpretation": { "status": "not_requested", "provider": null, "model": null, "statements": [], "rejected_statement_count": 0, "generated_at": null },
    "artifacts": [{ "kind": "original", "url": "/api/analyses/01J9Z3Q9D3F5H7K9N1R3T5W7Y9/artifacts/original", "media_type": "image/png", "sha256": "4f1c…3f2a", "width": 640, "height": 480, "size_bytes": 354891 }],
    "warnings": [], "failure": null, "poll_after_ms": 1000
  },
  "meta": { "request_id": "web-91c2", "generated_at": "2026-10-05T09:30:00Z", "api_version": "0.1.0" }
}
```

**Errors**

| Status | Code |
|---|---|
| 400 | `VALIDATION_ERROR` (e.g. scale without `scale_source`) |
| 413 | `PAYLOAD_TOO_LARGE` |
| 415 | `UNSUPPORTED_MEDIA_TYPE` |
| 422 | `IMAGE_INVALID`, `UNKNOWN_EXPERIMENT` |
| 429 | `RATE_LIMITED` |
| 503 | `DATABASE_UNAVAILABLE`, `STORAGE_UNAVAILABLE`, `QUEUE_UNAVAILABLE`, `MODEL_UNAVAILABLE` (the CV worker isn't ready, so the job is refused up front instead of being accepted only to fail) |
| 500 | `INTERNAL_ERROR` |

---

### 4.8 `GET /api/analyses/{analysis_id}`: status, result and detail

| | |
|---|---|
| **Purpose** | The polling target **and** the detail view for re-opening a past analysis. |
| **Auth** | Optional bearer. |
| **Path** | `analysis_id` (ULID). |
| **Response** | `AnalysisResponse` (200). While non-terminal it also sets `Retry-After` and `analysis.poll_after_ms`. |
| **Errors** | 404 `ANALYSIS_NOT_FOUND`, 400, 503 `DATABASE_UNAVAILABLE`, 429, 500. |

`Analysis` (top level):

| Field | Type | Notes |
|---|---|---|
| `analysis_id` | ULID | |
| `analysis_type` | `"flame_image"` | Only single-image analysis in v0.1. |
| `status` | `"queued" \| "processing" \| "completed" \| "failed" \| "cancelled"` | |
| `created_at`, `updated_at` | datetime | |
| `started_at`, `completed_at` | datetime \| null | |
| `input` | `AnalysisInput` | Input provenance: `image_sha256`, filename, detected media type, size, oriented width/height, `experiment_id`, `source_file_id`, `frame_index`, `calibration { state: "absent"\|"spatial_scale_provided", scale_px_per_mm, scale_source }`, `notes`. |
| `pipeline` | `PipelineInfo` \| null | `pipeline_version`, `preprocessing_version`, `detector` / `segmenter` as `{ name, version, artifact_digest\|null }`, and `measurement_space: "original_oriented_px"`. Null while queued. |
| `result` | `FlameAnalysisResult` \| null | Non-null **iff** `completed`. |
| `interpretation` | `Interpretation` | Always present. Its `status` says whether there is anything to show. |
| `artifacts` | `Artifact[]` | `original` from creation. `preprocessed`, `mask` and `overlay` once completed. |
| `warnings` | `Warning[]` | `{ code, severity: "info"\|"warning", message }`. |
| `failure` | `{ code, message, retryable }` \| null | Non-null iff `failed` or `cancelled`. |
| `poll_after_ms` | integer \| null | Null when terminal. |

`FlameAnalysisResult`:

| Field | Type | Notes |
|---|---|---|
| `detection` | `{ status: "present"\|"absent"\|"uncertain", confidence: number\|null, bounding_box: {x_min,y_min,x_max,y_max}\|null }` | The **single** place detection confidence lives. `confidence` is null for classical threshold detectors, which produce no calibrated score. Don't show a number you weren't given. |
| `segmentation` | `{ mask_type: "binary", threshold_policy, component_count, confidence\|null, contours: Point[][], simplification_tolerance_px }` \| null | Null when `absent`. `contours` holds the flame boundaries, for an SVG overlay toggle. |
| `measurements.geometry_px` | `{ area, width, height, perimeter, centroid, aspect_ratio, circularity }` | Each field except `centroid` is a `MeasuredValue` `{ value\|null, unit, classification: "measured", method, uncertainty\|null }`. Units: `px2` for area, `px` for lengths, `ratio`. `centroid` is `{ x, y, unit: "px", classification, method }`. |
| `measurements.geometry_physical` | `{ area, width, height, perimeter }` \| null | **Only** with a caller-supplied scale. Units `mm` / `mm2`, `classification: "estimated"`. This is a 2-D projection, not a 3-D flame size. |
| `measurements.appearance` | `{ color_space: "RGB", mean_r, mean_g, mean_b, mean_intensity, saturated_fraction, physical_interpretation: "none" }` | Image statistics inside the mask (`intensity_8bit`, `fraction`). `physical_interpretation` is the constant `"none"`: these are not physical state variables. |
| `quality_flags` | `{ blur, saturation_clipping, low_light, multiple_flames, occlusion, scale_absent, calibration_absent }` | Booleans. **`null` = the check isn't implemented or wasn't run**, which is different from `false`. Render it as "not checked". |
| `observations` | `Statement[]` | Deterministic text generated from the measurements (`origin: "cv_pipeline"`, class `observed`/`measured`/`estimated`). |

`Statement`: `{ statement_id, text, claim_class, origin: "cv_pipeline"|"aura_interpretation", evidence_ids: ULID[], measurement_refs: string[] }`. `claim_class` is one of `observed`, `measured`, `estimated`, `inferred`, `hypothesized` or `unsupported` (MVP plan §10 labels).

`Interpretation`: `{ status: "not_requested"|"pending"|"completed"|"unavailable"|"failed", provider: "aura"|null, model|null, statements: Statement[], rejected_statement_count, generated_at|null }`.

**Scientific display rules the schema enforces, and the UI must not undo**

1. **There is no temperature field anywhere.** `TEMPERATURE_NOT_AVAILABLE` (info) is attached to every completed analysis. Don't derive temperature from `mean_r`/`mean_g`/`mean_b`.
2. `measured` (pixels) and `estimated` (scaled mm) must look different. Never colour a hypothesis like a measurement (MVP plan §13).
3. `interpretation.statements` are AI-generated and limited to `inferred`, `hypothesized` or `unsupported`. Render them in a separate, labelled panel, never mixed into the measurement cards.
4. Each `evidence_ids` entry was verified to exist before the statement was stored. Statements that failed that check were dropped and counted in `rejected_statement_count`.
5. All coordinates (bounding box, contours, centroid) are in the **original image's pixel grid after EXIF orientation**. Overlay them on the `original` artifact at its natural size.

**Example response (completed)**

The numbers below are illustrative, for UI layout only. They are not a measurement of any real image (the spec example is labelled the same way).

```json
{
  "analysis": {
    "analysis_id": "01J9Z3Q9D3F5H7K9N1R3T5W7Y9", "analysis_type": "flame_image", "status": "completed",
    "created_at": "2026-10-05T09:30:00Z", "updated_at": "2026-10-05T09:30:04Z", "started_at": "2026-10-05T09:30:01Z", "completed_at": "2026-10-05T09:30:04Z",
    "input": { "…": "as in the 202 example" },
    "pipeline": { "pipeline_version": "cv-0.1.0", "preprocessing_version": "prep-0.1.0",
                  "detector": { "name": "otsu-threshold-contour", "version": "0.1.0", "artifact_digest": null },
                  "segmenter": { "name": "otsu-threshold-contour", "version": "0.1.0", "artifact_digest": null },
                  "measurement_space": "original_oriented_px" },
    "result": {
      "detection": { "status": "present", "confidence": null, "bounding_box": { "x_min": 250, "y_min": 140, "x_max": 390, "y_max": 330 } },
      "segmentation": { "mask_type": "binary", "threshold_policy": "otsu-v1", "component_count": 1, "confidence": null,
                        "contours": [[{ "x": 250, "y": 235 }, { "x": 320, "y": 140 }, { "x": 390, "y": 235 }, { "x": 320, "y": 330 }]],
                        "simplification_tolerance_px": 2.0 },
      "measurements": {
        "geometry_px": {
          "area":      { "value": 18900, "unit": "px2", "classification": "measured", "method": "mask_pixel_count", "uncertainty": null },
          "width":     { "value": 140,   "unit": "px",  "classification": "measured", "method": "mask_bbox", "uncertainty": null },
          "height":    { "value": 190,   "unit": "px",  "classification": "measured", "method": "mask_bbox", "uncertainty": null },
          "perimeter": { "value": 512.3, "unit": "px",  "classification": "measured", "method": "contour_perimeter_opencv", "uncertainty": null },
          "centroid":  { "x": 320.1, "y": 236.4, "unit": "px", "classification": "measured", "method": "mask_moments" },
          "aspect_ratio": { "value": 1.357, "unit": "ratio", "classification": "measured", "method": "bbox_height_over_width", "uncertainty": null },
          "circularity":  { "value": 0.905, "unit": "ratio", "classification": "measured", "method": "4pi_area_over_perimeter_sq", "uncertainty": null }
        },
        "geometry_physical": null,
        "appearance": { "color_space": "RGB", "mean_r": { "…": "MeasuredValue" }, "mean_g": { "…": "MeasuredValue" }, "mean_b": { "…": "MeasuredValue" },
                        "mean_intensity": { "…": "MeasuredValue" }, "saturated_fraction": { "…": "MeasuredValue" }, "physical_interpretation": "none" }
      },
      "quality_flags": { "blur": null, "saturation_clipping": false, "low_light": false, "multiple_flames": false, "occlusion": null, "scale_absent": true, "calibration_absent": true },
      "observations": [{ "statement_id": "obs-1", "text": "A single luminous region was segmented; area 18,900 px² (pixel units, no scale calibration).",
                         "claim_class": "measured", "origin": "cv_pipeline", "evidence_ids": [], "measurement_refs": ["geometry_px/area"] }]
    },
    "interpretation": { "status": "not_requested", "provider": null, "model": null, "statements": [], "rejected_statement_count": 0, "generated_at": null },
    "artifacts": [
      { "kind": "original", "url": "/api/analyses/01J9Z3Q9D3F5H7K9N1R3T5W7Y9/artifacts/original", "media_type": "image/png", "sha256": "4f1c…", "width": 640, "height": 480, "size_bytes": 354891 },
      { "kind": "mask",     "url": "/api/analyses/01J9Z3Q9D3F5H7K9N1R3T5W7Y9/artifacts/mask",     "media_type": "image/png", "sha256": "…", "width": 640, "height": 480, "size_bytes": 4096 },
      { "kind": "overlay",  "url": "/api/analyses/01J9Z3Q9D3F5H7K9N1R3T5W7Y9/artifacts/overlay",  "media_type": "image/png", "sha256": "…", "width": 640, "height": 480, "size_bytes": 4096 }
    ],
    "warnings": [
      { "code": "SCALE_CALIBRATION_ABSENT", "severity": "warning", "message": "No spatial scale supplied: sizes are in pixels, not physical units." },
      { "code": "TEMPERATURE_NOT_AVAILABLE", "severity": "info", "message": "Temperature is not reported: RGB/intensity cannot be converted to temperature without radiometric calibration." },
      { "code": "QUALITY_CHECK_NOT_IMPLEMENTED", "severity": "info", "message": "Blur and occlusion checks are not implemented in cv-0.1.0." }
    ],
    "failure": null, "poll_after_ms": null
  },
  "meta": { "request_id": "web-a01", "generated_at": "2026-10-05T09:30:05Z", "api_version": "0.1.0" }
}
```

The full, schema-valid version is the `completed` example under `getAnalysis` in `openapi.json`.

---

### 4.9 `GET /api/analyses/{analysis_id}/artifacts/{artifact_kind}`: images

| | |
|---|---|
| **Purpose** | Original / analysed image, flame mask and overlay for display. |
| **Path** | `analysis_id` (ULID). `artifact_kind`: `original`, `preprocessed`, `mask` or `overlay`. |
| **Response** | 200 `image/png` or `image/jpeg` bytes. `ETag` is the quoted sha256. `Cache-Control: public, max-age=31536000, immutable`. |
| **Errors** | 404 `ANALYSIS_NOT_FOUND` / `ARTIFACT_NOT_FOUND`. **409 `ARTIFACT_NOT_READY`** (still processing; `Retry-After`). 503 `STORAGE_UNAVAILABLE`. 429, 500. |

**Notes**

- Use `artifact.url` from the analysis response directly as `<img src>`. Don't build URLs yourself.
- The mask is a binary PNG at the original's resolution. The overlay is the original with the contour drawn.
- For an interactive toggle, prefer drawing `segmentation.contours` as SVG over the `original` image. Use the `overlay` PNG for thumbnails and downloads.
- Why not presigned object-storage URLs: they would expose bucket layout and expire inside cached pages (MVP plan §19 allows signed URLs, but the API proxy keeps the frontend topology-free).

---

### 4.10 `GET /api/analyses`: analysis history

| | |
|---|---|
| **Purpose** | History list. |
| **Auth** | Optional bearer. Once auth is enforced, results are scoped to the caller. |
| **Response** | `AnalysisListResponse { items: AnalysisSummary[], pagination, meta }` |
| **Errors** | 400 (bad enum or date), 503 `DATABASE_UNAVAILABLE`, 429, 500. |

**Query parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `status` | `AnalysisStatus[]` (repeat) | all | e.g. `?status=completed&status=failed` |
| `experiment_id` | ULID | – | |
| `pipeline_version` | string ≤ 64 | – | Exact match. This is the model filter. |
| `created_from` | datetime | – | Inclusive. |
| `created_to` | datetime | – | Exclusive. |
| `sort` | `created_at_desc` \| `created_at_asc` | `created_at_desc` | |
| `page` | ≥ 1 | 1 | |
| `page_size` | 1–100 | 20 | |

`AnalysisSummary` has these fields:

- `analysis_id`, `analysis_type`, `status`, `created_at`, `completed_at`
- `original_filename`, `image_sha256`, `experiment_id`, `pipeline_version`
- `detection_status`, `flame_area_px`, `calibration_state`, `warning_count`
- `overlay_url` (a thumbnail; null unless completed with a flame)

To re-open a past analysis, call `GET /api/analyses/{analysis_id}`. Completed analyses are immutable. A re-run creates a new analysis with its own ID, so history is reproducible: `image_sha256` plus `pipeline_version` identify what was computed.

**Example request:** `GET /api/analyses?status=completed&page=1&page_size=20`

**Example response:** the `history` example in the spec.

---

## 5. Asynchronous analysis: lifecycle and polling

```
POST /api/analyses ──► 202 {status: queued}   Location: /api/analyses/{id}
        │
        ▼
 queued ──► processing ──► completed            (result + artifacts present)
    │            ├────────► failed              (failure.code set; partial artifacts may exist)
    └────────────┴────────► cancelled           (server-initiated only; no client cancel in v0.1)
```

**Why asynchronous rather than synchronous:**

- MVP plan §5.2 requires job submission and status retrieval for long-running analysis, so the browser never holds a connection open.
- The CV stage doesn't exist yet (§1 of the status report), and its GPU/CPU latency is unmeasured.
- The optional AURA interpretation runs on a CPU-only LLM measured at roughly 5–10 tokens/s in AURA's production. That alone is tens of seconds per interpretation.

A synchronous contract would have to be broken later, while an asynchronous one costs a single poll when the job happens to be fast.

**Polling contract:**

1. After the 202, wait `Retry-After` seconds (or `poll_after_ms`), then `GET /api/analyses/{id}`.
2. Repeat, honouring each response's `poll_after_ms` (the server backs off from 1 s to 5 s).
3. Stop at `completed`, `failed` or `cancelled`.
4. Give up client-side after 5 minutes. Show "still processing, check History" and keep the ID.
5. `interpretation.status` can be `pending` while `status` is already `completed`. Measurements are final at that point. Keep polling only if you are showing the interpretation panel, and stop when it leaves `pending`.
6. Never re-POST to "retry" a non-terminal job. Use the same `Idempotency-Key` if you re-submit after a network error.

---

## 6. Not in v0.1 (planned, so don't build against them yet)

| Endpoint | Source | Status |
|---|---|---|
| `POST /api/chat` (grounded RAG answer) | MVP plan §12 | Planned, Days 5–7. Needs the corpus, retrieval and the Flame model router. |
| `GET /api/documents` (list) | MVP plan §12 | Planned. Search covers discovery for v0.1. |
| `GET /api/experiments` (list and facets) | MVP plan §12 | Planned, Experiment Explorer. |
| `GET /api/openapi.json` | DAY2_TASKS §2 | Served by FastAPI once `apps/api` exists. It must match this file (contract test). |
| Analysis cancel, video/temporal analysis | MVP plan §10 "Future CV" | Weeks 3–6. |
