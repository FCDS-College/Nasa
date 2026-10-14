# L-6: Background jobs

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review (sign-off: Princess E3, Anas E2) | 1.0.0 | 2026-10-12 | A4, B2 | `apps/api/flame_api/analysis.py`, `worker.py`, `ingest.py`, `vector_index.py` |

## 1. Queues and job types

| Job | Mechanism | Queue | Payload | Idempotency key |
|---|---|---|---|---|
| Image analysis | RQ `flame_api.worker.process_analysis(analysis_id)` | `flame-analysis` (Redis, AOF) | `analysis_id` only; inputs are in `analysis_result` and MinIO | `Idempotency-Key` header → `analysis_result.idempotency_key` (unique) |
| Interpretation | in-process at the end of the analysis job | — | measured evidence + linked context | `analysis_id` (sent to AURA as `Idempotency-Key`) |
| Ingestion | CLI `python -m flame_api.ingest` (Compose start-up, Railway pre-deploy) | — | the file registry | `ingestion_run (file_id, transformation_id, input_sha256)` unique |
| Vector index build | CLI `python -m flame_api.vector_index build` | — | — | chunk_id + model |
| Video analysis | **planned** (Workstream A, ADR-008) | `flame-analysis` | `analysis_id` | as image |

## 2. Status lifecycle (analysis)

`queued` → `processing` → `completed` | `failed`. The status is stored in PostgreSQL (`analysis_result.status`), not only in RQ, so it survives Redis loss and API restarts. `interpretation.status` is separate: `not_requested`, `pending`, `completed` or `unavailable`. A failed interpretation never fails the analysis.

## 3. Retries, timeouts, cancellation
- **Retries.**
  - RQ default: none.
  - A `failed` analysis with `failure.retryable = true` (`MODEL_UNAVAILABLE`) can be resubmitted with the same idempotency key once a provider is back.
  - Within a job, the router falls back across providers (H-2) instead of retrying the same one.
- **Timeouts.**
  - RQ job timeout: the RQ default of 180 s. Video jobs will need an explicit `job_timeout`.
  - Provider timeouts: `FLAME_CV_TIMEOUT_S`, `FLAME_LLM_TIMEOUT_S`, `FLAME_AURA_TIMEOUT_S`.
- **Cancellation:** not implemented (planned with video, A4).

## 4. Failure reporting
- `analysis_result.payload.failure = {code, message, retryable}`, with codes `MODEL_UNAVAILABLE`, `IMAGE_DECODE_FAILED` and `PIPELINE_ERROR`. Exceptions are logged with `analysis_id`.
- Ingestion: quarantine and `ingestion_run` rows with `transformation_id = "quarantine"` (E2-2).

## 5. Restart behaviour (2H scenario S9)
- **Image job:** if the worker dies mid-job, the RQ job is lost, but the row stays `processing`. The recovery is to resubmit (same idempotency key); a stale-`processing` sweeper is planned with video.
- **Video job (planned):** checkpoint per processed segment into `analysis_result.payload.progress`, then resume from the last checkpoint.
- **Ingestion and index build** are resumable by construction: stable IDs and `merge`, and "embed only missing".

## 6. Admin "System Operations" module (Belal, B9)

The module shows:
- queue depth: `/api/health` `cv_model.message`;
- jobs by status: `GET /api/analyses?status=queued&status=processing&status=failed`;
- the last `ingestion_run` rows and quarantined files (an admin endpoint is planned, E2-8);
- provider health and circuits: `GET /api/ai/providers`.

## Known limitations
No cancellation, no sweeper for stale `processing` rows, no explicit RQ timeouts.

## Changelog
- 1.0.0 (2026-10-12): documents the MVP job system plus the Phase 2 router integration.
