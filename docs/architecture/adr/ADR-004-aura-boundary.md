# ADR-004: AURA is an optional provider, never a core dependency

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Lead; Eman (E1) and Belal (E4) affected

## Context
AURA is the team's self-hosted AI platform (`anasibrahimgnedy-collab/AURA-AI`). Two links connect it to Flame:
- **Link 1** (Flame → AURA): Flame calls `POST /api/v3/chat` with a narrow `svc-flame` service key.
- **Link 2** (AURA → Flame): AURA compiles read-only tools from Flame's `openapi.json` (Track AP).

In the MVP, Flame's chat *required* Link 1. M6 also wants `/api/chat` in the public contract. Link 2 would then turn it into a tool that lets AURA call Flame, which calls AURA again: a loop that also hides which system answered.

## Decision
1. **Optional provider.** AURA is one external provider behind the router (`ai/providers/cloud/aura.py`). It is blocked in `offline_only` and is never the only path to a capability Flame needs.
2. **Same safety envelope.** Flame keeps it whichever provider answers:
   - retrieval is Flame's own;
   - evidence travels as DATA-channel `context`;
   - tools, knowledge and memory are off on the AURA side;
   - the reply is checked against Flame's own `response_schema` and validation (`flame_api/generation.py`);
   - citations outside the retrieved set are dropped.
3. **Kept out of Link 2.** `/api/chat`, `GET /api/ai/providers` and `PUT /api/admin/ai/mode` are in the contract but marked `x-aura-exclude: true`. AURA's OpenAPI discovery skips marked operations and reports each one as an `operation_excluded` issue (AURA PR #166). `tests/integration/aura_blueprint_dryrun.py` fails if a marked operation is ever compiled into a tool, or if the pinned AURA revision does not honor the flag.

## Alternatives considered
- **Keep `/api/chat` out of `openapi.json`** (the MVP choice). The contract would no longer describe the API (M6), and route-parity testing would be impossible. Rejected.
- **A separate "AURA-facing" contract file.** That is two contracts to keep in sync. Rejected.
- **Rely on AURA's read-only connector mode.** Discovery still records POST operations as write actions, and the twin and planner see them. An explicit exclusion is clearer and is audited in the discovery report.

## Consequences
- Flame works with AURA down, unreachable or removed. Chat and interpretation then use a local model, or degrade to evidence-only.
- The integration contract now depends on an AURA revision that includes PR #166. The `aura-link2-contract` workflow pins it and must be re-pinned to the merge commit.
- `docs/integration/AURA_INTEGRATION_STATUS.md` (L-12) marks the MVP statements that said AURA was required as superseded.

## Links
AURA PR #166; `docs/integration/AURA_INTEGRATION_STATUS.md`; AURA ADR-029 (service principals and caller context).
