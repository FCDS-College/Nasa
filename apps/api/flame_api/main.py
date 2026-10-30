import logging
import json
import time
from datetime import UTC, datetime
from hmac import compare_digest
import re
from collections import deque
from pathlib import Path
from typing import Annotated, Any
from threading import Lock
from uuid import uuid4

import boto3
from botocore.config import Config
from fastapi import Depends, FastAPI, Path as ApiPath, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue, Worker
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from starlette.exceptions import HTTPException as StarletteHTTPException

from flame_api.config import get_settings
from flame_api.contracts import error_body, response_meta
from flame_api.database import engine, get_session
from flame_api.analysis import router as analysis_router
from ai.routing import ExecutionMode, NoCompatibleProvider
from flame_api import ai_runtime, answer_cache, telemetry
from flame_api.generation import CHAT_INSTRUCTIONS, answer_question
from flame_api.knowledge_version import current_knowledge_version
from flame_api.models import AnalysisRecord, DocumentChunk, DocumentRecord, EvidenceRecord, ExperimentCondition, ExperimentRecord, SourceRecord
from ai.rag.retrieval.fusion import reciprocal_rank_fusion
from flame_api.vector_index import VectorUnavailableError, index_status, search_chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("flame_api")
settings = get_settings()

app = FastAPI(
    title="Flame in Freefall API",
    version=settings.api_version,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url=None,
)
app.include_router(analysis_router)
telemetry.setup(settings.otel_service_name, enabled=settings.otel_enabled)

_CONTRACT_PATH = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.json"


def _contract_openapi() -> dict[str, Any]:
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


app.openapi = _contract_openapi
ULID_PATTERN = r"^[0-9A-HJKMNP-TV-Z]{26}$"


@app.get("/health/live", include_in_schema=False)
def liveness():
    return {"status": "alive"}


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied_id = request.headers.get("X-Request-ID", "")
    request_id = supplied_id if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", supplied_id) else f"req_{uuid4().hex}"
    request.state.request_id = request_id
    started = time.perf_counter()
    with telemetry.span("http.request", **{"http.method": request.method, "http.route": request.url.path,
                                          "flame.request_id": request_id}) as current:
        response = await _authorized(request, call_next)
        telemetry.set_attributes(current, **{"http.status_code": response.status_code})
    response.headers["X-Request-ID"] = request_id
    logger.info("request_id=%s method=%s path=%s status=%s duration_ms=%.1f", request_id, request.method, request.url.path, response.status_code, (time.perf_counter() - started) * 1000)
    return response


