# RAG Architecture

## 1. Purpose

This document defines the Retrieval-Augmented Generation (RAG) architecture for the Flame in Freefall project.

The RAG component is responsible for retrieving relevant scientific evidence, constructing grounded context, and supporting the generation of answers and insights that can be traced back to authoritative sources.

The architecture is designed to be data-source agnostic because the actual NASA competition data will be provided during the competition.

---

## 2. Core Pipeline

The main pipeline is:

User Query
→ Query Analysis / Rewriting
→ Retrieval
→ Hybrid Ranking
→ Reranking
→ Context Construction
→ LLM Generation
→ Citation / Provenance Validation
→ Grounded Answer

---

## 3. Query Analysis and Rewriting

The system may analyze and rewrite the user's query before retrieval.

The goals are:

* clarify the user's intent
* identify important scientific terms
* improve retrieval recall
* generate search-friendly representations of the question
* preserve the original meaning of the question

Query rewriting must not introduce unsupported scientific facts.

The rewritten query is an intermediate retrieval representation and is not considered scientific evidence.

---

## 4. Retrieval

The retrieval layer may combine multiple retrieval strategies.

### 4.1 Semantic Retrieval

The user query is converted into an embedding and compared with document/chunk embeddings.

Pipeline:

Query
→ Embedding
→ Vector Search
→ Candidate Chunks

Semantic retrieval is useful when the query and source use different wording but have similar meaning.

---

### 4.2 Keyword Retrieval

Keyword or lexical retrieval searches for important terms directly in the indexed content.

This is particularly useful for:

* scientific terminology
* experiment names
* technical variables
* exact phrases
* numerical or symbolic identifiers

---

### 4.3 Metadata Filtering

Metadata filters can restrict retrieval to specific source characteristics when such metadata exists.

Examples may include:

* source type
* publication year
* document version
* experiment identifier
* dataset identifier

The exact metadata fields are intentionally not fixed before the NASA competition data is received.

---

## 5. Hybrid Retrieval

The system combines semantic and lexical retrieval where appropriate.

Conceptually:

Semantic Retrieval
+
Keyword Retrieval
+
Metadata Filtering
→ Candidate Set
→ Ranking

The exact ranking formula and weights will be evaluated using the actual corpus.

The system must avoid hard-coding assumptions about the NASA dataset.

---

## 6. Reranking

Initial retrieval may return a relatively large candidate set.

A reranker evaluates candidate relevance more precisely.

Pipeline:

Initial Retrieval
→ Candidate Documents/Chunks
→ Reranker
→ Top Relevant Evidence

The reranker operates after retrieval and before context construction.

The reranker is responsible for relevance ranking, not answer generation.

---

## 7. Context Builder

The context builder converts retrieved evidence into an LLM-ready context.

It is responsible for:

* selecting evidence
* removing duplicates
* ordering evidence
* respecting token limits
* preserving source metadata
* preserving uncertainty
* optionally compressing long evidence

The context builder must not change the scientific meaning of retrieved evidence.

---

## 8. LLM Generation

The LLM receives:

* system instructions
* user question
* retrieved evidence
* citation metadata
* relevant generation parameters

The LLM generates a response grounded in the supplied evidence.

The LLM must not treat its pretrained knowledge as authoritative evidence for project-specific scientific claims.

---

## 9. Citation and Provenance Validation

Generated scientific claims should be traceable to retrieved evidence.

The provenance chain is:

Answer Claim
→ Citation
→ Chunk
→ Document
→ Document Version
→ Original Source

If a scientific claim cannot be supported by retrieved evidence, the system should not present it as established fact.

---

## 10. Insufficient Evidence

If retrieval does not provide sufficient relevant evidence, the system should explicitly indicate insufficient evidence.

The system must not fabricate:

* scientific facts
* experimental results
* numerical values
* citations
* source references

---

## 11. Conflicting Evidence

If authoritative sources contain conflicting findings, the system should preserve the conflict rather than silently selecting one result.

The response should identify the relevant sources and explain that the available evidence is not fully consistent.

---

## 12. CAG Integration

Cache-Augmented Generation (CAG) is a supporting layer for efficiency and reuse.

Potential cacheable components include:

* embeddings
* retrieval results
* reranking results
* context construction
* selected final responses

Cache entries must be version-aware.

CAG does not replace retrieval and does not represent scientific truth.

---

## 13. MAG Integration

Memory-Augmented Generation (MAG) provides conversational and research continuity.

Potential memory types include:

* session memory
* research context
* experiment context
* team context

Memory is contextual information and is not considered scientific evidence.

Authoritative retrieved evidence has higher priority than memory.

---

## 14. Scientific Grounding Rule

The fundamental rule of the system is:

> Memory and cache can support the system, but authoritative retrieved evidence is the scientific truth boundary.

---

## 15. Data Availability Boundary

The actual NASA competition dataset is not available during the current development stage.

Therefore:

* no fixed NASA schema is assumed
* no specific NASA metadata fields are required
* no production retrieval ranking weights are fixed
* actual source mapping will be performed when the competition data is provided

The architecture must remain adaptable to the actual data format.
