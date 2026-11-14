# ADR-013: Historical scenarios, a gravity dimension and a scenario-level coverage verdict

- **Status:** Proposed (2026-11-13). Decision owner: Lead (Anas). Needs sign-off from Ziad (E5, ranking and evaluation methodology) and Anas (E2, data semantics).
- **Date:** 2026-11-13
- **Implemented in:**
  - `ai/fire_safety/scenarios.py` (`gravity`, `kind`, `load_historical`, `HISTORIES`) and `ai/fire_safety/historical/*.json`;
  - `ai/fire_safety/investigations.py` (`coverage`);
  - `apps/api/flame_api/investigations.py` (`coverage` in `GET /api/investigations`, the gravity refusal in the scenario model estimate, the extended O₂ sweep, `GET /api/scenarios/{scenario_id}/history`);
  - contract 0.7.0.

## Context

The dashboard ranks investigations by evidence relevance (ADR-011), and the FLEX model refuses conditions outside its flight envelope. Three gaps showed up when we tried the Apollo 1 atmosphere: 100 % O₂ at 16.7 psia, on the launch pad, at 1 g.

1. **The ranking never says "nothing covers this".**
   - FLEX scores about 0.40 for Apollo 1. Its pressure range contains 115 kPa, and its table records outcomes.
   - So the ranking looks like coverage even though no test was flown above 34 % O₂.
   - ADR-011 deliberately keeps relevance a relative score, so it should not be bent to encode an absolute verdict.
2. **Gravity was not a dimension.**
   - All 840 flight tests are microgravity.
   - A 1 g, lunar or Martian atmosphere could look "covered" whenever its O₂ and pressure matched.
   - The model has no gravity input, so it would happily estimate air at 1 g.
3. **Historical atmospheres need a story, and the story needs sources.**
   - The point of an Apollo 1 preset is the lesson: a decision made in an atmosphere nobody had tested.
   - That only works if every sentence is cited to a NASA page.
   - Hard-coding it would make each future incident (Apollo 13, Mir 1997, …) a code change.

## Decision

1. **Scenario-level coverage verdict.** `coverage(by_source, scenario, flight_gravity)` returns `none`, `partial` or `covered`, with:
   - a headline;
   - the reasons;
   - the nearest real flight test, with its evidence cells;
   - the gap (O₂ difference and ratio, pressure ratio);
   - the flown ranges;
   - the method text.

   The rules:
   - `none`: the scenario's gravity was never flown, or no test lies within ±0.03 O₂ (and ±25 % pressure when recorded). These are the neighbourhood bounds ADR-011 already uses.
   - `partial`: 1–4 such tests, or the atmosphere lies outside the flown O₂ or pressure range.
   - `covered`: otherwise.

   The nearest test minimises `sqrt((ΔO₂/0.05)² + (ln(P/Pₜ)/0.25)²)`, the scales of the relevance score. The relevance formula is unchanged. The dashboard shows the verdict before the ranking.
2. **Gravity is a scenario field**, one of `microgravity | lunar | martian | earth`.
   - Mission scenarios are microgravity, as before. Custom atmospheres take an optional `gravity` query parameter.
   - Any regime not present among the flight tests makes the verdict `none` and turns the scenario's model estimate into a refusal, with the reason "every FLEX test was flown in microgravity; this atmosphere is at …".
3. **Historical scenarios are data.**
   - Each is one JSON file in `ai/fire_safety/historical/`, validated against `historical_scenario.schema.json` in CI and structurally checked at load.
   - A file holds the atmosphere, gravity, story, lesson, a dated timeline and an alternative scenario to show next.
   - Every statement carries `FF-NTRS-*` source IDs and pages. CI checks that each page exists in a committed, registered report, and that each quote appears verbatim on its page.
   - `GET /api/scenarios/{scenario_id}/history` serves the file with titles, NTRS links and, when the report is ingested, the page's evidence ID.
4. **The alternative must be covered by data, not called safe.** Apollo 1's alternative is `orion_max_o2` (30 % O₂ on the normoxic curve), which is inside the FLEX envelope. Apollo's own post-fire atmospheres are outside it:
   - 100 % O₂ at about 6 psia in orbit;
   - limited O₂ on the pad;
   - Skylab's 65–70 % O₂.

   The text says "covered by flight data does not mean safe".
