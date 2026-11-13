# Apollo 1 scenario: fact sheet (2026-11-13)

Every claim the dashboard, the deck and the speaker scripts make about Apollo 1 and what followed, with its source and PDF page. Page numbers are PDF pages, as ingested and as `GET /api/scenarios/apollo1_pad_1967/history` cites them. A claim that is not here does not go into the UI or the pitch.

## Verified claims

| # | Claim | Source (PDF page) | Status |
|---|---|---|---|
| 1 | Ground test ("plugs-out") on 27 January 1967 | date: FF-NTRS-20170008542 p. 1; the test itself: FF-NTRS-19930078717 (Apollo 204 Review Board report) pp. 147, 189 | verified |
| 2 | Cabin atmosphere 100 % oxygen at **16.7 psia** (115.1 kPa) | FF-NTRS-19930078717 p. 189: "The test was conducted with a 16.7 pounds per square inch absolute, 100 percent oxygen atmosphere. DETERMINATION: The test conditions were extremely hazardous." | verified (OCR text) |
| 3 | The Orion ECLSS paper gives 16.2 psia for the same test | FF-NTRS-20070021223 p. 2 | verified. The Board's 16.7 is the primary figure. |
| 4 | Most probable initiator: an electrical arc; many combustibles next to possible ignition sources | FF-NTRS-19930078717 p. 189 (findings 1–2) | verified |
| 5 | Pressure began rising about 6 s after the crew reported the fire; the cabin ruptured at **at least 29 psia** | FF-NTRS-19930078717 p. 147 | verified |
| 6 | The inner hatch could not be opened before the rupture because of internal pressure | FF-NTRS-19930078717 p. 189 (finding 4) | verified |
| 7 | Velcro and nylon netting spread the fire faster than the materials themselves | FF-NTRS-19930078717 p. 111 (Webb statement, third interim report) | verified |
| 8 | Pure O₂ "presents severe fire hazards" unless combustibles are restricted. The Board recommended full-scale mock-up fire tests, diluent-gas studies and faster egress | FF-NTRS-19930078717 pp. 189–190 (findings 4, 8, 9) | verified |
| 9 | Crew: Grissom, White, Chaffee | FF-NTRS-20170008542 p. 1 | verified |
| 10 | Materials "were exposed to … 100 % oxygen environment in which they had never been tested" | FF-NTRS-20070021223 p. 2 | verified (quote checked by CI) |
| 11 | Two lessons: an ignition source will always exist; test flammability at worst-case conditions | FF-NTRS-20070021223 p. 2; FF-NTRS-20080034883 p. 5 | verified |
| 12 | After the fire: O₂ concentration limited on the pad, orbit still 100 % O₂ at about 6.2 psia; a full CM mock-up fire-tested | FF-NTRS-20070021223 p. 2 | verified |
| 13 | Beta glass fabric was used for Apollo suit outer layers and the command-module liner | FF-NTRS-20170008542 pp. 1–2 | verified |
| 14 | Mercury, Gemini and Apollo were designed for 100 % O₂; about 34.5 kPa in flight | FF-NTRS-20070021223 p. 2; FF-NTRS-20070010766 p. 8 | verified. FF-NTRS-20000034017 p. 9 says 24 kPa, and the UI shows the discrepancy. |
| 15 | Atmospheres moved: Apollo 100 % O₂ → Skylab 65 % at 37 kPa → Shuttle/ISS sea-level air | FF-NTRS-20000034017 p. 9 | verified |
| 16 | Orion and Altair are designed for up to 30 % and 34 % O₂ on the normoxic curve | FF-NTRS-20080034883 p. 5 | verified |
| 17 | FLEX flight envelope: O₂ 0.12–0.34, 70.2–309 kPa, ppO₂ 0.105–0.641 atm, microgravity | `ai/fire_safety/artifacts/flex_outcome_model.json` | computed |
| 18 | Across all 840 tests, the highest O₂ flown is 0.34; Apollo 1's is 2.9× that | `GET /api/investigations?scenario=apollo1_pad_1967` → `coverage` | computed |
| 19 | Nearest test to Apollo 1: FLEX 196F003 at 34 % O₂, 72.4 kPa (disruption) | same | computed |
| 20 | Orion 30 % (71 kPa) is inside the FLEX domain: 8 neighbouring tests and an estimate for both fuels | same, with `scenario=orion_max_o2` | computed |

## Claims from the original idea that are wrong or unsupported

| Original claim | What the sources say | Decision |
|---|---|---|
| FLEX covers "about 13–60 %" O₂ | 12–34 % | corrected |
| "1.16 atm" | 16.7 psia = 1.136 atm (115.1 kPa) | corrected |
| "Cabin pressure more than doubled" | rose to at least 29 psia before rupture (about 1.7×) | say "rose until the cabin ruptured" |
| "At launch 60 % O₂ / 40 % N₂" | the corpus only says O₂ was limited on the pad; no page gives 60/40 | not used |
| "New hatch opens outward in 3 seconds" | the Board recommended reducing egress time; no corpus page gives the redesign's time | not used |
| "Low-pressure O₂, which NASA uses today, is inside our envelope" | 100 % O₂ at ~5–6 psia is outside the envelope (O₂ and pressure); ISS uses sea-level air | replaced by Orion 30 % (inside) |
| "NASA abandoned high-oxygen atmospheres forever" | Orion and Altair plan 30–34 % O₂ | not used; the opposite is the pitch's point |
| "Each point linked to the 24 NTRS reports" | none of the 24 was about Apollo 1 | 3 public reports added (27 in total) |
