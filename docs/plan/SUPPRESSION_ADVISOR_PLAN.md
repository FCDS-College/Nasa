# Suppression Advisor: implementation plan (feature 5)

| Owner | Status | Created | Depends on |
|---|---|---|---|
| Lead (Anas) | Implemented on `main` 2026-11-14: commit 15687d4 (feat: Suppression Advisor, contract 0.8.0) and AURA pin 22b40a0 (every suppression-advice parameter reaches AURA). D1–D4 decided; MIST gate failed, water-mist probability withheld (ADR-014). Open: Figma screen not made (Starter-plan limit); solid-material models are a later extension | 2026-11-13 | FLEX outcome model 1.0.0 (`ai/fire_safety/`), `GET /api/insights/flex-outcome` |

## 1. Goal

Given the crew's cabin environment (free volume, pressure, O₂, current CO₂, fuel), recommend **which extinguisher, CO₂ or water mist, is most likely to put the fire out without creating a worse hazard**, and say why, how sure we are, and what evidence it rests on.

It is decision support. It never overrides flight rules or emergency procedures, and the response says so.

## 2. What we actually have (audit, 2026-11-13)

| Need | Available in the repo | Gap |
|---|---|---|
| CO₂ effect on flame outcome | **FLEX (PSI-69)**: 261 labelled ISS droplet tests; CO₂ diluent 0–0.70 mole fraction, non-zero in 123 tests. The deployed model already takes `co2` as a feature. | FLEX CO₂ was in the atmosphere **before ignition**, not discharged onto a burning flame. |
| Water-mist effect | **Nothing.** No PSI investigation, table or ingested NTRS document covers water mist. FLEX-2 (PSI-68) is a 9-line design summary (O₂/N₂, O₂/He); BASS/BASS-II suppression means lowering flow or O₂, not an extinguisher. | A whole branch of the comparison has no data. |
| Cabin and extinguisher parameters | None (cabin volumes, PFE charge masses, discharge rates) | Need sourced constants (NTRS / ISS PFE documentation). |
| Crew-hazard limits | None in code | Need sourced ppCO₂ / O₂ / pressure limits (NASA-STD-3001, SMACs). |
| Model domain | FLEX ranges: O₂ 0.12–0.34, pressure 0.69–3.05 atm, CO₂ ≤ 0.70, droplet 1.1–4.67 mm, heptane/methanol only | Exploration atmospheres (e.g. 56.5 kPa / 34 % O₂) are **below the flown pressure range** and will come back out-of-domain. |

**Consequence.** We can make an honest, data-backed estimate for CO₂. We cannot do that for water mist from flight data. The plan below makes the CO₂ branch empirical, and the water-mist branch a calibrated physics computation that is labelled as such.

## 3. Approach

### 3.1 Turn an extinguisher discharge into an atmosphere

For each agent, compute the well-mixed cabin state after discharge (ideal gas, ventilation off):

- `n_cabin = P·V / (R·T)`; agent moles from charge mass (CO₂: 44.01 g/mol; water mist: water + N₂ propellant).
- New mole fractions of O₂, CO₂, N₂, H₂O (water mist only, as vapour that actually evaporates), and the new total pressure.
- Two placements: **well-mixed** (whole cabin, the conservative floor) and **local** (a fire-zone volume the crew aims at, user-set fraction of cabin, default from sourced PFE guidance). Both are shown; the recommendation uses well-mixed unless the user selects local.

New module: `ai/fire_safety/suppression/discharge.py`. Pure functions, unit-tested for mass and mole conservation.

### 3.2 CO₂ branch (empirical, claim class `estimated`)

Feed the post-discharge atmosphere straight into the existing FLEX outcome model (`co2`, `o2`, `pressure_atm`, `ppo2_atm` change; fuel and droplet size stay). Output `P(Extinction)`, applicability and the nearest real flight tests, exactly as `flex-outcome` does today. No retraining.

### 3.3 Thermal (critical flame temperature) model, for both agents (claim class `computed`)

A standard engineering suppression model: a flame goes out when the agent's heat sink pulls the adiabatic flame temperature below a critical value `T_crit`.

