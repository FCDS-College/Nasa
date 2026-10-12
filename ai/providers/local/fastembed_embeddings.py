"""fastembed ONNX embeddings (``BAAI/bge-small-en-v1.5``), runnable without internet once cached.

With ``offline=True`` the Hugging Face hub is never contacted: a missing model is reported as
``model_missing`` instead of being downloaded. Prepare the cache while connected with
``python -m ai.providers.local.fastembed_embeddings prepare --cache-dir <dir>``.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import time
from pathlib import Path

from ai.providers.contracts.base import Capability, HealthStatus, Locality, ProviderInfo
from ai.providers.contracts.embeddings import EmbeddingRequest, EmbeddingResponse
from ai.providers.contracts.errors import ProviderError, ProviderErrorCode

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
MAX_CHUNK_CHARS = 2000


class FastEmbedProvider:
    def __init__(self, *, model_name: str = MODEL_NAME, cache_dir: str | None = None, offline: bool = False) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._offline = offline
        self._model = None
        self.info = ProviderInfo(
            name="fastembed", runtime="fastembed", locality=Locality.LOCAL,
            capabilities=frozenset({Capability.EMBEDDINGS}), model=model_name, version=None,
        )

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
        return HealthStatus("up" if present or not self._offline else "down", latency, model_present=present)

    def _load(self):
        if self._model is not None:
            return self._model
        if self._offline:
            os.environ["HF_HUB_OFFLINE"] = "1"
            if not self._cached_files():
                raise ProviderError(ProviderErrorCode.MODEL_MISSING, "Embedding model is not in the offline cache.",
                                    provider="fastembed", request_sent=False)
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise ProviderError(ProviderErrorCode.MODEL_MISSING, "fastembed is not installed.",
                                provider="fastembed", request_sent=False) from exc
        try:
            kwargs = {"cache_dir": self._cache_dir} if self._cache_dir else {}
            self._model = TextEmbedding(model_name=self._model_name, **kwargs)
        except Exception as exc:  # download/IO/ONNX load failures all mean "model not usable here"
            raise ProviderError(ProviderErrorCode.MODEL_MISSING, "Embedding model could not be loaded.",
                                provider="fastembed", request_sent=False) from exc
        return self._model

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        model = self._load()
        prepared = [(QUERY_PREFIX + t if request.query else t)[:MAX_CHUNK_CHARS] for t in request.texts]
        vectors = tuple(tuple(float(x) for x in vector) for vector in model.embed(prepared))
        return EmbeddingResponse(vectors=vectors, model=self._model_name, dimensions=DIMENSIONS)

    def checksums(self) -> dict[str, str]:
        """sha256 of every cached ONNX file, for the model manifest (H-3)."""
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self._cached_files()}


def _main(argv: list[str]) -> int:
    if len(argv) < 1 or argv[0] not in {"prepare", "verify"}:
        print("usage: python -m ai.providers.local.fastembed_embeddings prepare|verify --cache-dir DIR")
        return 2
    cache_dir = argv[argv.index("--cache-dir") + 1] if "--cache-dir" in argv else None
    provider = FastEmbedProvider(cache_dir=cache_dir, offline=argv[0] == "verify")
    provider.embed(EmbeddingRequest(texts=("warm-up",)))
    for path, digest in provider.checksums().items():
        print(f"{digest}  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
