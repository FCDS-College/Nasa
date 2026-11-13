# Retrieval and Graph RAG evaluation results (E1-10)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Eman | In review | 0.2.0 | 2026-10-14 | C3, D7 | `ai/rag/evaluation/`, `run_evaluation.py`, `datasets/evaluation/` |

Sign-off: Ziad (metrics) pending.

# Retrieval and evaluation design

## 1. Overview

This document describes the retrieval layer implemented for the Flame in Freefall RAG prototype.

The retrieval pipeline is responsible for finding relevant evidence from the available document corpus, ranking the retrieved evidence, building a context for downstream generation, and preserving citation information.

The current implementation is a prototype and uses test data because the official NASA competition dataset is not yet available.

---

## 2. Retrieval Architecture

The current retrieval flow is:

```text
User Question
      ↓
Metadata Filtering
      ↓
Query Embedding
      ↓
Hybrid Retrieval
   ┌──┴─────────────┐
   ↓                ↓
Vector Search   Keyword Search
   └───────┬────────┘
           ↓
      Hybrid Ranking
           ↓
        Reranking
           ↓
     Context Builder
           ↓
    Citation Manager
           ↓
   Retrieved Evidence
```

---

## 3. Document Ingestion

Documents are converted into an internal document representation containing:

* document ID
* document version
* title
* source
* source type
* text
* metadata

Documents are then divided into smaller chunks for retrieval.

Each chunk preserves:

* chunk ID
* document ID
* document version
* chunk index
* text
* metadata

This allows retrieved evidence to remain traceable to its original document and version.

---

## 4. Embedding Generation

The prototype uses:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Each text chunk is converted into a numerical embedding vector.

The current embedding dimension is:

```text
384
```

The same embedding service is used to encode both document chunks and user queries.

---

## 5. Vector Retrieval

Vector retrieval uses cosine similarity between the query embedding and stored chunk embeddings.

The most semantically similar chunks are returned first.

This allows the system to retrieve evidence even when the wording of the question does not exactly match the wording in the document.

The current vector search implementation stores embeddings in memory.

---

## 6. Keyword Retrieval

A keyword-based retrieval component is also implemented.

It measures the overlap between words in the query and words appearing in document chunks.

This provides a lexical retrieval signal that complements semantic similarity.

The current keyword implementation is intentionally simple and is considered a prototype.

---

## 7. Hybrid Retrieval

The system combines semantic and keyword retrieval.

The current prototype uses:

```text
Hybrid Score =
0.7 × Vector Score
+
0.3 × Normalized Keyword Score
```

These weights are provisional.

They must be evaluated and potentially adjusted after the real NASA corpus becomes available.

The hybrid approach is intended to combine:

* semantic similarity
* exact/lexical matching

---

## 8. Metadata Filtering

Metadata filters can restrict retrieval to documents or chunks matching specific metadata values.

For example:

```text
environment = microgravity
```

This prevents irrelevant documents from entering the retrieval stage when appropriate metadata is available.

The metadata schema will be adapted to the actual NASA dataset once the dataset is received.

---

## 9. Reranking

After hybrid retrieval, the retrieved candidates are passed to a reranking layer.

The current prototype reranker combines:

* the hybrid retrieval score
* query/chunk keyword relevance

The reranking stage is positioned after retrieval and before context construction.

A more advanced reranker, such as a cross-encoder, may be evaluated later if the baseline retrieval quality is insufficient.

---

## 10. Context Building

The Context Builder receives reranked chunks and creates the context that will be passed to the downstream language model.

The current implementation:

* selects the highest-ranked chunks
* removes duplicate chunks
* limits the number of chunks
* limits the total context size
* preserves document IDs
* preserves document versions
* preserves metadata

The current prototype uses a character-based limit.

A tokenizer-based token budget can be introduced once the final LLM is selected.

---

## 11. Citation Generation

Every selected source is converted into citation information.

The citation maintains the relationship:

```text
Citation
   ↓
Chunk
   ↓
Document
   ↓
Document Version
```

This provides provenance for retrieved evidence.

The current citation mechanism does not generate scientific claims itself.

Its role is to preserve the identity and provenance of retrieved evidence.

---

## 12. End-to-End Retrieval Pipeline

The complete prototype has been tested using:

