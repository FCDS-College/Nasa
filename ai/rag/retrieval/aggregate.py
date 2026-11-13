"""Window hits to page hits: a page scores as its best window (audit roadmap item 11)."""
from __future__ import annotations

from typing import Iterable


def aggregate_windows(hits: Iterable[tuple[str, float]], *, limit: int | None = None) -> list[tuple[str, float]]:
    """(page id, similarity) per page, best first; ties by page id. `hits` are (page id, window similarity) in any order."""
    best: dict[str, float] = {}
    for page_id, similarity in hits:
        if similarity > best.get(page_id, float("-inf")):
            best[page_id] = similarity
    ranked = sorted(best.items(), key=lambda item: (-item[1], item[0]))
    return ranked if limit is None else ranked[:limit]
