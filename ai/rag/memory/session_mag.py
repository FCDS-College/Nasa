"""Session Memory-Augmented Generation (MAG).

Rules enforced here:
  * Memory is scoped to (user_id, conversation_id); no cross-user or
    cross-conversation reads.
  * Memory expires (TTL) and can be superseded or deleted.
  * Memory is CONTEXT, never scientific evidence: it is returned separately
    and rendered in <memory> tags, never merged into evidence passages.
  * Memory that conflicts with authoritative evidence is flagged and dropped.
"""
from __future__ import annotations

import re
import time
import uuid
from typing import Callable

from pydantic import BaseModel, Field, model_validator

from ai.interfaces import MemoryStore

ORIGINS = ("user", "extracted", "system_summary")
DEFAULT_TTL_SECONDS = 24 * 3600.0


def new_conversation_id() -> str:
    """Issue an unguessable conversation id."""
    return "conv_" + uuid.uuid4().hex[:16]


class MemoryRecord(BaseModel):
    """One session memory item (see docs/ai/mag-policy.md).

    Raises:
        ValueError: for an origin outside ORIGINS, confidence outside 0..1, expires_at <= created_at, or an empty user_id/conversation_id."""

    id: str = Field(default_factory=lambda: "mem_" + uuid.uuid4().hex[:12])
    user_id: str
    conversation_id: str
    scope: str = "session"
    actor: str = "user"
    origin: str
    text: str
    confidence: float = 1.0
    created_at: float
    expires_at: float
    superseded_by: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    claim_key: str | None = None
    claim_value: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.origin not in ORIGINS:
            raise ValueError(f"origin must be one of {ORIGINS}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        if not self.user_id or not self.conversation_id:
            raise ValueError("user_id and conversation_id are required")
        return self


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class InMemorySessionMemory(MemoryStore):
    """Process-local session memory store scoped by user and conversation. Data is lost on restart."""
    def __init__(self, clock: Callable[[], float] = time.time):
        self._clock = clock
        self._records: dict[str, MemoryRecord] = {}

    def add(self, record: MemoryRecord) -> MemoryRecord:
        """Store a MemoryRecord (a record with the same id is replaced) and return it."""
        self._records[record.id] = record
        return record

    def add_text(
        self,
        user_id: str,
        conversation_id: str,
        text: str,
        origin: str = "user",
        confidence: float = 1.0,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        evidence_refs: list[str] | None = None,
        claim_key: str | None = None,
        claim_value: str | None = None,
    ) -> MemoryRecord:
        """Create and store a record from plain text.

        Args:
            user_id, conversation_id: owner and scope (required).
            text: memory content.
            origin: user, extracted or system_summary.
            confidence: 0..1.
            ttl_seconds: lifetime (default 24 hours).
            evidence_refs, claim_key, claim_value: optional provenance and conflict-check fields.

        Raises:
            ValueError: from MemoryRecord validation."""

        now = self._clock()
        return self.add(
            MemoryRecord(
                user_id=user_id,
                conversation_id=conversation_id,
                origin=origin,
                text=text,
                confidence=confidence,
                created_at=now,
                expires_at=now + ttl_seconds,
                evidence_refs=evidence_refs or [],
                claim_key=claim_key,
                claim_value=claim_value,
            )
        )

    def supersede(self, old_id: str, new_record: MemoryRecord) -> MemoryRecord:
        """Mark `old_id` as replaced by `new_record` (old stops being returned)."""
        self._records[old_id].superseded_by = new_record.id
        return self.add(new_record)

    def search(self, user_id: str, conversation_id: str, query: str, top_k: int = 5) -> list[MemoryRecord]:
        """Relevant, live memory for exactly this user and conversation."""
        now = self._clock()
        q = _tokens(query)
        scored = []
        for r in self._records.values():
            if r.user_id != user_id or r.conversation_id != conversation_id:
                continue
            if r.expires_at <= now or r.superseded_by is not None:
                continue
            overlap = len(q & _tokens(r.text))
            if overlap == 0:
                continue
            scored.append((overlap * r.confidence, r.created_at, r))
        scored.sort(key=lambda t: (-t[0], -t[1]))
        return [r for _, _, r in scored[:top_k]]

    def delete_conversation(self, user_id: str, conversation_id: str) -> int:
        """Delete every record of one user's conversation.

        Returns:
            The number of records deleted."""

        ids = [
            i for i, r in self._records.items()
            if r.user_id == user_id and r.conversation_id == conversation_id
        ]
        for i in ids:
            del self._records[i]
        return len(ids)

    def purge_expired(self) -> int:
        """Delete expired records.

        Returns:
            The number of records deleted."""

        now = self._clock()
        ids = [i for i, r in self._records.items() if r.expires_at <= now]
        for i in ids:
            del self._records[i]
        return len(ids)


def memory_disclosure(records: list[MemoryRecord]) -> list[dict]:
    """What the API/UI shows as `memory_used` for transparency."""
    return [
        {"id": r.id, "origin": r.origin, "snippet": r.text[:120], "created_at": r.created_at}
        for r in records
    ]


def flag_conflicts(records: list[MemoryRecord], evidence_chunks: list[dict]) -> tuple[list[MemoryRecord], list[dict]]:
    """Split memory into usable records and conflicts with authoritative evidence.

    A record conflicts when it has a `claim_key`/`claim_value` and a retrieved
    chunk's `metadata["facts"][claim_key]` has a different value. Evidence
    always wins; conflicting memory is dropped from the prompt.

    Returns:
        (usable_records, conflicts) where conflicts = [{memory_id, chunk_id, key, memory_value, evidence_value}]
    """
    usable, conflicts = [], []
    for r in records:
        clash = None
        if r.claim_key is not None:
            for c in evidence_chunks:
                facts = (c.get("metadata") or {}).get("facts", {})
                if r.claim_key in facts and str(facts[r.claim_key]) != str(r.claim_value):
                    clash = {
                        "memory_id": r.id,
                        "chunk_id": c["chunk_id"],
                        "key": r.claim_key,
                        "memory_value": r.claim_value,
                        "evidence_value": str(facts[r.claim_key]),
                    }
                    break
        if clash:
            conflicts.append(clash)
        else:
            usable.append(r)
    return usable, conflicts