- Heat sink per mole of mixture: CO₂ by its heat capacity; water by sensible heat to 373 K + latent heat + vapour heat capacity up to flame temperature, multiplied by an **evaporation efficiency η** (fraction of the mist that evaporates in the flame zone).
- **Calibrate `T_crit` on FLEX** (fuel-specific, microgravity) by fitting the extinction boundary on CO₂- and He-diluted tests, with the same grouped-by-test-day CV as the outcome model. This is the step that ties the computed water-mist branch to real ISS data: the model's CO₂ predictions are scored against flight outcomes before it is ever used for water.
- Sanity check against published normal-gravity cup-burner CO₂ extinguishing concentrations for heptane (cited, not tuned on).
- **Water mist** uses the calibrated `T_crit` with η swept over a sourced range, so the answer is a **band**, not a point. η is the **effective delivery fraction** (share of the discharged water that reaches the fire zone as fine mist), per the D1 outcome.
- **MIST validation (no tuning):** run the model on the STS-107 MIST lean propane–air cases and report how far it under-predicts the measured extinction loadings (ω_w 3.3 % at 20 µm, 4.8 % at 30 µm). The response states that the water branch is conservative once the mist reaches the flame and is not validated for cabin-scale delivery.

New module: `ai/fire_safety/suppression/thermal.py`; trainer `ai/fire_safety/suppression/calibrate.py` writing `artifacts/suppression_thermal.json` + evaluation JSON (same `--check` pattern as `train_flex_outcome.py`).

### 3.4 Crew-hazard checks (rule-based, claim class `reference`)

Computed from the post-discharge atmosphere and sourced limits, never from a model:

- ppCO₂ after a CO₂ discharge against emergency exposure limits (time-weighted, with a crew-time input).
- O₂ partial pressure drop (hypoxia) and total pressure rise.
- Water mist: free-floating water in microgravity, electronics exposure, visibility. These are qualitative flags with an NTRS citation, not numbers.

New module: `ai/fire_safety/suppression/hazards.py`; limits in `ai/fire_safety/suppression/constants.py`, each with source, document id and page.

### 3.5 Recommendation logic (deterministic, auditable)

`ai/fire_safety/suppression/advisor.py`. No LLM in the decision.

1. Per agent: suppression likelihood (CO₂: FLEX probability and thermal-model cross-check; water mist: thermal band if the D2 gates pass, otherwise the crossover delivery fraction η* only) + hazard flags + applicability. With η* only, the comparison is "water mist removes more heat if ≥ η* reaches the fire", and the ranking step returns "no clear winner" unless a hazard veto decides it.
2. Discard an agent whose hazard check is **red** (e.g. ppCO₂ above the emergency limit for the crew time given).
3. Rank the rest by suppression likelihood, using the lower bound of any band.
4. If the two agents' intervals overlap, return **"no clear winner"** and list what decides it (cabin size, aim, crew time).
5. If both agents are out of domain, return **no recommendation**, the reasons, and "follow the flight rule".
6. The `fire_type` input (D4) gates which of the above outputs exist at all: probabilities only for heptane / methanol, η* also for other liquids, sourced rules only for battery / electrical, evidence links only for solids.

Output per call: `recommended_agent` (or `null`), `confidence` (`high` / `moderate` / `low` / `none`, from interval separation and domain), per-agent breakdown with claim class per number, `why` (2–4 plain sentences), `what_would_change_it`, similar FLEX tests and literature evidence ids, and the scope/disclaimer string.

## 4. Deliverables by layer

| # | Layer | Work | Files | Owner |
|---|---|---|---|---|
| 1 | Data | Source constants: ISS CO₂ PFE and water PFE charge mass and discharge time; module free volumes; ppCO₂/O₂ limits; water-mist η range; cup-burner reference values. Add the NTRS documents to the corpus and source registry with provenance and checksums. | `knowledge/ingestion/fetch_ntrs.py` (new ids), `datasets/registry/source_registry.csv`, `docs/data/SUPPRESSION_SOURCES.md` | Anas (E2) |
| 2 | Physics | Discharge, thermal, hazards, advisor modules + calibration script and artefacts | `ai/fire_safety/suppression/*` | Anas |
| 3 | Tests | Conservation, monotonicity (more agent never lowers P(ext)), domain refusal, red-hazard veto, overlap → no winner, D2 gate read from artefact, fire-type output matrix (D4: no unsupported number for any type), artefact-current check | `apps/api/tests/test_suppression_advice.py`, `tests/fire_safety/` | Anas, reviewed by Ziad |
| 4 | API (contract first, ADR-010) | `GET /api/insights/suppression-advice`; update OpenAPI, `API_SCHEMAS.md`, `CHANGELOG.md`; add path to the web proxy allow-list | `apps/api/flame_api/investigations.py` (or a new `suppression.py` router), `docs/api/*`, `apps/web/app/api/[...path]/route.ts` | Anas |
| 5 | Web | `/suppression` page per D3: banner, cabin inputs, side-by-side agent cards, delivery slider with η*, why / what would change it, evidence, out-of-domain state; sidebar entry; dashboard card; Explorer ↔ advisor links | `apps/web/lib/api/fireSafety.ts`, new `apps/web/app/suppression/page.tsx`, `components/layout/Sidebar.tsx`, `app/page.tsx`, `app/explorer/page.tsx`, `components/fire/FireUi.tsx`, mock data | Belal (E4) |
| 6 | Chat | Let the assistant call the advisor and quote its result with claim classes (no free-text recommendations) | `apps/api/flame_api/generation.py`, `ai/routing` | Eman (E1) |
| 7 | Evaluation | Model card `docs/evaluation/reports/suppression-advisor.md`: thermal model CV on FLEX, cup-burner check, η sensitivity, scenario table (small vs large module, Earth-normal vs exploration atmosphere) | `docs/evaluation/reports/` | Ziad (E5) |
| 8 | Docs | ADR-014 (scope: water mist is computed, not flight-validated; ADR-013 was already taken); README / FINAL_ARCHITECTURE / DEMO_RUNBOOK sections | `docs/architecture/adr/`, root docs | Anas |

