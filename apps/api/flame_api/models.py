from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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
    size_bytes: Mapped[int] = mapped_column(Integer)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    canonical_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_original: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_file_id: Mapped[str | None] = mapped_column(ForeignKey("file_record.file_id"), nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)


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
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    artifacts: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_analysis_idempotency_key"),)


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
