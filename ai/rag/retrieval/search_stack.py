"""Flame's one retrieval stack (ADR-006): query rewrite, Reciprocal Rank Fusion, reranking, paging.

The API's `/api/search` (and through it `/api/chat`) calls this module. The API keeps only data
access: it fetches candidates from PostgreSQL full-text search and pgvector, with every filter
applied in SQL, and hands each candidate here with its 1-based rank in each ranked list it appears
in. Everything that decides the order lives here:

1. ``plan(query)``: the rule-based rewrite (``ai.rag.query.rewrite``) is kept next to the original.
   Lexical search uses the original, because ``plainto_tsquery`` requires every term and appended
   expansions would only narrow it; semantic search embeds the rewritten query.
2. ``rank(...)``: RRF, ``score = sum(1 / (k + rank))`` over the lists a candidate appears in
   (``k = 60``), ties broken by result type and ID, so the order is deterministic.
3. Optional reranking of the first ``depth`` fused results by a cross-encoder reached through
   the model router's ``rerank`` task. Only the order inside that window changes: the reranked
   results take over the window's fused scores in their new order, so ``score`` stays monotonic
   with ``rank`` and results after the window keep their fused order and score. The window does
   not depend on the page, so paging stays exact. A reranker that fails leaves the fused order
   and is reported as ``unavailable``; it never fails the search.

Pure Python, no storage or model imports: the reranker is passed in as a callable.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from ai.rag.query.rewrite import QueryRewriter

STACK_VERSION = "flame-search-2.0.0"
RRF_K = 60
DEFAULT_RERANK_DEPTH = 20


class RerankUnavailable(RuntimeError):
    """The reranker could not score the window; the fused order is kept."""


# (query, [(result_id, text), ...]) -> ({result_id: score}, model name). Higher score is more relevant.
RerankFn = Callable[[str, Sequence[tuple[str, str]]], tuple[dict[str, float], str]]


@dataclass(frozen=True)
class QueryPlan:
    original: str
    rewritten: str
    rules_applied: tuple[str, ...]
    rewriter_version: str

    @property
    def lexical_query(self) -> str:
        return self.original

    @property
    def semantic_query(self) -> str:
        return self.rewritten

    def as_dict(self) -> dict:
        return {
            "rewritten": self.rewritten,
            "changed": self.rewritten != self.original,
            "rules_applied": list(self.rules_applied),
            "rewriter_version": self.rewriter_version,
            "used_for": ["semantic"],
        }


@dataclass(frozen=True)
class Candidate:
    """One hit to rank. ``ranks`` maps a ranked list's name to the candidate's 1-based position in it."""

    result_id: str
    result_type: str
    text: str
    ranks: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Ranked:
    candidate: Candidate
    score: float
    fused_score: float
    rerank_score: float | None = None


@dataclass(frozen=True)
class RerankOutcome:
    status: str  # "disabled" | "applied" | "unavailable"
    model: str | None = None
    depth: int | None = None

    def as_dict(self) -> dict:
        return {"status": self.status, "model": self.model, "depth": self.depth}


class SearchStack:
    def __init__(self, *, rewriter: QueryRewriter | None = None, rrf_k: int = RRF_K,
                 rerank: RerankFn | None = None, rerank_depth: int = DEFAULT_RERANK_DEPTH) -> None:
        if rrf_k < 1 or rerank_depth < 1:
            raise ValueError("rrf_k and rerank_depth must be >= 1")
        self.rewriter = rewriter or QueryRewriter()
        self.rrf_k = rrf_k
        self.rerank = rerank
        self.rerank_depth = rerank_depth

    def plan(self, query: str) -> QueryPlan:
        rewritten = self.rewriter.rewrite(query)
        return QueryPlan(original=rewritten.original, rewritten=rewritten.rewritten,
                         rules_applied=tuple(rewritten.rules_applied), rewriter_version=rewritten.rewriter_version)

    def fuse(self, candidates: Sequence[Candidate]) -> list[Ranked]:
        seen: set[str] = set()
        ranked = []
        for candidate in candidates:
            if candidate.result_id in seen:
                raise ValueError(f"duplicate candidate {candidate.result_id!r}")
            seen.add(candidate.result_id)
            if any(position < 1 for position in candidate.ranks.values()):
                raise ValueError(f"ranks are 1-based: {candidate.result_id!r}")
            fused = sum(1.0 / (self.rrf_k + position) for position in candidate.ranks.values())
            ranked.append(Ranked(candidate=candidate, score=fused, fused_score=fused))
        ranked.sort(key=lambda item: (-item.fused_score, item.candidate.result_type, item.candidate.result_id))
        return ranked

    def rank(self, query: QueryPlan | str, candidates: Sequence[Candidate]) -> tuple[list[Ranked], RerankOutcome]:
        """All candidates in final order, and what reranking did."""
        fused = self.fuse(candidates)
        if self.rerank is None:
            return fused, RerankOutcome("disabled")
        window = fused[: self.rerank_depth]
        if len(window) < 2:
            return fused, RerankOutcome("applied", depth=self.rerank_depth)
        text = query.original if isinstance(query, QueryPlan) else query
        try:
            scores, model = self.rerank(text, [(item.candidate.result_id, item.candidate.text) for item in window])
        except RerankUnavailable:
            return fused, RerankOutcome("unavailable", depth=self.rerank_depth)
        missing = [item.candidate.result_id for item in window if item.candidate.result_id not in scores]
        if missing:
            return fused, RerankOutcome("unavailable", model=model, depth=self.rerank_depth)
        # Stable sort: equal reranker scores keep their fused order.
        reordered = sorted(window, key=lambda item: -scores[item.candidate.result_id])
        slots = [item.fused_score for item in window]
        reranked = [Ranked(candidate=item.candidate, score=slot, fused_score=item.fused_score,
                           rerank_score=float(scores[item.candidate.result_id]))
                    for item, slot in zip(reordered, slots)]
        return [*reranked, *fused[len(window):]], RerankOutcome("applied", model=model, depth=self.rerank_depth)

    @staticmethod
    def page(ranked: Sequence[Ranked], page: int, page_size: int) -> list[tuple[int, Ranked]]:
        """(1-based rank across all pages, result) for one page."""
        offset = (page - 1) * page_size
        return [(offset + index, item) for index, item in enumerate(ranked[offset:offset + page_size], start=1)]
