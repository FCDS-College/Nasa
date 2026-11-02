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
- **Stuck-job recovery (P2-4).** If the worker dies mid-job, the RQ job is lost but the row stays `processing`, and `process_*` only start from `queued`. `python -m flame_api.worker recover [--older-than SECONDS]` (run by the worker's start command in Compose and `.railway/railway.py`) handles this:
  - it finds `processing` rows older than the job timeout + 60 s (image: RQ's default 180 s; video: `FLAME_VIDEO_JOB_TIMEOUT_S`), and `queued` rows older than 60 s with no live RQ job;
  - it resets each to `queued`, appends a `JOB_RECOVERED` warning (the attempt counter is the number of these warnings), and re-enqueues the same job function with the same timeout;
  - after 3 re-queues it marks the row `failed` with `PIPELINE_ERROR`, `retryable: false`.
  - Each row is claimed with `UPDATE … WHERE status = :read AND updated_at = :read`, so concurrent recoverers act on it once, and a re-run is a no-op.
  - It runs once at worker start only: a worker that restarts within the timeout leaves the row for the next run (see RUNBOOK §7).
- **Video resume does not happen today.** The checkpoint (`frames.jsonl`) is written under a fresh `tempfile.TemporaryDirectory` per run, which is deleted on exit, so a re-queued video job starts from frame 0. Resuming would need a stable per-analysis work directory on a persistent volume.
- **Ingestion and index build** are resumable by construction: stable IDs and `merge`, and "embed only missing".

## 6. Admin "System Operations" module (Belal, B9)

The module shows:
- queue depth: `/api/health` `cv_model.message`;
- jobs by status: `GET /api/analyses?status=queued&status=processing&status=failed`;
- the last `ingestion_run` rows and quarantined files (an admin endpoint is planned, E2-8);
- provider health and circuits: `GET /api/ai/providers`.

## Known limitations
No cancellation. Recovery runs at worker start (or by hand), not on a schedule. Video jobs restart from scratch after recovery.

## Changelog
- Unreleased (P2-4): stuck-job recovery (`worker recover`), and a note that video jobs do not resume.
- 1.0.0 (2026-10-12): documents the MVP job system plus the Phase 2 router integration.
