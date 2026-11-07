# Flame API integration reference (for AURA and other clients)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current for contract 0.3.0 | 1.0.0 | 2026-10-30 | L-4, L-12 | `docs/api/openapi.json`, `apps/api/flame_api/main.py`, `apps/api/flame_api/analysis.py` |

**Start with [README.md](README.md)** for the current setup (contract 0.5.0: 14 tools, per-client keys). This page is the per-endpoint reference written for 0.3.0.

**Source of truth:** [`docs/api/openapi.json`](../api/openapi.json), served at `GET /api/openapi.json`, plus the rendered [API_SCHEMAS.md](../api/API_SCHEMAS.md). This page tells a client what to call and how to behave; it does not repeat every field. Changes are listed in [CHANGELOG](../api/CHANGELOG.md).

## 1. Configuration

| Setting | Value |
|---|---|
| Base URL | the Flame API origin (e.g. `https://<flame-api-host>`); every path below starts with `/api/` |
| Contract | `GET /api/openapi.json` (public, no token). `info.version` = `meta.api_version` on every response (0.3.0). |
| AURA connector | `POST /api/v3/admin/connectors` on AURA, with the OpenAPI URL above as the `endpoint`, the Flame **read** token as the vaulted `secret` (https only), and `read_only_attested: true` |
| Tools AURA compiles | 10 (GET only): `api_get_health`, `api_get_dashboard_counts`, `api_search`, `api_list_documents`, `api_get_document`, `api_list_experiments`, `api_get_experiment`, `api_get_evidence`, `api_list_analyses`, `api_get_analysis` |
| Never compiled | `POST /api/chat`, `GET /api/ai/providers`, `PUT /api/admin/ai/mode` (`x-aura-exclude`); `POST /api/analyses` (a write); artifacts (binary) |

## 2. Authentication

`Authorization: Bearer <token>`. There are two static tokens (≥ 32 chars, distinct; ADR-009 will replace them):

| Token | Allows |
|---|---|
| read | every `GET`/`HEAD`, and `POST /api/chat` |
| write | `POST /api/analyses`, `PUT /api/admin/ai/mode` |

A missing or wrong token returns **401** `AUTHENTICATION_REQUIRED` with `WWW-Authenticate: Bearer`. A read token on a write is also 401. AURA should hold only the read token. Firebase tokens are **not** accepted.

## 3. Conventions

- JSON is snake_case. Timestamps are RFC 3339 **UTC** with `Z`. IDs are 26-char Crockford ULIDs (`^[0-9A-HJKMNP-TV-Z]{26}$`), except `source_file_id` (`sha256:` + 16 hex).
- `null` means "not present or not established"; it is never 0.
- Every success body has `meta {request_id, generated_at, api_version}`. Send `X-Request-ID` (`[A-Za-z0-9._-]{1,128}`) to correlate; it is echoed back.
- Pagination: `page` (from 1), `page_size` (search ≤ 50, lists ≤ 100). The response carries `pagination {page, page_size, total_items, total_pages}`.

## 4. Errors

Every non-2xx response has the same body:

```json
{"error": {"code": "VALIDATION_ERROR", "message": "Search parameters are invalid.", "request_id": "req_…",
           "retryable": false, "field_errors": [{"field": "page_size", "message": "…"}], "details": {}}}
```

Switch on `error.code`, never on `message`.

| Status | Codes | Client action |
|---|---|---|
| 400 | `VALIDATION_ERROR` | fix the request; do not retry |
| 401 | `AUTHENTICATION_REQUIRED` | check the token; do not retry |
| 404 | `ROUTE_NOT_FOUND`, `DOCUMENT_NOT_FOUND`, `EXPERIMENT_NOT_FOUND`, `EVIDENCE_NOT_FOUND`, `ANALYSIS_NOT_FOUND`, `ARTIFACT_NOT_FOUND` | do not retry |
| 405 | `METHOD_NOT_ALLOWED` (0.3.0) | client bug |
| 409 | `ARTIFACT_NOT_READY` (+ `Retry-After`) | poll later |
| 413 / 415 / 422 | `PAYLOAD_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE`, `IMAGE_INVALID`, `VIDEO_INVALID`, `UNKNOWN_EXPERIMENT` | do not retry |
| 429 | `RATE_LIMITED` (+ `Retry-After`) | back off for `Retry-After` |
| 503 | `DATABASE_UNAVAILABLE`, `SEARCH_UNAVAILABLE`, `STORAGE_UNAVAILABLE`, `QUEUE_UNAVAILABLE`, `CHAT_UNAVAILABLE`, `MODEL_UNAVAILABLE` | retry with backoff when `retryable: true` |
| 500 | `INTERNAL_ERROR` | retry once at most; report `request_id` |