```text
Question
   ↓
Metadata Filter
   ↓
Embedding
   ↓
Hybrid Search
   ↓
Reranking
   ↓
Context Builder
   ↓
Citation Manager
   ↓
Cited Evidence
```

The end-to-end retrieval test completed successfully.

---

## 13. Evaluation Methodology

A small test evaluation corpus was created to validate the retrieval implementation before the official NASA dataset becomes available.

Each evaluation example contains:

```text
Question
Relevant Chunk IDs
```

The evaluation process runs each question through the retrieval pipeline and compares the retrieved chunks against the expected relevant chunks.

---

## 14. Evaluation Metrics

### Recall@K

Recall@K measures the proportion of relevant chunks that appear within the top K retrieved results.

For this prototype:

```text
Recall@5
```

was used.

### Reciprocal Rank

Reciprocal Rank measures the position of the first relevant retrieved result.

For a relevant result at rank `r`:

```text
Reciprocal Rank = 1 / r
```

The mean reciprocal rank across evaluation questions is used as an overall ranking metric.

### Citation Coverage

Citation Coverage measures how many expected relevant chunks are represented in the generated citations.

---

## 15. Evaluation results

All numbers in this section are copied from the generated `evaluation_report.json` (committed at `a5fb062`, produced by `python run_evaluation.py`). Nothing is typed by hand. The earlier hand-typed prototype table (Recall@5 0.667, MRR 0.812) was removed because no run ID backed it.

| Field | Value |
|---|---|
| Harness | Ziad's `run_evaluation.py` (scorer v2.0, rubric v2.0) |
| Run timestamp | 2026-10-14T00:45:43.759317+00:00 |
| Code commit recorded by the run | `7d3658d` |
| Benchmark | `datasets/evaluation/rag_gold.jsonl`, 38 cases, SHA-256 `013e1738a85e5da9bd4d096b989f3a231e774c9d334748d3137cc8ae95211dd2` |
| Retrieval under test | the harness `RAGConnector` in mock mode, **not** `ai/rag` (not yet wired into the harness) |

### 15.1 Variant comparison

| Variant | Recall@5 | MRR | Citation F1 | Run |
|---|---:|---:|---:|---|
| standard (dense only) | Planned | Planned | Planned | none |
| hybrid (`HybridSearchService` + RRF) | Planned | Planned | Planned | none |
| graph-only | Planned | Planned | Planned | none (D4 not built) |
| hybrid + graph | Planned | Planned | Planned | none (D4 not built) |
| graph + rerank | Planned | Planned | Planned | none (D4 not built) |
| harness mock connector (reference only) | 0.0323 | 0.0323 | 0.0323 | `2026-11-13T15:44:06.956637+00:00` |

Targets: Recall@5 0.8, MRR 0.7, Citation F1 0.75. The reference row misses all three. It measures the mock connector, so it says nothing about `ai/rag` or the served API. Since 2026-11-13 the means are over the 31 answerable cases only: an unanswerable case expects no evidence, so its recall and MRR are undefined and are no longer scored as 1.0 (the earlier 0.2105 was inflated that way; it is 1 hit in 31 answerable cases). The gold file's evidence IDs (`DOC-001-P15`, ...) are not documents of the indexed corpus, and there are no confidence intervals.

### 15.2 Results by difficulty (the gold set has no cross-doc or multi-hop labels)

Mock connector, answerable cases only. These are artefacts of what the mock hard-codes, not a property of any retrieval system.

| Difficulty | Answerable cases | Recall@5 | MRR | Citation F1 |
|---|---:|---:|---:|---:|
| easy | 9 | 0.111 | 0.111 | 0.111 |
| hard | 11 | 0.000 | 0.000 | 0.000 |
| medium | 11 | 0.000 | 0.000 | 0.000 |

### 15.3 Conclusion

No component can be credited with an improvement yet: the variants above were not run, so there are no regressions to list either. The next step is to point the harness `RAGConnector` at `FlameRAGService` and re-run for the standard and hybrid variants (Week 4 baseline). Safety: 0 of 38 cases passed, which is Ziad's to explain. The gold set has 38 cases, while some documents state 35; this must be settled with Ziad.

---

## 16. Failure Cases Tested

The prototype includes tests for:

### No Relevant Document

The system is tested with a query unrelated to the available test corpus.

Expected behavior:

