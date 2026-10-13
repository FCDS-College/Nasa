# ADR-001: Monorepo layout

- **Status:** Accepted
- **Date:** 2026-10-12 (records the 2026-10-06 restructure)
- **Deciders:** Lead (Anas); all engineers affected

## Context
The MVP grew as separate notebooks and scripts per engineer. MVP Plan §14 reserved a single repository with top-level areas, and on 2026-10-06 the repository was reorganised to match. Phase 2 adds video, admin, evaluation and graph work that crosses those areas, and the 2H router has to be shared by the API, the worker and Eman's RAG code.

## Decision
One repository, `FCDS-College/Nasa`, with these top-level areas and owners:

| Path | Contents | Owner |
|---|---|---|
| `apps/api` | FastAPI service, Alembic migrations, API tests | Lead |
| `apps/web` | Next.js dashboard | Belal (E4) |
| `ai/` | `rag/` (Eman), `providers/` and `routing/` (Lead): shared AI code, importable as `ai.*` from the repo root | E1 / Lead |
| `cv/` | CV pipeline and contracts | Princess (E3) |
| `knowledge/` | Acquisition, provenance and registry scripts | Anas (E2) |
| `datasets/` | Registry, manifests, checksums, evaluation sets (raw mirrors are git-ignored) | Anas (E2) / Ziad (E5) |
| `docs/` | All documentation (`docs/README.md` is the index) | Each owner |
| `infrastructure/`, `.railway/` | Compose stack, Railway IaC | Lead |
| `tests/` | Repo-level unit, CV, integration and evaluation tests | Ziad (E5) + owners |

The repo root is the import root: `pytest.ini` sets `pythonpath = . apps/api apps/api/tests`, and the API image sets `PYTHONPATH=/app` and copies `ai/providers`, `ai/routing` and `cv`.

## Alternatives considered
- **One repository per app.** This would need versioned packages for `ai/` and `cv/`, plus cross-repo CI, for a six-person team. Rejected.
- **`apps/api/app/ai/` inside the API package.** Eman's `ai/rag` and the worker could not share it without importing the API. Rejected (Phase 2 Plan §7A Task 2 names `ai/providers`, `ai/routing`).

## Consequences
- A single `python -m pytest` and one CI workflow (`.github/workflows/ci.yml`) cover everything.
- `ai/` is a namespace package with no `__init__.py`, so `ai.rag`, `ai.providers` and `ai.routing` are separate subpackages. The Dockerfile must copy each subpackage it needs.
- Raw data never enters git (`.gitignore`: `datasets/raw/`, `datasets/derived/`), so some tests skip when a mirror is absent. This is stated in each such test.

## Links
MVP Plan §14; `README.md` repository map; [ADR-010](ADR-010-contract-first-openapi.md).
