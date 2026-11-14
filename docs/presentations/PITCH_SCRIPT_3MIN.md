# Flame in Freefall: 3-minute pitch script (English)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Ready to rehearse | 1.0.0 | 2026-11-13 | ADR-013 | `docs/presentations/build_pitch_deck.py`, `docs/presentations/flame-in-freefall-3min-pitch.pptx` |

About 410 spoken words, which is about 2:45 at 150 words a minute and leaves 15 s of margin. Every number is in the [fact sheet](../../.internal/research/2026-11-13-apollo1-facts.md). The order is deliberate: the hook opens a story, the ISS demo shows that the system **solves**, then Apollo 1 shows that it **knows when not to**.

The deck is `flame-in-freefall-3min-pitch.pptx` (7 slides; these words are also its speaker notes). Rebuild it with `python docs/presentations/build_pitch_deck.py`.

---

### Slide 1 · Hook (0:00–0:25)

> January 27th, 1967. Apollo 1 sits on the launch pad for a ground test.
> The cabin is filled with **one hundred percent oxygen, at sixteen point seven psi**.
> One spark. Within seconds the pressure climbs until the cabin ruptures, and the hatch cannot be opened.
> Gus Grissom, Ed White and Roger Chaffee die.
> NASA later wrote that the cabin materials had been exposed to an atmosphere **in which they had never been tested**.

*(Pause one beat. Change slide.)*

### Slide 2 · The problem today (0:25–0:45)

> Sixty years later, we are choosing new atmospheres again. Orion and lunar landers plan for up to **thirty and thirty-four percent oxygen**, more than the ISS. Commercial stations are being designed this decade.
> NASA's flight evidence exists: **1950 microgravity combustion tests and 27 technical reports**. But it is scattered across tables nobody can search in an afternoon, and none of them tell you where the data ends.

### Slide 3 · It solves (0:45–1:10)

> Flame in Freefall reads all of it. Pick an atmosphere, here ISS air.
> **310 flight tests lie near it.** The investigations are ranked by how directly they apply, every number links to its NASA table cell, and a validated model estimates how droplet flames end.

### Slide 4 · It knows when not to answer (1:10–1:45)

> Now we give it Apollo 1's atmosphere. It refuses.
> **"None of the 1950 flight tests cover this atmosphere."**
> Its oxygen is **2.5 times** the highest ever flown, and it is at Earth gravity, while every test was in microgravity. It shows the nearest real test, and it makes **no estimate**.
> That is exactly the gap that cost three lives: a decision made in an atmosphere nobody had tested.

### Slide 5 · What changed, and where the data is (1:45–2:05)

> Then it shows what changed after: Beta cloth, less oxygen on the pad, testing materials at worst-case conditions. Each line links to a NASA page.
> And it points to where data does exist: **Orion's thirty-percent atmosphere sits inside our flight envelope**, with eight real tests. Covered by data, not called safe.

### Slide 6 · The business (2:05–2:35)

> This is a product. Our first customers are commercial station and habitat teams, and the suppliers qualifying their materials.
> They pay for a workspace and an API that tells them in minutes what the flight evidence covers, and what it does not, with citations a review board can check.
> We start with NASA SBIR and ESA incubation pilots. And it is measured: our outcome model scores **0.54 macro-F1 against a 0.27 baseline**, validated by test day.

### Slide 7 · Close (2:35–3:00)

> An AI that sits in a spacecraft design review must do one thing before anything else: **know when not to answer**.
> Ours does, and it shows you why.
> Flame in Freefall. Thank you.

---

## Delivery notes
- **Hook:** no "hello, we are…". Start on the date, in a low voice, with no slide text read aloud.
- **Live demo option:** slides 3–5 can be the live dashboard instead of screenshots. Click ISS cabin, then **Apollo 1**, then **Show the flight data for Orion**. The `npm run smoke` journey checks this exact path.
- **If asked "why not just predict?"** "Because the model was trained between 12 and 34 % oxygen in microgravity. Anything it said about 100 % at 1 g would be invented."
- **If asked about the 60/40 launch mix or the new hatch:** no page in our corpus gives those numbers, so the system does not state them.

## Known limitations
- Timed by word count (about 410 words at 150 wpm), not yet by a stopwatch rehearsal. Cut slide 6's last sentence first if a run goes over.
- The screenshots come from a local run on 2026-11-13. A live demo shows the deployed numbers, which match only when it runs from this branch with the 27-report corpus ingested.

## Changelog
- 1.0.0 (2026-11-13): first script, timed for 3:00.