* return retrieval results if the current retrieval mechanism finds candidates
* preserve the retrieval output structure
* avoid assuming that retrieved text is automatically authoritative evidence

A future confidence/abstention layer should determine when evidence is insufficient for answering.

### No Metadata Match

When metadata filters match no documents, the pipeline returns:

```text
context = ""
sources = []
citations = []
```

This prevents unrelated documents from being passed into the context.

### Insufficient Context

The pipeline was tested with a restricted top-K value to verify that context construction still functions when only limited evidence is available.

---

## 17. Known limitations

The current implementation has several prototype limitations.

### Test Data

The official NASA competition dataset is not yet available.

Therefore:

* current evaluation results are not NASA results
* current relevant-chunk labels are test labels
* retrieval performance may change substantially with the real corpus

### In-Memory Vector Store

The current vector search stores embeddings in memory.

A persistent vector database or optimized vector index can be introduced later depending on corpus size and project requirements.

### Simple Keyword Search

The current keyword search uses basic token splitting and substring matching.

It does not yet provide:

* stemming
* lemmatization
* BM25
* advanced lexical ranking

### Prototype Reranker

The current reranker is based on simple relevance signals.

A cross-encoder or another stronger reranking method can be evaluated later.

### Character-Based Context Limit

The current Context Builder uses a character limit instead of a tokenizer-based token budget.

### Provisional Hybrid Weights

The `0.7 / 0.3` hybrid weighting is a prototype choice and should be tuned using the real evaluation corpus.

---

## 18. Transition to the NASA Dataset

When the official NASA dataset becomes available, the following components should remain unchanged where possible:

* retrieval interfaces
* evaluation metric implementation
* pipeline architecture
* citation structure
* testing framework

The following components may need adaptation:

* document loader
* metadata schema
* chunking strategy
* chunk size and overlap
* embedding model
* hybrid retrieval weights
* reranker
* evaluation questions
* relevant-source annotations

The evaluation dataset should then be replaced or expanded with representative NASA/PSI questions and authoritative relevant sources.

---

## 19. Scientific Grounding Principle

Retrieved text is evidence, not automatically scientific truth.

Scientific claims must ultimately be grounded in authoritative source material.

Memory, cached information, or previously generated content must not override authoritative source evidence.

When evidence is missing, conflicting, or outdated, the system should preserve that uncertainty rather than presenting an unsupported scientific conclusion.

---

## 20. Day 2 Deliverables Status

| Deliverable                     | Status               |
| ------------------------------- | -------------------- |
| Working RAG retrieval prototype | Complete             |
| Vector search implementation    | Complete             |
| Metadata filtering              | Complete             |
| Hybrid search                   | Complete             |
| Reranking                       | Complete             |
| Context Builder v1              | Complete             |
| Citation mechanism v1           | Complete             |
| Retrieval evaluation dataset    | Prototype complete   |
| Recall@K evaluation             | Complete             |
| Ranking evaluation              | Complete             |
| Citation coverage evaluation    | Complete             |
| Failure/edge-case tests         | Prototype complete   |
| NASA-corpus evaluation          | Pending NASA dataset |

---

## 21. Final Prototype Flow

```text
                 ┌─────────────────┐
                 │   User Query    │
                 └────────┬────────┘
                          ↓
                 ┌─────────────────┐
                 │ Metadata Filter │
                 └────────┬────────┘
                          ↓
              ┌───────────────────────┐
              │   Hybrid Retrieval    │
              │                       │
              │ Vector + Keyword      │
              └───────────┬───────────┘
                          ↓
                 ┌─────────────────┐
                 │    Reranker     │
                 └────────┬────────┘
                          ↓
                 ┌─────────────────┐
                 │ Context Builder │
                 └────────┬────────┘
                          ↓
                 ┌─────────────────┐
                 │    Citations    │
                 └────────┬────────┘
                          ↓
                 ┌─────────────────┐
                 │ Cited Evidence  │
                 └─────────────────┘
```

This prototype establishes the retrieval and evidence-grounding foundation required before connecting the system to the official NASA competition corpus.

---

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 2026-10-14 | Added header block. Replaced the hand-typed baseline with numbers generated by the harness, added the variant table (Planned), the by-difficulty table and the conclusion. |
| 0.1.0 | prior | First prototype description. |
