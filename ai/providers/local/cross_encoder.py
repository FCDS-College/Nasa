"""Optional local cross-encoder reranker (sentence-transformers). Unavailable unless installed and cached."""
from __future__ import annotations

import importlib.util
from collections.abc import Callable

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.reranking import RerankRequest, RerankResponse

DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    def __init__(self, *, model_name: str = DEFAULT_MODEL, offline: bool | Callable[[], bool] = False) -> None:
        self._model_name = model_name
        self._offline_source = offline
        self._model = None
        self.info = ProviderInfo(
            name="cross_encoder", runtime="sentence-transformers", locality=Locality.LOCAL,
            capabilities=frozenset({Capability.RERANKING}), model=model_name,
        )

    @property
    def _offline(self) -> bool:
        source = self._offline_source
        return bool(source()) if callable(source) else bool(source)

    def health(self, timeout_s: float) -> HealthStatus:
        if importlib.util.find_spec("sentence_transformers") is None:
            return HealthStatus("down", 0.0, "dependency_missing", model_present=False)
        return HealthStatus("unknown" if self._model is None else "up", 0.0, model_present=self._model is not None or None)

    def _load(self):
        if self._model is None:
            if self._offline:
                import os

                os.environ["HF_HUB_OFFLINE"] = "1"
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self._model_name)
            except Exception as exc:
                raise ProviderError(ProviderErrorCode.MODEL_MISSING, "Reranker model could not be loaded.",
                                    provider="cross_encoder", request_sent=False) from exc
        return self._model

    def rerank(self, request: RerankRequest) -> RerankResponse:
        model = self._load()
        scores = model.predict([(request.query, text) for _, text in request.documents])
        ranked = sorted(zip((doc_id for doc_id, _ in request.documents), (float(s) for s in scores)),
                        key=lambda pair: pair[1], reverse=True)
        if request.top_k:
            ranked = ranked[: request.top_k]
        return RerankResponse(scores=tuple(ranked), model=self._model_name)
