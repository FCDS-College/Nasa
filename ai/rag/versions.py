"""Versions recorded for every retrieval/answer request (for reproducibility)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PipelineVersions(BaseModel):
    embedding_model: str
    chunker: str
    reranker: str
    corpus_version: str
    retrieval_config: str = "1.0.0"
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    llm_model: str | None = None
