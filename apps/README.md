# apps/

User-facing applications. **Status:** not started.

| Folder | Owner | What goes here |
|---|---|---|
| `web/` | Engineer 4 | Next.js + TypeScript scientific dashboard. UI only: talks to the API through a generated client and never touches a database directly. |
| `api/` | Lead | FastAPI + Pydantic service: routes, schemas, the auth boundary and service composition. No provider-specific logic in route handlers. |

See MVP plan §12 (FastAPI backend) and §13 (Frontend) in `docs/plan/`.