async def _authorized(request: Request, call_next):
    path = request.url.path
    public_metadata = path == "/api/openapi.json" or path == "/api/docs" or path.startswith("/api/docs/")
    if path.startswith("/api/") and not public_metadata and settings.api_auth_enabled:
        # Chat only reads the corpus (and asks AURA), so the read token is enough for it; the web
        # service never needs the write token.
        reads = request.method in {"GET", "HEAD"} or (request.method == "POST" and path == "/api/chat")
        expected = settings.read_api_token if reads else settings.write_api_token
        authorization = request.headers.get("Authorization", "")
        scheme, separator, supplied = authorization.partition(" ")
        if (
            expected is None
            or scheme.lower() != "bearer"
            or not separator
            or not supplied
            or not compare_digest(supplied.encode(), expected.get_secret_value().encode())
        ):
            response = JSONResponse(
                status_code=401,
                content=error_body(request, "AUTHENTICATION_REQUIRED", "A valid API bearer token is required."),
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            response = await call_next(request)
    else:
        response = await call_next(request)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    fields = [
        {"field": ".".join(str(part) for part in error["loc"] if part != "query"), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=400,
        content=error_body(request, "VALIDATION_ERROR", "Request validation failed.", field_errors=fields),
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    logger.warning("request_id=%s database_error=%s", request.state.request_id, type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content=error_body(request, "DATABASE_UNAVAILABLE", "Database is unavailable.", retryable=True),
        headers={"Retry-After": "1"},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content=error_body(request, "ROUTE_NOT_FOUND", "Route was not found."))
    if exc.status_code == 405:
        return JSONResponse(status_code=405, content=error_body(request, "METHOD_NOT_ALLOWED", "Method is not allowed on this route."),
                            headers=getattr(exc, "headers", None))
    return JSONResponse(status_code=exc.status_code, content=error_body(request, "INTERNAL_ERROR", "Request could not be completed."))


@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception):
    logger.exception("request_id=%s unhandled_error=%s", request.state.request_id, type(exc).__name__)
    return JSONResponse(status_code=500, content=error_body(request, "INTERNAL_ERROR", "An unexpected error occurred."))


def _service(status: str, required: bool, checked_at: str | None, **values: Any) -> dict[str, Any]:
    return {
        "status": status,
        "required": required,
        "latency_ms": values.get("latency_ms"),
        "checked_at": checked_at,
        "version": values.get("version"),
        "message": values.get("message"),
    }


def _cv_worker_service(redis_client: Redis, checked_at: str) -> dict[str, Any]:
    """RQ registers each live worker in Redis (key TTL = heartbeat), so no custom heartbeat is needed."""
    start = time.perf_counter()
    try:
        queue = Queue("flame-analysis", connection=redis_client)
        workers = Worker.all(queue=queue)
        backlog = queue.count
    except Exception:
        return _service("unknown", False, checked_at, message="CV worker status could not be checked.")
    latency = round((time.perf_counter() - start) * 1000, 1)
    if not workers:
        return _service("down", False, checked_at, latency_ms=latency, message=f"No CV worker is consuming the analysis queue ({backlog} waiting).")
    try:
        from cv.flame_cv import PIPELINE_VERSION as version
    except ImportError:
        version = None
    return _service("up", False, checked_at, latency_ms=latency, version=version, message=None)


def _ai_status() -> dict[str, Any]:
    """Refresh provider probes (bounded, parallel, cached) and return the router's view."""
    router = ai_runtime.get_router(settings)
    router.refresh_health(force=False)
    return router.status()


def _model_services(ai_status: dict[str, Any], checked_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """The fixed `llm` and `aura` health entries, derived from the router (2H Task 8 indicators)."""
    mode = ai_status["mode"]
    text_models = [p for p in ai_status["providers"] if "structured" in p["capabilities"] and p["name"] != "aura"]
    usable = [p for p in text_models if p["permitted"] and p["health"]["state"] in {"up", "degraded"}]
    if not text_models:
        llm = _service("disabled", False, None, message="No local language model is configured (FLAME_OLLAMA_BASE_URL / FLAME_VLLM_BASE_URL).")
    elif usable:
        best = usable[0]
        llm = _service("up", False, checked_at, latency_ms=best["health"]["latency_ms"], version=f"{best['name']}:{best['model']}")
    else:
        llm = _service("down", False, checked_at, message="No local language model is ready.")
    aura = next((p for p in ai_status["providers"] if p["name"] == "aura"), None)
    if aura is None:
        aura_service = _service("disabled", False, None, message="FLAME_AURA_ENABLED is false.")
    elif not aura["permitted"]:
        aura_service = _service("disabled", False, None, message=f"AURA is blocked in {mode} mode.")
    else:
        state = aura["health"]["state"]
        aura_service = _service(
            state if state in {"up", "down", "degraded"} else "unknown", False, checked_at,
            latency_ms=aura["health"]["latency_ms"], version="3", message=None if state == "up" else "AURA is not ready.",
        )
    return llm, aura_service


@app.get("/api/health", tags=["System"])
def health(request: Request):
    checked_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    knowledge_version: str | None = None
    ai_status = _ai_status()
    llm_service, aura_service = _model_services(ai_status, checked_at)
    services: dict[str, dict[str, Any]] = {
        "api": _service("up", True, checked_at, latency_ms=0.0, version=settings.api_version),
        "database": _service("down", True, checked_at, message="Database is unavailable."),
        "vector_index": _service("down", False, checked_at, message="No vector index has been published."),
        "object_storage": _service("down", True, checked_at, message="Object storage is unavailable."),
        "cache": _service("unknown", False, checked_at, message="Cache status was not checked."),
        "cv_model": _service("unknown", False, None, message="CV worker is not available."),
        "llm": llm_service,
        "aura": aura_service,
    }
    try:
        start = time.perf_counter()
        with engine.connect() as connection:
            version = connection.execute(text("select version()")).scalar_one()
        services["database"] = _service("up", True, checked_at, latency_ms=round((time.perf_counter() - start) * 1000, 1), version=version.split(",")[0])
        try:
            with Session(engine) as index_session:
                index = index_status(index_session)
            knowledge_version = index.get("version") if index["state"] in {"up", "stale"} else None
            services["vector_index"] = _service(
                {"up": "up", "stale": "degraded", "missing": "down"}.get(index["state"], "unknown"),
                False,
                checked_at,
                version=index.get("model"),
                message=index["message"],
            )
        except SQLAlchemyError:
            services["vector_index"] = _service("unknown", False, checked_at, message="Vector index status could not be checked.")
    except SQLAlchemyError:
        logger.warning("request_id=%s database_health=down", request.state.request_id)
    try:
        start = time.perf_counter()
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
            config=Config(connect_timeout=0.5, read_timeout=0.5, retries={"total_max_attempts": 1}),
        )
        client.head_bucket(Bucket=settings.s3_bucket)
        services["object_storage"] = _service("up", True, checked_at, latency_ms=round((time.perf_counter() - start) * 1000, 1))
    except Exception:
        logger.warning("request_id=%s object_storage_health=down", request.state.request_id)
    try:
        start = time.perf_counter()
        redis_client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
            retry_on_timeout=False,
        )
        redis_client.ping()
        services["cache"] = _service("up", False, checked_at, latency_ms=round((time.perf_counter() - start) * 1000, 1))
        services["cv_model"] = _cv_worker_service(redis_client, checked_at)
    except Exception:
        services["cache"] = _service("down", False, checked_at, message="Cache is unavailable.")

    required_down = any(service["required"] and service["status"] == "down" for service in services.values())
    degraded = any(service["status"] in {"down", "degraded", "unknown"} and not service["required"] for service in services.values())
    status = "unhealthy" if required_down else "degraded" if degraded else "healthy"
    body = {
        "status": status,
        "environment": settings.environment,
        "version": {"api_version": settings.api_version, "build_id": settings.build_id, "git_sha": settings.git_sha},
        "knowledge_version": knowledge_version,
        "services": services,
        "ai": {"mode": ai_status["mode"], "providers": ai_status["providers"]},
        "meta": response_meta(request),
    }
    return JSONResponse(status_code=503 if required_down else 200, content=body)


@app.get("/api/", include_in_schema=False)
def api_root():
    return {"service": "Flame in Freefall API", "version": settings.api_version}


def _not_found(request: Request, code: str, label: str, resource_id: str):
    return JSONResponse(
        status_code=404,
        content=error_body(request, code, f"{label} was not found.", details={"resource_id": resource_id}),
    )


def _pagination(page: int, page_size: int, total: int) -> dict[str, int]:
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _source_payload(source) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "title": source.title,
        "short_name": source.short_name,
        "repository": source.repository,
        "persistent_identifier": source.persistent_identifier,
        "license": source.license,
        "access_url": source.access_url,
    }


