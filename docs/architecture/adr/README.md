# Architecture Decision Records

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | 1.2.0 | 2026-11-07 | M12, L-1 | — |

Template: **Title, Status (proposed/accepted/superseded), Date, Context, Decision, Alternatives considered, Consequences, Links.**
ADRs are immutable. A changed decision gets a new ADR that supersedes the old one, and the old one's status is changed to `superseded by ADR-NNN`; nothing else in it is edited.

| ADR | Title | Status | Affected engineers | Sign-off |
|---|---|---|---|---|
| [001](ADR-001-monorepo-layout.md) | Monorepo layout | Accepted | All | Signed off 2026-11-07 |
| [002](ADR-002-pgvector-first.md) | PostgreSQL + pgvector before a dedicated vector DB | Accepted | Eman (E1), Anas (E2) | Signed off 2026-11-07 |
| [003](ADR-003-provider-neutral-model-router.md) | Provider-neutral model router | Accepted | Eman (E1), Ziad (E5) | Signed off 2026-11-07 |
| [004](ADR-004-aura-boundary.md) | AURA is an optional provider, never a core dependency | Accepted | Eman (E1), Belal (E4) | Signed off 2026-11-07 |
| [005](ADR-005-analyses-endpoint-naming.md) | `/api/analyses` instead of `/api/analysis/image` | Accepted | Belal (E4), Princess (E3) | Signed off 2026-11-07 |
| [006](ADR-006-single-retrieval-stack.md) | One retrieval stack | Proposed | Eman (E1) | Proposal signed off 2026-11-07 |
| [007](ADR-007-graph-storage.md) | Graph storage: relational tables first | Proposed | Anas (E2), Eman (E1) | Proposal signed off 2026-11-07 |
| [008](ADR-008-job-system.md) | RQ stays the job system for Phase 2 | Proposed | Princess (E3) | Proposal signed off 2026-11-07 |
| [009](ADR-009-auth-and-rbac.md) | Authentication and RBAC | Proposed | Belal (E4) | Proposal signed off 2026-11-07 |
| [010](ADR-010-contract-first-openapi.md) | Contract-first OpenAPI with a route-parity test | Accepted | Belal (E4) | Signed off 2026-11-07 |
| [011](ADR-011-scenario-relevance-ranking.md) | Rank investigations by evidence relevance to a cabin atmosphere | Accepted (implemented in PR #24) | Ziad (E5), Anas (E2) | Signed off 2026-11-07 |
| [012](ADR-012-commit-psi-tables.md) | Commit the PSI experimental tables and ISA-Tab metadata to Git | Accepted (implemented in PR #24) | Princess (E3), Ziad (E5) | Signed off 2026-11-07 |

"Accepted" means the decision describes what is built: ADR-001 to 005 and 010 on branch `ccr-c6a5a263-498la9` (PR #14), ADR-011 and 012 on `main` (PR #24).

**Sign-offs.** On 2026-11-07 the Lead (Anas) confirmed that every engineer named in the "Affected engineers" column had approved the ADRs listed against them. No approval is recorded as a GitHub review, so the Lead's confirmation is the record. For ADR-006 to 009 the approval is of the proposal: they stay Proposed until their decision is implemented, or until their owner accepts them under the terms each ADR states.

## Known limitations

- ADR-006 to 009 are Proposed: approved as proposals, not yet implemented or accepted.
- The 2026-11-07 sign-offs are recorded from the Lead's confirmation, not from individual reviews; an engineer who disagrees should say so, and the row will be corrected.
- ADRs describe decisions, not behaviour. The code and tests are the source of truth.

## Changelog

- 1.0.0 (2026-10-12): ADR-001 to ADR-010.
- 1.1.0 (2026-11-07): ADR-011 (scenario relevance ranking) and ADR-012 (committed PSI tables), Proposed.
- 1.2.0 (2026-11-07): sign-offs recorded for ADR-001 to 012 (Lead's confirmation); ADR-011 and 012 Accepted.
