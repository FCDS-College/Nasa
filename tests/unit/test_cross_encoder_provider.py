"""ADR-006 reranker provider: fastembed ONNX cross-encoder, cache-only when offline."""
import sys
import types

import pytest

from ai.providers.contracts.errors import ProviderError, ProviderErrorCode
from ai.providers.contracts.reranking import RerankRequest
from ai.providers.local import cross_encoder
from ai.providers.local.cross_encoder import CrossEncoderReranker


def test_offline_without_a_cached_model_is_model_missing_and_never_downloads(tmp_path, monkeypatch):
    def no_download(*args, **kwargs):
        raise AssertionError("an offline reranker must not load (and so download) a model")

    fake = types.ModuleType("fastembed.rerank.cross_encoder")
    fake.TextCrossEncoder = no_download
    monkeypatch.setitem(sys.modules, "fastembed.rerank.cross_encoder", fake)
    provider = CrossEncoderReranker(cache_dir=str(tmp_path), offline=True)

    health = provider.health(1.0)
    assert health.state == "down" and health.model_present is False
    with pytest.raises(ProviderError) as error:
        provider.rerank(RerankRequest(query="q", documents=(("a", "x"), ("b", "y"))))
    assert error.value.code is ProviderErrorCode.MODEL_MISSING and error.value.request_sent is False


def test_scores_come_back_best_first_with_long_passages_truncated(tmp_path, monkeypatch):
    seen = {}

    class FakeCrossEncoder:
        def __init__(self, model_name, **kwargs):
            seen["model"], seen["kwargs"] = model_name, kwargs

        def rerank(self, query, documents):
            seen["documents"] = documents
            return [len(text) / 1000 for text in documents]

    fake = types.ModuleType("fastembed.rerank.cross_encoder")
    fake.TextCrossEncoder = FakeCrossEncoder
    monkeypatch.setitem(sys.modules, "fastembed.rerank.cross_encoder", fake)
    provider = CrossEncoderReranker(cache_dir=str(tmp_path))

    response = provider.rerank(RerankRequest(query="flame", documents=(("short", "abc"), ("long", "x" * 5000))))

    assert seen["model"] == cross_encoder.DEFAULT_MODEL == "Xenova/ms-marco-MiniLM-L-6-v2"
    assert seen["kwargs"] == {"cache_dir": str(tmp_path)}
    assert max(len(text) for text in seen["documents"]) == cross_encoder.MAX_PASSAGE_CHARS
    assert [doc_id for doc_id, _ in response.scores] == ["long", "short"] and response.model == cross_encoder.DEFAULT_MODEL
    assert provider.health(1.0).state == "up"
    assert provider.info.runtime == "fastembed" and provider.info.name == "cross_encoder"
