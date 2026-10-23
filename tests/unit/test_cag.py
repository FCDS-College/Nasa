import pytest

from ai.rag.cache.cag import (
    DependencyManifest, InMemoryCacheService, build_cache_key, cached_call, is_cacheable,
)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def key(**over):
    args = dict(query="Flame  spread", filters={"domain": "combustion"}, top_k=5,
                corpus_version="c1", prompt_version="p1", model="m1", reranker_version="r1")
    args.update(over)
    return build_cache_key(**args)


def manifest(corpus="c1", docs=None):
    return DependencyManifest(corpus_version=corpus, document_versions=docs or {"d1": "v1"})


def test_key_is_deterministic_and_normalized():
    assert key() == key(query="flame spread")
    assert key().startswith("rag:v1:corpus:c1:prompt:p1:model:m1:rerank:r1:")


@pytest.mark.parametrize("field,value", [
    ("corpus_version", "c2"), ("prompt_version", "p2"), ("model", "m2"),
    ("reranker_version", "r2"), ("top_k", 6), ("filters", {"domain": "x"}),
])
def test_any_version_change_changes_key(field, value):
    assert key() != key(**{field: value})


def test_hit_miss_and_ttl_expiry():
    clock = Clock()
    cache = InMemoryCacheService(clock=clock)
    calls = []

    def compute():
        calls.append(1)
        return {"answer": "x", "status": "answered"}

    _, hit1 = cached_call(cache, "k", manifest(), compute)
    _, hit2 = cached_call(cache, "k", manifest(), compute)
    assert (hit1, hit2) == (False, True) and len(calls) == 1
    clock.t += 10_000
    _, hit3 = cached_call(cache, "k", manifest(), compute)
    assert hit3 is False and len(calls) == 2
    assert cache.metrics()["hits"] == 1


def test_corpus_publication_invalidates_old_entries():
    cache = InMemoryCacheService()
    cache.set("a", 1, 100, manifest("c1").model_dump())
    cache.set("b", 2, 100, manifest("c2").model_dump())
    assert cache.invalidate_corpus("c2") == 1
    assert cache.get("a") is None and cache.get("b") == 2


def test_document_update_invalidates_dependents_only():
    cache = InMemoryCacheService()
    cache.set("a", 1, 100, manifest(docs={"d1": "v1"}).model_dump())
    cache.set("b", 2, 100, manifest(docs={"d2": "v1"}).model_dump())
    assert cache.invalidate_document("d1", new_version="v2") == 1
    assert cache.get("b") == 2


def test_answers_that_used_memory_are_not_cached():
    cache = InMemoryCacheService()
    _, hit = cached_call(cache, "k", manifest(), lambda: {"memory_used": ["mem_1"], "status": "answered"})
    assert hit is False and len(cache) == 0
    assert is_cacheable({"memory_used": []})


def test_manifest_required():
    with pytest.raises(ValueError):
        InMemoryCacheService().set("k", 1, 10, {})


def test_manifest_records_provider_and_execution_mode():
    m = DependencyManifest(corpus_version="c1", provider="extractive-baseline", execution_mode="local")
    dumped = m.model_dump()
    assert dumped["provider"] == "extractive-baseline"
    assert dumped["execution_mode"] == "local"
    assert DependencyManifest(corpus_version="c1").execution_mode == ""
