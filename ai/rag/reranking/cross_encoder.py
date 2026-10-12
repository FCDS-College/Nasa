"""Real reranker: cross-encoder scoring with score logging.

There is deliberately NO silent fallback. If the model cannot load or the
scorer fails, `RerankerUnavailable` is raised so the caller can return an
explicit error / insufficient-evidence instead of an unreranked answer.
"""
from __future__ import annotations

import logging

from ai.interfaces import Reranker

logger = logging.getLogger(__name__)


class RerankerUnavailable(RuntimeError):
    """The reranker could not score candidates."""


class CrossEncoderReranker(Reranker):
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        version: str = "1.0.0",
        candidate_size: int = 20,
        scorer=None,
    ):
        """
        Args:
            model_name: sentence-transformers CrossEncoder name.
            version: our own version string recorded per request.
            candidate_size: max candidates sent to the model.
            scorer: optional callable(list[(query, text)]) -> list[float];
                injected in tests so no model download is needed.
        """
        if candidate_size < 1:
            raise ValueError("candidate_size must be >= 1")
        self.name = model_name
        self.version = version
        self.candidate_size = candidate_size
        self._scorer = scorer
        self.last_scores: list[dict] = []

    def _load_scorer(self):
        if self._scorer is not None:
            return self._scorer
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(self.name)
            self._scorer = lambda pairs: [float(s) for s in model.predict(pairs)]
            return self._scorer
        except Exception as exc:  # noqa: BLE001
            raise RerankerUnavailable(f"cannot load reranker {self.name}: {exc}") from exc

    def rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        """Score the first `candidate_size` results and return the best `top_k`.

        Returns dicts with `chunk`, `retrieval_score`, `rerank_score`.
        Raises RerankerUnavailable on any scoring failure.
        """
        candidates = results[: self.candidate_size]
        if not candidates:
            return []
        scorer = self._load_scorer()
        pairs = [(query, c["chunk"]["text"]) for c in candidates]
        try:
            scores = scorer(pairs)
        except Exception as exc:  # noqa: BLE001
            raise RerankerUnavailable(f"reranker scoring failed: {exc}") from exc
        if len(scores) != len(candidates):
            raise RerankerUnavailable("scorer returned wrong number of scores")

        out = []
        for cand, score in zip(candidates, scores):
            out.append(
                {
                    "chunk": cand["chunk"],
                    "retrieval_score": float(cand.get("hybrid_score", cand.get("retrieval_score", 0.0))),
                    "rerank_score": float(score),
                }
            )
        out.sort(key=lambda r: r["rerank_score"], reverse=True)

        self.last_scores = [
            {
                "chunk_id": r["chunk"]["chunk_id"],
                "retrieval_score": r["retrieval_score"],
                "rerank_score": r["rerank_score"],
                "reranker": self.name,
                "reranker_version": self.version,
            }
            for r in out
        ]
        logger.info("rerank scores: %s", self.last_scores)
        return out[:top_k]