5. **The O₂ sweep reaches a requested O₂ outside the trained range.**
   - Six extra out-of-domain points (no probabilities) extend it, so the chart can show the distance as a red zone.
   - Inside the range the 12 points are unchanged.

## Alternatives considered

- **Encode coverage in the relevance score**, for example by multiplying by an O₂ gate. Rejected:
  - it changes a signed-off formula (ADR-011);
  - it mixes "how relevant" with "is there any data";
  - it would still not explain the gap.
- **Make gravity a model feature.** Impossible: every training row is microgravity, so the feature would be constant. Refusing outside the flown regime is the honest equivalent.
- **Hard-code Apollo 1 in Python**, or put it in `datasets/`. Rejected:
  - a data file makes future incidents content-only changes;
  - `ai/fire_safety/` is already shipped in the API image, while `datasets/` is excluded by `.dockerignore`.
- **Suggest Apollo's post-fire atmosphere as the safe alternative.** Rejected: it is outside our flight data, so the system would be recommending something it cannot support.

## Consequences

- Contract 0.7.0 adds required response fields:
  - `Scenario.gravity` and `Scenario.kind`;
  - `InvestigationListResponse.coverage`;
  - a new `GET /api/scenarios/{scenario_id}/history`.

  Clients that validate strictly (AURA's compiled tools) need the 0.7.0 contract. The `aura-link2-contract` job checks this.
- **Corpus:** three NTRS reports were added for the citations (the Apollo 204 Review Board report, flame-retardant fibres, and Orion ECLSS fire protection), 27 in total. The Review Board report is 8.0 MB, so `fetch_ntrs.py` has a per-report size exception for it.
- **Lunar lander** now shows verdict `partial`: 9 neighbouring tests, but 62.7 kPa is below every flown pressure. This matches the model's refusal.
- **Future incidents** are added by writing one JSON file and registering any new report. Nothing else changes.

## Links

- [ADR-011](ADR-011-scenario-relevance-ranking.md), the relevance ranking this verdict sits beside.
- [docs/reports/APOLLO1_SCENARIO_ANALYSIS.md](../../reports/APOLLO1_SCENARIO_ANALYSIS.md), the event, sources and corrections.
- [docs/api/CHANGELOG.md](../../api/CHANGELOG.md), contract 0.7.0.

## Note (2026-11-14): current counts

The decision is unchanged. The figures in Context and Consequences were measured on 2026-11-13 with the 4 PSI tables. With the 19 PSI flight investigations now on `main` (ACME, CFI, BASS, SAFFIRE-II/III, SAME, SAME-R, SLICE, DAFT and FLEX-2 added):

- **Flight tests:** 1950 from 19 investigations, all microgravity (`apps/api/tests/test_fire_safety_api.py`: `totals == {"investigations": 19, "with_data": 19, "flight_tests": 1950}`). Context point 2 said 840.
- **Apollo 1:** still verdict `none`, now "None of the 1950 flight tests cover this atmosphere." The highest O₂ flown is 40 % (2.5×, not 34 % and 2.9×), and the nearest real test is ACME CFI-G 21162A1 (FF-PSI-159, 40 % O₂, 101 kPa), not FLEX 196F003 (`test_apollo1_gets_no_model_estimate_and_gravity_is_a_refusal_reason`; [APOLLO1_SCENARIO_ANALYSIS.md](../../reports/APOLLO1_SCENARIO_ANALYSIS.md) step B).
- **Lunar lander:** verdict `covered`, not `partial`. ACME CFI-G flames were flown down to about 43 kPa, so 20 tests lie in its neighbourhood (11 CFI-G, 9 FLEX) (`test_mission_scenarios_keep_their_verdicts`). The FLEX outcome model still refuses 62.7 kPa, because it is below the lowest FLEX test pressure; the verdict and the model now differ, and the verdict is the one about data coverage.

The original text above is kept as written, per the ADR index rule on dated notes.
