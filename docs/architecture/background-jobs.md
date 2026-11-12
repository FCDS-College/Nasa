# L-6: Background jobs

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review (sign-off: Princess E3, Anas E2) | 1.1.0 | 2026-11-12 | A4, B2, ADR-008 | `apps/api/flame_api/analysis.py`, `worker.py`, `ingest.py`, `vector_index.py`, `cv/video_analysis.py` |

## 1. Queues and job types

| Job | Mechanism | Queue | Payload | Idempotency key |
|---|---|---|---|---|
| Image analysis | RQ `flame_api.worker.process_analysis(analysis_id)` | `flame-analysis` (Redis, AOF) | `analysis_id` only; inputs are in `analysis_result` and MinIO | `Idempotency-Key` header → `analysis_result.idempotency_key` (unique) |
| Interpretation | in-process at the end of the analysis job | — | measured evidence + linked context | `analysis_id` (sent to AURA as `Idempotency-Key`) |
| Ingestion | CLI `python -m flame_api.ingest` (Compose start-up, Railway pre-deploy) | — | the file registry | `ingestion_run (file_id, transformation_id, input_sha256)` unique |
| Vector index build | CLI `python -m flame_api.vector_index build` | — | — | chunk_id + model |
| Video analysis | RQ `flame_api.worker.process_video_analysis(analysis_id)`, `job_timeout = FLAME_VIDEO_JOB_TIMEOUT_S` | `flame-analysis` | `analysis_id`; the checkpoint is in `video_checkpoint_frame` | as image |

## 2. Status lifecycle (analysis)

`queued` → `processing` → `completed` | `failed` | `cancelled` (and `queued` → `cancelled`). The status is stored in PostgreSQL (`analysis_result.status`), not only in RQ, so it survives Redis loss and API restarts. `interpretation.status` is separate: `not_requested`, `pending`, `completed` or `unavailable`. A failed interpretation never fails the analysis.

## 3. Retries, timeouts, cancellation
- **Retries.**
  - RQ default: none.
  - A `failed` analysis with `failure.retryable = true` (`MODEL_UNAVAILABLE`) can be resubmitted with the same idempotency key once a provider is back.
  - Within a job, the router falls back across providers (H-2) instead of retrying the same one.
- **Timeouts.**
  - RQ job timeout: the RQ default of 180 s for images; `FLAME_VIDEO_JOB_TIMEOUT_S` (default 3600 s) for video.
  - Provider timeouts: `FLAME_CV_TIMEOUT_S`, `FLAME_LLM_TIMEOUT_S`, `FLAME_AURA_TIMEOUT_S`.
- **Cancellation (ADR-008).** `POST /api/analyses/{id}/cancel`, write scope, never from AURA:
  - `queued` → `cancelled` at once (200). The RQ job may still run, and does nothing, because the worker only starts `queued` rows.
  - `processing` → `analysis_result.cancel_requested_at` is set and the response is 202 with status still `processing`. A video job stops at its next checkpoint segment; an image job (seconds long) stops before storing its result. Either way it ends `cancelled` with `failure.code = CANCELLED`, no result, no evidence row and no checkpoint.
  - already `cancelled` → 200 (idempotent); `completed` or `failed` → 409 `ANALYSIS_NOT_CANCELLABLE`.
  - Every status change is made on the locked row (`SELECT … FOR UPDATE` in PostgreSQL), so a cancel cannot be lost between the worker's read and its commit.

## 4. Failure reporting
- `analysis_result.payload.failure = {code, message, retryable}`, with codes `MODEL_UNAVAILABLE`, `IMAGE_DECODE_FAILED`, `VIDEO_DECODE_FAILED`, `PIPELINE_ERROR` and `CANCELLED`. A failure never overwrites a terminal state. Exceptions are logged with `analysis_id`.
- Ingestion: quarantine and `ingestion_run` rows with `transformation_id = "quarantine"` (E2-2).

## 5. Restart behaviour (2H scenario S9)
- **Stuck-job recovery (P2-4).** If the worker dies mid-job, the RQ job is lost but the row stays `processing`, and `process_*` only start from `queued`. `python -m flame_api.worker recover [--older-than SECONDS]` (run by the worker's start command in Compose and `.railway/railway.py`) handles this:
  - it finds `processing` rows older than the job timeout + 60 s (image: RQ's default 180 s; video: `FLAME_VIDEO_JOB_TIMEOUT_S`), and `queued` rows older than 60 s with no live RQ job;
  - it resets each to `queued`, appends a `JOB_RECOVERED` warning (the attempt counter is the number of these warnings), and re-enqueues the same job function with the same timeout;
  - after 3 re-queues it marks the row `failed` with `PIPELINE_ERROR`, `retryable: false`;
  - a stuck row with a cancel request is marked `cancelled` instead of being re-queued.
  - Each row is claimed with `UPDATE … WHERE status = :read AND updated_at = :read`, so concurrent recoverers act on it once, and a re-run is a no-op.
  - It runs once at worker start only: a worker that restarts within the timeout leaves the row for the next run (see RUNBOOK §7).
- **Video jobs resume from their last segment (ADR-008).** The CV pipeline still writes its `frames.jsonl` checkpoint into a scratch directory that dies with the process. PostgreSQL holds the durable copy:
  - every `FLAME_VIDEO_CHECKPOINT_EVERY_FRAMES` sampled frames (default 10), the worker's `VideoCheckpoint` hook writes the new rows to `video_checkpoint_frame`, the job's `progress` (`frames_done`, `frames_total`, `checkpointed_at`) and `updated_at`, in one transaction on the locked analysis row, then checks for a cancel request;
  - a re-queued job loads those rows, `cv.video_analysis.seed_checkpoint` writes them back into the new scratch directory, and the pipeline measures only the missing frames; the result is identical to an uninterrupted run (tested frame for frame) and carries a `JOB_RESUMED_FROM_CHECKPOINT` warning;
  - the rows carry the job digest (video checksum, pipeline versions, sampling); rows from another digest are discarded and the job starts over;
  - a crash loses at most one segment; the rows are deleted when the analysis completes, fails or is cancelled;
  - because each segment refreshes `updated_at`, recovery treats a job as stuck only once it has made no progress for the job timeout + 60 s; a run that finds its row no longer `processing` (re-queued or cancelled) stops at its next segment without writing.
- **Ingestion and index build** are resumable by construction: stable IDs and `merge`, and "embed only missing".

## 6. Admin "System Operations" module (Belal, B9)

The module shows:
- queue depth: `/api/health` `cv_model.message`;
- jobs by status: `GET /api/analyses?status=queued&status=processing&status=failed`;
- the last `ingestion_run` rows and quarantined files (an admin endpoint is planned, E2-8);
- provider health and circuits: `GET /api/ai/providers`.

## Known limitations
Recovery runs at worker start (or by hand), not on a schedule. Image jobs are not checkpointed (they take seconds) and are re-run whole. A cancel stops a video job at the next segment boundary, so up to one segment of work is done after the request. An RQ timeout (`JobTimeoutException`) marks a video job `failed`, not resumable: only a dead worker leaves the row for recovery.

## Changelog
- 1.1.0 (2026-11-12): ADR-008 built: video checkpoints in PostgreSQL per segment, resume after recovery, progress, and cancellation (`POST /api/analyses/{id}/cancel`).
- Unreleased (P2-4): stuck-job recovery (`worker recover`), and a note that video jobs do not resume.
- 1.0.0 (2026-10-12): documents the MVP job system plus the Phase 2 router integration.
