# Documentation Requirements: Lead Engineer (Anas, Backend / AI Infrastructure / Integration / DevOps)

| | |
|---|---|
| **Phase** | Phase 2: Advanced Scientific Intelligence Platform |
| **Issued** | 2026-10-10 |
| **Branch** | `main` (task branches from `main` for larger changes) |
| **Basis** | [Phase 2 Plan](../plan/PHASE2_PLAN.md): §2 carry-over items **M1** (model router), **M6** (API gaps) and **M12** (CI, OpenTelemetry, ADRs, runbook, release); §9 "Lead Engineer priorities"; and the §11 integrated-release gate; MVP Plan §5.2–§5.3, §11, §12, §19, §22 |
| **Reviewers** | Each Lead document needs a sign-off from the engineer most affected by it (listed per document in §3), because there is no reviewer above the Lead. |

The Lead has two documentation jobs:
1. **Write the platform documents** (§3–§4).
2. **Run documentation governance for the whole team** (§5): the docs index, the PR template, the review matrix, weekly status and release sign-off.

Each engineer has their own requirements file on their branch:
- `docs/reports/DOC_REQUIREMENTS_Eman.md` on `Eman`
- `docs/reports/DOC_REQUIREMENTS_Princess.md` on `Princess`
- `docs/reports/DOC_REQUIREMENTS_Belal.md` on `Belal`
- `docs/reports/DOC_REQUIREMENTS_Ziad.md` on `Ziad`
- `docs/reports/DOC_REQUIREMENTS_Anas.md` on `main` (Engineer 2)

---

## 1. Why this matters

The Lead's first Phase 2 priority is contracts stable enough for the team to work independently, and only written contracts are stable. The audit on 2026-10-10 found these platform gaps:
- **no ADRs**, **no runbook** and **no release tag**;
- `docs/architecture/` holds only `overview.md`;
- the only CI is the AURA contract dry run;
- `python -m pytest` from the repo root fails at collection;
- no model router exists, so chat requires AURA;
- `/api/chat` is outside OpenAPI;
- `GET /api/documents` and `GET /api/experiments` are missing;
- there is no OpenTelemetry tracing.

## 2. Rules for every Lead document

1. **Location and format:** Markdown at the path given in §3, in English. The OpenAPI file stays machine-generated JSON.
2. **Header block:** the same header as the engineers use (Owner, Status, Version, Last updated, Plan items, Code paths).
3. **Evidence over claims:** every operational step in a runbook has been executed at least once, and the doc records the date and the commit it was tested on. Every "CI checks X" statement links the workflow file.
4. **Contracts are versioned:** API changes follow semver, with an entry in `docs/api/CHANGELOG.md` and a deprecation window for breaking changes ("Existing MVP APIs should remain compatible wherever practical").
5. **ADRs are immutable:** a changed decision gets a new ADR that supersedes the old one; the old one isn't edited.
6. **Secrets:** no tokens, passwords or connection strings. Environment variables are documented by name and purpose only.
7. **Limitations:** every document ends with **Known limitations** (or, for an ADR, **Consequences**).

## 3. Required documents

| ID | Document | Path | Covers | Due (Phase 2 week) | Sign-off |
|---|---|---|---|---|---|
| L-1 | Architecture Decision Records | `docs/architecture/adr/ADR-NNN-<slug>.md` | M12, D3 | ADR-001 to ADR-004: Week 1; more as decisions are made | Affected engineer |
| L-2 | Architecture overview (update) | `docs/architecture/overview.md` | §3 architecture | Week 2, Week 8 | Eman, Princess |
| L-3 | Model routing and providers | `docs/architecture/model-routing.md` | M1, B5, C2 | Week 1–2 | Eman, Ziad |
| L-4 | API contract and changelog | `docs/api/openapi.json` (generated), `docs/api/API_SCHEMAS.md`, `docs/api/CHANGELOG.md` | M6, A4, B, C | Continuous; every API PR | Belal |
| L-5 | Index synchronization contract | `docs/architecture/index-sync-contract.md` | D3, D6 | Week 4 | Anas (E2), Eman |
| L-6 | Background jobs | `docs/architecture/background-jobs.md` | A4, B2 | Week 3 | Princess, Anas (E2) |
| L-7 | CI/CD and testing guide | `docs/operations/CI_CD.md` | M12 | Week 1 | Ziad |
| L-8 | Runbook | `docs/operations/RUNBOOK.md` | M12, §11 | Week 2, Week 8 | Any engineer who has dry-run it |
| L-9 | Observability guide | `docs/operations/OBSERVABILITY.md` | M12, §11 | Week 3 | Ziad |
| L-10 | Security and access control | `docs/operations/SECURITY.md` | B6, MVP §19 | Week 7 | Belal, Anas (E2) |
| L-11 | Release notes | `docs/releases/<version>.md` | M12, Week 8 | `v0.1.0-mvp` in Week 1; release candidate in Week 8 | Ziad (gate verdict) |
| L-12 | AURA boundary (update) | `docs/integration/AURA_INTEGRATION_STATUS.md` | M1, §12 | Week 2 | — |

