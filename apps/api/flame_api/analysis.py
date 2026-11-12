import hashlib
import io
import math
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, Path as ApiPath, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session
from PIL import Image, ImageOps, UnidentifiedImageError

from flame_api import ai_runtime
from flame_api.config import get_settings
from flame_api.contracts import error_body, response_meta
from flame_api.database import get_session
from flame_api.ids import new_ulid
from flame_api.models import AnalysisRecord, ExperimentRecord, FileRecord
from flame_api.storage import client as storage_client, put_bytes, put_file

router = APIRouter(tags=["Analysis"])
settings = get_settings()
ULID_PATTERN = r"^[0-9A-HJKMNP-TV-Z]{26}$"
DEFAULT_SAMPLE_EVERY = 30   # one frame per second at 30 fps
DEFAULT_MAX_FRAMES = 300
_UPLOAD_CHUNK = 1024 * 1024


def _error(request: Request, status: int, code: str, message: str, *, details=None, retryable=False):
    return JSONResponse(
        status_code=status,
        content=error_body(request, code, message, retryable=retryable, details=details),
    )


def _utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _analysis_response(record: AnalysisRecord, request: Request):
    return {"analysis": record.payload, "meta": response_meta(request)}


@router.post("/api/analyses", status_code=202)
async def create_analysis(
    request: Request,
    image: UploadFile | None = File(None),
    video: UploadFile | None = File(None),
    sample_every_n_frames: int | None = Form(None, ge=1, le=10_000),
    max_frames: int | None = Form(None, ge=1),
    experiment_id: str | None = Form(None),
    source_file_id: str | None = Form(None),
    frame_index: int | None = Form(None, ge=0),
    scale_px_per_mm: float | None = Form(None, gt=0),
    scale_source: str | None = Form(None, min_length=1, max_length=500),
    request_interpretation: bool = Form(False),
    notes: str | None = Form(None, max_length=2000),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", min_length=8, max_length=128),
    session: Session = Depends(get_session),
):
    if (image is None) == (video is None):
        return _error(request, 400, "VALIDATION_ERROR", "Send exactly one of `image` or `video`.")
    if (scale_px_per_mm is None) != (scale_source is None):
        return _error(request, 400, "VALIDATION_ERROR", "scale_px_per_mm and scale_source must be provided together.")
    if video is None and (sample_every_n_frames is not None or max_frames is not None):
        return _error(request, 400, "VALIDATION_ERROR", "sample_every_n_frames and max_frames apply to video uploads only.")
    if idempotency_key:
        existing = session.query(AnalysisRecord).filter_by(idempotency_key=idempotency_key).one_or_none()
        if existing:
            return JSONResponse(status_code=202, content=_analysis_response(existing, request), headers={"Location": f"/api/analyses/{existing.analysis_id}", "Retry-After": "1"})
    if experiment_id and session.get(ExperimentRecord, experiment_id) is None:
        return _error(request, 422, "UNKNOWN_EXPERIMENT", "Experiment was not found.", details={"resource_id": experiment_id})
    if source_file_id and session.get(FileRecord, source_file_id) is None:
        return _error(request, 422, "VALIDATION_ERROR", "Source file was not found.")
    if video is not None:
        return await _create_video_analysis(
            request, session, video, experiment_id=experiment_id, source_file_id=source_file_id,
            sample_every=sample_every_n_frames or DEFAULT_SAMPLE_EVERY, max_frames=max_frames or DEFAULT_MAX_FRAMES,
            scale_given=scale_px_per_mm is not None, request_interpretation=request_interpretation, notes=notes,
            idempotency_key=idempotency_key,
        )

    content = await image.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        return _error(request, 413, "PAYLOAD_TOO_LARGE", "Image exceeds the upload limit.", details={"limit_bytes": settings.max_upload_bytes})
    try:
        with Image.open(io.BytesIO(content)) as decoded:
            image_format = (decoded.format or "").upper()
            if image_format not in {"PNG", "JPEG"}:
                return _error(request, 415, "UNSUPPORTED_MEDIA_TYPE", "Only PNG and JPEG images are accepted.", details={"allowed_media_types": ["image/png", "image/jpeg"]})
            width, height = decoded.size
            if decoded.getexif().get(274) in {5, 6, 7, 8}:
                width, height = height, width
            if width < 64 or height < 64 or width * height > settings.max_image_pixels:
                return _error(request, 422, "IMAGE_INVALID", "Image dimensions are outside the supported range.")
            oriented = ImageOps.exif_transpose(decoded)
            width, height = oriented.size
            oriented.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return _error(request, 422, "IMAGE_INVALID", "Image cannot be decoded.")
    media_type = "image/png" if image_format == "PNG" else "image/jpeg"
    checksum = hashlib.sha256(content).hexdigest()
    analysis_id = new_ulid()
    now = datetime.now(UTC)
    original_key = f"analyses/{analysis_id}/original.{ 'png' if image_format == 'PNG' else 'jpg' }"
    try:
        put_bytes(original_key, content, media_type)
    except Exception:
        return _error(request, 503, "STORAGE_UNAVAILABLE", "Image storage is unavailable.", retryable=True)

    input_payload = {
        "image_sha256": checksum,
        "original_filename": image.filename or f"upload.{ 'png' if image_format == 'PNG' else 'jpg' }",
        "media_type": media_type,
        "size_bytes": len(content),
        "width": width,
        "height": height,
        "experiment_id": experiment_id,
        "source_file_id": source_file_id,
        "frame_index": frame_index,
        "calibration": {
            "state": "spatial_scale_provided" if scale_px_per_mm is not None else "absent",
            "scale_px_per_mm": scale_px_per_mm,
            "scale_source": scale_source,
        },
        "notes": notes,
    }
    original_artifact = {
        "kind": "original",
        "url": f"/api/analyses/{analysis_id}/artifacts/original",
        "media_type": media_type,
        "sha256": checksum,
        "width": width,
        "height": height,
        "size_bytes": len(content),
    }
    warnings = []
    interpreter_ready = request_interpretation and ai_runtime.get_router(settings).available("analysis.interpret")
    interpretation_status = "pending" if interpreter_ready else "unavailable" if request_interpretation else "not_requested"
    if request_interpretation and not interpreter_ready:
        warnings.append({"code": "INTERPRETATION_UNAVAILABLE", "severity": "info", "message": "No interpretation model is configured or permitted in the current mode."})
    payload = {
        "analysis_id": analysis_id,
        "analysis_type": "flame_image",
        "status": "queued",
        "created_at": _utc(now),
        "updated_at": _utc(now),
        "started_at": None,
        "completed_at": None,
        "input": input_payload,
        "pipeline": None,
        "result": None,
        "interpretation": {"status": interpretation_status, "provider": None, "model": None, "statements": [], "rejected_statement_count": 0, "generated_at": None},
        "artifacts": [original_artifact],
        "warnings": warnings,
        "failure": None,
        "poll_after_ms": 1000,
    }
    record = AnalysisRecord(
        analysis_id=analysis_id,
        status="queued",
        created_at=now,
        updated_at=now,
        experiment_id=experiment_id,
        image_sha256=checksum,
        original_filename=input_payload["original_filename"],
        idempotency_key=idempotency_key,
        payload=payload,
        artifacts={"original": {**original_artifact, "object_key": original_key}},
    )
    return _store_and_enqueue(request, session, record, payload, original_key, "flame_api.worker.process_analysis")


