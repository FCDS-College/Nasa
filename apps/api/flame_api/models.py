from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


JsonType = JSON().with_variant(JSONB, "postgresql")


class SourceRecord(Base):
    __tablename__ = "source"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    short_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    repository: Mapped[str] = mapped_column(Text)
    persistent_identifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(32), default="combustion", index=True)


class FileRecord(Base):
    __tablename__ = "file_record"

    file_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("source.source_id"), index=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    original_filename: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    canonical_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_original: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_file_id: Mapped[str | None] = mapped_column(ForeignKey("file_record.file_id"), nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # active | quarantined (M9). A quarantined file is kept for review but never parsed or indexed.
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active", index=True)
    quarantine_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class DocumentRecord(Base):
    __tablename__ = "document"

    document_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("source.source_id"), index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("file_record.file_id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    document_type: Mapped[str] = mapped_column(String(48), default="other")
    identifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    persistent_identifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_layer: Mapped[str] = mapped_column(String(24), default="unknown")
    pages_without_text: Mapped[list[int]] = mapped_column(JsonType, default=list)
    parser_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    knowledge_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    source: Mapped[SourceRecord] = relationship()
    file: Mapped[FileRecord] = relationship()
    chunks: Mapped[list[DocumentChunk]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunk"

    chunk_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("document.document_id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("source.source_id"), index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("file_record.file_id"), index=True)
    evidence_id: Mapped[str] = mapped_column(String(26), index=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    document: Mapped[DocumentRecord] = relationship(back_populates="chunks")
    __table_args__ = (Index("ix_document_chunk_source_page", "source_id", "page"),)


class ExperimentRecord(Base):
    __tablename__ = "experiment"

    experiment_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("source.source_id"), index=True)
    test_id: Mapped[str] = mapped_column(Text)
    investigation: Mapped[str | None] = mapped_column(Text, nullable=True)
    gravity_regime: Mapped[str] = mapped_column(String(32), default="unknown")
    fuel_or_material: Mapped[str | None] = mapped_column(Text, nullable=True)
    table_file_id: Mapped[str | None] = mapped_column(ForeignKey("file_record.file_id"), nullable=True)
    searchable_text: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    # When ingest.py last wrote this row (migration 0006). Nullable only for rows that predate it and
    # had no ingestion run or table file to backfill from.
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[SourceRecord] = relationship()
    table_file: Mapped[FileRecord | None] = relationship(foreign_keys=[table_file_id])
    conditions: Mapped[list[ExperimentCondition]] = relationship(back_populates="experiment", cascade="all, delete-orphan")


class ExperimentCondition(Base):
    __tablename__ = "experiment_condition"

    condition_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiment.experiment_id", ondelete="CASCADE"), index=True)
    variable: Mapped[str] = mapped_column(Text)
    value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_si: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_si: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str] = mapped_column(String(32))
    evidence_id: Mapped[str] = mapped_column(String(26), index=True)

    experiment: Mapped[ExperimentRecord] = relationship(back_populates="conditions")


class EvidenceRecord(Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("source.source_id"), nullable=True, index=True)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("file_record.file_id"), nullable=True, index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("document.document_id"), nullable=True, index=True)
    experiment_id: Mapped[str | None] = mapped_column(ForeignKey("experiment.experiment_id"), nullable=True, index=True)
    analysis_id: Mapped[str | None] = mapped_column(String(26), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32))
    origin: Mapped[str] = mapped_column(String(32))
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[SourceRecord | None] = relationship(foreign_keys=[source_id])
    file: Mapped[FileRecord | None] = relationship(foreign_keys=[file_id])


class AnalysisRecord(Base):
    __tablename__ = "analysis_result"

    analysis_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    experiment_id: Mapped[str | None] = mapped_column(ForeignKey("experiment.experiment_id"), nullable=True, index=True)
    image_sha256: Mapped[str] = mapped_column(String(64), index=True)
    original_filename: Mapped[str] = mapped_column(Text)
    pipeline_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Set by POST /api/analyses/{id}/cancel while the job is processing; the worker stops at its next
    # checkpoint (video) or before storing its result (image) and marks the analysis cancelled (ADR-008).
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    artifacts: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_analysis_idempotency_key"),)


class VideoCheckpointFrame(Base):
    """One sampled frame a running video job has measured (ADR-008 per-segment checkpoint).

    The worker writes a segment of rows at a time, so a job re-queued after a crash (worker.recover)
    resumes after the last stored segment, even on a new container. `job_digest` identifies the video,
    pipeline version and sampling; rows from another digest are ignored on resume. Rows are deleted
    when the analysis reaches a terminal state.
    """

    __tablename__ = "video_checkpoint_frame"

    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_result.analysis_id", ondelete="CASCADE"),
                                             primary_key=True)
    frame_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[str] = mapped_column(String(64))
    job_digest: Mapped[str] = mapped_column(String(64))
    row: Mapped[dict[str, Any]] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IngestionRun(Base):
    __tablename__ = "ingestion_run"

    run_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("source.source_id"), index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("file_record.file_id"), index=True)
    transformation_id: Mapped[str] = mapped_column(String(80))
    input_sha256: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    counts: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    __table_args__ = (UniqueConstraint("file_id", "transformation_id", "input_sha256", name="uq_ingestion_file_transform"),)


