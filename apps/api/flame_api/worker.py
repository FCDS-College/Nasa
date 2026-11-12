import hashlib
import json
import logging
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from redis import Redis
from rq import Queue
from sqlalchemy import delete, select, update

from flame_api.config import get_settings
from flame_api.database import SessionLocal
from ai.providers.contracts.errors import ProviderError
from ai.providers.contracts.vision import ImageAnalysisRequest
from ai.routing import NoCompatibleProvider
from flame_api import ai_runtime
from flame_api.generation import interpret_analysis
from flame_api.ids import stable_ulid
from flame_api.models import AnalysisRecord, EvidenceRecord, ExperimentCondition, FileRecord, VideoCheckpointFrame
from flame_api.storage import get_bytes, put_file

settings = get_settings()
logger = logging.getLogger("flame_worker")
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _now():
    return datetime.now(UTC)


CANCEL_MESSAGE = "The analysis was cancelled on request."
RESUME_WARNING = "JOB_RESUMED_FROM_CHECKPOINT"


class JobCancelled(Exception):
    """Raised at a checkpoint when the analysis has a cancel request (ADR-008)."""


class JobSuperseded(Exception):
    """Raised at a checkpoint when the row is no longer `processing` for this run (recovered or cancelled)."""


def _cancelled_values(record: AnalysisRecord, now: datetime) -> None:
    """Mark the locked record cancelled; the caller commits. `failure` is non-null for cancelled (contract)."""
    stamp = _iso(now)
    record.status = "cancelled"
    record.updated_at = now
    record.completed_at = now
    record.payload = {
        **record.payload, "status": "cancelled", "updated_at": stamp, "completed_at": stamp, "poll_after_ms": None,
        "failure": {"code": "CANCELLED", "message": CANCEL_MESSAGE, "retryable": False},
        "cancel_requested_at": _iso(_aware(record.cancel_requested_at)) if record.cancel_requested_at else None,
    }


def _drop_checkpoint(session, analysis_id: str) -> None:
    session.execute(delete(VideoCheckpointFrame).where(VideoCheckpointFrame.analysis_id == analysis_id))


def _finish_cancelled(analysis_id: str) -> None:
    session = SessionLocal()
    try:
        record = session.get(AnalysisRecord, analysis_id, with_for_update=True)
        if record is not None and record.status == "processing":
            _cancelled_values(record, _now())
        _drop_checkpoint(session, analysis_id)
        session.commit()
    finally:
        session.close()
    logger.info("analysis_id=%s cancelled", analysis_id)


def _load_checkpoint(analysis_id: str) -> dict | None:
    """The frames a previous run of this job stored, as `VideoAnalysisRequest.resume_from`, or None."""
    session = SessionLocal()
    try:
        rows = list(session.scalars(select(VideoCheckpointFrame).where(VideoCheckpointFrame.analysis_id == analysis_id)
                                    .order_by(VideoCheckpointFrame.created_at, VideoCheckpointFrame.frame_index)))
    finally:
        session.close()
    if not rows:
        return None
    latest = rows[-1]   # one job has one digest; should it ever change, the newest run wins
    kept = sorted((r for r in rows if r.job_digest == latest.job_digest), key=lambda r: r.frame_index)
    return {"video_id": latest.video_id, "digest": latest.job_digest, "rows": [dict(r.row) for r in kept]}


class VideoCheckpoint:
    """The `on_frame` hook of a video job: stores measured frames one segment at a time (ADR-008).

    Each flush writes the segment's rows, the job's progress and `updated_at` in one transaction on
    the locked analysis row, then honours a cancel request. A crash loses at most one segment, and
    `worker.recover` re-queues the job, which resumes from the stored rows.
    """

    def __init__(self, analysis_id: str, every: int) -> None:
        self.analysis_id = analysis_id
        self.every = every
        self.pending: list[dict] = []
        self.resumed: int | None = None
        self.done = 0
        self.total = 0

    def __call__(self, event: dict) -> None:
        self.video_id, self.digest = event["videoId"], event["digest"]
        self.done, self.total = event["done"], event["total"]
        if event["event"] == "start":
            self.resumed = event["done"]
            self.flush()
            return
        self.pending.append(event["row"])
        if len(self.pending) >= self.every or self.done >= self.total:
            self.flush()

    def flush(self) -> None:
        session = SessionLocal()
        try:
            record = session.get(AnalysisRecord, self.analysis_id, with_for_update=True)
            if record is None or record.status != "processing":
                raise JobSuperseded()
            now = _now()
            for row in self.pending:
                session.merge(VideoCheckpointFrame(
                    analysis_id=self.analysis_id, frame_index=row["frameIndex"], video_id=self.video_id,
                    job_digest=self.digest, row=row, created_at=now,
                ))
            record.updated_at = now
            record.payload = {**record.payload, "updated_at": _iso(now), "progress": {
                "frames_done": self.done, "frames_total": self.total, "checkpointed_at": _iso(now)}}
            cancel = record.cancel_requested_at is not None
            session.commit()
            self.pending = []
        finally:
            session.close()
        if cancel:
            raise JobCancelled()