def _file_payload(file_record) -> dict[str, Any]:
    return {
        "file_id": file_record.file_id,
        "sha256": file_record.sha256,
        "original_filename": file_record.original_filename,
        "media_type": file_record.media_type,
        "size_bytes": file_record.size_bytes,
        "retrieved_at": file_record.retrieved_at.isoformat().replace("+00:00", "Z"),
        "canonical_source_url": file_record.canonical_source_url,
        "is_original": file_record.is_original,
        "parent_file_id": file_record.parent_file_id,
    }


@app.get("/api/dashboard/counts", tags=["Dashboard"])
def dashboard_counts(request: Request, session: Session = Depends(get_session)):
    try:
        documents = session.query(DocumentRecord).count()
        experiments = session.query(ExperimentRecord).filter(ExperimentRecord.conditions.any()).count()
        completed = session.query(AnalysisRecord).filter(AnalysisRecord.status == "completed").count()
        in_progress = session.query(AnalysisRecord).filter(AnalysisRecord.status.in_(["queued", "processing"])).count()
        knowledge_version = current_knowledge_version(session)
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content=error_body(request, "DATABASE_UNAVAILABLE", "Database is unavailable.", retryable=True))
    return {
        "documents": documents,
        "experiments": experiments,
        "analyses": completed,
        "analyses_in_progress": in_progress,
        "knowledge_version": knowledge_version,
        "meta": response_meta(request),
    }


