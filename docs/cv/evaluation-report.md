| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess & Ziad | Draft | 2.2.0 | 2026-11-14 | M10, A3, C1, CV audit CV-3 | `cv/gold.py`, `cv/flame_cv.py`, `cv/video_analysis.py` |

# CV Evaluation Report (v2.2.0, cv_gold_v1)

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

`python -m cv.gold evaluate` (full output for the current pipeline: `cv/contracts/gold_evaluation_report.json`). Four pipelines, each scored with the same command:

- **Before** fixes 1–2: commit `92b2ef3`.
- **v1.3.0:** with overlay masking and the detection-scoring fixes.
- **v1.4.0:** with the small-flame fix from section 4.
- **v1.5.0:** the current pipeline, with the lit-scene rule from section 4.

| Holdout (8 unseen tests) | Before fixes 1–2 | v1.3.0 | v1.4.0 | **v1.5.0 (current)** |
|---|---|---|---|---|
| False-positive rate | 0.97 [0.89, 1.00] | 0.30 [0.00, 0.65] | 0.30 [0.00, 0.65] | **0.00** (0 of 37 absent frames) |
| Precision | 0.53 [0.30, 0.75] | 0.68 [0.29, 1.00] | 0.72 [0.31, 1.00] | **1.00** |
| Localized recall | 0.37 [0.05, 0.76] | 0.56 [0.22, 0.91] | 0.68 [0.28, 1.00] | **0.68 [0.28, 1.00]** |
| Recall (frame-level) | 1.00, illusory: almost every frame was PRESENT | 0.56 | 0.68 | 0.68 |
| Mean mask IoU | 0.28 [0.04, 0.57] | 0.30 [0.10, 0.55] | 0.32 [0.13, 0.55] | **0.32 [0.13, 0.55]** |
| Mean IoU on detected flames | 0.28 | 0.53 | 0.47 (the recovered T23 flames are tiny, so their masks overlap less) | 0.47 |

At v1.5.0 the holdout false-positive rate and precision have no spread across bootstrap draws (interval [0.00, 0.00] and [1.00, 1.00]), because no resample of 8 tests can contain a false positive. That is not a guarantee of zero: 37 absent frames from 8 tests cannot rule out a false-positive rate of a few per cent.

| Dev (16 sample tests, tuned on) | Before | v1.3.0 and v1.4.0 (identical) | v1.5.0 |
|---|---|---|---|
| False-positive rate | 0.86 [0.65, 1.00] | 0.41 [0.14, 0.71] | 0.16 [0.03, 0.37] |
| Precision | 0.28 [0.05, 0.52] | 0.45 [0.08, 0.80] | 0.68 [0.17, 0.94] |
| Localized recall | 0.87 [0.67, 1.00] | 0.93 [0.67, 1.00] | 0.93 [0.67, 1.00] |
| Mean mask IoU | 0.54 [0.32, 0.79] | 0.55 [0.33, 0.79] | 0.55 [0.33, 0.79] |

Read the intervals before reading the point values. With 8 tests, a single test moves every number.

## 4. Where it fails (holdout, v1.5.0)

| Failure | Frames | Cause |
|---|---|---|
| ~~Cabin view called a flame~~ (fixed in v1.5.0) | T20: was 8 of 8 absent frames PRESENT, now UNCERTAIN | Lit scene; see below |
| ~~Chamber lights on, called a flame~~ (fixed in v1.5.0) | B3: was 3 of 5 absent frames PRESENT, now UNCERTAIN | Lit scene; see below |
| Dim blue flame missed | M10: 9 of 9 flame frames ABSENT | Too faint for a brightness detector. A real limit of the method, not a threshold. |
| ~~Small flame missed~~ (fixed in v1.4.0) | T23: was 5 of 9 flame frames ABSENT in v1.3.0, now 9 of 9 PRESENT | See below |
| Dim lobes not PRESENT | B3: 4 of 5 flame frames (3 UNCERTAIN, 1 ABSENT) | Low contrast |
| Low IoU on detected flames | B1, T23, F1 | The pipeline keeps only the largest region, so a two-lobed flame scores about half |

