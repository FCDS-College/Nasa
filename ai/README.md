# ai/

Evidence-first research intelligence. **Owner:** Engineer 1, with the Lead for deployment and router integration. **Status (2026-11-13):** the API serves `rag/retrieval/search_stack.py` (query rewrite, RRF, rerank), `rag/retrieval/evidence_window.py` and `rag/cache/cag.py`, and generates answers through `routing/` + `providers/` (Ollama, vLLM, llama.cpp, AURA). `rag/retrieval/rag_retrieval_pipeline.py`, the composer, session memory and `rag/nlp/` are library code that no API request reaches. No local language model has been run in the test environment.

| Folder | Status | What goes here |
|---|---|---|
| `rag/` | **active** | `ingestion/` (loader, chunker, pipeline), `embeddings/`, `retrieval/` (vector, keyword, hybrid, metadata filter, RAG pipeline, `fusion.py` RRF), `reranking/` (`reranker.py` passthrough, `cross_encoder.py` real reranker), `context/`, `citations/`, `evaluation/` (retrieval metrics) |
| `rag/prompts/` | **active** | Versioned prompt registry: `registry.py` + one JSON file per prompt in `library/` |
| `rag/generation/` | **active** | `composer.py` (grounded answer, citation validation, abstention), `providers.py` (offline extractive baseline) |
| `rag/cache/` | **active** | `cag.py`: versioned cache keys, dependency manifests, TTL, invalidation, metrics |
| `rag/memory/` | **active** | `session_mag.py`: scoped, expiring, provenance-tagged session memory |
| `rag/query/` | **active** | `rewrite.py`: query rewrite (original + rewritten both kept) |
| `rag/service.py` | **active** | `FlameRAGService`: rewrite -> memory -> cache -> retrieval -> composer |
| `interfaces.py` | **active** | ABCs: EmbeddingProvider, Retriever, Reranker, LLMProvider, CacheService, MemoryStore, AnswerComposer |
| `routing/`, `providers/` | **active** | model router (modes, circuit breaker, egress guard) and providers: Ollama, vLLM, llama.cpp, AURA, fastembed embeddings, cross-encoder reranker, CV |
| `rag/nlp/` | **active (library, not wired)** | D1 rule-based extractors: identifiers, measurements and units, vocabulary, document class, metadata, table/figure association. No gold set yet, so no measured precision or recall |
| `orchestration/` | planned | MVP plan §14 |

Import as `from ai.rag.retrieval.hybrid_search import HybridSearchService`, running from the repo root. Tests live in `tests/unit/`; design notes live in `docs/ai/`.

## Module map (entry points and tests)

| Path | Entry point | Tests |
|---|---|---|
| `ai/rag/dto.py` | `EvidenceBundle`, `RetrievalRequest`, `RetrievedChunk`, `Locator` | `tests/unit/test_dto.py` |
| `ai/rag/prompts/registry.py` | `PromptRegistry` | `tests/unit/test_prompt_registry.py` |
| `ai/rag/generation/composer.py` | `GroundedAnswerComposer.compose` | `tests/unit/test_composer.py` |
| `ai/rag/cache/cag.py` | `build_cache_key`, `InMemoryCacheService` | `tests/unit/test_cag.py` |
| `ai/rag/memory/session_mag.py` | `InMemorySessionMemory` | `tests/unit/test_session_mag.py` |
| `ai/rag/query/rewrite.py`, `retrieval/fusion.py`, `reranking/cross_encoder.py` | `QueryRewriter`, `reciprocal_rank_fusion`, `CrossEncoderReranker` | `tests/unit/test_query_rewrite_fusion_rerank.py` |
| `ai/rag/service.py` | `FlameRAGService.answer` | `tests/unit/test_flame_service.py` |

Run: `python -m pytest -q tests/unit`

Rules:
- Answers cite only retrieved evidence IDs. When the evidence is inadequate, the system abstains.
- Application code depends on provider-neutral interfaces (Ollama/vLLM sit behind `providers/`).
- Memory is never treated as scientific evidence.
