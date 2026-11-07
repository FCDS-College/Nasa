# ADR-008: RQ stays the job system for Phase 2

- **Status:** Accepted (2026-11-07). Decision owner: Lead, with Princess (E3). Accepted by the Lead; Princess's approval is recorded in ADR index 1.2.0. Partly implemented: see ADR index 1.3.0.
- **Date:** 2026-10-12

## Context
Image analysis runs on RQ (`rq worker flame-analysis`) over Redis with AOF persistence. Video analysis (Workstream A) adds long jobs that need progress, cancellation and resumption after a restart (2H Task 6, scenario "the application restarts during a video job").

## Decision (proposed)
Keep RQ, add the missing parts in application code (L-6), and do not change the queue:
- job status lives in PostgreSQL (`analysis_result.status`), not only in Redis;
- jobs are idempotent by `idempotency_key`;
- video jobs checkpoint per processed segment, so a restarted job resumes at the last checkpoint.

## Alternatives considered
- **Celery.** More features (canvas, retries) at a higher operational cost; it brings no capability we lack.
- **Dramatiq.** Similar, but no reason to migrate.
- **Temporal.** Durable workflows by design, but it adds a server and is heavy for one team. Revisit if video pipelines become multi-stage DAGs.

## Consequences
Restart safety comes from the PostgreSQL status and checkpoints, not from RQ. L-6 documents the lifecycle.

## Links
[L-6 background jobs](../background-jobs.md); `apps/api/flame_api/worker.py`.
