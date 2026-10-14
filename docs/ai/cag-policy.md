# CAG implementation (E1-4)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Eman | In review | 0.2.0 | 2026-10-14 | M4, 2H (Planned parts marked) | `ai/rag/cache/cag.py`, `ai/rag/service.py` |

Cache-Augmented Generation (CAG) here means: a final, already-validated answer is stored under a key that contains every version it depends on, and is served again only when all those versions are unchanged. This document describes the code at commit `9319d65` (cache module) and `0fc94c3` (service wiring). The fix that records `compute_ms` in the service is in commit `d7bf6b2` . **Planned** marks behaviour not yet in code.

## 1. What is implemented

| Capability | Status | Code | Test | 
|---|---|---|---|
| Versioned, deterministic cache key | Implemented | `build_cache_key` | `test_key_is_deterministic_and_normalized`, `test_any_version_change_changes_key` |
| TTL and expiry | Implemented | `InMemoryCacheService.get/set` | `test_hit_miss_and_ttl_expiry` |
| Dependency manifest stored with every entry | Implemented | `DependencyManifest` | `test_manifest_required` |
| Invalidate by corpus version | Implemented (method), **trigger not wired** | `InMemoryCacheService.invalidate_corpus` | `test_corpus_publication_invalidates_old_entries`, `test_second_call_is_a_cache_hit_and_corpus_publish_invalidates` |
| Invalidate by document (and version) | Implemented (method), **trigger not wired** | `InMemoryCacheService.invalidate_document` | `test_document_update_invalidates_dependents_only` |
| Answers that used session memory are never cached | Implemented | `is_cacheable`, `FlameRAGService.answer` | `test_answers_that_used_memory_are_not_cached`, `test_memory_is_disclosed_and_bypasses_cache` |
| `cache_hit` produced by Flame's own cache | Implemented | `FlameResponse.cache_hit` in `ai/rag/service.py` | `test_second_call_is_a_cache_hit_and_corpus_publish_invalidates` |
| Metrics (hits, misses, hit rate, time saved p50/p95) | Implemented | `InMemoryCacheService.metrics` | `test_cache_metrics_record_time_saved_on_hits` |
| Redis / shared cache backend | **Planned** | only `InMemoryCacheService` exists (process-local) | - |
| Embedding, retrieval-ID and rerank caches | **Planned** | - | - |
| Provider and execution mode recorded in entries | Implemented | `DependencyManifest.provider` / `.execution_mode` in `ai/rag/cache/cag.py`, filled by `FlameRAGService.answer` (commit `1c118b3`); test `test_manifest_records_provider_and_execution_mode` and `test_second_call_is_a_cache_hit_and_corpus_publish_invalidates` | `python -m pytest tests/unit/test_cag.py tests/unit/test_flame_service.py`: passed |
| Serving entries offline | Implemented for the in-process cache only | An entry built by the local `ExtractiveLLMProvider` (`execution_mode="local"`) needs no network to be served; no Redis or shared cache exists | - |

Test command: `python -m pytest -q tests/unit`. Result on Eman's machine at `0fc94c3` (2026-10-12): **81 passed**. Sandbox run after the `compute_ms` fix (`test_cag.py`, `test_flame_service.py`): **19 passed**.

## 2. Cache inventory

| Cache type | Key format | Value | TTL | Invalidation trigger | Status |
|---|---|---|---|---|---|
| Final answer | `rag:v1:corpus:<corpus_ver>:prompt:<prompt_ver>:model:<model>:rerank:<rerank_ver>:<hash24>` | `GroundedAnswer` (status, claims, citations, warnings, versions) | 3600 s for answers; 300 s for `insufficient_evidence` and `conflicting_evidence` | (1) any version in the key changes, so the old entry is simply never hit; (2) `invalidate_corpus(new_version)` removes entries from other corpus versions; (3) `invalidate_document(id, new_version)` removes entries that cite that document | Implemented |
| Embedding cache | not defined | - | - | - | Planned |
| Retrieval-ID cache (for offline reuse) | not defined | - | - | - | Planned (2H) |

Key details (`build_cache_key`): `<hash24>` is the first 24 hex characters of SHA-256 over the normalised query (lower-case, collapsed whitespace), the filters (sorted JSON) and `top_k`. Characters outside `[A-Za-z0-9._@-]` in version parts are replaced by `_`. Key scheme version is `v1` (`KEY_SCHEME`).

Example key from a synthetic demo run (2026-10-12, commit `9319d65` + wiring):

```
rag:v1:corpus:corpus-1:prompt:system_scientific_qa@1.0.0_grounded_answer@1.0.0:model:extractive-baseline@1.0.0:rerank:cross-encoder_ms-marco-MiniLM-L-6-v2@1.0.0:c13adac446ca0e48969f99a0
```