### Lit scenery and the v1.5.0 rule

Every held-out false positive at v1.4.0 was a bright region in a **lit** scene: the T20 cabin view (glovebox floor and monitors) and the B3 chamber with its lights on. The detector assumes a dark background, because luminous flames are filmed in dark chambers. In a lit scene a bright region may be scenery, so v1.5.0 reports it UNCERTAIN, never PRESENT.

- **Lighting measure:** the median gray minus the 1st-percentile gray. A first version used the median alone; an existing 12-bit sensor test showed it would call a sensor's constant black level (pedestal) "lit" and demote every flame on such a sensor.
- **Cut-off:** chosen on **dev data only**. Dev flame frames reach 4 at most; lit scenery false positives (the T25 cabin view, lit FLEX hardware) start at 19; the cut-off is 11, the midpoint. Across all committed samples it demoted 82 T25 cabin frames, 8 lit-hardware FLEX frames, 4 DSI frames, and one FLEX frame (`X168M03D_00164`) that shows glowing igniter tips in an orange-lit chamber, which is probably not a flame. It demoted no dev flame frame.
- **Holdout result:** all 11 false positives gone, no held-out flame lost.
- **How blind?** No holdout number was used and T20 and B3 were never measured. But the choice of *cue* (lighting) came from knowing that the held-out false positives were lit scenes. Treat the holdout gain as less blind than a fresh test would be.
- **Not fixed:** bright hardware in a **dark** scene. In dev, the glowing FLEX igniter arc and point lights (`176F001D`, `195F002D`, `H08M101D`) and DSI frames are still PRESENT (dev false-positive rate 0.16).
- **Recall cost:** a real flame filmed in a lit scene would now be UNCERTAIN. `cv_gold_v1` has no such frame, so this cost is not measured.

### The v1.3.0 small-flame regression and its fix

v1.3.0 raised the minimum region to 0.05% of the frame to drop edge specks in empty frames. On the holdout this missed 5 of the 9 T23 flame frames: real flames 0.019–0.049% of the frame with contrast 100–128. The specks overlap these flames in size, so size alone cannot separate them.

**v1.4.0** restores the 0.01% minimum. A region under 0.05% of the frame is then a speck unless its contrast is ≥ 83. The cut-off was chosen on **dev data only**: 92 small dev specks reach contrast 61.6 at most, real dev flames start at 104.9, and 83 is the midpoint. It changes no status on any committed sample (132 images and every sampled frame of the three dev videos), and fixes all 5 T23 misses with no new false positive on any held-out test.

**How blind is the holdout now?** No number was fitted to holdout data. The holdout did reveal *that* small flames exist and fail, and the T23 contrasts (100–128) were seen before the 83 cut-off was fixed. So T23's v1.4.0 result is not fully blind. The other seven held-out tests are unaffected (their status counts did not change). A fresh held-out test with small flames would give a fully blind check.

Correct and solid: T7 (8/8 flames found, 2/2 empty frames ABSENT), T23 (9/9 and 1/1, v1.4.0), T12 (6/6 and 4/4), F1 (4/4 and 6/6), P20 (10/10 empty frames ABSENT), and all SPICE flames in dev.

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
- **v2.2.0 (2026-11-14):** Added v1.5.0 results. The lit-scene rule (tuned on dev only) removes all 11 held-out false positives with no recall loss; the blindness caveat and the remaining dark-scene false positives are documented.
- **v2.1.0 (2026-11-13):** Added v1.4.0 results. The small-flame regression is fixed with a contrast rule tuned on dev only; the holdout-blindness caveat is documented.

- **v2.0.0 (2026-11-13):** Replaced the v1.1.0 report (10 flame-only SPICE images, no negatives, no ground truth) with an evaluation on `cv_gold_v1`: a held-out split, negatives, masks, test-level intervals, localized recall, and a before/after comparison of fixes 1–2. Found the T23 small-flame regression.
- **v1.2.0 (2026-10-12):** Initial report from a sample batch.
