"""Audited admin data operations (ADMIN_DATA_OPERATIONS.md procedures 3, 4, 5 and 7; plan B2/B3).

Every route here needs the write token, reads included: quarantine reasons, ingestion runs and the
audit log are operator data, not something the read-only web tier or AURA should see. Every change
writes one `audit_event` row (actor, action, target, before, after, request_id) in the same
transaction as the change itself, and nothing here deletes scientific source data: reprocessing only
clears a quarantine flag, and a review only changes `evidence.payload.review_status`.

All operations are `x-aura-exclude: true` in docs/api/openapi.json (ADR-004).
"""
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Path as ApiPath, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from flame_api.contracts import error_body, response_meta
from flame_api.database import get_session
from flame_api.ids import new_ulid
from flame_api.models import AuditEvent, EvidenceRecord, FileRecord, IngestionRun

ULID_PATTERN = r"^[0-9A-HJKMNP-TV-Z]{26}$"
FILE_ID_PATTERN = r"^sha256:[a-f0-9]{16}$"
MAX_PAGE_SIZE = 100
ACTOR = "write-token"   # until ADR-009 step 2 there is one admin credential, as for PUT /api/admin/ai/mode

REPROCESS_ACTION = "file.reprocess"
REVIEW_ACTION = "evidence.review"


class WriteTokenRequired(Exception):
    """Raised by `require_write_token`; main.py turns it into a 401 ErrorResponse."""


def require_write_token(request: Request) -> None:
    """Defence in depth behind the auth middleware: refuse anything not authenticated with the write token.

    The middleware records which token it accepted in `request.state.token_scope` ("unchecked" only
    when API auth is disabled for local development).
    """
    if getattr(request.state, "token_scope", None) not in {"write", "unchecked"}:
        raise WriteTokenRequired()


router = APIRouter(tags=["Admin"], dependencies=[Depends(require_write_token)])


async def write_token_required_handler(request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=error_body(request, "AUTHENTICATION_REQUIRED", "The write token is required for admin operations."),
        headers={"WWW-Authenticate": "Bearer"},
    )


def _error(request: Request, status: int, code: str, message: str, *, details=None) -> JSONResponse:
    return JSONResponse(status_code=status, content=error_body(request, code, message, details=details))


def _utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _pagination(page: int, page_size: int, total: int) -> dict[str, int]:
    return {"page": page, "page_size": page_size, "total_items": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0}


def _file(record: FileRecord) -> dict[str, Any]:
    return {
        "file_id": record.file_id,
        "source_id": record.source_id,
        "sha256": record.sha256,
        "original_filename": record.original_filename,
        "media_type": record.media_type,
        "size_bytes": record.size_bytes,
        "retrieved_at": _utc(record.retrieved_at),
        "canonical_source_url": record.canonical_source_url,
        "is_original": record.is_original,
        "parent_file_id": record.parent_file_id,
        "status": record.status,
        "quarantine_reason": record.quarantine_reason,
    }


def _run(run: IngestionRun) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "source_id": run.source_id,
        "file_id": run.file_id,
        "transformation_id": run.transformation_id,
        "input_sha256": run.input_sha256,
        "started_at": _utc(run.started_at),
        "finished_at": _utc(run.finished_at),
        "counts": run.counts or {},
    }


def _audit(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "occurred_at": _utc(event.occurred_at),
        "actor": event.actor,
        "action": event.action,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "before": event.before,
        "after": event.after,
        "request_id": event.request_id,
    }


def _record(session: Session, request: Request, *, action: str, target_type: str, target_id: str,
            before: dict[str, Any], after: dict[str, Any]) -> AuditEvent:
    """Add the audit row to the caller's transaction; the caller commits it together with the change."""
    event = AuditEvent(
        event_id=new_ulid(), occurred_at=datetime.now(UTC), actor=ACTOR, action=action, target_type=target_type,
        target_id=target_id, before=before, after=after, request_id=request.state.request_id,
    )
    session.add(event)
    return event


@router.get("/api/admin/files")
def list_files(
    request: Request,
    status: Literal["active", "quarantined"] | None = None,
    source_id: Annotated[str | None, Query(max_length=64)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    session: Session = Depends(get_session),
):
    """Procedure 3: files and why they were quarantined."""
    query = session.query(FileRecord)
    if status:
        query = query.filter(FileRecord.status == status)
    if source_id:
        query = query.filter(FileRecord.source_id == source_id)
    total = query.count()
    rows = query.order_by(FileRecord.source_id, FileRecord.file_id).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_file(r) for r in rows], "pagination": _pagination(page, page_size, total), "meta": response_meta(request)}


