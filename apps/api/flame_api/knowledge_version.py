"""Knowledge-version publication (M4, E2-5).

A knowledge version names one consistent state of the indexed corpus. Publishing it writes a
``knowledge_publication`` row (the source of truth) and then announces it on the Redis channel
``flame:knowledge.published`` (best effort). Consumers — CAG invalidation (E1), vector and graph
index sync — react to the message, and on startup or after a missed message they compare their
own version against ``current_knowledge_version`` and catch up from the table.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from flame_api.ids import stable_ulid
from flame_api.models import KnowledgePublication

logger = logging.getLogger("flame_api")

CHANNEL = "flame:knowledge.published"
EVENT_TYPE = "knowledge_version.published"
SCHEMA_VERSION = "1.0.0"
TRIGGERS = frozenset({"vector_index_build", "ingestion", "manual", "rollback", "sync"})


def current_knowledge_version(session: Session) -> str | None:
    return session.execute(
        select(KnowledgePublication.knowledge_version).order_by(KnowledgePublication.published_at.desc()).limit(1)
    ).scalar_one_or_none()


def build_event(publication: KnowledgePublication) -> dict[str, Any]:
    return {
        "type": EVENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "publication_id": publication.publication_id,
        "knowledge_version": publication.knowledge_version,
        "previous_version": publication.previous_version,
        "trigger": publication.trigger,
        "published_at": publication.published_at.isoformat().replace("+00:00", "Z"),
        "counts": publication.payload.get("counts", {}),
    }


def _announce(event: dict[str, Any], redis_url: str | None) -> bool:
    if not redis_url:
        return False
    try:
        from redis import Redis

        Redis.from_url(redis_url, socket_connect_timeout=0.5, socket_timeout=0.5).publish(CHANNEL, json.dumps(event))
        return True
    except Exception:  # Redis down or offline: the table row still records the publication
        logger.warning("knowledge_version_announce_failed version=%s", event["knowledge_version"])
        return False


def publish(
    session: Session,
    knowledge_version: str,
    *,
    trigger: str,
    counts: dict[str, Any] | None = None,
    redis_url: str | None = None,
) -> dict[str, Any]:
    """Record and announce a version. Idempotent: republishing an existing version returns it unchanged."""
    if trigger not in TRIGGERS:
        raise ValueError(f"unknown publication trigger {trigger!r}")
    existing = session.execute(
        select(KnowledgePublication).where(KnowledgePublication.knowledge_version == knowledge_version)
    ).scalar_one_or_none()
    if existing is not None and trigger != "rollback":
        return build_event(existing)
    previous = current_knowledge_version(session)
    if existing is not None:   # rollback: re-publish an older version as the newest row
        session.delete(existing)
        session.flush()
    now = datetime.now(UTC)
    publication = KnowledgePublication(
        publication_id=stable_ulid(f"knowledge-publication:{knowledge_version}:{now.isoformat()}"),
        knowledge_version=knowledge_version,
        previous_version=previous if previous != knowledge_version else None,
        trigger=trigger,
        published_at=now,
        payload={"counts": counts or {}},
    )
    session.add(publication)
    session.commit()
    event = build_event(publication)
    event["announced"] = _announce(event, redis_url)
    logger.info("knowledge_version_published version=%s previous=%s trigger=%s", knowledge_version, previous, trigger)
    return event
