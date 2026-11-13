# ADR-014: Suppression Advisor scope: what each fire type and each extinguisher may claim

- **Status:** Proposed (2026-11-14). Decision owner: Lead (Anas). Needs sign-off from Ziad (E5, evaluation and gates) and Belal (E4, the `/suppression` page).
- **Date:** 2026-11-14
- **Plan:** `docs/plan/SUPPRESSION_ADVISOR_PLAN.md` (decisions D1–D4, 2026-11-13/14)
- **Implemented in:**
  - `ai/fire_safety/suppression/` (`constants`, `discharge`, `thermal`, `calibrate`, `hazards`, `advisor`) and `ai/fire_safety/artifacts/suppression_thermal_*.json`;
  - `apps/api/flame_api/suppression.py` (`GET /api/insights/suppression-advice`), contract 0.8.0;
  - `apps/web/app/suppression/page.tsx`, with links from the sidebar, the dashboard and the Explorer.

## Context

Feature 5 asks the system to tell a crew which extinguisher, CO₂ or water mist, will work best in their cabin. The evidence for the two agents is very unequal:

- **CO₂:** the FLEX flight tests (PSI-69) include CO₂ diluent in 123 of 261 usable tests, so the existing FLEX outcome model can score a post-discharge atmosphere directly.
- **Water mist:** no tabulated microgravity dataset exists. The time-boxed search (D1) found:
  - the MIST flight experiment on STS-107 (extinction thresholds for lean propane–air flames, in text form);
  - ground tests of the ISS Fine Water Mist PFE (pass/fail).
- **Fire types:** most realistic cabin fires (solids, wiring, batteries) are outside FLEX's two liquid fuels.

A confident single answer would overstate what the data supports. In a safety domain, that is the failure to avoid.

## Decision

1. **The decision is deterministic and auditable.**
   - No language model is involved.
   - Every number carries a claim class: `estimated` (FLEX), `computed` (physics), `reference` (sourced limit or rule).
   - Every constant cites its source (`docs/data/SUPPRESSION_SOURCES.md`).
2. **Both agents are put on one scale** by the effective enthalpy per mole of O₂, the energy to heat everything accompanying a mole of O₂ from 298 K to 1600 K.
   - This is the Sheinson/Huggett criterion, which NASA used for CO₂, N₂ and He in microgravity (NTRS 20040161262).
   - A logistic model on (effective enthalpy, ln p, fuel) is fitted on FLEX, with the same grouped-by-test-day protocol as the outcome model.
3. **The crossover delivery fraction η\* is always shown for liquid fires.** It is the share of the water that must reach the fire for water mist to remove more heat than CO₂. It is thermodynamics only, with no fitted parameter.
4. **The absolute water-mist probability needs two gates (D2)**, read from the evaluation file and never hand-set:
   - FLEX extinction ROC-AUC lower bound (mean − 1 SD) ≥ 0.75;
   - conservative on MIST: the model's 50 % water loading must be at least the highest measured extinguishing loading.
5. **Crew hazards can veto an agent.** A CO₂ discharge that, well mixed, brings cabin ppCO₂ to the CO₂ IDLH (40,000 ppm, applied as a partial pressure) is never recommended.
6. **The fire type limits what may be shown (D4):**

   | Fire type | Shown |
   |---|---|
   | Heptane, methanol | Probabilities + η* + hazards |
   | Other liquid | η* + hazards |
   | Electrical / battery | Sourced rule + hazards |
   | Solid | Hazards + evidence |

7. **"No clear winner" and "no recommendation" are first-class answers**, always paired with "follow the flight rule".

## Result at decision time (calibration 2026-11-14)

- **FLEX gate passed:** repeated grouped-CV ROC-AUC 0.814 ± 0.005, lower bound 0.809.
- **MIST gate failed:**
  - The model reaches P = 0.5 at 2.0 % water, but MIST needed 3.3 % (20 µm) and 4.8 % (30 µm). It **over-predicts** water mist.
  - The likely reason is that FLEX droplet flames are weak: the heptane 50 % point is 52 kcal/mol O₂, against 48 for plain air. A threshold calibrated on them is too low for MIST's premixed flames.
  - So the water-mist probability is withheld. The advisor shows η* and hazards, and names a winner only through a hazard veto or a sourced rule.

## Consequences

- **What the crew gets:** a decision they can act on for the cases with real evidence: CO₂ ruled out in a small cabin, and battery fires.
- **Most liquid-fire cases are "no clear winner"** with η\* (about 23 % for one PFE of each). That states the deciding factor, delivery, rather than hiding it.
- **The CO₂ thermal probability is shown, but the same limitation applies.** FLEX flames are weak, so it is likely optimistic for stronger fires. The FLEX flight-data estimate and its nearest tests sit beside it.
- **The page answers no question the data cannot support:**
  - exploration atmospheres below FLEX's 70 kPa get no probability;
  - solids get no model.
- **Reopening:** the water-mist gate can be re-evaluated if a better water-mist dataset or a stronger-flame calibration set (e.g. ACME, BASS) is added. The gate result updates automatically from `python -m ai.fire_safety.suppression.calibrate`.

## Alternatives considered

- **Literature-only, qualitative water mist (D1 b):** honest, but it turns the advisor into a CO₂ safety check.
- **Ship the water-mist number with a warning (D2 b):** rejected; an over-prediction in the dangerous direction should not be shown.
- **Generic hydrocarbon through the thermal model (D4 b):** rejected; it would give absolute numbers for fuels the threshold was never fitted on.