**Never cached:** any answer whose `memory_used` is non-empty (it depends on personal context), and any request where session memory candidates exist (the cache lookup is skipped). Retrieval errors (`retrieval_unavailable`) are not cached.

## 3. Dependency manifest (schema 1.0.0)

Stored with each entry (`DependencyManifest`):

| Field | Meaning |
|---|---|
| `schema_version` | `1.0.0` |
| `corpus_version` | Corpus/knowledge version the answer was built on (required) |
| `document_versions` | `{document_id: document_version}` for every cited evidence chunk |
| `chunk_ids` | IDs of the evidence chunks used |
| `prompt_versions` | `{prompt_id: version}` as recorded in `GroundedAnswer.versions` |
| `model` | `<provider name>@<version>` of the LLM |
| `embedding_model` | Embedding model name |
| `reranker_version` | `<reranker name>@<version>` or `passthrough@1` |

`set()` rejects an entry without a manifest containing `corpus_version`.

## 4. Knowledge-version publication and invalidation

Required behaviour: when a new knowledge version is published (event owned by Anas, E2), cached answers built on older versions must stop being served. See `docs/data/KNOWLEDGE_VERSIONING.md` (owned by E2; confirm that file exists at this path).

- **Implemented:** the cache can do it: `invalidate_corpus(current_corpus_version)` removes every entry whose manifest has a different `corpus_version`, and `invalidate_document(document_id, new_version)` removes entries that cite an outdated document. Even without calling them, entries cannot be served after a version change because `corpus_version` is part of the key.
- **Planned:** nothing subscribes to the publication event yet, so no code calls these methods automatically. The integration point is the API layer owned by the Lead and E2.

## 5. Where `cache_hit` comes from

`FlameRAGService.answer` (`ai/rag/service.py`) looks the key up in its own `CacheService`. A hit returns `FlameResponse(cache_hit=True)`; a miss computes the answer and returns `cache_hit=False`. AURA is not involved in this value. The `/api/chat` endpoint does not call this service yet (**Planned**, owned by the Lead), so today the value is produced only inside the service and its tests.

## 6. Metrics and how to read them

`InMemoryCacheService.metrics()` returns `hits`, `misses`, `hit_rate`, `saved_ms_p50`, `saved_ms_p95`, `entries`.

- `hit_rate = hits / (hits + misses)`.
- `saved_ms_*` are percentiles of the compute time (retrieval + composition) of the entry that was served, recorded when it was stored; each hit adds one sample. Higher p95 means the cache is saving the slowest requests.

Synthetic demo run (2026-10-12, fake embedder, tiny corpus, one query asked three times; **timings are not representative** and differ on every run):

```
cache_hit sequence: [False, True, True]
{"hits": 2, "misses": 1, "hit_rate": 0.6667, "saved_ms_p50": 2.9965, "saved_ms_p95": 2.9965, "entries": 1}
```

No production hit rate exists: no real traffic and no real corpus have been run through the cache.

## 7. Known limitations

- Process-local memory only: the cache is lost on restart and not shared between workers.
- No automatic invalidation yet (no subscriber to the knowledge-version event).
- Keys depend on the normalised query text; paraphrases miss.
- TTLs (3600 s / 300 s) are defaults, not tuned.
- `model` keeps `<name>@<version>`; `provider` and `execution_mode` ("local" or "cloud") are now stored separately in the manifest (commit `1c118b3`). Only the local baseline provider exists, so no entry has `execution_mode="cloud"` yet. The execution mode is not part of the cache key, so a cloud and a local answer to the same query with the same model name would share a key (**Planned** decision).
- Metrics are not exposed through an API endpoint yet.

## 8. Changelog

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-14 | Manifest now records provider and execution mode (`1c118b3`); placeholder commit text removed. |
| 0.1.0 | 2026-10-12 | First version: rewrite of `cag-policy.md` to match `ai/rag/cache/cag.py` and `ai/rag/service.py`; policies that are not implemented are marked Planned. |

## 9. ملخص بالعربي

الـ cache بيخزّن الإجابة النهائية بس، والـ key فيه نسخة الـ corpus والـ prompt والموديل والـ reranker، فأي تغيير في نسخة بيخلّي الـ entry القديم مش بيتقدّم. فيه TTL وmanifest لكل entry وmethods للـ invalidation، بس لسه مفيش حاجة بتنده عليهم لما الـ knowledge version يتنشر (Planned). والـ cache محلي في الذاكرة وبس، ومفيش Redis لسه. وقيمة `cache_hit` جاية من الـ cache بتاعنا مش من AURA.