# --- Phase 2 M8 tables (migration 0004_phase2_tables). Schemas: docs/data/DATA_DICTIONARY.md. ---


class KnowledgeEntity(Base):
    """A node of the scientific knowledge graph (D2). IDs are stable_ulid(entity_type + canonical_name)."""

    __tablename__ = "knowledge_entity"

    entity_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(48), index=True)
    canonical_name: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list[str]] = mapped_column(JsonType, default=list)
    properties: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("source.source_id"), nullable=True, index=True)
    evidence_ids: Mapped[list[str]] = mapped_column(JsonType, default=list)
    review_status: Mapped[str] = mapped_column(String(16), default="unreviewed")
    merged_into: Mapped[str | None] = mapped_column(ForeignKey("knowledge_entity.entity_id"), nullable=True)
    knowledge_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("entity_type", "canonical_name", name="uq_knowledge_entity_type_name"),)


class KnowledgeRelation(Base):
    """A directed, evidence-backed edge between two entities (D2, D6)."""

    __tablename__ = "knowledge_relation"

    relation_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("knowledge_entity.entity_id", ondelete="CASCADE"), index=True)
    predicate: Mapped[str] = mapped_column(String(64), index=True)
    object_id: Mapped[str] = mapped_column(ForeignKey("knowledge_entity.entity_id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[str | None] = mapped_column(String(26), nullable=True, index=True)
    extraction_method: Mapped[str] = mapped_column(String(48))
    extractor_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[str] = mapped_column(String(16), default="unreviewed")
    properties: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    knowledge_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("subject_id", "predicate", "object_id", "evidence_id", name="uq_knowledge_relation_edge"),
    )


class MemoryRecord(Base):
    """Session/project memory (M5 MAG). Every row carries scope, origin, confidence and expiry."""

    __tablename__ = "memory"

    memory_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    scope: Mapped[str] = mapped_column(String(16), index=True)
    actor: Mapped[str] = mapped_column(String(128))
    conversation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    superseded_by: Mapped[str | None] = mapped_column(ForeignKey("memory.memory_id"), nullable=True)


class CacheEntry(Base):
    """Durable index of CAG entries (M4). The value lives in Redis; this row is its dependency manifest."""

    __tablename__ = "cache_entry"

    cache_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    knowledge_version: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    dependencies: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)


class ModelRecord(Base):
    """Model registry (C1, 2H Task 4). Seeded from ai/routing/model_manifest.json."""

    __tablename__ = "model"

    model_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    capability: Mapped[str] = mapped_column(String(32), index=True)
    provider: Mapped[str] = mapped_column(String(48))
    runtime: Mapped[str] = mapped_column(String(48))
    name: Mapped[str] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantization: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    locality: Mapped[str] = mapped_column(String(16))
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="candidate")
    model_card: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DatasetRecord(Base):
    """A versioned dataset built from sources (evaluation sets, CV sets, derived corpora)."""

    __tablename__ = "dataset"

    dataset_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str | None] = mapped_column(ForeignKey("source.source_id"), nullable=True, index=True)
    split: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    item_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    license: Mapped[str | None] = mapped_column(Text, nullable=True)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("name", "version", name="uq_dataset_name_version"),)


class ImageAsset(Base):
    """An image or video frame known to Flame, with lineage to the file it came from."""

    __tablename__ = "image_asset"

    image_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("file_record.file_id"), nullable=True, index=True)
    parent_file_id: Mapped[str | None] = mapped_column(ForeignKey("file_record.file_id"), nullable=True, index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("source.source_id"), nullable=True, index=True)
    analysis_id: Mapped[str | None] = mapped_column(String(26), nullable=True, index=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    media_type: Mapped[str] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    derivation: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    """Append-only audit log for admin and configuration changes (B6, 2H mode changes)."""

    __tablename__ = "audit_event"

    event_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str] = mapped_column(String(48))
    target_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    before: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class KnowledgePublication(Base):
    """One row per published knowledge_version (M4). The row, not the Redis message, is authoritative."""

    __tablename__ = "knowledge_publication"

    publication_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    knowledge_version: Mapped[str] = mapped_column(Text, unique=True)
    previous_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str] = mapped_column(String(32))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class ApiClient(Base):
    """One row per API caller (P2-1, ADR-009 step 2): `web`, `aura`, an operator's script.

    Only the SHA-256 of the key is stored; the key itself is printed once by
    `python -m flame_api.clients create`. Scopes are any of `read`, `write` and `admin`; an `admin`
    client always has an `owner`, the person accountable for what it does (ADR-009).
    """

    __tablename__ = "api_client"

    client_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scopes: Mapped[list[str]] = mapped_column(JsonType, default=list)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