_VIDEO_MEDIA = {"mp4": "video/mp4", "mov": "video/quicktime", "avi": "video/x-msvideo"}


def _sniff_video(head: bytes) -> str | None:
    """Container from the leading bytes (ISO-BMFF `ftyp` box or RIFF/AVI), never from the filename."""
    if head[4:8] == b"ftyp":
        return "mov" if head[8:12] == b"qt  " else "mp4"
    if head[:4] == b"RIFF" and head[8:12] == b"AVI ":
        return "avi"
    return None


async def _spool(upload: UploadFile, target: Path, limit: int) -> int | None:
    """Copy the upload to disk in chunks; None when it exceeds ``limit`` (nothing is kept in memory)."""
    size = 0
    with open(target, "wb") as out:
        while chunk := await upload.read(_UPLOAD_CHUNK):
            size += len(chunk)
            if size > limit:
                return None
            out.write(chunk)
    return size


def _probe(path: Path):
    from cv.video_ingestion import VideoConfig, probe_video

    return probe_video(path, VideoConfig(max_bytes=settings.max_video_upload_bytes))


async def _create_video_analysis(request: Request, session: Session, video: UploadFile, *, experiment_id, source_file_id,
                                 sample_every: int, max_frames: int, scale_given: bool, request_interpretation: bool,
                                 notes, idempotency_key):
    if scale_given:
        # The video pipeline reports pixel measurements only; accepting a scale would imply physical output.
        return _error(request, 400, "VALIDATION_ERROR", "Spatial calibration is not supported for video analyses yet.")
    if max_frames > settings.max_video_frames:
        return _error(request, 400, "VALIDATION_ERROR", f"max_frames must be at most {settings.max_video_frames}.")
    with tempfile.TemporaryDirectory(prefix="flame-video-upload-") as working:
        spooled = Path(working) / "upload.bin"
        size = await _spool(video, spooled, settings.max_video_upload_bytes)
        if size is None:
            return _error(request, 413, "PAYLOAD_TOO_LARGE", "Video exceeds the upload limit.",
                          details={"limit_bytes": settings.max_video_upload_bytes})
        with open(spooled, "rb") as handle:
            container = _sniff_video(handle.read(16))
        if container is None:
            return _error(request, 415, "UNSUPPORTED_MEDIA_TYPE", "Only MP4, MOV and AVI videos are accepted.",
                          details={"allowed_media_types": sorted(_VIDEO_MEDIA.values())})
        path = spooled.rename(spooled.with_suffix(f".{container}"))
        try:
            from cv.flame_cv import CVError
        except ImportError:
            return _error(request, 503, "MODEL_UNAVAILABLE", "The video pipeline is not installed on this server.", retryable=True)
        try:
            record = await run_in_threadpool(_probe, path)
        except CVError as exc:
            status = {"UNSUPPORTED_MEDIA_TYPE": 415, "VIDEO_TOO_LONG": 413, "FILE_TOO_LARGE": 413}.get(exc.code, 422)
            code = "UNSUPPORTED_MEDIA_TYPE" if status == 415 else "PAYLOAD_TOO_LARGE" if status == 413 else "VIDEO_INVALID"
            return _error(request, status, code, exc.message)
        checksum = record["checksum"].removeprefix("sha256:")
        media_type = _VIDEO_MEDIA[container]
        width, height = record["resolution"]
        analysis_id = new_ulid()
        now = datetime.now(UTC)
        original_key = f"analyses/{analysis_id}/original.{container}"
        try:
            put_file(original_key, str(path), media_type)
        except Exception:
            return _error(request, 503, "STORAGE_UNAVAILABLE", "Video storage is unavailable.", retryable=True)

    filename = video.filename or f"upload.{container}"
    input_payload = {
        "image_sha256": checksum,
        "original_filename": filename,
        "media_type": media_type,
        "size_bytes": size,
        "width": width,
        "height": height,
        "experiment_id": experiment_id,
        "source_file_id": source_file_id,
        "frame_index": None,
        "calibration": {"state": "absent", "scale_px_per_mm": None, "scale_source": None},
        "notes": notes,
        "video": {
            "container": container,
            "codec": record["codec"],
            "fps": record["fps"],
            "frame_count": record["frameCount"],
            "duration_seconds": record["durationSeconds"],
            "variable_frame_rate": record["timestamps"]["variableFrameRate"],
            "sample_every_n_frames": sample_every,
            "max_frames": max_frames,
        },
    }
    original_artifact = {"kind": "original", "url": f"/api/analyses/{analysis_id}/artifacts/original", "media_type": media_type,
                         "sha256": checksum, "width": width, "height": height, "size_bytes": size}
    warnings = []
    if request_interpretation:
        warnings.append({"code": "INTERPRETATION_UNAVAILABLE", "severity": "info",
                         "message": "Model interpretation is not available for video analyses yet; measurements only."})
    payload = {
        "analysis_id": analysis_id,
        "analysis_type": "flame_video",
        "status": "queued",
        "created_at": _utc(now),
        "updated_at": _utc(now),
        "started_at": None,
        "completed_at": None,
        "input": input_payload,
        "pipeline": None,
        "result": None,
        "interpretation": {"status": "unavailable" if request_interpretation else "not_requested", "provider": None, "model": None,
                           "statements": [], "rejected_statement_count": 0, "generated_at": None},
        "artifacts": [original_artifact],
        "warnings": warnings,
        "failure": None,
        "poll_after_ms": 2000,
    }
    record_row = AnalysisRecord(
        analysis_id=analysis_id, status="queued", created_at=now, updated_at=now, experiment_id=experiment_id,
        image_sha256=checksum, original_filename=filename, idempotency_key=idempotency_key, payload=payload,
        artifacts={"original": {**original_artifact, "object_key": original_key}},
    )
    return _store_and_enqueue(request, session, record_row, payload, original_key, "flame_api.worker.process_video_analysis",
                              job_timeout=settings.video_job_timeout_s)


