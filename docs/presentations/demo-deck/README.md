# Flame in Freefall: 7-slide product demo deck

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Draft (ready to present) | 1.0.0 | 2026-11-14 | T7, ADR-013 | `docs/presentations/demo-deck/` |

A designed walkthrough of the product in 7 slides, in the dashboard's own deep-space style (palette from `apps/web/app/globals.css`). Where the [3-minute pitch](../PITCH_SCRIPT_3MIN.md) tells the Apollo 1 story first, this deck demonstrates the product step by step and ends on the refusal.

- **Live deck (claude.ai Slides):** https://claude.ai/artifact/BaR3E388cZyBNbpxKLXnLn. It is private to its owner until shared from the deck's Share menu, and can be presented, commented on and exported to PPTX or PDF from there.
- **PDF export:** [flame-in-freefall-demo.pdf](flame-in-freefall-demo.pdf), 7 pages at 1920×1080.

## Slides

| # | Slide | What it shows | Screenshot |
|---|---|---|---|
| 1 | Flame in Freefall | Spherical droplet-flame illustration; 1950 flight tests, 19 investigations, 27 NASA reports | — |
| 2 | Start with the air in your cabin | The five preset atmospheres, each O₂ against the 40 % highest-flown line, and the coverage verdict | — |
| 3 | Which flight data covers this cabin? | Lunar-lander ranking (ACME CFI-G first, FLEX second) and the four score components | `images/rank.png` |
| 4 | Every number cites its NASA cell | 94 % of 48 vs 8 % of 24 self-extinctions; Measured / Model estimate / Coverage gap labels | `images/insights.png` |
| 5 | Will a droplet flame put itself out? | FLEX model: 261 tests, macro-F1 0.54 vs 0.27, ROC-AUC 0.86; no estimate below 70.2 kPa | `images/explorer.png` |
| 6 | The refusal: Apollo 1 | “None of the 1950 flight tests cover this atmosphere”: 2.5× the highest O₂ flown, 1 g, no estimate; then Orion | `images/apollo.png` |
| 7 | One evidence base, three ways in | Chat (hit@1 0.88), knowledge graph (25,415 edges, 2,304 entities), 16 AURA tools; closing line | — |

Every slide has speaker notes (the `<aside>` in each slide file). Slide 6's notes include the live-demo click path: ISS cabin → Apollo 1 → “Show the flight data for Orion”.

## Sources of the numbers

| Number | Source |
|---|---|
| 1950 flight tests, 19 investigations, 27 reports | [README](../../../README.md) “Data”, `apps/api/tests/test_fire_safety_api.py` |
| Preset O₂ and pressure (ISS 101.4 kPa, pre-EVA 70.3, Orion 71.0, lunar lander 62.7, Apollo 1 115.1) | `ai/fire_safety/scenarios.py` (Orion and lunar lander are derived there from 3.09 psia ppO₂) |
| Lunar-lander ranking, Apollo 1 verdict, 40 % highest O₂ flown, Orion with 8 tests | [FINAL_CHALLENGE_PRESENTATION.md](../../../FINAL_CHALLENGE_PRESENTATION.md) §3a and §6 |
| 94 % of 48 vs 8 % of 24; model metrics; 70.2 kPa lowest FLEX pressure | [FINAL_CHALLENGE_PRESENTATION.md](../../../FINAL_CHALLENGE_PRESENTATION.md) §5–§6, [model card](../../evaluation/reports/flex-outcome-model.md) |
| hit@1 0.88; 2,304 entities and 25,415 edges; 16 AURA tools | [FINAL_CHALLENGE_PRESENTATION.md](../../../FINAL_CHALLENGE_PRESENTATION.md) §3 and §5 |

## Files

```
deck.json          slide order, sections and typefaces (Space Grotesk, Inter, JetBrains Mono)
deck.css           the shared look: palette, type scale 120/64/40/28/24, layouts, arrival motion
slides/<id>.html   one <section> per slide, with speaker notes
images/            the four screenshots, cropped from ../screenshots/ (sidebar and header removed)
assets.json        maps the live deck's asset URLs (/_blob/…) to images/
render_pdf.js      rebuilds flame-in-freefall-demo.pdf
```

Rebuild the PDF from the repository root (needs Playwright with Chromium, and access to fonts.googleapis.com):

```bash
node docs/presentations/demo-deck/render_pdf.js
```

## Known limitations
- The screenshots are crops of the captures in `../screenshots/` (ranking, insights and outcome explorer retaken 2026-11-14 in 613eab6; the Apollo 1 verdict from 2026-11-14 in ea38ea3). They come from a local capture stack, so the live app can differ where data has changed since.
- The Orion pressure (71.0 kPa) is computed from the formula in `scenarios.py`, not read from the running app.
- The cover sphere is an illustration, labelled as such on the slide, not flight imagery.
- Slide edits made in the live deck do not flow back here; copy the changed slide files back and re-run `render_pdf.js`.

## Changelog
- 1.0.0 (2026-11-14): first version, 7 slides, live deck and PDF export.
