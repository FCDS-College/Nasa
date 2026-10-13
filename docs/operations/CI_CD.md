# L-7: CI/CD and testing guide

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | In review (sign-off: Ziad E5) | 1.0.0 | 2026-10-12 | M12 | `.github/workflows/`, `pytest.ini`, `ruff.toml`, `.gitleaks.toml` |

## 1. The single repo-root test command

```bash
python -m pip install -e "apps/api[dev,cv,ingestion,observability]" -r ai/requirements.txt
python -m pytest
```

`pytest.ini` collects `tests/` and `apps/api/tests` in one run. `--import-mode=importlib` lets the two `test_ingestion.py` files coexist, which was the 2026-10-10 collection failure. `pythonpath` makes `ai`, `cv` and `flame_api` importable without an editable install. `apps/api` can still be run alone with `cd apps/api && python -m pytest`.

Result at `2afbc37`, 2026-10-12: **179 passed, 1 skipped**. The skip is `test_mirrored_psi_tables_are_ingested_with_provenance_and_stable_ids`, which needs the git-ignored `datasets/raw/` PSI mirror.

## 2. Workflows

| Workflow / job | File | Runs | Trigger |
|---|---|---|---|
| CI / `python` | [`ci.yml`](../../.github/workflows/ci.yml) | installs `tesseract-ocr` (for the real OCR test); `ruff check .` (error-only rules); `knowledge/ingestion/validate_registry.py`; `docs/tools/render_api_schemas.py --check`; `python -m pytest`. This includes the contract-parity test (ADR-010), contract-shape tests and the offline-routing scenarios (H-5). | every PR, push to `main` |
| CI / `migrations` | `ci.yml` | pgvector/pg16 service: `alembic upgrade head`, `downgrade -1`, `upgrade head`, `seed`, `ingest` twice (idempotency) | every PR, push to `main` |
| CI / `web` | `ci.yml` | `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build` in `apps/web` | every PR, push to `main` |
| CI / `secrets` | `ci.yml` | gitleaks 8.28.0 (download checksum-pinned) over full git history with `.gitleaks.toml` | every PR, push to `main` |
| AURA Link 2 Contract | [`aura-link2-contract.yml`](../../.github/workflows/aura-link2-contract.yml) | `tests/integration/aura_blueprint_dryrun.py` against a pinned AURA revision. It compiles AURA tools from `openapi.json`, validates every tool against the 200 examples, and **fails if an `x-aura-exclude` operation is compiled or the pinned AURA ignores the flag**. | changes to `openapi.json`, `apps/api/**`, the dry run, the workflow |

The OpenAPI freshness check is the parity test plus the `API_SCHEMAS.md` check (ADR-010). `openapi.json` is hand-authored, so there is nothing to regenerate.

## 3. Required checks for merging into `main`

Set in GitHub → Settings → Branches → `main` → "Require status checks". This is a repository-admin action and is **not yet done**.

`Python lint + tests (repo root)`, `Migrations, seed and ingest on PostgreSQL + pgvector`, `Web lint, typecheck and build`, `Secret scan (gitleaks, full history)`, `flame-openapi`.

`flame-openapi` needs the `AURA_REPO_TOKEN` secret (read access to AURA-AI).

## 4. Deployments
- **Railway (connected demos).** `.railway/railway.py` (L-8 §6). Applied manually with `railway config apply`; there is no deploy workflow, by choice, until the Week 8 release gate.
- **L40S / offline.** Compose on the host (H-6). Manual.

## 5. Adding a test
- API behaviour goes in `apps/api/tests/`. Use the `client` / `session_factory` fixtures (SQLite), and validate response shapes with `api_contract.assert_contract_component`.
- Router and provider behaviour goes in `tests/unit/test_model_router.py` style: fake providers, no network.
- Anything that needs PostgreSQL goes in the `migrations` job, or in a test that skips without `FLAME_DATABASE_URL`.
- Never add a test that needs internet. The offline tests patch `socket.create_connection` to catch that.

## Known limitations
- Branch protection is not configured (§3).
- Ruff runs a narrow rule set, to be widened per directory by each owner.
- The web app has no tests yet (M7, Belal).

## Changelog
- 1.0.0 (2026-10-12): first CI (previously only the AURA dry run existed).
