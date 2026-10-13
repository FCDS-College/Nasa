# ADR-010: Contract-first OpenAPI with a route-parity test

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Lead; Belal (E4) affected

## Context
L-4 asks for "`openapi.json` generated from the code, plus a CI check that it is current". Today `docs/api/openapi.json` is hand-authored, and FastAPI serves it as-is (`app.openapi = _contract_openapi`). Two things depend on its hand-written parts:
- the scientific rules encoded in its schemas, and its examples;
- AURA's Link 2 dry run, which validates every compiled tool against the contract's 200 examples.

FastAPI's generated schema would drop the examples, the `x-aura-exclude` and `x-implementation-status` extensions, and the precise nullable/enum rules, unless every route grew a full Pydantic response model.

## Decision
Keep the contract hand-authored, contract-first. Prove it matches the code in CI instead of generating it:
- `apps/api/tests/test_contract_parity.py`:
  - every FastAPI route (method + path) is in the contract and vice versa;
  - every GET has a 200 example;
  - chat, AI status and admin writes are excluded from AURA.
- Response-shape tests validate real responses against contract components (`api_contract.assert_contract_component`).
- `python docs/tools/render_api_schemas.py --check` keeps `API_SCHEMAS.md` in sync (CI `python` job).
- `tests/integration/aura_blueprint_dryrun.py` validates the AURA view (CI `aura-link2-contract`).

## Alternatives considered
- **Generate from FastAPI.** Response models for 15 operations and their examples would need moving into code. Weeks of work that changes no behaviour. It would also lose the extensions unless they were re-added through `openapi_extra`. Deferred, not rejected: if response models are added for other reasons, revisit.

## Consequences
- This deviates from the literal L-4 wording. The parity test is the stand-in, and this ADR is the record of it.
- Every API change touches three files: the route, `openapi.json` and `CHANGELOG.md`. The PR template asks for all three.

## Links
`docs/api/CHANGELOG.md`; `.github/workflows/ci.yml`.