def process_analysis(analysis_id: str) -> None:
    session = SessionLocal()
    # Locked, so a cancel (POST /api/analyses/{id}/cancel) cannot land between this read and the commit.
    record = session.get(AnalysisRecord, analysis_id, with_for_update=True)
    if record is None or record.status != "queued":
        session.close()
        return
    record.status = "processing"
    record.updated_at = _now()
    record.payload = {**record.payload, "status": "processing", "updated_at": record.updated_at.isoformat().replace("+00:00", "Z"), "started_at": record.updated_at.isoformat().replace("+00:00", "Z"), "poll_after_ms": 1000}
    session.commit()
    payload = dict(record.payload)
    artifacts = dict(record.artifacts)
    session.close()

    aura_request = None
    try:
        import cv2  # noqa: F401  (fail fast with MODEL_UNAVAILABLE when OpenCV is missing)

        input_data = payload["input"]
        original = artifacts["original"]
        image_bytes = get_bytes(original["object_key"])
        with tempfile.TemporaryDirectory(prefix="flame-cv-") as working:
            work = Path(working)
            suffix = ".png" if input_data["media_type"] == "image/png" else ".jpg"
            image_path = work / f"original{suffix}"
            image_path.write_bytes(image_bytes)
            calibration = input_data["calibration"]
            mm_per_pixel = 1 / calibration["scale_px_per_mm"] if calibration["scale_px_per_mm"] else None
            # Vision goes through the router: FLAME_CV_PROVIDER picks the preferred provider, the other
            # is the fallback, offline_only never contacts the HF Space, and no text model is eligible.
            request = ImageAnalysisRequest(
                image_path=image_path, image_id=analysis_id, media_type=input_data["media_type"], work_dir=work,
                mm_per_pixel=mm_per_pixel, max_pixels=settings.max_image_pixels,
            )
            routed_cv = ai_runtime.get_router(settings).route("vision.analyze", lambda provider: provider.analyze_image(request))
            legacy = routed_cv.value.analysis
            cv_execution = routed_cv.metadata.to_dict()
            result = _adapt_result(legacy, input_data, work)
            produced = []
            preprocessing_path = Path(legacy["preprocessing"]["derivedUri"])
            if preprocessing_path.exists():
                produced.append(("preprocessed", preprocessing_path, "image/png"))
            for kind, uri in (("mask", legacy["segmentation"].get("maskUri")), ("overlay", legacy["segmentation"].get("overlayArtifactUri"))):
                if uri and Path(uri).exists():
                    produced.append((kind, Path(uri), "image/png"))
            for kind, path, media_type in produced:
                key = f"analyses/{analysis_id}/{kind}.png"
                put_file(key, str(path), media_type)
                file_bytes = path.read_bytes()
                with Image.open(path) as artifact_image:
                    artifact_width, artifact_height = artifact_image.size
                artifact = {
                    "kind": kind,
                    "url": f"/api/analyses/{analysis_id}/artifacts/{kind}",
                    "media_type": media_type,
                    "sha256": hashlib.sha256(file_bytes).hexdigest(),
                    "width": artifact_width,
                    "height": artifact_height,
                    "size_bytes": len(file_bytes),
                    "object_key": key,
                }
                artifacts[kind] = artifact

        now = _now()
        session = SessionLocal()
        record = session.get(AnalysisRecord, analysis_id, with_for_update=True)
        if record is not None and record.status != "processing":
            record = None   # recovered or cancelled meanwhile: this run's result is not stored
        elif record is not None and record.cancel_requested_at is not None:
            _cancelled_values(record, now)
            session.commit()
            record = None
        if record:
            completed = {
                **record.payload,
                "status": "completed",
                "updated_at": now.isoformat().replace("+00:00", "Z"),
                "completed_at": now.isoformat().replace("+00:00", "Z"),
                "pipeline": {**result["pipeline"], "execution": cv_execution},
                "result": result["result"],
                # Keep the recovery history (P2-4) so a re-run analysis says it was re-queued.
                "warnings": [*_recovery_warnings(record.payload), *result["warnings"]],
                "artifacts": [{key: value for key, value in item.items() if key != "object_key"} for item in artifacts.values()],
                "poll_after_ms": None,
            }
            measurement_evidence = _image_measurement_evidence(
                session, record, result, input_data, now
            )
            result["result"]["observations"] = [
                {
                    **observation,
                    "evidence_ids": list(
                        dict.fromkeys(
                            [*observation.get("evidence_ids", []), measurement_evidence.evidence_id]
                        )
                    ),
                }
                for observation in result["result"]["observations"]
            ]
            completed["result"] = result["result"]
            record.status = "completed"
            record.updated_at = now
            record.completed_at = now
            record.pipeline_version = result["pipeline"]["pipeline_version"]
            record.payload = completed
            record.artifacts = artifacts
            session.add(measurement_evidence)
            if completed["interpretation"]["status"] == "pending":
                aura_request = _aura_request_context(session, record, measurement_evidence)
            session.commit()
        session.close()
    except Exception as exc:
        decode_code = "IMAGE_DECODE_FAILED" if isinstance(exc, (OSError, ValueError)) else "PIPELINE_ERROR"
        _mark_failed(analysis_id, exc, decode_code, "Image analysis could not be completed.")
        raise
    # Outside the CV try: the analysis is already committed as completed, so an interpretation
    # problem must never turn it into a failed one (interpretation is optional and separate).
    if aura_request is not None:
        try:
            _run_aura_interpretation(analysis_id, aura_request["context"], aura_request["evidence_ids"])
        except Exception:
            logger.exception("analysis_id=%s interpretation_error", analysis_id)
            _store_interpretation(analysis_id, _UNAVAILABLE_INTERPRETATION, warning=True)