def _store_and_enqueue(request: Request, session: Session, record: AnalysisRecord, payload: dict, original_key: str,
                       job: str, *, job_timeout: int | None = None):
    analysis_id = record.analysis_id
    try:
        session.add(record)
        session.commit()
    except Exception:
        session.rollback()
        try:
            storage_client().delete_object(Bucket=settings.s3_bucket, Key=original_key)
        except Exception:
            pass
        return _error(request, 503, "DATABASE_UNAVAILABLE", "Analysis could not be stored.", retryable=True)
    try:
        queue = Queue("flame-analysis", connection=Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=2))
        options = {"job_timeout": job_timeout} if job_timeout else {}
        queue.enqueue(job, analysis_id, job_id=analysis_id, result_ttl=86400, failure_ttl=604800, **options)
    except Exception:
        record.status = "failed"
        record.updated_at = datetime.now(UTC)
        record.completed_at = record.updated_at
        payload.update({"status": "failed", "updated_at": _utc(record.updated_at), "completed_at": _utc(record.completed_at), "failure": {"code": "PIPELINE_ERROR", "message": "Analysis could not be queued.", "retryable": True}, "poll_after_ms": None})
        record.payload = payload
        session.commit()
        return _error(request, 503, "QUEUE_UNAVAILABLE", "Analysis queue is unavailable.", retryable=True)
    return JSONResponse(status_code=202, content=_analysis_response(record, request), headers={"Location": f"/api/analyses/{analysis_id}", "Retry-After": "1"})


