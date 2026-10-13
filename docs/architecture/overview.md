# Architecture overview (Phase 2)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review (sign-off: Eman E1, Princess E3) | 2.0.0 | 2026-10-12 | §3, L-2 | `apps/`, `ai/`, `cv/`, `infrastructure/` |

Part A describes the system **as built** on branch `ccr-c6a5a263-498la9` (PR #14). Part B is the MVP RAG design that was this whole file before Phase 2, kept as it was. Decisions are in [`adr/`](adr/README.md).

## Part A: System as built

### A.1 Services vs modules

| Runs as a separate process / service | Is a module inside one |
|---|---|
| `api` (FastAPI, uvicorn), from `apps/api/Dockerfile` | `flame_api.main` (routes), `analysis` (upload routes), `generation` (prompts + validation), `ai_runtime` (provider wiring), `knowledge_version`, `registry`, `ingest`, `seed`, `vector_index`, `telemetry` |
| `worker` (RQ, the same image) | `flame_api.worker` → router `vision.analyze` and `analysis.interpret` |
| `postgres` (pgvector), `redis`, `minio` | — |
| `ollama` (optional profile `local-llm`), vLLM on the L40S (optional, separate host) | `ai.providers.*` adapters, `ai.routing` |
| `web` (Next.js) | `apps/web` |
| AURA (separate system, Railway) | `ai/providers/cloud/aura.py` |
| HF Space CV (optional, external) | `ai/providers/cloud/hf_space_cv.py` |
| — | `ai.rag` (Eman's pipeline; not yet wired into the API, ADR-006) |

### A.2 Request lifecycles

**Chat** (`POST /api/chat`, read token):

```text
web → api middleware (auth, request_id, span http.request)
    → _retrieve_passages: search() lexical (+ pgvector via router embed.query) for the question and up to 5 key terms
    → [no passages] → 200 "no_matching_evidence" (no model call)
    → generation.answer_question → router.route("chat.answer"):
          mode filter → circuit/health → provider.generate_structured(passages on DATA channel) → Flame validation
    → keep only cited IDs that were retrieved → 200 {answer, sources, model, execution, knowledge_version}
    → [no provider succeeded] → 200 evidence-only + "generation_unavailable"
```

**Search** (`GET /api/search`): PostgreSQL full-text over chunks and experiments; on page 1 without an experiment filter, pgvector nearest neighbours are appended (M2 will fuse them; ADR-006).

**Image analysis**:

```text
POST /api/analyses (write token, Idempotency-Key)
  → validate image (size, pixels, decode)
  → store original in MinIO
  → row `queued`
  → RQ job flame-analysis
worker → router.route("vision.analyze") (flame_cv | hf_space)
       → measurements + measurement evidence → `completed`
       → if interpretation was requested and a model is available: router.route("analysis.interpret")
       → statements validated → stored
client polls GET /api/analyses/{id}
```

**Admin operation** (`PUT /api/admin/ai/mode`, write token): write `audit_event` → switch this process → other processes pick it up from the newest audit row within 10 s.

**Ingestion** (CLI at start-up): seed registry/files/image assets/models → per file: checksum → parser adapter (PDF + OCR fallback / HTML / JSON / PSI table) or quarantine → `ingestion_run` → publish `corpus-<hash>` knowledge version.

### A.3 Where each version identifier is set

| Identifier | Set by | Stored / exposed |
|---|---|---|
| API / contract version | `FLAME_API_VERSION`; `openapi.json` `info.version` (0.2.0) | `meta.api_version`, `/api/health.version` |
| Corpus / knowledge version | `knowledge_version.publish` (ingest: `corpus-<hash>`; index build: `bge-small-en-v1.5-<rows>-<date>`) | `knowledge_publication`, `vector_index_manifest`, chat `knowledge_version`, dashboard |
| Parser versions | `ingest.py` (`pymupdf-pages-0.2.0`, `html-sections-0.1.0`, `json-paths-0.1.0`, `psi-tables-0.1.0`) | `document.parser_version`, `ingestion_run.transformation_id`, evidence `transformation_id` |
| OCR engine version | `ingest._ocr_page` (`tesseract-<v>`) | `document.payload.ocr.engine` |
| Model versions | `ai/routing/model_manifest.json`; provider responses | `model` table, `execution.model/version` |
| CV pipeline version | `cv/flame_cv.py` `PIPELINE_VERSION` (`cv-opencv-v1.2.0-auto`) | `analysis_result.pipeline_version` |
| Prompt version | not versioned yet (M3, Eman's prompt registry) | — |
| Benchmark version | Ziad's harness (M11) | — |
| Migration | Alembic (`0004_phase2_tables`) | `alembic_version` |

### A.4 Known limitations
Two retrieval stacks remain until M2. Prompts are not versioned until M3. Video and Graph RAG are planned and appear only as contracts and tables.

### A.5 Changelog
- 2.0.0 (2026-10-12): Part A added (L-2); the former content is kept as Part B.

---

# Part B: RAG design (MVP, unchanged)


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
