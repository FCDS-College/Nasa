# Implementation changelog (2026-10-30 audit follow-up)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas), changes by Claude Code | Current | 1.0.0 | 2026-10-30 | see the roadmap IDs | listed below |

Branch `claude/nasa-flame-aura-audit-abu89q`, based on `main` @ `7340782`. Task IDs refer to [IMPLEMENTATION_ROADMAP.md](../plan/IMPLEMENTATION_ROADMAP.md).

## Stage A: critical corrections

| ID | Change | Files |
|---|---|---|
| P0-1 | Exclude the reviewed external drop `tests/eval/Ziad____10/` from pytest (`--ignore`) and ruff (`extend-exclude`). CI was red on `main`. | `pytest.ini`, `ruff.toml` |
| P0-2 | `next` / `eslint-config-next` 16.3.8 → 16.4.3 (critical RCE advisories) | `apps/web/package.json`, `apps/web/package-lock.json` |
| P0-3 | `pillow` `>=10,<13` → `>=13,<14` (39 CVEs in 12.x) | `apps/api/pyproject.toml`, `cv/hf_space/requirements.txt`, `requirements.txt` |

## Stage B: integration (Link 1 and contract)

| ID | Change | Files |
|---|---|---|
| P1-2 | A 422 whose body is AURA's `{"error":"output_invalid"}` maps to `INVALID_OUTPUT`, so the router falls back to another model. Other 422s stay `INVALID_REQUEST`. | `ai/providers/http.py` |
| P1-3 | The AURA `Idempotency-Key` is `<analysis_or_request_id>:<sha256(body)[:16]>`; `X-Correlation-Id` stays the bare ID. `context[].text` is capped at AURA's 2000-char limit. | `ai/providers/cloud/aura.py` |
| I7 | `meta.api_version` = contract `info.version` (was 0.1.0 against contract 0.2.0) | `apps/api/flame_api/contracts.py`, `apps/api/tests/test_health.py` |
| I8 | 405 returns `METHOD_NOT_ALLOWED` (was `INTERNAL_ERROR`) and keeps the `Allow` header | `apps/api/flame_api/main.py` |

## Stage C: core AI (video)

| ID | Change | Files |
|---|---|---|
| P1-1 | `POST /api/analyses` accepts `video` (exactly one of `image`/`video`), with `sample_every_n_frames` (default 30) and `max_frames` (default 300, ≤ `FLAME_MAX_VIDEO_FRAMES`). The upload is spooled to disk in 1 MiB chunks under `FLAME_MAX_VIDEO_UPLOAD_BYTES` (200 MiB), the container is sniffed from the bytes (ISO-BMFF `ftyp` / RIFF AVI), and the video is probed with `cv.video_ingestion.probe_video` in a thread pool (codec, fps, VFR, duration ≤ 600 s). It is stored as the `original` artifact and queued as `flame_api.worker.process_video_analysis` with `job_timeout = FLAME_VIDEO_JOB_TIMEOUT_S`. Calibration and interpretation are refused or marked unavailable for video, so no physical claims are implied. | `apps/api/flame_api/analysis.py`, `apps/api/flame_api/config.py` |
| P1-1 | Worker: `process_video_analysis` routes `video.analyze` (local `flame_cv_video`), maps frames in time order, maps the temporal summary, adds a `video_measurement` evidence record, and links the observation to it. When sampled frames are further apart than the 0.5 s tracking gap, `track_sessions` and `tracking_stability_px2` are `null` with a `tracking_note`. Failures become `VIDEO_DECODE_FAILED` (not retryable) or `MODEL_UNAVAILABLE`. The shared `_store_and_enqueue` is reused by the image path. | `apps/api/flame_api/worker.py`, `apps/api/flame_api/analysis.py` |
| P1-5 | Interpretation runs after the CV result is committed. Any unexpected error stores interpretation `unavailable` and never marks the analysis failed. | `apps/api/flame_api/worker.py` |
| — | `AnalysisSummary.analysis_type` comes from the stored analysis | `apps/api/flame_api/analysis.py` |

## Stage F: quality, honesty, documentation

| ID | Change | Files |
|---|---|---|
| P1-4 | The Knowledge page no longer shows mock entities, "Verified" badges or fake citations; it says the graph is not available | `apps/web/lib/api/client.ts`, `apps/web/app/knowledge/page.tsx` |
| — | The Analysis Studio picks the newest completed **image** analysis (it renders image overlays) | `apps/web/lib/api/client.ts` |
| R4 | API tests no longer read the persisted AI mode from a developer's real Postgres (15 false failures when one was running) | `apps/api/tests/conftest.py` |
| — | Audit and integration documents | `docs/reviews/SYSTEM_STATUS_AUDIT.md`, `docs/reviews/FINAL_SYSTEM_READINESS_REPORT.md`, this file, `docs/integration/AURA_INTEGRATION_AUDIT.md`, `docs/integration/API_INTEGRATION_REFERENCE.md`, `docs/plan/IMPLEMENTATION_ROADMAP.md`; index and status pointers updated |

