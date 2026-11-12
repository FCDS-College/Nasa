"""Read API for the knowledge graph (ADR-007, E2-6). Read scope; the consistency report is admin data.

The graph is derived from the ingested tables by `flame_api.knowledge_graph` (deterministic table
parse, every edge citing its evidence row). Rejected edges are never returned.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Path as ApiPath, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from flame_api import knowledge_graph as kg
from flame_api.admin import require_admin_scope
from flame_api.contracts import error_body, response_meta
from flame_api.database import get_session
from flame_api.models import KnowledgeEntity, KnowledgeRelation

router = APIRouter(tags=["Knowledge graph"])
admin_router = APIRouter(tags=["Admin"], dependencies=[Depends(require_admin_scope)])
ULID_PATTERN = r"^[0-9A-HJKMNP-TV-Z]{26}$"
EntityType = Literal["investigation", "experiment", "fuel", "condition_variable", "phenomenon", "document"]
Predicate = Literal["part_of", "uses_fuel", "has_condition", "observed", "describes"]


def _entity(entity: KnowledgeEntity, depth: int | None = None) -> dict[str, Any]:
    body = {
        "entity_id": entity.entity_id,
        "entity_type": entity.entity_type,
        "canonical_name": entity.canonical_name,
        "display_name": (entity.properties or {}).get("display_name") or entity.canonical_name,
        "aliases": list(entity.aliases or []),
        "properties": {k: v for k, v in (entity.properties or {}).items() if k != "display_name"},
        "source_id": entity.source_id,
        "evidence_ids": list(entity.evidence_ids or []),
        "review_status": entity.review_status,
        "merged_into": entity.merged_into,
        "knowledge_version": entity.knowledge_version,
    }
    if depth is not None:
        body["depth"] = depth
    return body


def _edge(relation: KnowledgeRelation) -> dict[str, Any]:
    return {
        "relation_id": relation.relation_id,
        "subject_id": relation.subject_id,
        "predicate": relation.predicate,
        "object_id": relation.object_id,
        "evidence_id": relation.evidence_id,
        "extraction_method": relation.extraction_method,
        "extractor_version": relation.extractor_version,
        "confidence": relation.confidence,
        "review_status": relation.review_status,
        "properties": dict(relation.properties or {}),
    }


@router.get("/api/graph/entities")
def list_entities(
    request: Request,
    entity_type: Annotated[EntityType | None, Query(alias="type")] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    session: Session = Depends(get_session),
):
    """Live (unmerged) entities, by type and a case-insensitive match on the name or an alias."""
    query = select(KnowledgeEntity).where(KnowledgeEntity.merged_into.is_(None))
    if entity_type:
        query = query.where(KnowledgeEntity.entity_type == entity_type)
    if q:
        needle = f"%{q.strip().lower()}%"
        query = query.where(or_(KnowledgeEntity.canonical_name.like(needle),
                                func.lower(cast(KnowledgeEntity.aliases, String)).like(needle)))
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.scalars(query.order_by(KnowledgeEntity.entity_type, KnowledgeEntity.canonical_name, KnowledgeEntity.entity_id)
                           .offset((page - 1) * page_size).limit(page_size)).all()
    relations = dict(session.execute(
        select(KnowledgeEntity.entity_id, func.count(KnowledgeRelation.relation_id))
        .join(KnowledgeRelation, or_(KnowledgeRelation.subject_id == KnowledgeEntity.entity_id,
                                     KnowledgeRelation.object_id == KnowledgeEntity.entity_id))
        .where(KnowledgeEntity.entity_id.in_([r.entity_id for r in rows]), KnowledgeRelation.review_status != "rejected")
        .group_by(KnowledgeEntity.entity_id)).all()) if rows else {}
    return {
        "items": [{**_entity(row), "relation_count": relations.get(row.entity_id, 0)} for row in rows],
        "pagination": {"page": page, "page_size": page_size, "total_items": total,
                       "total_pages": (total + page_size - 1) // page_size if total else 0},
        "meta": response_meta(request),
    }


@router.get("/api/graph/entities/{entity_id}")
def get_entity(
    request: Request,
    entity_id: Annotated[str, ApiPath(pattern=ULID_PATTERN)],
    depth: Annotated[int, Query(ge=1, le=kg.MAX_DEPTH)] = 1,
    predicate: Annotated[list[Predicate] | None, Query(max_length=5)] = None,
    max_edges: Annotated[int, Query(ge=1, le=500)] = 200,
    session: Session = Depends(get_session),
):
    """One entity and its neighbourhood (recursive CTE, both directions), every edge with its provenance."""
    entity = kg.resolve(session, entity_id)
    if entity is None:
        return JSONResponse(status_code=404, content=error_body(
            request, "ENTITY_NOT_FOUND", "Knowledge-graph entity was not found.", details={"resource_id": entity_id}))
    found = kg.neighbourhood(session, entity.entity_id, depth=depth, predicates=list(predicate) if predicate else None,
                             max_edges=max_edges)
    return {
        "entity": _entity(entity),
        "resolved_from": entity_id if entity.entity_id != entity_id else None,
        "neighbourhood": {
            "depth": depth,
            "predicates": list(predicate or []),
            "entities": [_entity(e, found["depths"].get(e.entity_id, 0)) for e in found["entities"]],
            "edges": [_edge(r) for r in found["edges"]],
            "truncated": found["truncated"],
            "reachable_entities": found["reachable_entities"],
            "reachable_by_type": found["reachable_by_type"],
        },
        "meta": response_meta(request),
    }


@admin_router.get("/api/admin/graph/consistency")
def graph_consistency(request: Request, session: Session = Depends(get_session)):
    """E2-6 §5 consistency checks. `ok` is false when a blocking check finds anything."""
    report = kg.check_consistency(session)
    ok = report.pop("ok")
    return {"ok": ok, "extractor_version": kg.EXTRACTOR_VERSION, "checks": report, "meta": response_meta(request)}