_UNAVAILABLE_INTERPRETATION = {
    "status": "unavailable", "provider": None, "model": None, "statements": [], "rejected_statement_count": 0, "generated_at": None,
}


def _mark_failed(analysis_id: str, exc: Exception, decode_code: str, message: str) -> None:
    session = SessionLocal()
    try:
        record = session.get(AnalysisRecord, analysis_id, with_for_update=True)
        if record and record.status in {"queued", "processing"}:
            now = _now()
            failure_code = "MODEL_UNAVAILABLE" if isinstance(exc, (ImportError, ProviderError, NoCompatibleProvider)) else decode_code
            cause = exc.last_error if isinstance(exc, NoCompatibleProvider) else exc
            if isinstance(cause, ProviderError) and cause.code.value == "invalid_request":
                failure_code = decode_code   # the provider rejected the media itself; retrying will not help
            record.status = "failed"
            record.updated_at = now
            record.completed_at = now
            record.payload = {
                **record.payload,
                "status": "failed",
                "updated_at": now.isoformat().replace("+00:00", "Z"),
                "completed_at": now.isoformat().replace("+00:00", "Z"),
                "failure": {"code": failure_code, "message": message, "retryable": failure_code == "MODEL_UNAVAILABLE"},
                "poll_after_ms": None,
            }
            _drop_checkpoint(session, analysis_id)
            session.commit()
    finally:
        session.close()


def process_video_analysis(analysis_id: str) -> None:
    """flame_video (ADR-005): sampled frames through the routed local video provider, then a temporal summary."""
    from ai.providers.contracts.video import VideoAnalysisRequest

    session = SessionLocal()
    # Locked, so a cancel (POST /api/analyses/{id}/cancel) cannot land between this read and the commit.
    record = session.get(AnalysisRecord, analysis_id, with_for_update=True)
    if record is None or record.status != "queued":
        session.close()
        return
    started = _now()
    record.status = "processing"
    record.updated_at = started
    record.payload = {**record.payload, "status": "processing", "updated_at": _iso(started), "started_at": _iso(started),
                      "poll_after_ms": 2000}
    session.commit()
    payload = dict(record.payload)
    original = dict(record.artifacts["original"])
    session.close()

    checkpoint = VideoCheckpoint(analysis_id, settings.video_checkpoint_every_frames)
    try:
        video_input = payload["input"]["video"]
        with tempfile.TemporaryDirectory(prefix="flame-video-") as working:
            work = Path(working)
            video_path = work / f"original.{video_input['container']}"
            video_path.write_bytes(get_bytes(original["object_key"]))
            # The scratch directory dies with the process; the checkpoint lives in PostgreSQL (ADR-008).
            request = VideoAnalysisRequest(
                video_path=video_path, video_id=analysis_id, work_dir=work / "job",
                sample_every_n_frames=video_input["sample_every_n_frames"], max_frames=video_input["max_frames"],
                resume_from=_load_checkpoint(analysis_id), on_frame=checkpoint,
            )
            routed = ai_runtime.get_router(settings).route("video.analyze", lambda provider: provider.analyze_video(request))
        response = routed.value
        result, pipeline, warnings = _adapt_video_result(response, video_input)
    except JobCancelled:
        _finish_cancelled(analysis_id)
        return
    except JobSuperseded:
        logger.warning("analysis_id=%s video_run_superseded at=%s/%s", analysis_id, checkpoint.done, checkpoint.total)
        return
    except Exception as exc:
        _mark_failed(analysis_id, exc, "VIDEO_DECODE_FAILED", "Video analysis could not be completed.")
        raise
    if checkpoint.resumed:
        warnings.append({"code": RESUME_WARNING, "severity": "info",
                         "message": f"Resumed from a checkpoint: {checkpoint.resumed} of {checkpoint.total} sampled "
                                    "frames were measured before the job was interrupted."})

    now = _now()
    session = SessionLocal()
    try:
        record = session.get(AnalysisRecord, analysis_id, with_for_update=True)
        if record is None or record.status != "processing":
            return   # recovered or cancelled meanwhile
        if record.cancel_requested_at is not None:
            _cancelled_values(record, now)
            _drop_checkpoint(session, analysis_id)
            session.commit()
            return
        evidence = _video_measurement_evidence(session, record, payload["input"], pipeline["pipeline_version"], result, now)
        for observation in result["observations"]:
            observation["evidence_ids"] = [evidence.evidence_id]
        record.status = "completed"
        record.updated_at = now
        record.completed_at = now
        record.pipeline_version = pipeline["pipeline_version"]
        record.payload = {
            **record.payload,
            "status": "completed",
            "updated_at": _iso(now),
            "completed_at": _iso(now),
            "pipeline": {**pipeline, "execution": routed.metadata.to_dict()},
            "result": result,
            "warnings": [*record.payload.get("warnings", []), *warnings],
            "poll_after_ms": None,
        }
        session.add(evidence)
        _drop_checkpoint(session, analysis_id)
        session.commit()
    finally:
        session.close()


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _video_frame(row: dict) -> dict:
    centroid = row.get("centroid") or None
    status = str(row.get("detectionStatus", "UNCERTAIN")).lower()
    return {
        "frame_index": row["frameIndex"],
        "source_frame_index": row.get("sourceFrameIndex"),
        "timestamp_s": row["timestamp"],
        "source_timestamp_s": row.get("sourceTimestamp"),
        "detection_status": status if status in {"present", "absent", "uncertain"} else "uncertain",
        "detection_confidence": row.get("detectionConfidence"),
        "pixel_area": row.get("pixelArea"),
        "centroid": {"x": centroid["x"], "y": centroid["y"]} if centroid else None,
        "error_code": (row.get("error") or {}).get("code"),
    }


