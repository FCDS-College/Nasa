# Architecture Decision Records

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | 1.5.0 | 2026-11-13 | M12, L-1 | — |

Template: **Title, Status (proposed/accepted/superseded), Date, Context, Decision, Alternatives considered, Consequences, Links.**
ADRs are immutable. A changed decision gets a new ADR that supersedes the old one, and the old one's status is changed to `superseded by ADR-NNN`; nothing else in it is edited.

| ADR | Title | Status | Affected engineers | Sign-off |
|---|---|---|---|---|
| [001](ADR-001-monorepo-layout.md) | Monorepo layout | Accepted | All | Signed off 2026-11-07 |
| [002](ADR-002-pgvector-first.md) | PostgreSQL + pgvector before a dedicated vector DB | Accepted | Eman (E1), Anas (E2) | Signed off 2026-11-07 |
| [003](ADR-003-provider-neutral-model-router.md) | Provider-neutral model router | Accepted | Eman (E1), Ziad (E5) | Signed off 2026-11-07 |
| [004](ADR-004-aura-boundary.md) | AURA is an optional provider, never a core dependency | Accepted | Eman (E1), Belal (E4) | Signed off 2026-11-07 |
| [005](ADR-005-analyses-endpoint-naming.md) | `/api/analyses` instead of `/api/analysis/image` | Accepted | Belal (E4), Princess (E3) | Signed off 2026-11-07 |
| [006](ADR-006-single-retrieval-stack.md) | One retrieval stack | Accepted (implemented in PR #29) | Eman (E1) | Signed off 2026-11-07 |
| [007](ADR-007-graph-storage.md) | Graph storage: relational tables first | Accepted (implemented in PR #29) | Anas (E2), Eman (E1) | Signed off 2026-11-07 |
| [008](ADR-008-job-system.md) | RQ stays the job system for Phase 2 | Accepted (implemented in PR #29) | Princess (E3) | Signed off 2026-11-07 |
| [009](ADR-009-auth-and-rbac.md) | Authentication and RBAC | Accepted (implemented in PR #29) | Belal (E4) | Signed off 2026-11-07 |
| [010](ADR-010-contract-first-openapi.md) | Contract-first OpenAPI with a route-parity test | Accepted | Belal (E4) | Signed off 2026-11-07 |
| [011](ADR-011-scenario-relevance-ranking.md) | Rank investigations by evidence relevance to a cabin atmosphere | Accepted (implemented in PR #24) | Ziad (E5), Anas (E2) | Signed off 2026-11-07 |
| [012](ADR-012-commit-psi-tables.md) | Commit the PSI experimental tables and ISA-Tab metadata to Git | Accepted (implemented in PR #24) | Princess (E3), Ziad (E5) | Signed off 2026-11-07 |
| [013](ADR-013-historical-scenarios-coverage-verdict.md) | Historical scenarios, a gravity dimension and a scenario-level coverage verdict | Proposed (implemented on branch `ccr-93d3f1f0-bf65vh`) | Ziad (E5), Anas (E2) | Pending |
| [014](ADR-014-suppression-advisor-scope.md) | Suppression Advisor scope: what each fire type and each extinguisher may claim | Proposed (implemented on `main`, commit 15687d4) | Ziad (E5), Belal (E4) | Pending |

"Accepted" means the decision is approved and binding. For ADR-001 to 005, 010, 011 and 012 it also describes what is built: ADR-001 to 005 and 010 on branch `ccr-c6a5a263-498la9` (PR #14), ADR-011 and 012 on `main` (PR #24). ADR-006 to 009 were accepted on 2026-11-07 before they were fully built, and built on 2026-11-12 (below).

**Sign-offs.** On 2026-11-07 the Lead (Anas) confirmed that every engineer named in the "Affected engineers" column had approved the ADRs listed against them. No approval is recorded as a GitHub review, so the Lead's confirmation is the record. For ADR-006 to 009 that approval was first recorded as approval of the proposal (1.2.0); on 2026-11-07 the Lead then moved all four to Accepted.

## Implementation state of ADR-006 to 009 (built 2026-11-12, PR #29)

The 1.3.0 table listed what was missing on `main` at `73b014b`. Each item is now built:

| ADR | Built on 2026-11-12 | Still not built, and why |
|---|---|---|
| 006 | `ai/rag/retrieval/search_stack.py` orders every `/api/search` (and through it `/api/chat`) result: query rewrite kept next to the original, RRF, and the cross-encoder reranker through the router's `rerank` task (`FLAME_RERANKER_ENABLED`). The API's inline ranking is retired. ADR-006's benchmark gate was met: identical top 5 on all 26 gold questions. The reranker (fastembed ONNX, on by default since PR #30) gives hit@1 0.81 → 0.88 ([retrieval-2026-11-12.md](../../evaluation/reports/retrieval-2026-11-12.md)). | The reranker costs about 0.7 s per search on CPU, and the gold set it was measured on is not human-reviewed. The library's in-memory `RAGRetrievalPipeline` / `FlameRAGService` are not on the serving path; whether to retire them is Eman's call. |
| 007 | `flame_api/knowledge_graph.py`: 951 entities and 10,683 evidence-cited `table_parse` edges from the PSI tables and ISA-Tab records, rebuilt at every ingest. Also: recursive-CTE traversal (`GET /api/graph/entities/{id}`), the five E2-6 consistency checks (`GET /api/admin/graph/consistency`) and audited merges ([E2-6 §0](../../data/KNOWLEDGE_GRAPH_SCHEMA.md)). The web app's Knowledge Graph page (`/knowledge`, PR #32) browses entities and walks their links, 1 or 2 hops, each with its evidence cell. | No NLP extraction (D1), so no platforms, instruments or NTRS links. Graph RAG in chat is not built. Checks run on demand, not on a schedule. |
| 008 | Video jobs checkpoint to `video_checkpoint_frame` every segment and resume after `worker recover`; the result is identical to an uninterrupted run (tested). `POST /api/analyses/{id}/cancel`, with `progress` on the analysis (L-6 1.1.0). | Image jobs are not checkpointed (they take seconds). An RQ timeout still fails a video job rather than leaving it to resume. |
| 009 | An `admin` scope for every `/api/admin/` route; a `write` key gets 403 there. Admin keys must name an `--owner` (migration `0008`), so each audited actor maps to one person (SECURITY.md 0.7.0). | Owners are free text, not verified identities (no identity provider, by design). The deprecated write token is still an admin credential until it is removed. |

## Known limitations

- ADR-006 to 009 are built, with the gaps the table above names. Where an ADR and the code differ, the code is the truth.
- The 2026-11-07 sign-offs are recorded from the Lead's confirmation, not from individual reviews; an engineer who disagrees should say so, and the row will be corrected.
- ADRs describe decisions, not behaviour. The code and tests are the source of truth.

## Changelog

- 1.0.0 (2026-10-12): ADR-001 to ADR-010.
- 1.1.0 (2026-11-07): ADR-011 (scenario relevance ranking) and ADR-012 (committed PSI tables), Proposed.
- 1.2.0 (2026-11-07): sign-offs recorded for ADR-001 to 012 (Lead's confirmation); ADR-011 and 012 Accepted.
- 1.3.0 (2026-11-07): ADR-006 to 009 Accepted on the Lead's instruction; their implementation state recorded; "Accepted" redefined as approved, not necessarily built.
- 1.4.0 (2026-11-12): ADR-006 to 009 built (PR #29); the implementation table now records what was built and what is still open.
- 1.4.1 (2026-11-12): reranker on by default; reviewed spelling aliases in the graph (951 entities).
- 1.4.2 (2026-11-12): ADR-007's built column names the Knowledge Graph page (PR #32).
- 1.5.0 (2026-11-13): ADR-013 (historical scenarios, gravity, coverage verdict), Proposed.
- 1.6.0 (2026-11-14): ADR-014 (Suppression Advisor scope, D2 gates, fire-type matrix), Proposed.
