"""Rank fusion for lexical + dense retrieval (Reciprocal Rank Fusion)."""
from __future__ import annotations


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[tuple[str, float]]:
    """Fuse several ranked ID lists with RRF.

    score(id) = sum_i  w_i / (k + rank_i(id)),  rank starting at 1.

    Args:
        rankings: one ranked list of chunk IDs per retriever (best first).
        k: RRF damping constant (default 60).
        weights: optional per-ranking weights (default all 1.0).

    Returns:
        [(chunk_id, fused_score)] sorted by score desc, ties broken by id.

    Raises:
        ValueError: if k <= 0 or weights length mismatches rankings.
    """
    if k <= 0:
        raise ValueError("k must be > 0")
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights must match rankings")

    scores: dict[str, float] = {}
    for ranking, weight in zip(rankings, weights):
        seen = set()
        for rank, chunk_id in enumerate(ranking, start=1):
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (k + rank)

    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def fuse_and_page(
    rankings: list[list[str]],
    page: int = 1,
    page_size: int = 5,
    k: int = 60,
    weights: list[float] | None = None,
) -> list[tuple[str, float]]:
    """Fuse over the FULL lists first, then slice the page.

    Slicing before fusing would drop semantic results on page 2+; this
    function never does that.
    """
    if page < 1 or page_size < 1:
        raise ValueError("page and page_size must be >= 1")
    fused = reciprocal_rank_fusion(rankings, k=k, weights=weights)
    start = (page - 1) * page_size
    return fused[start : start + page_size]