def _adapt_video_result(response, video_input):
    summary = response.summary or {}
    temporal = summary.get("temporalSummary") or {}
    metadata = summary.get("videoMetadata") or {}
    frames = [_video_frame(row) for row in response.frames]
    present = sum(frame["detection_status"] == "present" for frame in frames)
    errors = sum(frame["error_code"] is not None for frame in frames)
    flicker = temporal.get("flickerFrequencyHz")
    area_rate = temporal.get("areaChangeRate") or {}
    stability = temporal.get("trackingStability") or {}
    width, height = (metadata.get("resolution") or [None, None])[:2]
    # cv/temporal_analysis.py starts a new track after a gap > max_gap_s, so when sampled frames are
    # further apart than that every frame is its own "session" (docs/cv/temporal-analysis.md). Report
    # tracking as not estimable instead of publishing those numbers.
    from cv.temporal_analysis import TemporalConfig

    fps = metadata.get("fps") or video_input["fps"]
    interval_s = video_input["sample_every_n_frames"] / fps if fps else None
    max_gap_s = TemporalConfig().max_gap_s
    tracking_ok = interval_s is not None and interval_s <= max_gap_s
    result = {
        "video": {
            "fps": metadata.get("fps", video_input["fps"]),
            "frame_count": metadata.get("frameCount", video_input["frame_count"]),
            "duration_seconds": metadata.get("durationSeconds", video_input["duration_seconds"]),
            "width": width,
            "height": height,
        },
        "sampling": {
            "sample_every_n_frames": video_input["sample_every_n_frames"],
            "max_frames": video_input["max_frames"],
            "frames_analyzed": len(frames),
            "frames_with_errors": errors,
        },
        "frames": frames,
        "temporal_summary": {
            "persistence_rate": temporal.get("persistenceRate"),
            "flicker_frequency_hz": flicker if isinstance(flicker, (int, float)) else None,
            "flicker_status": "estimated" if temporal.get("flickerStatus") == "ESTIMATED" else "not_estimable",
            "flicker_note": temporal.get("flickerNote"),
            "area_change_rate_px2_per_s": {"mean_abs": area_rate.get("meanAbs"), "max_abs": area_rate.get("maxAbs"),
                                           "pairs": area_rate.get("pairs", 0)},
            "tracking_stability_px2": stability.get("value") if tracking_ok else None,
            "track_sessions": temporal.get("trackSessions", 0) if tracking_ok else None,
            "tracking_note": None if tracking_ok else (
                f"Sampling interval {interval_s:.3f} s exceeds the {max_gap_s} s tracking gap, so tracking is not estimable; "
                "sample more densely (smaller sample_every_n_frames) to track the flame."
            ),
            "classification": "measured",
            "method": "cv/temporal_analysis.py summarize() over sampled per-frame CV detections",
        },
        "observations": [{
            "statement_id": "cv-video-persistence",
            "text": f"Brightness-based CV detected a flame in {present} of {len(frames)} sampled frames.",
            "claim_class": "measured",
            "origin": "cv_pipeline",
            "evidence_ids": [],
            "measurement_refs": ["temporal_summary/persistence_rate"],
        }],
    }
    pipeline = {
        "pipeline_version": response.pipeline_version or "unknown",
        "preprocessing_version": (response.pipeline_version or "unknown").split("+")[-1],
        "detector": None,
        "segmenter": None,
        "measurement_space": "original_oriented_px",
    }
    warnings = [
        {"code": "TEMPERATURE_NOT_AVAILABLE", "severity": "info", "message": "Temperature is not reported without radiometric calibration."},
        {"code": "SCALE_CALIBRATION_ABSENT", "severity": "warning", "message": "Video measurements are in pixels; no scale calibration was supplied."},
    ]
    if present:
        warnings.append({"code": "LOW_DETECTION_CONFIDENCE", "severity": "warning",
                         "message": "Brightness-based detection is heuristic; per-frame results are not validated against labels."})
    return result, pipeline, warnings


def _video_measurement_evidence(session, record, input_data, pipeline_version, result, now):
    source_file = session.get(FileRecord, input_data["source_file_id"]) if input_data.get("source_file_id") else None
    sampling = result["sampling"]
    return EvidenceRecord(
        evidence_id=stable_ulid(f"video-measurement:{record.analysis_id}:{pipeline_version}"),
        source_id=source_file.source_id if source_file else None,
        file_id=source_file.file_id if source_file else None,
        document_id=None,
        experiment_id=record.experiment_id,
        analysis_id=record.analysis_id,
        kind="video_measurement",
        origin="calculated_measurement",
        excerpt=None,
        locator={"type": "file", "page": None, "section": None, "row": None, "frame_index": None,
                 "label": f"video analysis {record.analysis_id} ({sampling['frames_analyzed']} sampled frames)"},
        payload={
            "citation": f"Flame CV video analysis {record.analysis_id}, video SHA-256 {record.image_sha256}",
            "value": None,
            "measurement_or_claim_type": "flame_video_temporal_measurements",
            "extraction_method": "cv_pipeline",
            "extraction_confidence": None,
            "review_status": "machine_extracted",
            "transformation_id": pipeline_version,
            "knowledge_version": None,
        },
        created_at=now,
    )