## API changes (contract 0.2.0 → 0.3.0, additive)

See [docs/api/CHANGELOG.md](../api/CHANGELOG.md#030-2026-10-30).
- New schemas: `VideoInput`, `VideoFrameMeasurement`, `VideoTemporalSummary`, `FlameVideoAnalysisResult`.
- Enum additions: `AnalysisType.flame_video`, `EvidenceKind.video_measurement`, `AnalysisFailureCode.VIDEO_DECODE_FAILED`, `ErrorCode.VIDEO_INVALID`/`METHOD_NOT_ALLOWED`, video media types on `AnalysisInput` and `Artifact`.
- `AnalysisCreateForm`: `image` is no longer required on its own; `oneOf` image/video.
- `API_SCHEMAS.md` regenerated. The AURA dry run (HEAD `6417c43`) still compiles 10 tools and excludes 3.

**Database migrations:** none. Video analyses use the existing `analysis_result` table: `analysis_type` lives in `payload`, and `image_sha256` holds the video's SHA-256, as documented in the contract.

**Architecture decisions:** ADR-005 is followed as written (one `/api/analyses` resource). Video stays local-only (`flame_cv_video`), consistent with the dependency audit.

## Tests

New file `apps/api/tests/test_video_analysis.py` with 8 tests:
- Upload probe and queue, using a real ffmpeg-encoded H.264 clip.
- Six rejection paths.
- A real worker run checking time order, temporal summary, evidence and contract validity.
- Tracking marked not estimable when sampling is too sparse.
- A provider rejection mapped to `VIDEO_DECODE_FAILED`.
- An interpretation crash leaving the image analysis completed.
- 405 returns `METHOD_NOT_ALLOWED`.

Two new tests in `test_aura_integration.py`; one updated assertion (idempotency key format). The video tests skip when ffmpeg/libx264 is absent.

Final results: see the [readiness report §7](FINAL_SYSTEM_READINESS_REPORT.md#7-test-and-build-results).

## Remaining work

The open roadmap items are P1-6, P1-7, P1-8 and all of P2 and P3. Each one names its blocker in the roadmap.

## 2026-11-02: roadmap P2

Contract 0.3.0 → 0.4.0 ([docs/api/CHANGELOG.md](../api/CHANGELOG.md)). Migrations `0005_api_clients`, `0006_experiment_ingested_at`, `0007_chunk_search_tsv` (all reversible; upgrade → downgrade → upgrade checked on PostgreSQL 16 + pgvector). Per-item status and what stays open: [roadmap, P2 status](../plan/IMPLEMENTATION_ROADMAP.md#p2-status-2026-11-02).

| Items | Change | Main files |
|---|---|---|
| P2-1, P2-2, P2-6 | Per-client hashed API keys with scopes and a CLI; per-client Redis rate limits on every authenticated route; production refuses local default secrets | `flame_api/clients.py`, `flame_api/rate_limit.py`, `flame_api/main.py`, `flame_api/config.py`, `docs/operations/SECURITY.md` |
| P2-3 | Search ranks and caps lexical candidates in SQL; PostgreSQL uses a stored, GIN-indexed `search_tsv` | `flame_api/main.py`, `migrations/versions/0007_chunk_search_tsv.py` |
| P2-4, P2-5 | Stuck-job recovery command, run at worker start; `mode_source` / `env_mode` | `flame_api/worker.py`, `flame_api/ai_runtime.py`, `infrastructure/compose.yaml`, `.railway/railway.py` |
| P2-8 | Audited admin endpoints; rejected evidence excluded from search and chat; re-ingest keeps reviews | `flame_api/admin.py`, `flame_api/ingest.py`, `docs/data/ADMIN_DATA_OPERATIONS.md` |
| P2-9, P2-10 | Real experiment `ingested_at`; evidence-based document/experiment links; `chunks` / `indexed_chunks` | `flame_api/models.py`, `migrations/versions/0006_experiment_ingested_at.py`, `apps/web/lib/api/client.ts` |
| P2-11 | Backup and restore scripts; local restore drill | `infrastructure/backup/`, `docs/operations/RUNBOOK.md`, `docs/data/OFFLINE_DATA_AND_SYNC.md` |

Tests: `python -m pytest` 368 passed, 7 skipped (one opt-in real-Redis test); `ruff check .` clean; `render_api_schemas.py --check` current; web lint (0 errors), typecheck and build pass; AURA dry run against `d696fad`: 10 tools ACCEPTED, 8 operations excluded (the 3 before plus the 5 admin routes).

