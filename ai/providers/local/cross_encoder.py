"""Local cross-encoder reranker (ADR-006): fastembed ONNX ``Xenova/ms-marco-MiniLM-L-6-v2``.

The ONNX export of ``cross-encoder/ms-marco-MiniLM-L-6-v2``: on the same (query, passage) pairs both
return identical scores (checked 2026-11-12), and this one needs no PyTorch. fastembed is already in
the API image for embeddings, so enabling reranking adds no dependency.

Like the embedding provider, ``offline=True`` never contacts the Hugging Face hub: a missing model is
``model_missing``, which `/api/search` reports as ``reranking.status = "unavailable"`` (fused order).
Prepare the cache while connected:

    python -m ai.providers.local.cross_encoder prepare --cache-dir <dir>
    python -m ai.providers.local.cross_encoder verify  --cache-dir <dir>   # offline load check
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.reranking import RerankRequest, RerankResponse

DEFAULT_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
MAX_PASSAGE_CHARS = 2000   # the model reads 512 tokens; longer text only costs time


class CrossEncoderReranker:
    def __init__(self, *, model_name: str = DEFAULT_MODEL, cache_dir: str | None = None,
                 offline: bool | Callable[[], bool] = False) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._offline_source = offline
        self._model = None
        self.info = ProviderInfo(
            name="cross_encoder", runtime="fastembed", locality=Locality.LOCAL,
            capabilities=frozenset({Capability.RERANKING}), model=model_name,
        )

    @property
    def _offline(self) -> bool:
        source = self._offline_source
        return bool(source()) if callable(source) else bool(source)

    def _cached_files(self) -> list[Path]:
        if not self._cache_dir:
            return []
        slug = self._model_name.split("/")[-1]
        return [p for p in Path(self._cache_dir).rglob("*.onnx") if slug in str(p)]

    def health(self, timeout_s: float) -> HealthStatus:
        started = time.perf_counter()
        if importlib.util.find_spec("fastembed") is None:
            return HealthStatus("down", 0.0, "dependency_missing", model_present=False)
        present = bool(self._cached_files()) if self._cache_dir else None
        latency = round((time.perf_counter() - started) * 1000, 1)
        if self._offline and not present:
            return HealthStatus("down", latency, ProviderErrorCode.MODEL_MISSING.value, model_present=False)
        if self._model is not None:
            return HealthStatus("up", latency, model_present=True)
        return HealthStatus("up" if present else "unknown", latency, model_present=present)

    def _load(self):
        if self._model is not None:
            return self._model
        if self._offline:
            os.environ["HF_HUB_OFFLINE"] = "1"
            if not self._cached_files():
                raise ProviderError(ProviderErrorCode.MODEL_MISSING, "Reranker model is not in the offline cache.",
                                    provider="cross_encoder", request_sent=False)
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
        except ImportError as exc:
            raise ProviderError(ProviderErrorCode.MODEL_MISSING, "fastembed is not installed.",
                                provider="cross_encoder", request_sent=False) from exc
        try:
            kwargs = {"cache_dir": self._cache_dir} if self._cache_dir else {}
            self._model = TextCrossEncoder(model_name=self._model_name, **kwargs)
        except Exception as exc:  # download/IO/ONNX load failures all mean "model not usable here"
            raise ProviderError(ProviderErrorCode.MODEL_MISSING, "Reranker model could not be loaded.",
                                provider="cross_encoder", request_sent=False) from exc
        return self._model

    def rerank(self, request: RerankRequest) -> RerankResponse:
        model = self._load()
        ids = [doc_id for doc_id, _ in request.documents]
        scores = [float(s) for s in model.rerank(request.query, [text[:MAX_PASSAGE_CHARS] for _, text in request.documents])]
        ranked = sorted(zip(ids, scores), key=lambda pair: pair[1], reverse=True)
        if request.top_k:
            ranked = ranked[: request.top_k]
        return RerankResponse(scores=tuple(ranked), model=self._model_name)

    def checksums(self) -> dict[str, str]:
        """sha256 of every cached ONNX file, for the model manifest (H-3)."""
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self._cached_files()}


def _main(argv: list[str]) -> int:
    if len(argv) < 1 or argv[0] not in {"prepare", "verify"}:
        print("usage: python -m ai.providers.local.cross_encoder prepare|verify --cache-dir DIR")
        return 2
    cache_dir = argv[argv.index("--cache-dir") + 1] if "--cache-dir" in argv else None
    provider = CrossEncoderReranker(cache_dir=cache_dir, offline=argv[0] == "verify")
    provider.rerank(RerankRequest(query="warm-up", documents=(("a", "warm-up passage"), ("b", "another passage"))))
    for path, digest in provider.checksums().items():
        print(f"{digest}  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