def _image_measurement_evidence(session, record, result, input_data, now):
    source_file = (
        session.get(FileRecord, input_data["source_file_id"])
        if input_data.get("source_file_id")
        else None
    )
    evidence_id = stable_ulid(
        f"image-measurement:{record.analysis_id}:{result['pipeline']['pipeline_version']}"
    )
    citation = f"Flame CV analysis {record.analysis_id}, image SHA-256 {record.image_sha256}"
    frame_index = input_data.get("frame_index")
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_id=source_file.source_id if source_file else None,
        file_id=source_file.file_id if source_file else None,
        document_id=None,
        experiment_id=record.experiment_id,
        analysis_id=record.analysis_id,
        kind="image_measurement",
        origin="calculated_measurement",
        excerpt=None,
        locator={
            "type": "frame" if frame_index is not None else "file",
            "page": None,
            "section": None,
            "row": None,
            "frame_index": frame_index,
            "label": f"image analysis {record.analysis_id}",
        },
        payload={
            "citation": citation,
            "value": None,
            "measurement_or_claim_type": "flame_image_measurements",
            "extraction_method": "cv_pipeline",
            "extraction_confidence": None,
            "review_status": "machine_extracted",
            "transformation_id": result["pipeline"]["pipeline_version"],
            "knowledge_version": None,
        },
        created_at=now,
    )


def _aura_request_context(session, record, measurement_evidence):
    result = record.payload.get("result") or {}
    context = [
        {
            "id": measurement_evidence.evidence_id,
            "source": "flame/image_measurement",
            "text": json.dumps(
                {
                    "analysis_id": record.analysis_id,
                    "evidence_id": measurement_evidence.evidence_id,
                    "image_sha256": record.image_sha256,
                    "pipeline_version": (record.payload.get("pipeline") or {}).get(
                        "pipeline_version"
                    ),
                    "detection": (result.get("detection") or {}).get("status"),
                    "measurements": _measurement_summary(result.get("measurements") or {}),
                    "quality_flags": result.get("quality_flags") or {},
                },
                separators=(",", ":"),
                allow_nan=False,
            ),
        }
    ]
    evidence_ids = {measurement_evidence.evidence_id}
    if record.experiment_id is None:
        return {"context": context, "evidence_ids": evidence_ids}

    conditions = (
        session.query(ExperimentCondition)
        .filter(ExperimentCondition.experiment_id == record.experiment_id)
        .limit(15)
        .all()
    )
    condition_ids = {condition.evidence_id for condition in conditions}
    evidence = (
        session.query(EvidenceRecord)
        .filter(EvidenceRecord.evidence_id.in_(condition_ids))
        .all()
        if condition_ids
        else []
    )
    evidence_by_id = {item.evidence_id: item for item in evidence}
    for condition in conditions:
        source_evidence = evidence_by_id.get(condition.evidence_id)
        if source_evidence is None:
            continue
        context.append(
            {
                "id": source_evidence.evidence_id,
                "source": "flame/source_evidence",
                "text": source_evidence.excerpt
                or f"{condition.variable}: "
                + str(
                    condition.value_numeric
                    if condition.value_numeric is not None
                    else condition.value_text
                ),
            }
        )
        context[-1]["text"] = context[-1]["text"][:2000]
        evidence_ids.add(source_evidence.evidence_id)
    return {"context": context, "evidence_ids": evidence_ids}


def _measurement_summary(measurements):
    summary = {}
    for group_name, group in measurements.items():
        if not isinstance(group, dict):
            continue
        values = {}
        for name, measurement in group.items():
            if not isinstance(measurement, dict):
                if name in {"color_space", "physical_interpretation"} and isinstance(
                    measurement, str
                ):
                    values[name] = measurement
                continue
            if "value" in measurement:
                values[name] = {
                    key: measurement.get(key)
                    for key in ("value", "unit", "classification")
                }
            elif "x" in measurement and "y" in measurement:
                values[name] = {
                    key: measurement.get(key)
                    for key in ("x", "y", "unit", "classification")
                }
        summary[group_name] = values
    return summary


def _store_interpretation(analysis_id, interpretation, *, warning):
    session = SessionLocal()
    record = session.get(AnalysisRecord, analysis_id)
    if record is None or record.status != "completed":
        session.close()
        return
    payload = dict(record.payload)
    payload["interpretation"] = interpretation
    if warning and not any(
        item.get("code") == "INTERPRETATION_UNAVAILABLE"
        for item in payload.get("warnings", [])
    ):
        payload.setdefault("warnings", []).append(
            {
                "code": "INTERPRETATION_UNAVAILABLE",
                "severity": "info",
                "message": "AURA interpretation was unavailable or included rejected statements.",
            }
        )
    record.payload = payload
    record.updated_at = _now()
    try:
        session.commit()
    finally:
        session.close()