## 5. Timeouts and retries

| Call | Suggested client timeout | Retry policy |
|---|---|---|
| health, counts, get-by-id, lists | 10 s | GETs are idempotent: up to 3 tries, exponential backoff (0.5 s, 1 s, 2 s, ±20 % jitter), only on network errors, 502/503/504, or 429 after `Retry-After` |
| search | 20 s | same |
| `POST /api/chat` | 130 s (a local CPU model may need ~20 s; `FLAME_LLM_TIMEOUT_S` default 180 s) | retry only on 429/503 with `retryable: true`; chat changes nothing |
| `POST /api/analyses` | 30 s image, 120 s video (the upload is probed synchronously) | **always send `Idempotency-Key`** (8–128 chars); then a retry returns the same analysis instead of creating a second one |
| poll `GET /api/analyses/{id}` | 10 s | every `poll_after_ms` (1–2 s) while `queued`/`processing`; give up after a deadline you choose (videos: minutes) |

A circuit breaker on the client side is recommended for AURA: open after 5 consecutive 5xx or timeouts, half-open after 30 s.

## 6. Endpoint catalog

| Method | Path | Token | Main parameters | Response (schema) | Notes |
|---|---|---|---|---|---|
| GET | `/api/health` | read | — | `HealthResponse` | 200 healthy/degraded, **503 when a required service is down (with the same body)**. `services.{api,database,vector_index,object_storage,cache,cv_model,llm,aura}` each `{status, required, latency_ms, checked_at, version, message}`; `ai {mode, providers[]}`. Liveness without dependencies: `GET /health/live` (no token, not in the contract). |
| GET | `/api/dashboard/counts` | read | — | `DashboardCountsResponse` | `documents`, `experiments` (with ≥ 1 condition), `analyses` (completed), `analyses_in_progress`, `knowledge_version`. All counts are of persisted rows. |
| GET | `/api/search` | read | `q` (1–500), `type` (`document`/`experiment`), `source_id[]` ≤ 20, `experiment_id`, `domain` (`combustion`/`all`), `page`, `page_size` ≤ 50 | `SearchResponse` | Hybrid (full-text + pgvector, RRF) when an index is published; `retrieval.mode` says which. Each result has `evidence_id`, `source`, `locator` (page/row). `score` is ordinal, not a confidence. |
| GET | `/api/documents` · `/{document_id}` | read | `source_id[]`, `document_type`, `q` (title), paging | `DocumentListResponse` · `DocumentResponse` | |
| GET | `/api/experiments` · `/{experiment_id}` | read | `source_id[]`, `gravity_regime`, `fuel_or_material`, `investigation`, paging | `ExperimentListResponse` · `ExperimentResponse` | Conditions keep the original value and unit plus SI where resolvable, each with an `evidence_id`. |
| GET | `/api/evidence/{evidence_id}` | read | — | `EvidenceResponse` | `kind` (`document_passage`, `experiment_condition`, `dataset_file`, `image_measurement`, `video_measurement`), `origin` (`source_evidence` / `calculated_measurement`; model text is never evidence), `excerpt`, `locator`, `source`, `file` (sha256). Use it to render citations. |
| GET | `/api/analyses` | read | `status[]`, `experiment_id`, `pipeline_version`, `created_from`/`created_to`, `sort`, paging | `AnalysisListResponse` | Items carry `analysis_type` (`flame_image`/`flame_video`). |
| GET | `/api/analyses/{analysis_id}` | read | — | `AnalysisResponse` | `result` is `FlameAnalysisResult` (image) or `FlameVideoAnalysisResult` (video) once `completed`; `failure` when `failed`; `Retry-After` while running. |
| GET | `/api/analyses/{id}/artifacts/{kind}` | read | `kind` ∈ original, preprocessed, mask, overlay | bytes | Immutable, `ETag` = sha256. For a video only `original` exists (the video). |
| POST | `/api/analyses` | **write** | multipart: exactly one of `image` / `video`; `experiment_id`, `source_file_id`, `frame_index` (image), `scale_px_per_mm` + `scale_source` (image only), `sample_every_n_frames` (video, default 30), `max_frames` (video, default 300, ≤ 600), `request_interpretation`, `notes`; header `Idempotency-Key` | 202 `AnalysisResponse` + `Location` | Image: PNG/JPEG ≤ 10 MiB. Video: MP4/MOV/AVI, H.264/H.265, ≤ 200 MiB, ≤ 600 s. |
| POST | `/api/chat` | read | `{query (1–500), conversation_id?}` | `ChatResponse` | **x-aura-exclude.** Dashboard chat: Flame retrieves its own evidence, then the router picks a model. `model` and `execution` name who answered and where (`locality`); `warnings` include `generation_unavailable` (evidence only, nothing generated) and `model_fallback_used`. |
| GET | `/api/ai/providers` | read | — | `AiProvidersResponse` | **x-aura-exclude.** Operator view. |
| PUT | `/api/admin/ai/mode` | write | `{mode: cloud_preferred \| local_first \| offline_only}` | `ModeChangeResponse` | **x-aura-exclude.** Audited; persists across restarts and overrides `FLAME_AI_EXECUTION_MODE`. |

