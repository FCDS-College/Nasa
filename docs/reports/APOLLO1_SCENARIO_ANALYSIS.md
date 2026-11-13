# Apollo 1 scenario: analysis, design and how it generalises

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | 1.0.0 | 2026-11-13 | ADR-013 | `ai/fire_safety/historical/`, `ai/fire_safety/investigations.py` (`coverage`), `apps/api/flame_api/investigations.py`, `apps/web/components/fire/Coverage.tsx` |

## 1. The event, from NASA's own record

On 27 January 1967, Apollo 204 (Apollo 1) was on the pad for a "plugs-out" ground test.

- **The atmosphere.** The cabin held **100 % oxygen at 16.7 psia (115.1 kPa)**, above sea-level pressure, at 1 g. In the Review Board's words: *"The test conditions were extremely hazardous."* (Apollo 204 Review Board report, FF-NTRS-19930078717 p. 189).
- **The fire.**
  - An electrical arc was the most probable initiator (p. 189).
  - The fire spread along Velcro and nylon netting faster than through the materials themselves (p. 111).
  - Pressure began rising about 6 seconds after the crew reported the fire, and the cabin ruptured at at least 29 psia (p. 147).
  - The inner hatch could not be opened against the internal pressure (p. 189).
  - Virgil I. Grissom, Edward H. White II and Roger B. Chaffee died.
- **Why.** In the words of a later NASA paper (FF-NTRS-20070021223 p. 2), the cabin materials *"were exposed to … 100 % oxygen environment in which they had never been tested."*
- **What changed** (FF-NTRS-20070021223 p. 2; FF-NTRS-20170008542 pp. 1–2; FF-NTRS-20000034017 p. 9):
  - Beta glass fabric for suits and the command-module liner;
  - oxygen limited on the pad;
  - a full command-module mock-up fire-tested with flight materials;
  - a rule that materials are tested at worst-case conditions;
  - over the following decade, Skylab's 65 % O₂ and then sea-level air on Shuttle and ISS.
- **Where the story goes next.** NASA's exploration vehicles plan to raise oxygen again: up to 30 % for Orion and 34 % for the lunar lander (FF-NTRS-20080034883 p. 5).

Every number above is in [the fact sheet](../../.internal/research/2026-11-13-apollo1-facts.md) with its page.

## 2. What the system does with it

The preset **"Apollo 1: pure-O₂ ground test (1967)"** goes through four steps.

| Step | What the user sees | Where it comes from |
|---|---|---|
| A. Atmosphere | The envelope map puts Apollo 1 at 100 % O₂ / 115 kPa, far outside the green box of what was flown. The heptane O₂ sweep runs on into a red zone up to 100 %. | `EnvelopeMap`, `SweepChart`, `o2_sweep` extended to the requested O₂ |
| B. Refusal | **"None of the 840 flight tests cover this atmosphere."** The reasons: O₂ is 2.9× the highest O₂ flown, and the test was at 1 g, while every test was microgravity. The nearest real test is FLEX 196F003 (34 % O₂, 72.4 kPa), with its NASA table cells. The model gives no estimate. | `coverage` verdict `none`; the scenario model estimate refused with O₂, ppO₂ and gravity reasons |
| C. What changed after | The lesson, quoted from the Review Board and the Orion paper, then an 8-event timeline. Every event links to its NTRS page (or the ingested evidence page). | `GET /api/scenarios/apollo1_pad_1967/history` |
| D. Where data does exist | NASA's exploration atmosphere, Orion at 30 % O₂ / 71 kPa, is inside the FLEX envelope. One click shows 8 neighbouring flight tests and a model estimate, with the warning that covered by data does not mean safe. | `alternative` → `orion_max_o2` |

## 3. Corrections to the original idea

The original pitch text had five errors that a NASA judge could catch:

- FLEX covers 12–34 % O₂, not 13–60 %.
- The pressure was 16.7 psia (1.136 atm), not 1.16 atm.
- Cabin pressure rose to at least 29 psia (about 1.7×), not "more than doubled".
- The 60/40 launch mix and the "3-second hatch" have no page in our corpus, so the system doesn't state them.
- The "low-pressure O₂" alternative is **outside** our envelope.

The [fact sheet](../../.internal/research/2026-11-13-apollo1-facts.md) lists each one with its source. The corrected story is stronger: even NASA's post-fire atmosphere is beyond the flight data, and the data-covered atmosphere is the one NASA is designing now.

## 4. The general problem, and how the system now handles it

Apollo 1 is one case of a general failure: **a decision made outside the evidence envelope, without anyone noticing it was outside.** The system now has a control for each way that happens.

| Way it happens | Control in the system |
|---|---|
| The variable is beyond every test (O₂ 100 % vs 34 %) | Per-feature ranges in the model's applicability check, plus the scenario verdict, which states the ratio to the highest value flown |
| The combination is unseen even though each variable is in range | The model's nearest-neighbour distance limit (95th percentile) |
| A regime nobody tested (1 g, lunar, Martian) | `gravity` on every scenario. A regime not among the flight tests means verdict `none` and no estimate |
| A relevance score that looks like coverage | The verdict comes before the ranking, and the ranking stays a relevance score (ADR-011) |
| A confident story with no source | Historical scenarios are data files. CI checks that every cited page exists and that every quote is verbatim |
| "Safe" claims | The alternative text must say "covered by data does not mean safe". Coverage is never a risk score |

### Adding the next incident

Each is one JSON file in `ai/fire_safety/historical/`, plus any new NTRS report through `knowledge/ingestion/fetch_ntrs.py`. Candidates, each to be added only once a public NTRS report supports every sentence:

- **Apollo 13 (1970):** an oxygen-tank fire. FF-NTRS-20000034017 p. 9 already mentions it.
- **Mir (1997):** an oxygen-generator fire.
- **Skylab-era 5 psia / 70 % O₂ atmospheres:** outside the envelope on both O₂ and pressure.
- **Lunar-surface habitat at 1/6 g:** no flight test exists, and the gravity check refuses it today.

## Known limitations
- Coverage counts only the four ingested investigations. SAME, ACME and FLEX-2 are not ingested.
- The 1967 Review Board report is an OCR scan. Quotes are checked letters-only, but OCR errors elsewhere on its pages can affect search.
- The `partial` threshold of 5 neighbouring tests is a design choice, like ADR-011's weights. It has not been validated with users.

## Changelog
- 1.0.0 (2026-11-13): first version, with the Apollo 1 scenario (contract 0.7.0, ADR-013).
