# ADR-007: Graph storage — relational tables first

- **Status:** Accepted (2026-11-07). Decision owners: Anas (E2) with the Lead and Eman (E1). Accepted on the Lead's instruction; the owners' approval is recorded in ADR index 1.2.0. Partly implemented: see ADR index 1.3.0.
- **Date:** 2026-10-12

## Context
D2 (scientific knowledge graph), D3 (storage strategy) and D5 (graph memory) need entities, typed relations, edge provenance and consistency checks. The graph must work offline and be backed up and restored with everything else. Its size in Phase 2 is bounded by the corpus: thousands of entities.

## Decision (proposed)
Store the graph in PostgreSQL:
- `knowledge_entity` and `knowledge_relation`, created by migration `0004_phase2_tables`;
- each relation carries the edge provenance fields `evidence_id`, `extraction_method`, `extractor_version`, `confidence` and `review_status`;
- traversal uses recursive CTEs.

A dedicated graph database (Neo4j, Memgraph, Apache AGE) is introduced only when a measured Graph RAG query cannot meet its latency budget, by a superseding ADR.

## Alternatives considered
- **Neo4j from the start.** Another service, licence review, separate backup, and an ID-sync problem with pgvector (L-5).
- **Apache AGE inside PostgreSQL.** Keeps one database, but the extension is not in the `pgvector/pgvector` image. Revisit if Cypher becomes necessary.

## Consequences
- Stable IDs: `entity_id = stable_ulid(entity_type + ":" + canonical_name)`. The same rule is used in the vector index and any future graph store (L-5).
- Entity resolution, merge (`merged_into`) and consistency checks are SQL (E2-6).

## Links
[E2-6 knowledge graph schema](../../data/KNOWLEDGE_GRAPH_SCHEMA.md); `apps/api/flame_api/models.py`.
