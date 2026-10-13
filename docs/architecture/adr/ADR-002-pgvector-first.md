# ADR-002: PostgreSQL + pgvector before a dedicated vector database

- **Status:** Accepted
- **Date:** 2026-10-12 (records the MVP decision behind migration `0003_vector_index`)
- **Deciders:** Lead; Eman (E1) and Anas (E2) affected

## Context
Retrieval needs lexical and semantic search over about 10^4–10^5 chunks, with provenance joins to `document`, `evidence` and `source`. The corpus has to work on one machine and offline (Sub-phase 2H). A separate vector store would add another service to run, back up and keep in sync.

## Decision
Store embeddings in PostgreSQL with pgvector:
- `chunk_embedding(chunk_id → document_chunk, model, vector(384))` with an HNSW cosine index;
- one `vector_index_manifest` row that names the published index version.

The embedding model is `BAAI/bge-small-en-v1.5` through fastembed (ONNX, CPU), served by the `fastembed` provider behind the router (ADR-003).

Each index build publishes a knowledge version (`flame_api/knowledge_version.py`). The vector store is a derived index of PostgreSQL and is rebuilt from it (`python -m flame_api.vector_index build`).

## Alternatives considered
- **Qdrant / Weaviate / Milvus.** Better at above about 10^7 vectors. At our size they add a service, a backup target and a consistency problem (the L-5 index-sync contract would need two-phase updates). Deferred until a measured need exists.
- **FAISS files.** No transactional link to provenance rows. Rejected.

## Consequences
- One backup, `pg_dump`, covers metadata and vectors (L-8 runbook).
- Semantic search is PostgreSQL-only; SQLite tests exercise the lexical path only. The `migrations` CI job runs pgvector.
- When the corpus or the latency budget outgrows pgvector, a new ADR supersedes this one, and L-5 already defines the stable IDs a second store needs.

## Links
`apps/api/migrations/versions/0003_vector_index.py`, `apps/api/flame_api/vector_index.py`, [L-5 index-sync contract](../index-sync-contract.md).
