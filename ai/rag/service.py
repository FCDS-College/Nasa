"""FlameRAGService: wires the whole answer flow together.

question
  -> query rewrite (original + rewritten both recorded)
  -> session memory lookup (scoped to user + conversation)
  -> CAG lookup (skipped when memory is in play)
  -> retrieval (existing RAGRetrievalPipeline, optional real reranker)
  -> memory/evidence conflict check (evidence wins)
  -> grounded composer (citation validation + abstention)
  -> CAG store (never for answers that used memory)

Failure behaviour: if the reranker or retrieval is unavailable the service
returns status="retrieval_unavailable" with NO answer text. It never falls
back to an uncited answer.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from ai.rag.cache.cag import (
    DependencyManifest,
    build_cache_key,
    is_cacheable,
    ttl_for,
)
from ai.rag.dto import RetrievalRequest
from ai.rag.generation.composer import GroundedAnswerComposer
from ai.rag.generation.models import GroundedAnswer
from ai.rag.memory.session_mag import flag_conflicts, memory_disclosure
from ai.rag.query.rewrite import QueryRewriter
from ai.rag.reranking.cross_encoder import RerankerUnavailable

logger = logging.getLogger(__name__)

STATUS_UNAVAILABLE = "retrieval_unavailable"


class FlameResponse(BaseModel):
    """Response of FlameRAGService: original and rewritten query, the GroundedAnswer (None when retrieval is unavailable), status, cache_hit, memory used and conflicts, versions and error."""
    original_query: str
    rewritten_query: str
    answer: GroundedAnswer | None = None
    status: str
    cache_hit: bool = False
    memory_used: list[dict[str, Any]] = Field(default_factory=list)
    memory_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    versions: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class FlameRAGService:
    """Wires query rewrite, session memory, cache, retrieval, composer and failure handling (see docs/ai/retrieval-pipeline.md).

    If retrieval or the reranker fails the result has status "retrieval_unavailable" and no answer; it never returns an uncited answer."""

    def __init__(
        self,
        retrieval_pipeline,
        composer: GroundedAnswerComposer,
        corpus_version: str,
        embedding_model: str,
        chunker: str = "SimpleChunker@1",
        cache=None,
        memory=None,
        rewriter: QueryRewriter | None = None,
        reranker=None,
    ):
        """
        Args:
            retrieval_pipeline: src.retrieval.rag_retrieval_pipeline.RAGRetrievalPipeline.
            composer: GroundedAnswerComposer.
            corpus_version: current knowledge/corpus version string.
            embedding_model: embedding model name recorded per request.
            cache: optional CacheService (e.g. InMemoryCacheService).
            memory: optional MemoryStore (e.g. InMemorySessionMemory).
            rewriter: optional QueryRewriter (default rules if omitted).
            reranker: optional Reranker; replaces the pipeline's passthrough one.
        """
        self.pipeline = retrieval_pipeline
        self.composer = composer
        self.corpus_version = corpus_version
        self.embedding_model = embedding_model
        self.chunker = chunker
        self.cache = cache
        self.memory = memory
        self.rewriter = rewriter or QueryRewriter()
        if reranker is not None:
            self.pipeline.reranker = reranker
        self._reranker = getattr(self.pipeline, "reranker", None)

    # -- versions ------------------------------------------------------
    def _reranker_version(self) -> str:
        r = self._reranker
        name = getattr(r, "name", None)
        if name and name != "unknown":
            return f"{name}@{getattr(r, 'version', '0')}"
        return "passthrough@1"

    def _prompt_version(self) -> str:
        reg = self.composer.registry
        return "+".join(f"{pid}@{reg.get(pid).version}" for pid in ("system_scientific_qa", "grounded_answer"))

    def _llm_id(self) -> str:
        return f"{self.composer.llm.name}@{self.composer.llm.version}"

    def versions(self) -> dict[str, str]:
        """Return the versions recorded per request: embedding_model, chunker, reranker, corpus_version, prompt, llm."""
        return {
            "embedding_model": self.embedding_model,
            "chunker": self.chunker,
            "reranker": self._reranker_version(),
            "corpus_version": self.corpus_version,
            "prompt": self._prompt_version(),
            "llm": self._llm_id(),
        }

    # -- main entry ----------------------------------------------------
    def answer(
        self,
        question: str,
        chunks: list[dict],
        user_id: str | None = None,
        conversation_id: str | None = None,
        filters: dict | None = None,
        top_k: int = 5,
    ) -> FlameResponse:
        """Answer `question` using only `chunks` (the ingested corpus).

        Raises:
            ValueError: empty question.
        """
        rq = self.rewriter.rewrite(question)
        base = dict(
            original_query=rq.original,
            rewritten_query=rq.rewritten,
            versions=self.versions(),
        )

        # memory candidates (context only)
        candidates = []
        if self.memory and user_id and conversation_id:
            candidates = self.memory.search(user_id, conversation_id, rq.rewritten)

        # cache lookup (never when memory could change the answer)
        key = None
        if self.cache is not None and not candidates:
            key = build_cache_key(
                query=rq.rewritten,
                filters=filters,
                top_k=top_k,
                corpus_version=self.corpus_version,
                prompt_version=self._prompt_version(),
                model=self._llm_id(),
                reranker_version=self._reranker_version(),
            )
            hit = self.cache.get(key)
            if hit is not None:
                return FlameResponse(**{**base, "answer": hit, "status": hit.status, "cache_hit": True})

        # retrieval (explicit failure, never an uncited fallback)
        started = time.perf_counter()
        try:
            bundle = self.pipeline.retrieve(
                request=RetrievalRequest(query=rq.rewritten, top_k=top_k, filters=filters or {}),
                chunks=chunks,
            )
        except RerankerUnavailable as exc:
            logger.error("reranker unavailable: %s", exc)
            return FlameResponse(**base, status=STATUS_UNAVAILABLE, error=f"reranker unavailable: {exc}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("retrieval failed")
            return FlameResponse(**base, status=STATUS_UNAVAILABLE, error=f"retrieval failed: {exc}")

        # evidence wins over memory
        usable, conflicts = flag_conflicts(candidates, [c.model_dump() for c in bundle.evidence])

        t_answer = self.composer.compose(question, bundle, memory=usable)
        compute_ms = (time.perf_counter() - started) * 1000

        if key is not None and is_cacheable(t_answer):
            manifest = DependencyManifest(
                corpus_version=self.corpus_version,
                document_versions={c.document_id: c.document_version for c in bundle.evidence},
                chunk_ids=[c.chunk_id for c in bundle.evidence],
                prompt_versions={k: v for k, v in t_answer.versions.items() if k != "llm"},
                model=self._llm_id(),
                embedding_model=self.embedding_model,
                reranker_version=self._reranker_version(),
                provider=self.composer.llm.name,
                execution_mode=getattr(self.composer.llm, "execution_mode", ""),
            )
            self.cache.set(key, t_answer, ttl_for(t_answer), manifest.model_dump(), compute_ms=compute_ms)

        return FlameResponse(
            **base,
            answer=t_answer,
            status=t_answer.status,
            cache_hit=False,
            memory_used=memory_disclosure(usable),
            memory_conflicts=conflicts,
        )