@app.get("/api/search", tags=["Research"])
def search(
    request: Request,
    q: str,
    type: str | None = None,
    source_id: list[str] | None = None,
    experiment_id: str | None = None,
    domain: str = "combustion",
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_session),
):
    query = q.strip()
    if not query or len(query) > 500 or page < 1 or not 1 <= page_size <= 50:
        return JSONResponse(status_code=400, content=error_body(request, "VALIDATION_ERROR", "Search parameters are invalid."))
    if len(source_id or []) > 20 or domain not in {"combustion", "all"} or type not in {None, "document", "experiment"}:
        return JSONResponse(status_code=400, content=error_body(request, "VALIDATION_ERROR", "Search filters are invalid."))
    results: list[dict[str, Any]] = []
    total_items = 0
    index_version: str | None = None
    try:
        source_filter = source_id or None
        offset = (page - 1) * page_size
        if type in {None, "document"}:
            doc_query = session.query(DocumentChunk).options(joinedload(DocumentChunk.document).joinedload(DocumentRecord.source))
            if session.bind.dialect.name == "postgresql":
                doc_query = doc_query.filter(
                    text("to_tsvector('english', document_chunk.text) @@ plainto_tsquery('english', :search_query)")
                ).params(search_query=query)
            else:
                doc_query = doc_query.filter(DocumentChunk.text.ilike(f"%{query}%"))
            if domain == "combustion":
                doc_query = doc_query.filter(DocumentChunk.source_id.in_(select(SourceRecord.source_id).where(SourceRecord.domain == "combustion")))
            if source_filter:
                doc_query = doc_query.filter(DocumentChunk.source_id.in_(source_filter))
            if experiment_id:
                doc_query = doc_query.filter(text("document_chunk.evidence_id in (select evidence_id from evidence where experiment_id = :experiment_id)")).params(experiment_id=experiment_id)
            total_items += doc_query.count()
            lexical_chunks = doc_query.all()
            extra_chunks: list[DocumentChunk] = []
            semantic_scores: dict[str, float] = {}
            if domain in {"combustion", "all"}:
                try:
                    status = index_status(session)
                    if status["state"] == "up":
                        semantic_scores = dict(search_chunks(session, query, limit=10))
                        index_version = status["version"]
                except (VectorUnavailableError, SQLAlchemyError):
                    logger.warning("request_id=%s vector_search=unavailable", request.state.request_id)
            seen_chunks = {chunk.chunk_id for chunk in lexical_chunks}
            extra_ids = [cid for cid in semantic_scores if cid not in seen_chunks]
            if extra_ids:
                extra = session.query(DocumentChunk).options(joinedload(DocumentChunk.document).joinedload(DocumentRecord.source)).filter(DocumentChunk.chunk_id.in_(extra_ids))
                if source_filter:
                    extra = extra.filter(DocumentChunk.source_id.in_(source_filter))
                if experiment_id:
                    extra = extra.filter(text("document_chunk.evidence_id in (select evidence_id from evidence where experiment_id = :experiment_id)")).params(experiment_id=experiment_id)
                extra_chunks = extra.all()
                total_items += len(extra_chunks)
            terms = query.lower().split()
            lexical_chunks.sort(key=lambda c: (-sum(term in c.text[:400].lower() for term in terms), c.chunk_id))
            dense_ranking = sorted(semantic_scores, key=lambda cid: (-semantic_scores[cid], cid))
            # only true lexical hits enter the lexical ranking; dense-only hits are ranked by the dense list alone
            fused = dict(reciprocal_rank_fusion([[c.chunk_id for c in lexical_chunks], dense_ranking]))
            for chunk in [*lexical_chunks, *extra_chunks]:
                document = chunk.document
                snippet = chunk.text[:400]
                results.append({
                    "result_id": chunk.chunk_id,
                    "result_type": "document",
                    "rank": len(results) + 1 + offset,
                    "score": round(fused[chunk.chunk_id], 6),
                    "title": document.title,
                    "snippet": snippet,
                    "highlights": [],
                    "source": _source_payload(document.source),
                    "document_id": document.document_id,
                    "document_type": document.document_type,
                    "experiment_id": None,
                    "experiment": None,
                    "evidence_id": chunk.evidence_id,
                    "has_evidence": True,
                    "locator": {"type": "page", "page": chunk.page, "section": chunk.section, "row": None, "frame_index": None, "label": f"p. {chunk.page}" if chunk.page else "file"},
                    "ingested_at": _timestamp(document.ingested_at),
                })
        if type in {None, "experiment"}:
            exp_query = session.query(ExperimentRecord).options(joinedload(ExperimentRecord.conditions), joinedload(ExperimentRecord.source))
            if session.bind.dialect.name == "postgresql":
                exp_query = exp_query.filter(
                    text("to_tsvector('english', experiment.searchable_text) @@ plainto_tsquery('english', :search_query)")
                ).params(search_query=query)
            else:
                needle = f"%{query}%"
                exp_query = exp_query.filter(ExperimentRecord.searchable_text.ilike(needle))
            if domain == "combustion":
                exp_query = exp_query.filter(ExperimentRecord.source_id.in_(select(SourceRecord.source_id).where(SourceRecord.domain == "combustion")))
            if source_filter:
                exp_query = exp_query.filter(ExperimentRecord.source_id.in_(source_filter))
            if experiment_id:
                exp_query = exp_query.filter(ExperimentRecord.experiment_id == experiment_id)
            total_items += exp_query.count()
            experiments = sorted(
                exp_query.all(),
                key=lambda e: (-sum(term in e.searchable_text.lower() for term in query.lower().split()), e.experiment_id),
            )
            for experiment_rank, experiment in enumerate(experiments, start=1):
                snippet = experiment.fuel_or_material or experiment.test_id
                results.append({
                    "result_id": experiment.experiment_id,
                    "result_type": "experiment",
                    "rank": len(results) + 1 + offset,
                    "score": round(1.0 / (60 + experiment_rank), 6),
                    "title": f"{experiment.investigation or 'Experiment'} {experiment.test_id}",
                    "snippet": snippet,
                    "highlights": [],
                    "source": _source_payload(experiment.source),
                    "document_id": None,
                    "document_type": None,
                    "experiment_id": experiment.experiment_id,
                    "experiment": {"test_id": experiment.test_id, "gravity_regime": experiment.gravity_regime, "fuel_or_material": experiment.fuel_or_material},
                    "evidence_id": experiment.conditions[0].evidence_id if experiment.conditions else None,
                    "has_evidence": bool(experiment.conditions),
                    "locator": None,
                    "ingested_at": _timestamp(datetime.now(UTC)),
                })
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content=error_body(request, "SEARCH_UNAVAILABLE", "Search is unavailable.", retryable=True))
    results.sort(key=lambda item: (-item["score"], item["result_type"], item["result_id"]))
    results = results[offset:offset + page_size]
    for position, item in enumerate(results, start=offset + 1):
        item["rank"] = position
    return {
        "query": query,
        "results": results,
        "pagination": _pagination(page, page_size, total_items),
        "filters": {"type": type, "source_id": source_id or [], "experiment_id": experiment_id, "domain": domain},
        "retrieval": {"mode": "hybrid" if index_version else "lexical", "knowledge_version": index_version, "index_version": index_version, "searched_but_empty": not results},
        "meta": response_meta(request),
    }