@router.get("/api/admin/ingestion-runs")
def list_ingestion_runs(
    request: Request,
    transformation_id: Annotated[str | None, Query(max_length=80)] = None,
    file_id: Annotated[str | None, Query(max_length=80)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    session: Session = Depends(get_session),
):
    """Procedure 3: ingestion runs, newest first. `transformation_id=quarantine` lists the failed ones."""
    query = session.query(IngestionRun)
    if transformation_id:
        query = query.filter(IngestionRun.transformation_id == transformation_id)
    if file_id:
        query = query.filter(IngestionRun.file_id == file_id)
    total = query.count()
    rows = query.order_by(IngestionRun.finished_at.desc(), IngestionRun.run_id).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_run(r) for r in rows], "pagination": _pagination(page, page_size, total), "meta": response_meta(request)}


class ReprocessBody(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


@router.post("/api/admin/files/{file_id}/reprocess")
def reprocess_file(
    request: Request,
    file_id: Annotated[str, ApiPath(pattern=FILE_ID_PATTERN)],
    body: ReprocessBody | None = None,
    session: Session = Depends(get_session),
):
    """Procedure 4: clear the quarantine so the next `python -m flame_api.ingest` retries the file.

    Ingestion is not run here: it is a batch job that publishes a new corpus version, not a request.
    """
    record = session.get(FileRecord, file_id)
    if record is None:
        return _error(request, 404, "FILE_NOT_FOUND", "File was not found.", details={"resource_id": file_id})
    if record.status != "quarantined":
        return _error(request, 409, "FILE_NOT_QUARANTINED", "Only a quarantined file can be reprocessed.",
                      details={"resource_id": file_id, "status": record.status})
    before = {"status": record.status, "quarantine_reason": record.quarantine_reason}
    record.status = "active"
    record.quarantine_reason = None
    after = {"status": "active", "quarantine_reason": None}
    if body is not None and body.note:
        after["note"] = body.note
    event = _record(session, request, action=REPROCESS_ACTION, target_type="file_record", target_id=file_id,
                    before=before, after=after)
    session.commit()
    return {"file": _file(record), "audit_event": _audit(event), "meta": response_meta(request)}


class ReviewBody(BaseModel):
    # The subset of the contract's ReviewStatus an administrator may set; `raw` is never a review outcome.
    review_status: Literal["machine_extracted", "human_verified", "rejected"]
    note: str | None = Field(default=None, max_length=2000)


@router.put("/api/admin/evidence/{evidence_id}/review")
def review_evidence(
    request: Request,
    evidence_id: Annotated[str, ApiPath(pattern=ULID_PATTERN)],
    body: ReviewBody,
    session: Session = Depends(get_session),
):
    """Procedure 7: approve or reject an evidence row. Rejected evidence is never retrieved or cited."""
    evidence = session.get(EvidenceRecord, evidence_id)
    if evidence is None:
        return _error(request, 404, "EVIDENCE_NOT_FOUND", "Evidence was not found.", details={"resource_id": evidence_id})
    payload = dict(evidence.payload or {})
    previous = payload.get("review_status")
    payload["review_status"] = body.review_status
    evidence.payload = payload   # a new dict, so the JSON column is seen as changed
    after: dict[str, Any] = {"review_status": body.review_status}
    if body.note:
        after["note"] = body.note
    event = _record(session, request, action=REVIEW_ACTION, target_type="evidence", target_id=evidence_id,
                    before={"review_status": previous}, after=after)
    session.commit()
    return {
        "evidence_id": evidence_id,
        "previous_review_status": previous,
        "review_status": body.review_status,
        "audit_event": _audit(event),
        "meta": response_meta(request),
    }


@router.get("/api/admin/audit")
def list_audit_events(
    request: Request,
    action: Annotated[str | None, Query(max_length=64)] = None,
    target_type: Annotated[str | None, Query(max_length=48)] = None,
    target_id: Annotated[str | None, Query(max_length=128)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    session: Session = Depends(get_session),
):
    """The audit log, newest first (B6)."""
    query = session.query(AuditEvent)
    if action:
        query = query.filter(AuditEvent.action == action)
    if target_type:
        query = query.filter(AuditEvent.target_type == target_type)
    if target_id:
        query = query.filter(AuditEvent.target_id == target_id)
    total = query.count()
    rows = query.order_by(AuditEvent.occurred_at.desc(), AuditEvent.event_id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_audit(e) for e in rows], "pagination": _pagination(page, page_size, total), "meta": response_meta(request)}