@router.get("/api/analyses")
def list_analyses(
    request: Request,
    status: list[str] | None = None,
    experiment_id: str | None = None,
    pipeline_version: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort: str = "created_at_desc",
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
):
    if sort not in {"created_at_desc", "created_at_asc"} or page < 1 or not 1 <= page_size <= 100:
        return _error(request, 400, "VALIDATION_ERROR", "Analysis history filters are invalid.")
    query = session.query(AnalysisRecord)
    if status:
        query = query.filter(AnalysisRecord.status.in_(status))
    if experiment_id:
        query = query.filter(AnalysisRecord.experiment_id == experiment_id)
    if pipeline_version:
        query = query.filter(AnalysisRecord.pipeline_version == pipeline_version)
    if created_from:
        query = query.filter(AnalysisRecord.created_at >= created_from)
    if created_to:
        query = query.filter(AnalysisRecord.created_at < created_to)
    total = query.count()
    ordering = AnalysisRecord.created_at.desc() if sort == "created_at_desc" else AnalysisRecord.created_at.asc()
    records = query.order_by(ordering).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for record in records:
        detail = record.payload
        result = detail.get("result") or {}
        measurements = result.get("measurements") or {}
        geometry = measurements.get("geometry_px") or {}
        area = geometry.get("area") or {}
        items.append({
            "analysis_id": record.analysis_id,
            "analysis_type": detail.get("analysis_type", "flame_image"),
            "status": record.status,
            "created_at": _utc(record.created_at),
            "completed_at": _utc(record.completed_at),
            "original_filename": record.original_filename,
            "image_sha256": record.image_sha256,
            "experiment_id": record.experiment_id,
            "pipeline_version": record.pipeline_version,
            "detection_status": (result.get("detection") or {}).get("status"),
            "flame_area_px": area.get("value"),
            "calibration_state": (detail.get("input", {}).get("calibration") or {}).get("state", "absent"),
            "warning_count": len(detail.get("warnings", [])),
            "overlay_url": next((item["url"] for item in detail.get("artifacts", []) if item["kind"] == "overlay"), None),
        })
    return {"items": items, "pagination": {"page": page, "page_size": page_size, "total_items": total, "total_pages": math.ceil(total / page_size) if total else 0}, "meta": response_meta(request)}


