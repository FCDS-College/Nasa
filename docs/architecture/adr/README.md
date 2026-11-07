# Architecture Decision Records

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | 1.3.0 | 2026-11-07 | M12, L-1 | — |

Template: **Title, Status (proposed/accepted/superseded), Date, Context, Decision, Alternatives considered, Consequences, Links.**
ADRs are immutable. A changed decision gets a new ADR that supersedes the old one, and the old one's status is changed to `superseded by ADR-NNN`; nothing else in it is edited.

| ADR | Title | Status | Affected engineers | Sign-off |
|---|---|---|---|---|
| [001](ADR-001-monorepo-layout.md) | Monorepo layout | Accepted | All | Signed off 2026-11-07 |
| [002](ADR-002-pgvector-first.md) | PostgreSQL + pgvector before a dedicated vector DB | Accepted | Eman (E1), Anas (E2) | Signed off 2026-11-07 |
| [003](ADR-003-provider-neutral-model-router.md) | Provider-neutral model router | Accepted | Eman (E1), Ziad (E5) | Signed off 2026-11-07 |
| [004](ADR-004-aura-boundary.md) | AURA is an optional provider, never a core dependency | Accepted | Eman (E1), Belal (E4) | Signed off 2026-11-07 |
| [005](ADR-005-analyses-endpoint-naming.md) | `/api/analyses` instead of `/api/analysis/image` | Accepted | Belal (E4), Princess (E3) | Signed off 2026-11-07 |
| [006](ADR-006-single-retrieval-stack.md) | One retrieval stack | Accepted (partly implemented) | Eman (E1) | Signed off 2026-11-07 |
| [007](ADR-007-graph-storage.md) | Graph storage: relational tables first | Accepted (schema only) | Anas (E2), Eman (E1) | Signed off 2026-11-07 |
| [008](ADR-008-job-system.md) | RQ stays the job system for Phase 2 | Accepted (partly implemented) | Princess (E3) | Signed off 2026-11-07 |
| [009](ADR-009-auth-and-rbac.md) | Authentication and RBAC | Accepted (partly implemented) | Belal (E4) | Signed off 2026-11-07 |
| [010](ADR-010-contract-first-openapi.md) | Contract-first OpenAPI with a route-parity test | Accepted | Belal (E4) | Signed off 2026-11-07 |
| [011](ADR-011-scenario-relevance-ranking.md) | Rank investigations by evidence relevance to a cabin atmosphere | Accepted (implemented in PR #24) | Ziad (E5), Anas (E2) | Signed off 2026-11-07 |
| [012](ADR-012-commit-psi-tables.md) | Commit the PSI experimental tables and ISA-Tab metadata to Git | Accepted (implemented in PR #24) | Princess (E3), Ziad (E5) | Signed off 2026-11-07 |

"Accepted" means the decision is approved and binding. For ADR-001 to 005, 010, 011 and 012 it also describes what is built: ADR-001 to 005 and 010 on branch `ccr-c6a5a263-498la9` (PR #14), ADR-011 and 012 on `main` (PR #24). ADR-006 to 009 were accepted on 2026-11-07 before they were fully built; what exists and what does not is listed below.

**Sign-offs.** On 2026-11-07 the Lead (Anas) confirmed that every engineer named in the "Affected engineers" column had approved the ADRs listed against them. No approval is recorded as a GitHub review, so the Lead's confirmation is the record. For ADR-006 to 009 that approval was first recorded as approval of the proposal (1.2.0); on 2026-11-07 the Lead then moved all four to Accepted.

## Implementation state of ADR-006 to 009 (checked against `main` at `73b014b`)

| ADR | Built | Not built yet |
|---|---|---|
| 006 | `/api/search` fuses lexical and pgvector results with `ai.rag.retrieval.fusion.reciprocal_rank_fusion` on every page and filter, whenever the vector index is up; otherwise search is lexical only (`apps/api/flame_api/main.py`). The cross-encoder reranker provider is registered when `FLAME_RERANKER_ENABLED=true` (`ai_runtime.py`). | The reranker is not applied in `/api/search`, and the answer cache records `reranker_version` `none@1`. There is no query rewrite. The API's own search is still the serving path, so it has not been retired in favour of `ai/rag`. |
| 007 | `knowledge_entity` and `knowledge_relation` with the edge provenance fields and `merged_into` (migration `0004_phase2_tables`, `models.py`). | Nothing writes or reads these tables yet: no entity extraction, no recursive-CTE traversal, no consistency checks. |
| 008 | Job status in PostgreSQL (`analysis_result.status`). Idempotency by `Idempotency-Key` (unique `idempotency_key`). `worker.recover` re-queues analyses stuck in `queued` or `processing` after a restart, and fails them after the cap. | No per-segment checkpoint for video jobs, so a recovered video job re-runs from the start. No cancellation. |
| 009 | Step 1: admin endpoints need write scope, and each change writes an `audit_event` row. Step 2, in part: per-client API keys stored as SHA-256 hashes, with scopes `read` / `write`, revocation and the client name as the audit actor (migration `0005_api_clients`, `flame_api/clients.py`). | There is no `admin` role. `/api/admin/*` and destructive operations need `write`, so any write-scoped client can act as an admin. Keys identify clients, not people. |

## Known limitations

- ADR-006 to 009 are Accepted but only partly implemented (see the table above). Until the rest is built, the code, not the ADR, describes current behaviour.
- The 2026-11-07 sign-offs are recorded from the Lead's confirmation, not from individual reviews; an engineer who disagrees should say so, and the row will be corrected.
- ADRs describe decisions, not behaviour. The code and tests are the source of truth.

## Changelog

- 1.0.0 (2026-10-12): ADR-001 to ADR-010.
- 1.1.0 (2026-11-07): ADR-011 (scenario relevance ranking) and ADR-012 (committed PSI tables), Proposed.
- 1.2.0 (2026-11-07): sign-offs recorded for ADR-001 to 012 (Lead's confirmation); ADR-011 and 012 Accepted.
- 1.3.0 (2026-11-07): ADR-006 to 009 Accepted on the Lead's instruction; their implementation state recorded; "Accepted" redefined as approved, not necessarily built.
