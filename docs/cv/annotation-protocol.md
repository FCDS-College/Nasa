| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess & Ziad | Draft | 1.3.0 | 2026-11-13 | M10, A3, CV audit CV-3 | `cv/gold.py`, `datasets/evaluation/cv_gold_v1*` |

# Annotation Protocol and Ground-Truth Dataset (cv_gold_v1)

The CV evaluation set `cv_gold_v1` holds 150 frames, each labelled for whether a flame is visible, plus a flame mask for every frame with a flame. It measures the false positives the CV audit found (telemetry overlays, cabin views, hardware, empty frames) as well as misses and mask quality. Every label starts as a draft, and a person verifies it.

## 1. Files

| File | What it is | In Git |
|---|---|---|
| `datasets/evaluation/cv_gold_v1_sources.json` | Every source with its SHA-256, split, test (`groupId`) and the video sampling grid | yes |
| `datasets/evaluation/cv_gold_v1.jsonl` | One item per frame: label, mask reference, notes, provenance | yes |
| `datasets/evaluation/cv_gold_v1.schema.json` | JSON Schema for an item | yes |
| `datasets/evaluation/cv_gold_v1_masks/<itemId>.png` | Flame masks, original pixels, 255 = flame | yes |
| `datasets/evaluation/cv_gold_v1_review.csv` | The review sheet a verifier fills in | yes |
| `datasets/raw/psi_api/PSI-25/Raw Data/*.mp4` | Held-out videos (`python -m cv.gold fetch`, checksums verified) | no |
| `datasets/derived/cv_gold/frames/`, `…/review/` | Extracted frames and review overlays (`frames`, `review`) | no |

## 2. Splits and sampling

- **Split by test, never by frame.** No `groupId` appears in two splits (a test asserts this).
- **`holdout`:** 8 BASS-II tests that were never used to choose a threshold: T7, T12, T20 (cabin view), T23, B3, F1, M10 and P20. Use them only to measure. If you change the pipeline because of something seen in a holdout frame, that test becomes dev data; move it and record that in the evaluation report.
- **`dev`:** the committed samples (BASS-II B1, P12 and the T25 cabin view; SPICE; FLEX; SAFFIRE-I; DSI). Thresholds were tuned on these.
- **Video frames** are the served pipeline's sampling grid: `sample_every = frameCount // 10`, 10 frames per video, so pre-ignition, burning and post-extinction frames are all included and the evaluation scores exactly the frames the API would analyse.

## 3. Label rules

| Label | Use when |
|---|---|
| `present` | A flame is visible in the camera's own field of view, however small or dim (a faint blue crescent counts). |
| `absent` | No flame is visible. This includes pre-ignition and post-extinction frames, chamber-lit frames showing only hardware, the 16-bit FLEX sensor dark frames, and cabin views whose monitors show no flame. |
| `unclear` | You cannot tell. It is excluded from the metrics, so do not use it to avoid hard cases; say why in `notes`. |

Specific cases:

- **Flame shown on a monitor inside a cabin view** (T20, T25): `unclear`, with a note. It is a picture of a flame, not a flame in the scene.
- **Telemetry text, reflections, glowing hardware arcs, point lights and single bright specks:** not a flame. Label the frame from what else is in it.
- **Faint content visible only after a contrast stretch:** `unclear`, unless its shape is clearly a flame (for example the two arcs of a flame around a sample).

## 4. Mask rules

- **Cover the luminous flame,** including every lobe; a two-lobed flame gets both lobes.
- **Exclude** telemetry text, hardware, reflections, light streaks and the wide halo around a bright flame. Keep the glow only where it is continuous with the luminous core.
- **Masks are drafted from a box drawn around the flame:**
  - `grabcut-from-box`: GrabCut inside the box.
  - `threshold-in-box`: Otsu on the box's own contrast range, for dim flames where GrabCut finds nothing.

  Both are different from the pipeline's global Otsu threshold, and nothing outside the box can enter the mask. The box and method are stored with each mask, and `notes` says when the box was set by hand.
- **Redraw a mask:** `python -m cv.gold draft-mask ITEM X0 Y0 X1 Y1 [--method threshold-in-box]`. This resets the item to unverified.

## 5. Draft and verify workflow

1. `labeller: claude-draft` means Claude Code drafted the label by viewing the frame and contrast-stretched zooms; for a flame frame it also set or checked the box and inspected the mask. `verified: false` until a person checks it.
2. `python -m cv.gold frames` and then `python -m cv.gold review` writes one image per item (the frame, and the frame with the draft mask outlined) and refreshes the review sheet.
3. For each row of `cv_gold_v1_review.csv`, set:
   - `verdict`: `accept` or `fix` (blank to skip);
   - `correctedLabel` (for `fix`);
   - `maskOk` (`yes` or `no` for frames with a mask);
   - `reviewer` (your name);
   - `notes`, optionally.
4. `python -m cv.gold adopt` applies the sheet:
   - `accept` and `fix` mark the item verified, by you;
   - `maskOk = no` drops the mask and keeps the item unverified until the mask is redrawn.
5. `python -m cv.gold evaluate` reports every subset twice: all items, and verified items only.

## Known limitations

- **No item is verified yet.** Every number from this set is measured against Claude-drafted labels until people review it.
- **8 held-out tests is few.** Intervals that resample tests are wide (section 4 of the evaluation report).
- **Holdout is BASS-II only.** SPICE, FLEX and SAFFIRE appear only in dev, so held-out numbers say nothing about them.
- **Masks are drafts from GrabCut or a thresholded box,** not brush-traced. Their edges are approximate, and dim flames are traced as thin arcs.
- **One labeller,** so there is no inter-annotator agreement yet. A second person reviewing the same items would give one.

## Changelog

- **v1.3.0 (2026-11-13):** Built `cv_gold_v1`: 150 frames, 56 masks, a held-out split, label and mask rules, and the draft/verify workflow with tooling (`cv/gold.py`).
- **v1.2.0 (2026-10-12):** Initial protocol.
