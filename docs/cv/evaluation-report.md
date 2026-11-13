| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess & Ziad | Draft | 2.0.0 | 2026-11-13 | M10, A3, C1, CV audit CV-3 | `cv/gold.py`, `cv/flame_cv.py`, `cv/video_analysis.py` |

# CV Evaluation Report (v2.0.0, cv_gold_v1)

**Every label in this report is a Claude-drafted, unverified draft.** The numbers measure the pipeline against those drafts. They will change, probably a little, once people verify the set ([annotation-protocol.md §5](annotation-protocol.md#5-draft-and-verify-workflow)); the report then shows verified-only numbers next to these.

## 1. Data

| Split | Frames | Tests | present / absent / unclear | What it is |
|---|---|---|---|---|
| holdout | 80 | 8 | 41 / 37 / 2 | Unseen BASS-II tests (T7, T12, T20 cabin view, T23, B3, F1, M10, P20), never used to tune |
| dev | 70 | 16 | 15 / 44 / 11 | The committed samples (BASS-II B1, P12, T25; SPICE; FLEX; SAFFIRE-I; DSI), used to tune fix 2 |

Video frames are the served pipeline's sampling grid (10 per video). Holdout tests sit only in holdout (a test checks this). Masks: 56 (43 GrabCut, 13 threshold-in-box for dim flames).

## 2. Metrics

- **Precision, recall, false-positive rate** per frame, where PRESENT counts as a detection (`strict`). Unclear frames are excluded.
- **Localized recall:** a flame frame counts as found only if the pipeline's mask overlaps the labelled flame (IoU ≥ 0.1). Without it, a box on the telemetry text of a flame frame counts as finding the flame.
- **Mean mask IoU** over flame frames, on the pipeline's letterbox canvas. A missed flame scores 0.
- **95% intervals** come from 2,000 bootstrap draws that resample **whole tests**, not frames, because frames of one test are highly correlated.

## 3. Results

`python -m cv.gold evaluate` (pipeline `cv-opencv-v1.3.0-auto` / `cv-video-v1.1.0`, i.e. with overlay masking and the detection-scoring fixes; full output `cv/contracts/gold_evaluation_report.json`). "Before" is the same command run on the pipeline at commit `92b2ef3`, before those fixes.

| Holdout (8 unseen tests) | Before fixes 1–2 | **After fixes 1–2** |
|---|---|---|
| False-positive rate | 0.97 [0.89, 1.00] | **0.30 [0.00, 0.65]** |
| Precision | 0.53 [0.30, 0.75] | **0.68 [0.29, 1.00]** |
| Localized recall | 0.37 [0.05, 0.76] | **0.56 [0.22, 0.91]** |
| Recall (frame-level) | 1.00, illusory: almost every frame was PRESENT | 0.56 [0.22, 0.91] |
| Mean mask IoU | 0.28 [0.04, 0.57] | 0.30 [0.10, 0.55] (0.53 on flames it detects) |

| Dev (16 sample tests, tuned on) | Before | After |
|---|---|---|
| False-positive rate | 0.86 [0.65, 1.00] | 0.41 [0.14, 0.71] |
| Precision | 0.28 [0.05, 0.52] | 0.45 [0.08, 0.80] |
| Localized recall | 0.87 [0.67, 1.00] | 0.93 [0.67, 1.00] |
| Mean mask IoU | 0.54 [0.32, 0.79] | 0.55 [0.33, 0.79] |

Read the intervals before reading the point values. With 8 tests, a single test moves every number.

## 4. Where it fails (holdout, after the fixes)

| Failure | Frames | Cause |
|---|---|---|
| Cabin view called a flame | T20: 8 of 8 absent frames | Static bright scenery (glovebox floor, monitors). The same problem as T25 in dev; no rule in the detector can separate it. |
| Chamber lights on, called a flame | B3: 3 of 5 absent frames | Brightly lit hardware |
| Dim blue flame missed | M10: 9 of 9 flame frames ABSENT | Too faint for a brightness detector. A real limit of the method, not a threshold. |
| Small flame missed | T23: 5 of 9 flame frames ABSENT | **Regression from fix 2.** These flames are 0.019–0.049% of the frame, stable (0.79–0.86) and high-contrast (100–128), but below the new 0.05% minimum region. With the old 0.01% minimum all five are PRESENT. The edge specks that the minimum was raised for are 0.01–0.031%, so size alone cannot separate the two; contrast or stability probably can (the specks scored about 60). Not retuned here: doing so after looking at T23 would make T23 tuned data. |
| Dim lobes not PRESENT | B3: 4 of 5 flame frames (3 UNCERTAIN, 1 ABSENT) | Low contrast |
| Low IoU on detected flames | B1, T23, F1 | The pipeline keeps only the largest region, so a two-lobed flame scores about half |

Correct and solid: T7 (8/8 flames found, 2/2 empty frames ABSENT), T12 (6/6 and 4/4), F1 (4/4 and 6/6), P20 (10/10 empty frames ABSENT), and all SPICE flames in dev.

## 5. Reproduce

```bash
python -m cv.gold fetch      # the 8 held-out videos (about 60 MB), SHA-256 checked
python -m cv.gold evaluate   # writes cv/contracts/gold_evaluation_report.json
```

The committed tests (`tests/cv/test_gold.py`) check the set itself: it validates against the schema, covers every sampled frame, has no test in two splits, has at least 30% absent frames per split, and every mask file exists. They do not run the evaluation, which needs the held-out videos.

## Known limitations

- **Unverified drafts:** see the top of this page. There is one labeller and no inter-annotator agreement.
- **Holdout is 8 BASS-II tests:** there are no held-out SPICE, FLEX or SAFFIRE-I frames.
- **Masks are approximate,** and the pipeline is scored on its largest region only.
- **Detection confidence is not evaluated:** it is still a heuristic score, not a calibrated probability.
- **No measurement-error evaluation:** there are no calibrated physical reference values.

## Changelog

- **v2.0.0 (2026-11-13):** Replaced the v1.1.0 report (10 flame-only SPICE images, no negatives, no ground truth) with an evaluation on `cv_gold_v1`: a held-out split, negatives, masks, test-level intervals, localized recall, and a before/after comparison of fixes 1–2. Found the T23 small-flame regression.
- **v1.2.0 (2026-10-12):** Initial report from a sample batch.
