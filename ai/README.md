# ai/

Evidence-first research intelligence. **Owner:** Engineer 1, with the Lead for deployment and router integration. **Status:** RAG retrieval pipeline in progress.

| Folder | Status | What goes here |
|---|---|---|
| `rag/` | **active** | `ingestion/` (loader, chunker, pipeline), `embeddings/`, `retrieval/` (vector, keyword, hybrid, metadata filter, RAG pipeline), `reranking/`, `context/`, `citations/`, `evaluation/` (retrieval metrics) |
| `orchestration/`, `prompts/`, `routing/`, `cag/`, `mag/`, `providers/` | planned | MVP plan §14 |

Import as `from ai.rag.retrieval.hybrid_search import HybridSearchService`, running from the repo root. Tests live in `tests/unit/`; design notes live in `docs/ai/`.

Rules:
- Answers cite only retrieved evidence IDs. When the evidence is inadequate, the system abstains.
- Application code depends on provider-neutral interfaces (Ollama/vLLM sit behind `providers/`).
- Memory is never treated as scientific evidence.