## 4. Required contents

### L-1 Architecture Decision Records
Template: **Title, Status (proposed/accepted/superseded), Date, Context, Decision, Alternatives considered, Consequences, Links**. Required ADRs:
- **ADR-001** Monorepo layout (MVP §14 and the 2026-10-06 restructure).
- **ADR-002** PostgreSQL + pgvector before a dedicated vector DB.
- **ADR-003** Provider-neutral model router (Ollama local, vLLM on L40S, AURA optional).
- **ADR-004** AURA boundary: optional provider, never a core dependency, and why `/api/chat` is kept out of AURA's derived tools.
- **ADR-005** `/api/analyses` naming vs the MVP's `/api/analysis/image`.
- **ADR-006** Single retrieval stack (with Eman, M2).
- **ADR-007** Graph storage strategy (with Anas E2, D3).
- **ADR-008** Job system for image and video analysis (RQ or a replacement).
- **ADR-009** Authentication and RBAC model (B6).

### L-2 Architecture overview
- The Phase 2 logical architecture mapped to **actual** modules, services and deployments: what is a separate service and what is a module.
- Request lifecycle diagrams for chat, search, image/video analysis and admin operations.
- Where every version identifier is set (corpus, model, prompt, pipeline, benchmark).

### L-3 Model routing and providers
- The `LLMProvider` / `EmbeddingProvider` / CV provider interfaces and their DTOs.
- The capability → provider/model map, approved versions, and how routing configuration is changed and audited (B5).
- Timeout, retry (idempotent only), fallback and concurrency rules. A failed retrieval returns evidence-insufficient, never an uncited answer.
- L40S allocation: vLLM vs CV memory budgets and the profiles measured (with Princess's performance doc).

### L-4 API contract and changelog
- `openapi.json` generated from the code, plus a CI check that it is current.
- `API_SCHEMAS.md` regenerated with `docs/tools/render_api_schemas.py`.
- The error-envelope reference, auth requirements per route, and pagination rules.
- Phase 2 endpoints (video, admin, evaluation, graph), each with a request/response example and its contract-test file.
- `CHANGELOG.md` with semver entries and deprecations.

### L-5 Index synchronization contract
- The stable-ID rules across PostgreSQL, pgvector and the graph store.
- How a knowledge-version publication (Anas's E2-5) triggers re-embedding, graph updates and cache invalidation, and how partial failures are detected and recovered.
- An observable rebuild procedure (status, progress, rollback), as required by §11.

### L-6 Background jobs
Queues, job types, payload schemas, status lifecycle, retries, cancellation, timeouts, idempotency keys, failure reporting, and how jobs appear in the Admin "System Operations" module.

### L-7 CI/CD and testing guide
- Every workflow and what it runs: Python lint and tests for `tests/` and `apps/api`; web lint, typecheck and build; the OpenAPI freshness check; contract tests; the AURA dry run; secret scanning.
- The **single repo-root test command** (after fixing the `flame_api` import collection).
- Required checks for merging, and how deployments (Railway, then L40S) are triggered.

### L-8 Runbook
- Local setup from a clean machine: Compose, `.env` from `infrastructure/.env.example`, seed, ingest, vector index build.
- Deployment, migrations, rollback, secret rotation, **backup and restore drill** (performed and dated), the L40S model load and health check, and common incidents with fixes.
- How to reproduce the demo from a tagged release (MVP §22).

### L-9 Observability guide
OpenTelemetry span names and attributes along the API → orchestration → cache → retrieval → rerank → provider/CV → persistence path; the structured-log field list; metrics (latency p50/p95, queue depth, cache hit rate, GPU memory, tokens/s); dashboards; alert thresholds; and a description of how to follow one `request_id` end to end.

### L-10 Security and access control
Roles and permissions (read/write/admin), session handling, protected ingestion and destructive operations, the audit-log schema, upload validation limits, document-parsing isolation, prompt-injection defenses (with Eman), a threat model summary, and the result of the Week 8 security review.

### L-11 Release notes
For each release: the version and tag, commit, included changes (by plan item), migrations, evaluation summary (linking Ziad's scorecard), known limitations, upgrade steps and rollback target.

### L-12 AURA boundary
Update the status document so it describes AURA as an optional provider behind M1, and mark the MVP-era statements that are superseded.

## 5. Team documentation governance (Lead-owned)

| ID | Item | Path | Due |
|---|---|---|---|
| G-1 | **Documentation index**: one table listing every team document with its owner, status and last update | `docs/README.md` | Week 1, kept current |
| G-2 | **PR template** with a documentation checklist (docs updated? numbers generated? header and changelog updated? limitations?) | `.github/pull_request_template.md` | Week 1 |
| G-3 | **Review matrix**: who reviews which document type, taken from each engineer's requirements file | `docs/README.md` (section) | Week 1 |
| G-4 | **Weekly integration status**: per engineer, the plan items closed (with evidence links), the docs delivered vs due, blockers, and risks | `docs/reviews/PHASE2_WEEK_<n>.md` | End of every week |
| G-5 | **Documentation audit** at Weeks 4 and 8: check every doc against the code at a commit and list stale ones with owners | `docs/reviews/DOC_AUDIT_WEEK_<n>.md` | Weeks 4 and 8 |
| G-6 | **Release sign-off matrix**: each owner signs off their area for the release candidate | `docs/releases/<version>.md` (section) | Week 8 |

**Enforcement:** a PR that changes behavior without updating its documentation is not merged. Overdue documents go into the weekly status (G-4) with a new due date and an owner.

## 6. Existing documents to fix

| File | Problem found in the 2026-10-10 audit | Action |
|---|---|---|
| `docs/architecture/overview.md` | Pre-Phase 2; no ADRs referenced | Update as L-2 and link the ADRs |
| `docs/api/openapi.json`, `API_SCHEMAS.md` | `/api/chat` excluded; list endpoints missing | Update with M6 (L-4) |
| `docs/integration/AURA_INTEGRATION_*.md` | Describe AURA as required for chat | Update as L-12 |
| `README.md`, `tests/README.md` | The root test command fails at collection | Fix the command and document it (L-7) |
| `infrastructure/README.md`, `apps/api/README.md` | No backup/restore, rollback or incident steps | Move operational steps into L-8 and link it |
| `docs/plan/DAY2_TASKS.md` | MVP-era task list | Add a status line pointing to the Phase 2 plan |
| `.railway/` (untracked) | Unclear whether it belongs in the repo | Decide, then either commit it with docs or git-ignore it |

## 7. Acceptance checklist (affected engineer signs off)

- [ ] ADR-001 to ADR-004 are accepted in Week 1, and every later architectural decision has an ADR.
- [ ] The OpenAPI file is generated and checked in CI, and every endpoint has a contract test and a changelog entry.
- [ ] The runbook has been executed from a clean machine by someone other than the Lead, and the backup/restore drill is dated.
- [ ] One repo-root test command passes, and CI enforces the required checks.
- [ ] `v0.1.0-mvp` is tagged, with release notes.
- [ ] The docs index, PR template and weekly status (G-1 to G-4) are running from Week 1.
- [ ] Known limitations or consequences are stated in every document.