class ChatBody(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = Field(default=None, max_length=128)


_CHAT_STOPWORDS = frozenset(
    "a an and are as at be been by can could did do does for from has have how in into is it its of on or "
    "that the their there these this to was were what when where which who why will with would about "
    "between during after before than then them they you your tell explain describe give show find".split()
)
_chat_calls: deque[float] = deque()
_chat_lock = Lock()


def _chat_rate_limited() -> bool:
    now = time.monotonic()
    with _chat_lock:
        while _chat_calls and now - _chat_calls[0] > 60:
            _chat_calls.popleft()
        if len(_chat_calls) >= settings.chat_rate_limit_per_minute:
            return True
        _chat_calls.append(now)
        return False


def _question_terms(question: str) -> list[str]:
    seen: dict[str, None] = {}
    for word in re.findall(r"[a-z0-9][a-z0-9.\-]{2,}", question.lower()):
        word = word.strip(".-")
        if len(word) >= 3 and word not in _CHAT_STOPWORDS:
            seen.setdefault(word)
    return sorted(seen, key=len, reverse=True)[:5]


def _passage(item: dict[str, Any]) -> dict[str, str]:
    if item["result_type"] == "experiment":
        experiment = item.get("experiment") or {}
        text = (
            f"Experiment {item['title']}: fuel or material {experiment.get('fuel_or_material') or 'unknown'}; "
            f"gravity regime {experiment.get('gravity_regime') or 'unknown'}."
        )
    else:
        text = item["snippet"]
    label = (item.get("locator") or {}).get("label")
    source = item["title"] + (f" ({label})" if label else "")
    return {"id": item["evidence_id"][:128], "text": (text or "").strip()[:2000] or source[:128] or "(no text)", "source": re.sub(r"[^A-Za-z0-9_\-.:/ ]+", " ", source).strip()[:128]}


def _retrieve_passages(request: Request, session: Session, question: str):
    """Rank Flame hits for a natural-language question.

    Search ANDs its terms, so a whole sentence rarely matches. Search the sentence and each
    distinctive word, then prefer passages that several searches agree on.
    """
    found: dict[str, dict[str, Any]] = {}
    knowledge_version: str | None = None
    for position, term in enumerate([question, *_question_terms(question)]):
        result = search(request, q=term, page_size=5, session=session)
        if isinstance(result, JSONResponse):
            if result.status_code >= 500:
                return result
            continue
        knowledge_version = knowledge_version or result["retrieval"]["knowledge_version"]
        for item in result["results"]:
            evidence_id = item.get("evidence_id")
            if not evidence_id:
                continue
            entry = found.setdefault(evidence_id, {"hits": 0, "order": position * 10 + item["rank"], "item": item})
            entry["hits"] += 1
    ranked = sorted(found.values(), key=lambda entry: (-entry["hits"], entry["order"]))[:6]
    return [entry["item"] for entry in ranked], knowledge_version


@app.post("/api/chat", tags=["Research"])
def chat(request: Request, body: ChatBody, session: Session = Depends(get_session)):
    """Dashboard chat: Flame retrieves its own evidence; the model router picks who writes the answer.

    In the contract with `x-aura-exclude: true`: AURA derives its tools from that contract and must
    not be able to call back into its own caller.
    """
    question = body.query.strip()
    if not question:
        return JSONResponse(status_code=400, content=error_body(request, "VALIDATION_ERROR", "Question is empty."))
    router = ai_runtime.get_router(settings)
    if not router.available("chat.answer"):
        return JSONResponse(
            status_code=503,
            content=error_body(
                request, "CHAT_UNAVAILABLE",
                f"No language model is configured or permitted in {router.mode.value} mode.",
                details={"mode": router.mode.value},
            ),
        )
    if _chat_rate_limited():
        return JSONResponse(
            status_code=429,
            content=error_body(request, "RATE_LIMITED", "Too many chat requests. Try again shortly.", retryable=True),
            headers={"Retry-After": "10"},
        )
    started = time.perf_counter()
    cache_version = current_knowledge_version(session) or "unversioned"
    cache_key = answer_cache.make_key(question, knowledge_version=cache_version, instructions=CHAT_INSTRUCTIONS, mode=router.mode.value)
    cached = answer_cache.lookup(cache_key, cache_version)
    if cached is not None:
        return {**cached, "request_id": request.state.request_id, "cache_hit": True}
    with telemetry.span("chat.retrieve", **{"flame.request_id": request.state.request_id}) as current:
        retrieved = _retrieve_passages(request, session, question)
        if not isinstance(retrieved, JSONResponse):
            telemetry.set_attributes(current, **{"flame.passages": len(retrieved[0])})
    if isinstance(retrieved, JSONResponse):
        return retrieved
    items, knowledge_version = retrieved
    knowledge_version = knowledge_version or current_knowledge_version(session)
    base = {
        "request_id": request.state.request_id,
        "memory_used": False,
        "knowledge_version": knowledge_version or "unversioned",
    }
    if not items:
        return {
            **base,
            "answer": (
                "The Flame corpus has no passages matching this question, so there is nothing to ground an "
                "answer on. Try a specific term such as a fuel, an instrument or a test name."
            ),
            "sources": [],
            "cache_hit": False,
            "model": {"provider": "flame", "name": "retrieval-only", "version": "n/a"},
            "execution": None,
            "warnings": ["no_matching_evidence"],
        }

    def source_entry(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_id": item["evidence_id"],
            "document_id": item.get("document_id") or item.get("experiment_id") or "",
            "title": item["title"],
            "location": (item.get("locator") or {}).get("label") or item["result_type"],
        }

    try:
        with telemetry.span("chat.generate", **{"flame.request_id": request.state.request_id, "flame.knowledge_version": knowledge_version}):
            result = answer_question(
                router, request_id=request.state.request_id, question=question, passages=[_passage(i) for i in items]
            )
    except NoCompatibleProvider as exc:
        # Degraded mode (2H): say plainly that no model could write an answer, but still hand back the
        # evidence that was found, so the user keeps everything that still works.
        logger.warning("request_id=%s chat_generation_unavailable %s", request.state.request_id, exc.to_dict())
        return {
            **base,
            "answer": (
                "No language model could write an answer right now, so here is the evidence Flame found for "
                "this question without a summary. Nothing below was generated."
            ),
            "sources": [source_entry(item) for item in items],
            "cache_hit": False,
            "model": {"provider": "flame", "name": "retrieval-only", "version": "n/a"},
            "execution": {"mode": exc.mode.value, "reasons": exc.reasons},
            "warnings": ["generation_unavailable"],
        }
    by_id = {item["evidence_id"]: item for item in items}
    sources = [source_entry(by_id[evidence_id]) for evidence_id in result["evidence_ids"]]
    warnings = []
    if result["dropped_citations"]:
        warnings.append("citations_not_in_retrieved_evidence_removed")
    if not sources:
        warnings.append("answer_cites_no_evidence")
    execution = result["execution"]
    if execution["fallback_used"]:
        warnings.append("model_fallback_used")
    logger.info(
        "request_id=%s chat passages=%d cited=%d dropped=%d provider=%s locality=%s",
        request.state.request_id, len(items), len(sources), result["dropped_citations"],
        execution["provider"], execution["locality"],
    )
    response = {
        **base,
        "answer": result["answer"],
        "sources": sources,
        "cache_hit": False,
        "model": {"provider": result["provider"], "name": result["model"], "version": execution.get("version") or "unknown"},
        "execution": execution,
        "warnings": warnings,
    }
    if not warnings and sources:
        answer_cache.store(cache_key, response, knowledge_version=cache_version, instructions=CHAT_INSTRUCTIONS, started=started)
    return response


@app.get("/api/ai/providers", tags=["System"])
def ai_providers(request: Request):
    """Execution mode, every registered provider, its health and circuit state (2H Task 8)."""
    status = _ai_status()
    return {**status, "meta": response_meta(request)}


class ModeBody(BaseModel):
    mode: ExecutionMode


@app.put("/api/admin/ai/mode", tags=["Admin"])
def set_ai_mode(request: Request, body: ModeBody, session: Session = Depends(get_session)):
    """Switch cloud_preferred / local_first / offline_only. Write token; every change is audited."""
    change = ai_runtime.set_mode(
        session, body.mode, router=ai_runtime.get_router(settings), actor="write-token", request_id=request.state.request_id
    )
    return {**change, "meta": response_meta(request)}


_LIST_MAX_PAGE_SIZE = 100


@app.get("/api/documents", tags=["Research"])
def list_documents(
    request: Request,
    source_id: Annotated[list[str] | None, Query(max_length=20)] = None,
    document_type: str | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=_LIST_MAX_PAGE_SIZE)] = 20,
    session: Session = Depends(get_session),
):
    query = session.query(DocumentRecord).options(joinedload(DocumentRecord.source))
    if source_id:
        query = query.filter(DocumentRecord.source_id.in_(source_id))
    if document_type:
        query = query.filter(DocumentRecord.document_type == document_type)
    if q and q.strip():
        query = query.filter(DocumentRecord.title.ilike(f"%{q.strip()}%"))
    total = query.count()
    rows = query.order_by(func.lower(DocumentRecord.title), DocumentRecord.document_id).offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "document_id": d.document_id,
            "title": d.title,
            "document_type": d.document_type,
            "source": _source_payload(d.source),
            "page_count": d.page_count,
            "text_layer": d.text_layer,
            "parser_version": d.parser_version,
            "ingested_at": _timestamp(d.ingested_at),
            "knowledge_version": d.knowledge_version,
        }
        for d in rows
    ]
    return {"items": items, "pagination": _pagination(page, page_size, total), "meta": response_meta(request)}