def _run_aura_interpretation(analysis_id, context, evidence_ids):
    """Optional interpretation through the router (AURA, or a local model when AURA is absent or blocked)."""
    try:
        interpreted = interpret_analysis(
            ai_runtime.get_router(settings),
            analysis_id=analysis_id,
            context=context,
            allowed_evidence_ids=evidence_ids,
        )
    except (NoCompatibleProvider, ProviderError) as exc:
        logger.warning(
            "analysis_id=%s interpretation_unavailable status=%s",
            analysis_id,
            exc.status_code,
        )
        _store_interpretation(
            analysis_id,
            {
                "status": "unavailable",
                "provider": None,
                "model": None,
                "statements": [],
                "rejected_statement_count": 0,
                "generated_at": None,
            },
            warning=True,
        )
        return

    provider = interpreted["provider"]
    origin = "aura_interpretation" if provider == "aura" else "model_interpretation"
    _store_interpretation(
        analysis_id,
        {
            "status": "completed",
            "provider": provider,
            "model": interpreted["model"],
            "statements": [
                {
                    "statement_id": stable_ulid(
                        f"aura-statement:{analysis_id}:{index}:{statement['text']}"
                    ),
                    **statement,
                    "origin": origin,
                    "measurement_refs": [],
                }
                for index, statement in enumerate(interpreted["statements"])
            ],
            "rejected_statement_count": interpreted["rejected_statement_count"],
            "generated_at": interpreted["generated_at"],
            "execution": interpreted["execution"],
        },
        warning=interpreted["rejected_statement_count"] > 0,
    )


def _measured(value, unit, method, classification="measured"):
    return {"value": value, "unit": unit, "classification": classification, "method": method, "uncertainty": None}


def _adapt_result(legacy, input_data, work):
    import cv2

    detection = legacy["detection"]
    geometry = legacy["measurements"].get("geometry") or {}
    appearance = legacy["measurements"].get("appearance") or {}  # noqa: F841
    box = detection.get("boundingBox") or {}
    detected = detection["status"].lower()
    bbox = None if detected == "absent" else {"x_min": box.get("xmin"), "y_min": box.get("ymin"), "x_max": box.get("xmax"), "y_max": box.get("ymax")}
    width = (box.get("xmax", 0) - box.get("xmin", 0)) if bbox else None
    height = (box.get("ymax", 0) - box.get("ymin", 0)) if bbox else None
    area = geometry.get("pixelArea")
    perimeter = geometry.get("perimeter")
    centroid = geometry.get("centroid") or {}
    measured_geometry = {
        "area": _measured(area, "px2", "mask_pixel_count"),
        "width": _measured(width, "px", "mask_bbox"),
        "height": _measured(height, "px", "mask_bbox"),
        "perimeter": _measured(perimeter, "px", "contour_perimeter_opencv"),
        "centroid": {"x": centroid.get("x"), "y": centroid.get("y"), "unit": "px", "classification": "measured", "method": "mask_moments"},
        "aspect_ratio": _measured(height / width if width else None, "ratio", "mask_bbox_height_over_width"),
        "circularity": _measured(geometry.get("circularity"), "ratio", "contour_circularity"),
    }
    physical = None
    calibration = input_data["calibration"]
    if calibration["scale_px_per_mm"] and area is not None and width is not None and height is not None and perimeter is not None:
        mm_per_pixel = 1 / calibration["scale_px_per_mm"]
        physical = {
            "area": _measured(area * mm_per_pixel**2, "mm2", "pixel_area_scaled", "estimated"),
            "width": _measured(width * mm_per_pixel, "mm", "bbox_width_scaled", "estimated"),
            "height": _measured(height * mm_per_pixel, "mm", "bbox_height_scaled", "estimated"),
            "perimeter": _measured(perimeter * mm_per_pixel, "mm", "contour_perimeter_scaled", "estimated"),
        }
    mean_rgb: list[float | None] = [None, None, None]
    mean_intensity = None
    saturated_fraction = None
    if legacy["segmentation"].get("maskUri"):
        with Image.open(legacy["provenance"]["inputUri"]) as source_image:
            image = np.asarray(ImageOps.exif_transpose(source_image).convert("RGB"))
        mask = cv2.imread(legacy["segmentation"]["maskUri"], cv2.IMREAD_GRAYSCALE)
        pre = legacy["preprocessing"]
        if mask is not None:
            content_mask = mask[
                pre["padY"]:pre["padY"] + pre["contentHeight"],
                pre["padX"]:pre["padX"] + pre["contentWidth"],
            ]
            original_mask = cv2.resize(
                content_mask,
                (pre["originalWidth"], pre["originalHeight"]),
                interpolation=cv2.INTER_NEAREST,
            )
            selected = image[original_mask > 0]
            if selected.size:
                mean_rgb = [float(value) for value in selected.mean(axis=0)]
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                mean_intensity = float(gray[original_mask > 0].mean())
                saturated_fraction = float(np.any(selected == 255, axis=1).mean())
    measurements = {
        "geometry_px": measured_geometry,
        "geometry_physical": physical,
        "appearance": {
            "color_space": "RGB",
            "mean_r": _measured(mean_rgb[0], "intensity_8bit", "masked_mean_rgb") if mean_rgb[0] is not None else _measured(None, "intensity_8bit", "masked_mean_rgb"),
            "mean_g": _measured(mean_rgb[1], "intensity_8bit", "masked_mean_rgb") if mean_rgb[1] is not None else _measured(None, "intensity_8bit", "masked_mean_rgb"),
            "mean_b": _measured(mean_rgb[2], "intensity_8bit", "masked_mean_rgb") if mean_rgb[2] is not None else _measured(None, "intensity_8bit", "masked_mean_rgb"),
            "mean_intensity": _measured(mean_intensity, "intensity_8bit", "masked_mean_luma_bt601"),
            "saturated_fraction": _measured(saturated_fraction, "fraction", "channel_max_pixel_fraction"),
            "physical_interpretation": "none",
        },
    }
    if detected == "absent":
        for value in measured_geometry.values():
            if isinstance(value, dict) and "value" in value:
                value["value"] = None
            elif isinstance(value, dict) and "x" in value:
                value["x"] = value["y"] = None
        for value in measurements["appearance"].values():
            if isinstance(value, dict) and "value" in value:
                value["value"] = None
    flags = legacy["confidenceAndQualityFlags"]["qualityFlags"]
    quality_flags = {
        "blur": flags.get("blur"),
        "saturation_clipping": flags.get("saturationClipping"),
        "low_light": flags.get("lowLight"),
        "multiple_flames": flags.get("multipleFlames"),
        "occlusion": flags.get("occlusion"),
        "scale_absent": calibration["state"] == "absent",
        "calibration_absent": True,
    }
    contours = []
    if legacy["segmentation"].get("maskUri"):
        mask = cv2.imread(legacy["segmentation"]["maskUri"], cv2.IMREAD_GRAYSCALE)
        if mask is not None:
            found, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            scale = legacy["preprocessing"]["scale"]
            pad_x, pad_y = legacy["preprocessing"]["padX"], legacy["preprocessing"]["padY"]
            for contour in found[:10]:
                points = cv2.approxPolyDP(contour, 2.0, True).reshape(-1, 2)
                contours.append([
                    {
                        "x": min(float(input_data["width"]), max(0.0, (float(x) - pad_x) / scale)),
                        "y": min(float(input_data["height"]), max(0.0, (float(y) - pad_y) / scale)),
                    }
                    for x, y in points
                ])
    result = {
        "detection": {"status": detected, "confidence": detection.get("confidence"), "bounding_box": bbox},
        "segmentation": None if detected == "absent" else {"mask_type": "binary", "threshold_policy": "otsu-v1", "component_count": legacy["confidenceAndQualityFlags"]["qualityMetrics"].get("significantComponents", len(contours)), "confidence": legacy["confidenceAndQualityFlags"].get("segmenterConfidence"), "contours": contours, "simplification_tolerance_px": 2.0},
        "measurements": measurements,
        "quality_flags": quality_flags,
        "observations": [{"statement_id": "cv-detection", "text": "Brightness-based CV detection: " + detected + ".", "claim_class": "inferred", "origin": "cv_pipeline", "evidence_ids": [], "measurement_refs": []}],
    }
    warnings = [
        {"code": "TEMPERATURE_NOT_AVAILABLE", "severity": "info", "message": "Temperature is not reported without radiometric calibration."},
    ]
    if calibration["state"] == "absent":
        warnings.append({"code": "SCALE_CALIBRATION_ABSENT", "severity": "warning", "message": "Spatial measurements are in pixels; no scale calibration was supplied."})
    if detected != "absent":
        warnings.append({"code": "LOW_DETECTION_CONFIDENCE", "severity": "warning", "message": "Brightness-based detection is heuristic; inspect the overlay before scientific use."})
    pipeline = {
        "pipeline_version": legacy["pipelineVersion"],
        "preprocessing_version": legacy["preprocessing"]["version"],
        "detector": {"name": detection["modelName"], "version": detection["modelVersion"], "artifact_digest": None},
        "segmenter": {"name": detection["modelName"], "version": detection["modelVersion"], "artifact_digest": None},
        "measurement_space": "original_oriented_px",
    }
    return {"pipeline": pipeline, "result": result, "warnings": warnings}


