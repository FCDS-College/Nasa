# Architecture Decision Records

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review | 1.1.0 | 2026-11-07 | M12, L-1 | — |

Template: **Title, Status (proposed/accepted/superseded), Date, Context, Decision, Alternatives considered, Consequences, Links.**
ADRs are immutable. A changed decision gets a new ADR that supersedes the old one, and the old one's status is changed to `superseded by ADR-NNN`; nothing else in it is edited.

| ADR | Title | Status | Affected engineer (sign-off) |
|---|---|---|---|
| [001](ADR-001-monorepo-layout.md) | Monorepo layout | Accepted | All |
| [002](ADR-002-pgvector-first.md) | PostgreSQL + pgvector before a dedicated vector DB | Accepted | Eman (E1), Anas (E2) |
| [003](ADR-003-provider-neutral-model-router.md) | Provider-neutral model router | Accepted | Eman (E1), Ziad (E5) |
| [004](ADR-004-aura-boundary.md) | AURA is an optional provider, never a core dependency | Accepted | Eman (E1), Belal (E4) |
| [005](ADR-005-analyses-endpoint-naming.md) | `/api/analyses` instead of `/api/analysis/image` | Accepted | Belal (E4), Princess (E3) |
| [006](ADR-006-single-retrieval-stack.md) | One retrieval stack | Proposed | Eman (E1) |
| [007](ADR-007-graph-storage.md) | Graph storage: relational tables first | Proposed | Anas (E2), Eman (E1) |
| [008](ADR-008-job-system.md) | RQ stays the job system for Phase 2 | Proposed | Princess (E3) |
| [009](ADR-009-auth-and-rbac.md) | Authentication and RBAC | Proposed | Belal (E4) |
| [010](ADR-010-contract-first-openapi.md) | Contract-first OpenAPI with a route-parity test | Accepted | Belal (E4) |
| [011](ADR-011-scenario-relevance-ranking.md) | Rank investigations by evidence relevance to a cabin atmosphere | Proposed (implemented in PR #24) | Ziad (E5), Anas (E2) |

"Accepted" here means it describes what is built on branch `ccr-c6a5a263-498la9` (PR #14). Each still needs the named engineer's sign-off, recorded in the table above, before the Week 1 gate counts it.

## Known limitations

- ADR-009 is Proposed; the other ADRs describe what is built on PR #14 and still need the named engineer's sign-off.
- ADRs describe decisions, not behaviour. The code and tests are the source of truth.

## Changelog

- 1.0.0 (2026-10-12): ADR-001 to ADR-010.
- 1.1.0 (2026-11-07): ADR-011 (scenario relevance ranking), Proposed.