@app.get("/api/experiments", tags=["Research"])
def list_experiments(
    request: Request,
    source_id: Annotated[list[str] | None, Query(max_length=20)] = None,
    gravity_regime: str | None = None,
    fuel_or_material: Annotated[str | None, Query(max_length=200)] = None,
    investigation: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=_LIST_MAX_PAGE_SIZE)] = 20,
    session: Session = Depends(get_session),
):
    query = session.query(ExperimentRecord).options(joinedload(ExperimentRecord.source))
    if source_id:
        query = query.filter(ExperimentRecord.source_id.in_(source_id))
    if gravity_regime:
        query = query.filter(ExperimentRecord.gravity_regime == gravity_regime)
    if fuel_or_material and fuel_or_material.strip():
        query = query.filter(ExperimentRecord.fuel_or_material.ilike(f"%{fuel_or_material.strip()}%"))
    if investigation and investigation.strip():
        query = query.filter(ExperimentRecord.investigation.ilike(f"%{investigation.strip()}%"))
    total = query.count()
    rows = (
        query.order_by(ExperimentRecord.source_id, ExperimentRecord.test_id, ExperimentRecord.experiment_id)
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    counts = dict(
        session.query(ExperimentCondition.experiment_id, func.count(ExperimentCondition.condition_id))
        .filter(ExperimentCondition.experiment_id.in_([e.experiment_id for e in rows]))
        .group_by(ExperimentCondition.experiment_id).all()
    ) if rows else {}
    items = [
        {
            "experiment_id": e.experiment_id,
            "test_id": e.test_id,
            "investigation": e.investigation,
            "source": _source_payload(e.source),
            "gravity_regime": e.gravity_regime,
            "fuel_or_material": e.fuel_or_material,
            "condition_count": counts.get(e.experiment_id, 0),
        }
        for e in rows
    ]
    return {"items": items, "pagination": _pagination(page, page_size, total), "meta": response_meta(request)}

@app.get("/api/documents/{document_id}", tags=["Research"])
def get_document(request: Request, document_id: Annotated[str, ApiPath(pattern=ULID_PATTERN)], session: Session = Depends(get_session)):
    document = session.query(DocumentRecord).options(joinedload(DocumentRecord.source), joinedload(DocumentRecord.file), joinedload(DocumentRecord.chunks)).filter_by(document_id=document_id).one_or_none()
    if document is None:
        return _not_found(request, "DOCUMENT_NOT_FOUND", "Document", document_id)
    payload = {
        "document_id": document.document_id,
        "title": document.title,
        "document_type": document.document_type,
        "identifier": document.identifier,
        "persistent_identifier": document.persistent_identifier,
        "source": _source_payload(document.source),
        "file": _file_payload(document.file),
        "page_count": document.page_count,
        "text_layer": document.text_layer,
        "pages_without_text": document.pages_without_text,
        "parser_version": document.parser_version,
        "ingested_at": document.ingested_at.isoformat().replace("+00:00", "Z"),
        "knowledge_version": document.knowledge_version,
        "experiment_ids": [],
        "evidence_count": session.query(EvidenceRecord).filter_by(document_id=document_id).count(),
    }
    return {"document": payload, "meta": response_meta(request)}


@app.get("/api/experiments/{experiment_id}", tags=["Research"])
def get_experiment(request: Request, experiment_id: Annotated[str, ApiPath(pattern=ULID_PATTERN)], session: Session = Depends(get_session)):
    experiment = session.query(ExperimentRecord).options(joinedload(ExperimentRecord.conditions), joinedload(ExperimentRecord.source)).filter_by(experiment_id=experiment_id).one_or_none()
    if experiment is None:
        return _not_found(request, "EXPERIMENT_NOT_FOUND", "Experiment", experiment_id)
    payload = {
        "experiment_id": experiment.experiment_id,
        "test_id": experiment.test_id,
        "investigation": experiment.investigation,
        "source": _source_payload(experiment.source),
        "gravity_regime": experiment.gravity_regime,
        "fuel_or_material": experiment.fuel_or_material,
        "conditions": [
            {"variable": c.variable, "value_numeric": c.value_numeric, "value_text": c.value_text, "unit_original": c.unit_original, "value_si": c.value_si, "unit_si": c.unit_si, "origin": c.origin, "evidence_id": c.evidence_id}
            for c in experiment.conditions
        ],
        "document_ids": [],
        "table_file": _file_payload(experiment.table_file) if experiment.table_file_id else None,
    }
    return {"experiment": payload, "meta": response_meta(request)}


@app.get("/api/evidence/{evidence_id}", tags=["Evidence"])
def get_evidence(request: Request, evidence_id: Annotated[str, ApiPath(pattern=ULID_PATTERN)], session: Session = Depends(get_session)):
    evidence = session.query(EvidenceRecord).options(joinedload(EvidenceRecord.source), joinedload(EvidenceRecord.file)).filter_by(evidence_id=evidence_id).one_or_none()
    if evidence is None:
        return _not_found(request, "EVIDENCE_NOT_FOUND", "Evidence", evidence_id)
    payload = dict(evidence.payload)
    payload.update({"evidence_id": evidence.evidence_id, "kind": evidence.kind, "origin": evidence.origin, "document_id": evidence.document_id, "experiment_id": evidence.experiment_id, "analysis_id": evidence.analysis_id, "locator": evidence.locator, "excerpt": evidence.excerpt, "created_at": _timestamp(evidence.created_at), "knowledge_version": payload.get("knowledge_version")})
    payload["source"] = _source_payload(evidence.source) if evidence.source else None
    payload["file"] = _file_payload(evidence.file) if evidence.file else None
    return {"evidence": payload, "meta": response_meta(request)}