@router.get("/api/analyses/{analysis_id}")
def get_analysis(request: Request, analysis_id: Annotated[str, ApiPath(pattern=ULID_PATTERN)], session: Session = Depends(get_session)):
    record = session.get(AnalysisRecord, analysis_id)
    if not record:
        return _error(request, 404, "ANALYSIS_NOT_FOUND", "Analysis was not found.", details={"resource_id": analysis_id})
    if record.status in {"queued", "processing"}:
        return JSONResponse(content=_analysis_response(record, request), headers={"Retry-After": "1"})
    return _analysis_response(record, request)


@router.post("/api/analyses/{analysis_id}/cancel")
def cancel_analysis(request: Request, analysis_id: Annotated[str, ApiPath(pattern=ULID_PATTERN)],
                    session: Session = Depends(get_session)):
    """ADR-008: cancel a queued analysis now, or ask a running one to stop at its next checkpoint."""
    record = session.get(AnalysisRecord, analysis_id, with_for_update=True)
    if not record:
        return _error(request, 404, "ANALYSIS_NOT_FOUND", "Analysis was not found.", details={"resource_id": analysis_id})
    if record.status == "cancelled":
        return _analysis_response(record, request)
    if record.status not in {"queued", "processing"}:
        return _error(request, 409, "ANALYSIS_NOT_CANCELLABLE",
                      f"The analysis is already {record.status}; a finished analysis cannot be cancelled.",
                      details={"resource_id": analysis_id})
    now = datetime.now(UTC)
    stamp = _utc(now)
    if record.cancel_requested_at is None:
        record.cancel_requested_at = now
    if record.status == "queued":
        # The worker only starts `queued` rows, so the RQ job, if it runs at all, does nothing.
        record.status = "cancelled"
        record.updated_at = now
        record.completed_at = now
        record.payload = {
            **record.payload, "status": "cancelled", "updated_at": stamp, "completed_at": stamp, "poll_after_ms": None,
            "cancel_requested_at": _utc(record.cancel_requested_at),
            "failure": {"code": "CANCELLED", "message": "The analysis was cancelled on request.", "retryable": False},
        }
        session.commit()
        return _analysis_response(record, request)
    record.payload = {**record.payload, "cancel_requested_at": _utc(record.cancel_requested_at)}
    session.commit()
    return JSONResponse(status_code=202, content=_analysis_response(record, request), headers={"Retry-After": "1"})


@router.get("/api/analyses/{analysis_id}/artifacts/{artifact_kind}")
def get_analysis_artifact(
    request: Request,
    analysis_id: Annotated[str, ApiPath(pattern=ULID_PATTERN)],
    artifact_kind: Annotated[str, ApiPath(pattern=r"^(original|preprocessed|mask|overlay)$")],
    session: Session = Depends(get_session),
):
    record = session.get(AnalysisRecord, analysis_id)
    if not record:
        return _error(request, 404, "ANALYSIS_NOT_FOUND", "Analysis was not found.", details={"resource_id": analysis_id})
    artifact = record.artifacts.get(artifact_kind)
    if not artifact:
        if record.status in {"queued", "processing"} and artifact_kind != "original":
            response = _error(request, 409, "ARTIFACT_NOT_READY", "Artifact is not ready.", retryable=True)
            response.headers["Retry-After"] = "1"
            return response
        return _error(request, 404, "ARTIFACT_NOT_FOUND", "Artifact was not found.", details={"resource_id": analysis_id})
    try:
        body = storage_client().get_object(Bucket=settings.s3_bucket, Key=artifact["object_key"])["Body"].read()
    except Exception:
        return _error(request, 503, "STORAGE_UNAVAILABLE", "Image storage is unavailable.", retryable=True)
    return Response(
        content=body,
        media_type=artifact["media_type"],
        headers={"ETag": f'"{artifact["sha256"]}"', "Cache-Control": "public, max-age=31536000, immutable"},
    )