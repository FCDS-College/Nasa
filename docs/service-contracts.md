# AI Service Contracts

## 1. Purpose

This document defines the interfaces and ownership boundaries of the main AI/RAG services.

Each service should have a clear responsibility and should not duplicate the responsibility of another service.

---

## 2. LLMService

### Responsibility

Generate an answer from the user question and retrieved context.

### Interface

```text
generate(
    question,
    context,
    system_prompt,
    citation_metadata,
    generation_parameters
)
```

### Output

```text
{
    "answer": str,
    "citations": list,
    "metadata": dict
}
```

### Ownership

LLMService is responsible for:

* response generation
* following system instructions
* using supplied context
* producing citation-aware answers

LLMService is not responsible for:

* document retrieval
* vector search
* source discovery
* scientific evidence collection

---

## 3. EmbeddingService

### Responsibility

Convert text into vector representations.

### Interfaces

```text
embed_text(text)
embed_batch(texts)
```

### Output

```text
vector
```

or:

```text
list[vector]
```

### Ownership

EmbeddingService is responsible only for embedding generation.

It does not decide which documents are relevant.

---

## 4. VectorSearchService

### Responsibility

Retrieve candidate chunks based on vector similarity.

### Interface

```text
search(
    query_embedding,
    top_k,
    metadata_filters
)
```

### Output

```text
[
    {
        "chunk_id": str,
        "document_id": str,
        "score": float,
        "metadata": dict
    }
]
```

### Ownership

VectorSearchService is responsible for candidate retrieval.

It is not responsible for:

* final answer generation
* citation writing
* final context construction
* LLM prompting

---

## 5. CacheService

### Responsibility

Store and retrieve reusable intermediate or generated results.

### Interfaces

```text
get(key)
set(key, value, ttl)
invalidate(key)
```

### Ownership

CacheService improves efficiency and avoids unnecessary repeated computation.

Cached information must not automatically be treated as scientific evidence.

---

## 6. MemoryService

### Responsibility

Store and retrieve contextual information useful for continuity.

### Interfaces

```text
store(memory)
retrieve(query, filters)
delete(memory_id)
```

### Ownership

MemoryService is responsible for contextual memory.

Memory is not authoritative scientific evidence.

---

## 7. Service Boundaries

The intended ownership is:

```text
LLMService
    → answer generation

EmbeddingService
    → embedding generation

VectorSearchService
    → candidate retrieval

CacheService
    → caching and reuse

MemoryService
    → contextual memory
```

The services should communicate through explicit interfaces rather than directly depending on implementation details.

---

## 8. Versioning

Services that affect scientific retrieval or generation should expose or record relevant versions.

Potential version information includes:

* embedding model version
* retrieval configuration version
* reranker version
* prompt version
* LLM model version
* corpus/document version

This information is required for reproducibility and cache invalidation.
