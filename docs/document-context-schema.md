# Document and Context Schema

## 1. Purpose

This document defines the initial logical schema for documents, chunks, and citation metadata used by the RAG system.

The schema is intentionally flexible because the actual NASA competition data format is not yet available.

---

## 2. Document

A document represents an indexed scientific source.

Conceptual structure:

```python
Document = {
    "document_id": str,
    "version": str,
    "title": str,
    "source": str,
    "source_type": str,
    "publication_date": str | None,
    "retrieval_date": str,
    "license": str | None,
    "scientific_domain": list[str],
    "metadata": dict
}
```

### Important

Fields such as experiment identifiers, mission names, fuel types, oxidizers, or gravity conditions must not be assumed to exist.

They should be added only if they are actually present in the provided NASA data.

---

## 3. Chunk

A chunk represents a retrievable portion of a document.

```python
Chunk = {
    "chunk_id": str,
    "document_id": str,
    "document_version": str,
    "text": str,
    "chunk_index": int,
    "embedding_id": str | None,
    "metadata": dict,
    "citation_metadata": dict
}
```

The relationship is:

```text
Document
   ├── Chunk 1
   ├── Chunk 2
   ├── Chunk 3
   └── ...
```

---

## 4. Chunk Relationships

Chunks should retain their relationship to the parent document.

Required relationships:

```text
chunk_id
→ document_id
→ document_version
```

Optional relationships may be added if required by the actual corpus.

Examples:

* previous chunk
* next chunk
* section identifier
* table identifier
* figure identifier

These relationships should only be used when supported by the source structure.

---

## 5. Embedding Metadata

Embedding-related information may include:

```python
{
    "embedding_id": str,
    "model_name": str,
    "model_version": str,
    "dimension": int
}
```

The embedding model version should be recorded so that embeddings can be reproduced or invalidated when the model changes.

---

## 6. Citation Metadata

```python
CitationMetadata = {
    "citation_id": str,
    "document_id": str,
    "document_version": str,
    "chunk_id": str,
    "source": str,
    "source_url": str | None,
    "page": int | None
}
```

Additional fields can be added based on the actual source format.

---

## 7. Scientific Provenance

Every retrieved scientific evidence item should preserve enough information to identify its origin.

Minimum provenance chain:

```text
Chunk
→ Document
→ Version
→ Original Source
```

---

## 8. Context Item

The context builder may produce context items such as:

```python
ContextItem = {
    "chunk_id": str,
    "document_id": str,
    "text": str,
    "relevance_score": float,
    "citation_metadata": dict,
    "source_metadata": dict
}
```

---

## 9. Schema Design Principle

The schema must be:

* source-aware
* version-aware
* provenance-preserving
* extensible
* independent of assumptions about the future NASA dataset

The actual schema mapping will be performed after the competition data becomes available.