## 5. Order of work

1. **Sources first (D1).** Nothing numeric is coded until each constant has a citation in `SUPPRESSION_SOURCES.md`.
2. Discharge model + tests.
3. CO₂ branch through the FLEX model (fast win, demo-able on its own).
4. Thermal model + FLEX calibration + MIST check + evaluation JSON, including the crossover delivery fraction η*. **Gates (D2):** FLEX extinction ROC-AUC lower bound ≥ 0.75 *and* conservative on MIST. Otherwise the water branch ships relative-comparison only. The gate results are written into the evaluation JSON and read by the API, so the decision is not hand-set.
5. Hazards + advisor logic + tests.
6. API contract, endpoint, proxy allow-list.
7. Web view (can start against mock data once step 6's contract is fixed).
8. Chat integration, model card, ADR, docs.

## 6. Acceptance criteria

- Same inputs always give the same recommendation (deterministic, no LLM in the path).
- Every number in the response carries a claim class and every constant a citation.
- Out-of-domain or both-agents-uncertain cases return no recommendation, with reasons; never a confident guess.
- A CO₂ discharge that pushes ppCO₂ over the emergency limit is never recommended.
- Calibration artefacts reproduce with `--check`; full API and physics test suites pass.
- Model card reviewed by Ziad (E5).

## 7. Risks

| Risk | Mitigation |
|---|---|
| Water-mist numbers are extrapolated, not measured | Band output, `computed` claim class, explicit "not flight-validated" scope line, ADR-014 |
| FLEX CO₂ was pre-ignition diluent, not a discharge on a growing fire | Stated in scope; the advisor answers "would this atmosphere sustain a flame", and the local/well-mixed split shows aim sensitivity |
| Droplet flames are not cabin fires (solids, wiring) | D4 fire-type input: numbers only for FLEX fuels, a fuel-independent comparison for other liquids, sourced rules for batteries, evidence links for solids; solid-material models are a later extension via BASS/SAFFIRE |
| Exploration atmospheres fall below FLEX's pressure range | Thermal model may extend there; FLEX branch refuses. Shown explicitly, not hidden |
| Overstating authority in a safety domain | Disclaimer in every response; "follow the flight rule" when unsure |

## 8. Decisions needed

- **D1. Water-mist evidence. DECIDED 2026-11-13: (c) time-boxed, fall back to (a).** Spend half a day searching NTRS and the literature for microgravity water-mist data, aimed at bounding the evaporation efficiency η (back-of-envelope: per kg, fully evaporated water removes ~3× the heat of CO₂, so the choice flips near η ≈ 0.3). If usable data is found, it bounds η and validates the water-mist branch. If not, ship (a): thermal model calibrated on FLEX, η range from ground-test literature, banded output labelled `computed`, and the response names η (aim, distance) as the deciding factor. The D2 gate still applies. Findings go in `docs/data/SUPPRESSION_SOURCES.md`.
  - **Search outcome (2026-11-13): fall back to (a).** No tabulated microgravity water-mist dataset was found. Found and recorded: MIST (STS-107) extinction thresholds for lean propane–air flames (ω_w 3.3 % at 20 µm, 4.8 % at 30 µm), now a validation anchor; ISS FWM PFE charge (6 lb water + 1.2 lb N₂) and ground-test results. A rough check suggests the heat-sink model *under-predicts* uniform fine-mist suppression, so η is redefined as **effective delivery fraction** (share of the discharge reaching the fire as fine mist) and the model is reported as conservative for water. Details in `docs/data/SUPPRESSION_SOURCES.md` §3.
  - Options considered: (a) calibrated thermal model + literature, banded; (b) qualitative only; (c) find a measured water-mist dataset first.
- **D2. Water-mist output and gate. DECIDED 2026-11-14: (c) split the two questions.**
  - **Always shown, relative comparison** (thermodynamics, no fitted parameter): the **crossover delivery fraction** η*, the share of the water-mist discharge that must reach the fire for it to remove more heat than the CO₂ discharge in this cabin. "Water mist out-performs CO₂ here if at least η* of it reaches the fire."
  - **Absolute water-mist P(extinction), shown only if both gates pass:**
    1. *Signal on flight data:* thermal model on FLEX, 5× repeated grouped-by-test-day CV, extinction ROC-AUC **lower bound (mean − 1 SD) ≥ 0.75**. Compared with chance (0.5), not with the logistic model's 0.857.
    2. *Conservative for water:* on the MIST lean-flame cases (ω_w 3.3 % at 20 µm, 4.8 % at 30 µm) it must predict **less** suppression than measured. Over-prediction blocks the water number regardless of gate 1.
  - **If a gate fails:** the water branch shows the relative comparison plus the MIST and FWM PFE evidence, never an absolute probability.
  - Optional when both gates pass: express the water discharge as a CO₂-equivalent heat sink and run it through the FLEX model for a probability on the same scale as CO₂ (claim class `computed`).
  - Options considered: (a) qualitative only if the thermal model under-performed the logistic model; (b) ship the number with a warning; (c) as above.
- **D3. UI placement. DECIDED 2026-11-14: (a) new `/suppression` page.** The advisor answers a crew decision, not the Explorer's science question, and its inputs and outputs barely overlap with the Explorer's.
  - **Navigation:** sidebar entry "Suppression Advisor" directly after "Flame Outcome Explorer"; a dashboard card showing the recommendation for a default ISS cabin, linking to the page.
  - **Cross-links (URL parameters):** Explorer "Which extinguisher?" carries the current atmosphere to the advisor; each extinguisher card links to "see this post-discharge atmosphere in the Explorer".
  - **Layout, top to bottom:** recommendation banner (agent or "no clear winner" / "follow the flight rule", confidence, one-line reason) → compact cabin inputs (volume, extinguisher(s), well-mixed/local, crew exposure time, current atmosphere) → two agent cards side by side (P(extinction) or band or crossover only, post-discharge atmosphere, hazard flags) → **delivery slider** "how much of the mist reaches the fire?" with η* marked (left: CO₂ removes more heat; right: water mist) → why / what would change it → evidence and scope, with a permanent disclaimer footer.
  - **Design:** no Figma screen exists and Figma is blocked by the Starter-plan limit; build from existing `Card` / `FireUi` components and add the screen to Figma later.
  - Options considered: (a) new page; (b) panel on the Explorer.
- **D4. Fuel scope. DECIDED 2026-11-14: (c) a "fire type" input; each type shows only what the evidence supports.** Nothing is trained beyond FLEX.

  | Fire type | Shown |
  |---|---|
  | Heptane / methanol (liquid) | Everything: FLEX P(extinction) for CO₂, water-mist band if the D2 gates pass, η*, hazard checks |
  | Other liquid / unknown fuel | η* + hazard checks, labelled "fuel-independent approximation" (heat release per kg O₂ ≈ 13 MJ for hydrocarbons and alcohols, so the heat-sink comparison barely depends on fuel); no probabilities |
  | Electrical / battery | Sourced rule (FWM PFE paper, NTRS 20130011664: commercial CO₂ PFEs noted ineffective on stored-energy battery fires; FWM PFE extinguished 15/16 battery tests) + hazard checks; no numbers |
  | Solid materials | Hazard checks + links to BASS / SAFFIRE evidence; "model support planned" |

  - Tests assert that no fire type ever returns a number it is not supported for.
  - Options considered: (a) FLEX fuels only; (b) generic hydrocarbon through the thermal model (rejected: absolute numbers for fuels `T_crit` was never fitted on); (c) as above.

## Changelog

- 2026-11-14: Implemented on `main`: commit 15687d4 (feat: Suppression Advisor, contract 0.8.0) and AURA pin 22b40a0. Open: the Figma screen is not made (Starter-plan limit); solid-material models remain a later extension (BASS / SAFFIRE).