## 7. Examples (from the 2026-10-30 runtime verification)

```http
GET /api/dashboard/counts
Authorization: Bearer <read token>

200 {"documents":3,"experiments":0,"analyses":2,"analyses_in_progress":0,
     "knowledge_version":"bge-small-en-v1.5-37-20261030",
     "meta":{"request_id":"req_…","generated_at":"2026-10-30T16:45:57.802389Z","api_version":"0.3.0"}}
```

```http
GET /api/search?q=flame%20spread&page_size=3

200 {"query":"flame spread",
     "results":[{"result_id":"…","result_type":"document","rank":1,"score":0.031754,
                 "title":"Microgravity Flame Spread in Exploration Atmospheres: …","snippet":"…",
                 "evidence_id":"1HY71P8NP71R5H9GKMENXHRRNH","has_evidence":true,
                 "locator":{"type":"page","page":10,"label":"p. 10",…},"source":{"short_name":"NASA/TM-2008-215260",…},…}, …],
     "pagination":{"page":1,"page_size":3,"total_items":27,"total_pages":9},
     "retrieval":{"mode":"hybrid","knowledge_version":"bge-small-en-v1.5-37-20261030",…},"meta":{…}}
```

```http
POST /api/analyses        (write token, Idempotency-Key: aura-run-42-video-1)
Content-Type: multipart/form-data; video=@bass_b1.mp4; sample_every_n_frames=30; max_frames=40

202 {"analysis":{"analysis_id":"01M66TTKVJZQ585TNAPXHA4B7E","analysis_type":"flame_video","status":"queued",
     "input":{"media_type":"video/mp4","video":{"container":"mp4","codec":"h264","fps":29.97003,"frame_count":1343,
              "duration_seconds":44.811433,"variable_frame_rate":false,"sample_every_n_frames":30,"max_frames":40},…},
     "poll_after_ms":2000,…},"meta":{…}}

GET /api/analyses/01M66TTKVJZQ585TNAPXHA4B7E   →   200, status "completed":
  result.sampling           {"frames_analyzed":40,"frames_with_errors":0,…}
  result.frames[0]          {"frame_index":0,"timestamp_s":0.0,"detection_status":"present","pixel_area":3446.85,"centroid":{"x":647.02,"y":53.77},…}
  result.temporal_summary   {"persistence_rate":1.0,"flicker_frequency_hz":null,"flicker_status":"not_estimable",
                             "flicker_note":"sampling rate 1.00 Hz is below the Nyquist rate for 10 Hz",
                             "track_sessions":null,"tracking_note":"Sampling interval 1.001 s exceeds the 0.5 s tracking gap…",…}
  result.observations[0]    {"text":"Brightness-based CV detected a flame in 40 of 40 sampled frames.","claim_class":"measured",
                             "evidence_ids":["2FE81KPWX81CKBBHZVXHTG45E8"],…}
  pipeline.execution        {"provider":"flame_cv_video","locality":"local","mode":"local_first",…}
```

```http
POST /api/chat   {"query":"How does oxygen concentration affect flame spread in microgravity?"}
(no model reachable)
200 {"answer":"No language model could write an answer right now, so here is the evidence Flame found …",
     "sources":[{"evidence_id":"5ZB42PRGRR7T8KSWJTQFBMF5GH","title":"Microgravity Flame Spread …","location":"p. 1"},…],
     "model":{"provider":"flame","name":"retrieval-only","version":"n/a"},
     "execution":{"mode":"offline_only","reasons":[{"provider":"llamacpp","reason":"unavailable"}]},
     "warnings":["generation_unavailable"],…}
```

## 8. Scientific rules a client must preserve when presenting results

1. Never show a temperature; none exists. RGB means are not temperatures.
2. Show `classification` / `claim_class`: `measured` (pixels), `estimated` (scale-derived), `inferred`/`hypothesized`/`unsupported` (model text). Model text is never evidence.
3. Cite with `evidence_id` → `GET /api/evidence/{id}`; show the `source` and `locator`.
4. Show who answered (`model`, `execution.locality`) and pass on `warnings`. An evidence-only answer must not be rephrased as a generated conclusion.
5. Video: pass on `flicker_note` and `tracking_note`; null means not estimable, not zero.
