# Cache-Augmented Generation (CAG) Policy

## 1. Purpose

CAG is used to reduce repeated computation and improve system efficiency.

CAG does not replace retrieval and does not define scientific truth.

---

## 2. Potentially Cacheable Components

The system may cache:

* text embeddings
* batch embeddings
* retrieval results
* reranking results
* context construction
* selected final responses

Caching should be applied only when the result is safe to reuse.

---

## 3. Cache Key

A cache key should depend on all parameters that can materially affect the cached result.

Conceptually:

```text
normalized_query
+
embedding_model_version
+
retrieval_configuration
+
corpus_version
+
prompt_version
+
llm_model_version
```

---

## 4. TTL

Each cache type should have a configurable TTL.

Examples:

```text
Embedding cache
→ long-lived unless model changes

Retrieval cache
→ dependent on corpus updates

Final answer cache
→ shorter and more strictly versioned
```

Actual TTL values will be selected during implementation.

---

## 5. Version-Aware Invalidation

Cache entries must be invalidated when relevant versions change.

Examples:

* embedding model changes
* corpus changes
* document version changes
* retrieval configuration changes
* prompt changes
* LLM model changes

---

## 6. Scientific Safety

A cached answer must never be treated as new scientific evidence.

The system should preserve the original provenance associated with cached results.

---

## 7. Cache Failure

If the cache is unavailable:

```text
Cache miss
→ perform normal computation
```

Cache availability must not be required for scientific correctness.

---

## 8. Ownership

CacheService owns cache storage and invalidation.

Retrieval, context construction, and LLM services remain responsible for their own scientific/functional logic.
