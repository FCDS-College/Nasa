# Graph Memory design (E1-9)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Eman | Draft (design only; every behaviour is **Planned**) | 0.1.0 | 2026-10-14 | D5, M5 | `ai/rag/memory/session_mag.py` (M5, implemented); graph parts none yet |

**Status: design only.** Session MAG (M5) is implemented in `ai/rag/memory/session_mag.py` and documented in `mag-policy.md`. Both graph memories below are **Planned**. Examples are synthetic.

## 1. Two separate memories

| | Scientific Graph Memory | Session Graph Memory |
|---|---|---|
| Holds | Source-grounded relations: experiments and conditions, documents and datasets, measurements, claims with evidence, conflicting claims, derived findings | Current objective, selected experiments, evidence already examined, active filters, pending questions, links between tasks |
| Storage | PostgreSQL authoritative tables (M8 `KnowledgeEntity`, `KnowledgeRelation`) | Extends the M5 memory store; same `user_id` + `conversation_id` scope; graph links as rows, not a second store |
| Access control | Read for any authorised user; write only through the reviewed ingestion path | Only the owning user and conversation; no cross-user or cross-conversation reads |
| Retention | Versioned; superseded, never edited in place | Expiry set on every record (`expires_at`); default same as M5 |
| Deletion | By document or version through the knowledge-publication flow | Delete by conversation or by user on request; purge of expired records |
| Used as | Evidence source through its linked chunks | Context only; never cited, never merged into evidence passages |

The two never share a table, an id space or a prompt section. Session memory can **point at** scientific entity ids (e.g. "selected experiment `exp-01`") but cannot create or change scientific records.

## 2. How Session Graph Memory extends M5

- Records keep the M5 schema (`scope`, `actor`, `origin`, `confidence`, `created_at`, `expires_at`, `superseded_by`). New scope values (Planned): `session_graph_node` and `session_graph_edge`.
- A node record stores `{kind, ref_id}` (for example `kind=experiment`, `ref_id=exp-01`); an edge record stores `{from, to, relation}` using the same relation names as D2.
- `memory_used` disclosure, expiry, supersede and the contamination rule (memory conflicting with evidence is dropped) apply unchanged.
- Cached answers that used session graph memory are not cached, same as M5.

## 3. Promotion rules (session -> scientific)

Nothing moves automatically. A session fact can become a **candidate** scientific relation only when all of these hold:

1. It is backed by at least one retrieved evidence chunk with a resolvable `chunk_id`, not by the user's statement alone.
2. The relation type exists in the D2 schema and passes the association-versus-causation guard in `graph-rag.md`.
3. It does not contradict an existing reviewed relation; if it does, it opens a conflict record instead.
4. A human reviewer (domain reviewer, then Anas for the schema) marks it `reviewed`. Until then it has `review_status=candidate` and is excluded from default Graph RAG traversal.

Synthetic example: the user says "FX-0042 used oxygen". The reviewer finds chunk `c-demo-001` saying so, links it, and marks `exp-01 -USES-> oxidizer-2` as reviewed. Without the chunk the statement stays session-only and is discarded at expiry.

## Known limitations

- No graph tables, extractors or review workflow exist.
- Session MAG is in-memory only (`InMemorySessionMemory`); persistence is Planned, so Session Graph Memory has no store to extend yet.
- Reviewer roles and the review UI are not defined.
- Retention numbers for the graph scopes are not decided; they follow M5 until the Lead sets them.

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-14 | First design draft for E1-9 (D5); all graph behaviour Planned. |