# ----------------------------------------------------------------------------- stuck-job recovery (P2-4)
# A worker killed mid-job (OOM, SIGKILL, host restart) loses its RQ job but leaves the row `processing`,
# and `process_*` only start from `queued`. `recover` resets such rows to `queued` and re-enqueues them.

QUEUE_NAME = "flame-analysis"
RQ_DEFAULT_TIMEOUT_S = Queue.DEFAULT_TIMEOUT   # image jobs are enqueued without job_timeout (180 s)
RECOVERY_GRACE_S = 60          # on top of the job timeout: RQ needs a moment to kill a timed-out horse
QUEUED_GRACE_S = 60            # a row is committed just before its job is enqueued (analysis._store_and_enqueue)
MAX_RECOVERY_ATTEMPTS = 3
RECOVERY_WARNING = "JOB_RECOVERED"
_LIVE_JOB_STATES = {"queued", "started", "deferred", "scheduled"}
_JOBS = {"flame_image": "flame_api.worker.process_analysis", "flame_video": "flame_api.worker.process_video_analysis"}


def _job_timeout(analysis_type: str) -> int | None:
    return settings.video_job_timeout_s if analysis_type == "flame_video" else None


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)   # SQLite returns naive UTC


def _recovery_warnings(payload: dict) -> list[dict]:
    return [item for item in payload.get("warnings", []) if item.get("code") == RECOVERY_WARNING]


def _queue() -> Queue:
    connection = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=5)
    connection.ping()   # fail before touching any row when Redis is down
    return Queue(QUEUE_NAME, connection=connection)


def _has_live_job(queue: Queue, analysis_id: str) -> bool:
    job = queue.fetch_job(analysis_id)   # job_id == analysis_id
    if job is None:
        return False
    status = job.get_status(refresh=False)
    return getattr(status, "value", status) in _LIVE_JOB_STATES


