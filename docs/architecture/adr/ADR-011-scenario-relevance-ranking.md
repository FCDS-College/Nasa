# ADR-011: Rank investigations by evidence relevance to a cabin atmosphere

- **Status:** Proposed. Decision owner: Lead (Anas). Sign-off needed: Ziad (E5, ranking and evaluation methodology) and Anas (E2, data semantics).
- **Date:** 2026-11-07
- **Implemented in:** `ai/fire_safety/investigations.py` (`relevance`, `neighbours`, `rank`, `WEIGHTS`, `FORMULA`) and `ai/fire_safety/scenarios.py`, served by `GET /api/investigations` (contract 0.5.0, merged in PR #24).

## Context

The Space Apps challenge asks for a dashboard that **ranks** NASA microgravity combustion results to inform fire safety for Moon and Mars missions. "Rank" needs a definition, and the data constrains which definitions are honest:

- **No outcome is comparable across investigations.**
  - FLEX records a droplet end state (extinction, disruption or completion).
  - SAFFIRE-I records only burn duration.
  - BASS-II and SPICE record conditions but no outcome in their tables.
  - A ranking by flammability, hazard or "risk" would therefore compare unlike quantities, or invent missing ones.
- **The investigations record different variables.**
  - Only FLEX records pressure.
  - SPICE records no O₂ (it burned in an air co-flow).
  - SAFFIRE-I writes O₂ as text ("21.5–21.7", "~ 21.5").
- **The user's real question is about an atmosphere.** NASA/TM-2008-215260 p. 5 records that exploration vehicles move from ISS air (21 % O₂, 14.7 psia) to enriched, reduced-pressure cabins (up to 30 % for Orion and 34 % for Altair, on the normoxic curve). A mission designer needs to know which flight data covers *their* cabin atmosphere.
- **Every result must be explainable and traceable** (project rule: evidence-first). A judge or engineer must be able to see why one investigation ranks above another.

## Decision

Rank each investigation that has ingested flight-test data by an **evidence-relevance score** in [0, 1] for a chosen cabin atmosphere (scenario). The score is a fixed, documented weighted sum of four components, each computed from the investigation's published table:

```
relevance = 0.35·oxygen_match + 0.25·pressure_match + 0.25·evidence_density + 0.15·outcome_data
```

| Component | Definition | Unrecorded variable |
|---|---|---|
| `oxygen_match` | 1 if the scenario O₂ lies within the tested O₂ range, else `exp(−gap / 0.05)`, where `gap` is the distance in mole fraction to the nearest tested value | 0, and listed in `not_recorded` |
| `pressure_match` | 1 if the scenario pressure lies within the tested pressure range, else `exp(−\|ln(P / P_nearest)\| / 0.25)` | 0, and listed in `not_recorded` |
| `evidence_density` | `min(1, ln(1 + n) / ln(31))`, where `n` is the number of flight tests within ±0.03 O₂ (and ±25 % pressure when the investigation records pressure; a test without a valid pressure is then not counted) | — |
| `outcome_data` | 1 if each test records its end state, 0.5 if only a duration is recorded, 0 if no outcome is in the table | — |

Rules that go with the formula:

1. **It is relevance, never risk.** The UI and the API call it "evidence relevance (not a risk score)". It says how directly an investigation's flight data speaks to the atmosphere, not how dangerous the atmosphere is.
2. **Transparency.**
   - Every response returns the formula (`ranking_method`), the four component values, the weights, the neighbourhood count, the unrecorded variables and plain-language explanations (e.g. "scenario pressure 62.7 kPa is outside the tested range 70.2–309.3 kPa").
   - The dashboard shows the components as a stacked bar.
3. **Investigations without ingested data are listed but not ranked** (`rank: null`, status `metadata_only`): ACME-CLD and FLEX-2 today. Investigations named by the challenge but not acquired (SAME) are listed separately as `not_acquired`.
4. **Scenarios are sourced.**
   - The four presets quote, or derive arithmetically from, NASA/TM-2008-215260 p. 5.
   - Orion and Altair total pressures are derived on the normoxic curve: ppO₂ 3.09 psia divided by the O₂ fraction.
   - A custom O₂ and pressure is allowed, and is marked `basis: "user"`.
5. **Deterministic.** There is no model and no randomness in the ranking; ties break by test count, then by investigation ID.

### Why these weights and scales

| Choice | Reason |
|---|---|
| O₂ weighted highest (0.35) | Oxygen concentration is the variable exploration atmospheres change most and the primary flammability driver in the corpus (NASA-STD-6001 MOC work). In the FLEX outcome model it is also by far the most important input: permutation importance 0.217, against ≤ 0.055 for every other input (`docs/evaluation/reports/flex-outcome-model.md`). |
| Pressure and evidence density equal (0.25) | Reduced total pressure is the other half of the exploration-atmosphere change. Density rewards data at the scenario itself, not merely a range that spans it. |
| Outcome data lowest (0.15) | It measures how useful the data is, not whether it covers the atmosphere. It should break ties between covering investigations, not lift an uncovering one. |
| O₂ scale 0.05 mole fraction | One scale length is roughly the step between the ISS (0.21) and pre-EVA/Orion (0.30) atmospheres. |
| Log-pressure scale 0.25 | Pressure effects are multiplicative; a 25 % pressure difference costs one scale length, matching the ±25 % neighbourhood. |
| Density saturates at 30 tests | Beyond about 30 nearby tests, more tests at the same point add little; the log keeps 1 test meaningfully above 0. |

### Measured behaviour (merged `main` at `80c29ac`)

The values below come from `GET /api/investigations` in-process on the committed tables:

| Scenario (O₂, kPa) | FLEX | BASS-II | SAFFIRE-I | SPICE |
|---|---|---|---|---|
| ISS nominal (0.21, 101.3) | **1.00** (90 nearby tests) | 0.60 | 0.47 | 0.00 |
| Pre-EVA (0.30, 70.3) | **0.91** (8) | 0.07 | 0.14 | 0.00 |
| Orion max O₂ (0.30, 71.0) | **0.91** (8) | 0.07 | 0.14 | 0.00 |
| Lunar lander max O₂ (0.34, 62.7) | **0.83** (9; pressure outside FLEX's range) | 0.03 | 0.10 | 0.00 |

**Weight sensitivity.** Each weight was scaled by ×0.5 and ×1.5 and the weights renormalized; equal weights (0.25 each) were also tried. Across the three distinct scenarios that makes 27 cases, and **no case changes the ranking order**. The ordering is therefore driven by the data (what each table covers), not by the exact weights.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Rank by hazard or flammability ("riskiest atmosphere first") | No cross-investigation outcome measure exists (see Context); it would compare a droplet end state with a fabric burn time, or invent outcomes for BASS-II and SPICE. It would also invite reading the score as a safety rating, which this data cannot support. |
| Rank by test count | It ignores the atmosphere: SPICE (435 tests, no O₂ or pressure recorded) would rank first for every scenario. |
| A learned ranking (learning-to-rank, or an LLM judging relevance) | There are no relevance labels to train or validate against; the result would be neither reproducible nor explainable to a judge. |
| Distance in standardized condition space (nearest-neighbour only) | It is undefined for investigations missing a variable, and it hides *why* an investigation ranks where it does. The neighbourhood count survives as one component (`evidence_density`). |
| Impute unrecorded variables (e.g. assume BASS-II and SPICE flew at ISS cabin pressure) | Plausible, but not recorded in the published tables. The project rule is "unrecorded is not zero and not assumed": the score shows `pressure not recorded` instead. |
| No ranking, only a comparison table | It does not meet the challenge's "rank" requirement. The comparison matrix is kept alongside the ranking. |

## Consequences

- **Positive.**
  - Every rank is reproducible from the committed data and explainable component by component.
  - The ranking reacts to the atmosphere in the way a designer expects: BASS-II drops from 0.60 at ISS air to 0.03 at the lunar lander, because no solid-material test exceeded 22.2 % O₂.
  - It never presents absence of data as low risk.
- **Conservatism penalizes unrecorded variables.** An investigation whose table does not record pressure can reach at most 0.75. That is intended: the score measures what the published data demonstrates, not what is probably true.
- **SPICE always scores 0.** Its table records neither O₂ nor pressure, so it is always last. SPICE is relevant to other questions (soot, smoke point, detection), which this atmosphere-based ranking does not address. Its data remains visible in the comparison table and the Flight Test Browser.
- **Low scores are not meaningfully ordered.** Below roughly 0.2, the order mostly reflects `outcome_data`. Example: at pre-EVA, SAFFIRE-I (0.14) ranks above BASS-II (0.07) only because it records a burn duration. Both should be read as "does not cover this atmosphere"; the explanations say so.
- **Investigation granularity.** The score describes an investigation's table as a whole, not individual materials or fuels. Material-level relevance (e.g. "Nomex at 30 % O₂") would need per-material envelopes.
- **Weights are a reviewed design choice, not fitted.** They are not calibrated to expert judgement or outcomes. Calibration against expert rankings is future work, and changing the weights or scales requires a new ADR that supersedes this one.
- **Contract coupling.** `Relevance` in `docs/api/openapi.json` exposes the four component names. Adding, removing or renaming a component is a contract change (minor version bump while pre-1.0).

## Links

- Code: `ai/fire_safety/investigations.py`, `ai/fire_safety/scenarios.py`, `apps/api/flame_api/investigations.py`
- Contract: `docs/api/openapi.json` 0.5.0 (`InvestigationListResponse`, `Relevance`, `Scenario`), `docs/api/CHANGELOG.md`
- Tests: `apps/api/tests/test_fire_safety_api.py` (`test_investigations_are_ranked_for_the_lunar_lander_atmosphere`, `test_ranking_follows_the_atmosphere`, `test_a_test_without_valid_pressure_is_never_a_pressure_neighbour`)
- Evidence: NASA/TM-2008-215260 p. 5 (FF-NTRS-20080034883); `docs/evaluation/reports/flex-outcome-model.md` §5; `docs/data/COMBUSTION_DATASET_ANALYSIS.md` §3, §5
- Related: [ADR-010](ADR-010-contract-first-openapi.md) (contract-first API)
