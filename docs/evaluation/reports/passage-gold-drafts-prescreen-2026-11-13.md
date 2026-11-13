| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | Generated; **not a verification**: a person still has to verify | 0.1.0 | 2026-11-13 | E2, C2, annotation-guidelines §5 | `datasets/evaluation/passage_gold_v1_drafts.jsonl`, `datasets/evaluation/passage_gold_v1_verification.csv`, `ai/rag/evaluation/adopt_drafts.py` |

# Passage gold drafts: pre-screen by their author

The 35 drafts were written by an AI. This is a second, critical read by **the same AI**, so it is a pre-screen that makes a human's check faster and finds defects; it is not independent and not a verification (guidelines §5.5 asks for a different person, and `adopt_drafts` refuses an AI or the author). Nothing here is in `passage_gold_v1.jsonl`.

## What was checked, and how

For every answerable draft: the question against the cited passage (is the answer in the span, is the question answerable from it alone, is it a paraphrase); then, with the page text of all 240 indexable pages, whether the same answer, or a competing one, is written elsewhere (keyword and figure search, `verification_sheet`). For the 11 unanswerable drafts: that their topic words occur nowhere in the 240 pages (done earlier; four of a first eleven failed that check and were replaced).

## Defects found and fixed (all in the drafts now)

| Draft | Defect | Fix |
|---|---|---|
| PG-008 | the 17 % ignition-delay result is stated again on `20080012607` p4 | p4 added as second evidence |
| PG-009 | "up to 4 % oxygen" is stated on `20080034883` p11 and p13 as well as p5 | both added |
| PG-021 | the Saffire-I/III fabric (75 % cotton, 25 % fiberglass) is stated again on `20170000230` p4 | p4 added |
| PG-001 | a competing criterion for the same test (no transfer of burning debris, `20150008961` p1) made "what else must a material avoid" ambiguous | question now asks about the object under the holder and what must not happen to it |
| PG-013 | asked about "the worst fire", which the cited sentence does not say | reworded to the fire scenario |
| PG-010 | "in psi" was a clumsy hint | asks for the limit at 14.7 psia explicitly |
| PG-024 | "combustion chamber experiments" was vaguer than the passage | asks about low-momentum microgravity flames at elevated oxygen |
| PG-002, 005, 007, 016, 023 | (found earlier with the sheet) answer repeated on a second page | already cite both pages |

Eight drafts now cite more than one page (PG-002, 005, 007, 008, 009, 016, 021, 023); a retrieval hit on any cited page counts.

## What a verifier should still look at closely

- **PG-002:** `20000034017` p10 gives two environments: ISS worst case 105 kPa with 24.1 % oxygen for all places except airlocks, and 70.3 kPa with 30 % oxygen for airlocks. The question's answer (30 %, 70.3 kPa, from `19990063738` p4) matches the airlock one. Decide whether p10 should stay as evidence.
- **PG-005:** the second page (`20040161216` p10) lists `0.01, 0.16, 0.38 g` without saying lunar or Martian.
- **PG-015:** the span is a nomenclature list; only the `ULOI = …` entry answers the question.
- **PG-017, PG-019:** "transparent" stands for quartz, and "rod widths" for diameters; both are reasonable readings, not wording from the page.
- **PG-003, PG-004:** `20140009169` p1–p2 mention "~5 s" drop time and "±0.02 g" jitter: related, not the same answer.
- **Unanswerable drafts:** a keyword search found their topics absent; it cannot show that no passage answers the question in other words. §5.3 prefers that a person writes these, so rewrite any that read as machine-made.
- **The 18 drafts that share a figure with another page** are listed in `passage_gold_v1_verification.csv` (`same_figures_on`); most are coincidences (21 %, 3 mm).

## If the verifier agrees

The command below adopts all 24 answerable and all 11 unanswerable drafts under the verifier's own name. Run it only after reading the sheet and deciding; drop the IDs you reject (keep at least 20 answerable and an unanswerable share of at least 25 %).

```text
python -m ai.rag.evaluation.adopt_drafts --verifier "Your Name" --accept PG-001 PG-002 PG-003 PG-004 PG-005 PG-006 PG-007 PG-008 PG-009 PG-010 PG-011 PG-012 PG-013 PG-014 PG-015 PG-016 PG-017 PG-018 PG-019 PG-020 PG-021 PG-022 PG-023 PG-024 PG-025 PG-026 PG-027 PG-028 PG-029 PG-030 PG-031 PG-032 PG-033 PG-034 PG-035
```

## Known limitations

- Same author, same blind spots: a defect I could not see in the questions I wrote is still there. A human reading is the only independent check.
- The duplicate search is lexical (keywords and figures); an answer written in different words on another page would not be found.
- 24 answerable questions on 16 documents, all about combustion and fire safety in reduced gravity, all in English. Intervals computed from them will be wide.

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-11-13 | First pre-screen; seven drafts changed in it: four reworded (PG-001, 010, 013, 024) and three given extra evidence pages (PG-008, 009, 021). |