def recover(*, older_than: int | None = None, queue: Queue | None = None, now: datetime | None = None) -> dict:
    """Re-queue analyses stuck in `processing` (or `queued` without an RQ job); fail them after the cap.

    A re-queued video job resumes from its last stored segment (ADR-008). A stuck job with a cancel
    request is marked cancelled instead of being re-queued.

    Safe to run concurrently and repeatedly: each row is claimed with an UPDATE conditioned on the
    status and updated_at that were read, so only one recoverer acts on it and a re-run finds nothing.
    """
    queue = queue or _queue()
    now = now or _now()

    def threshold(status: str, analysis_type: str) -> int:
        if older_than is not None:
            return older_than
        if status == "queued":
            return QUEUED_GRACE_S
        return (_job_timeout(analysis_type) or RQ_DEFAULT_TIMEOUT_S) + RECOVERY_GRACE_S

    counts = {"requeued": 0, "failed": 0, "skipped": 0, "cancelled": 0}
    session = SessionLocal()
    try:
        oldest = min(threshold("queued", "flame_image"), threshold("processing", "flame_image"))
        cutoff = now.timestamp() - oldest
        candidates = [
            (row.analysis_id, row.status, row.updated_at, dict(row.payload), row.cancel_requested_at)
            for row in session.query(AnalysisRecord).filter(AnalysisRecord.status.in_(("queued", "processing"))).all()
            if _aware(row.updated_at).timestamp() <= cutoff
        ]
        for analysis_id, status, updated_at, payload, cancel_requested_at in candidates:
            analysis_type = payload.get("analysis_type", "flame_image")
            age = now.timestamp() - _aware(updated_at).timestamp()
            if analysis_type not in _JOBS or age < threshold(status, analysis_type) or (
                status == "queued" and _has_live_job(queue, analysis_id)
            ):
                counts["skipped"] += 1
                continue
            attempts = len(_recovery_warnings(payload))
            stamp = _iso(now)
            if cancel_requested_at is not None:
                values = {"status": "cancelled", "updated_at": now, "completed_at": now, "payload": {
                    **payload, "status": "cancelled", "updated_at": stamp, "completed_at": stamp, "poll_after_ms": None,
                    "failure": {"code": "CANCELLED", "message": CANCEL_MESSAGE, "retryable": False},
                }}
            elif attempts >= MAX_RECOVERY_ATTEMPTS:
                values = {"status": "failed", "updated_at": now, "completed_at": now, "payload": {
                    **payload, "status": "failed", "updated_at": stamp, "completed_at": stamp, "poll_after_ms": None,
                    "failure": {"code": "PIPELINE_ERROR", "retryable": False,
                                "message": f"Analysis did not complete after {attempts} automatic re-queues."},
                }}
            else:
                values = {"status": "queued", "updated_at": now, "payload": {
                    **payload, "status": "queued", "updated_at": stamp, "started_at": None,
                    "poll_after_ms": 2000 if analysis_type == "flame_video" else 1000,
                    "warnings": [*payload.get("warnings", []), {
                        "code": RECOVERY_WARNING, "severity": "info",
                        "message": f"The job was interrupted while {status} and was re-queued automatically "
                                   f"(attempt {attempts + 1} of {MAX_RECOVERY_ATTEMPTS}).",
                    }],
                }}
            claimed = session.execute(
                update(AnalysisRecord)
                .where(AnalysisRecord.analysis_id == analysis_id, AnalysisRecord.status == status,
                       AnalysisRecord.updated_at == updated_at)
                .values(**values)
            ).rowcount
            if claimed == 1 and values["status"] in {"failed", "cancelled"}:
                _drop_checkpoint(session, analysis_id)
            session.commit()
            if claimed != 1:   # another recoverer (or the worker) changed the row first
                counts["skipped"] += 1
                continue
            if values["status"] == "cancelled":
                logger.warning("analysis_id=%s recovery=cancelled", analysis_id)
                counts["cancelled"] += 1
                continue
            if values["status"] == "failed":
                logger.warning("analysis_id=%s recovery=failed attempts=%s", analysis_id, attempts)
                counts["failed"] += 1
                continue
            timeout = _job_timeout(analysis_type)
            # Same options as analysis._store_and_enqueue. If this raises, the row is `queued` without a
            # job, which the next `recover` run picks up after QUEUED_GRACE_S.
            queue.enqueue(_JOBS[analysis_type], analysis_id, job_id=analysis_id, result_ttl=86400, failure_ttl=604800,
                          **({"job_timeout": timeout} if timeout else {}))
            logger.warning("analysis_id=%s recovery=requeued from=%s attempt=%s", analysis_id, status, attempts + 1)
            counts["requeued"] += 1
    finally:
        session.close()
    return counts


def main(argv: list[str]) -> int:
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="python -m flame_api.worker")
    commands = parser.add_subparsers(dest="command", required=True)
    recover_cmd = commands.add_parser("recover", help="Re-queue analyses left in processing by a dead worker.")
    recover_cmd.add_argument("--older-than", type=int, metavar="SECONDS", default=None,
                             help="Age threshold for every stuck row (default: job timeout + 60 s; 60 s for queued rows).")
    args = parser.parse_args(argv)
    if args.older_than is not None and args.older_than < 0:
        parser.error("--older-than must be >= 0")
    print(json.dumps(recover(older_than=args.older_than)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
