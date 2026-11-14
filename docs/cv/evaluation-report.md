| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess & Ziad | Draft | 2.5.1 | 2026-11-14 | M10, A3, C1, CV audit CV-3 | `cv/gold.py`, `cv/flame_cv.py`, `cv/video_analysis.py` |

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

`python -m cv.gold evaluate` (full output for the current pipeline: `cv/contracts/gold_evaluation_report.json`). Seven pipelines, each scored with the same command:

- **Before** fixes 1–2: commit `92b2ef3`.
- **v1.3.0:** with overlay masking and the detection-scoring fixes.
- **v1.4.0:** with the small-flame fix from section 4.
- **v1.5.0:** with the lit-scene rule from section 4.
- **v1.6.0:** with camera profiles (section 4). The evaluation passes each source's `cameraProfile` (the 15 FLEX colour sources use `flex-colour`), as a client would send `camera_profile`. Its holdout figures equal v1.5.0's: the holdout has no FLEX frames.
- **v1.7.0:** with the camera profile's size floor (section 4). Holdout unchanged, for the same reason.
- **v1.8.0:** the current pipeline, with the straight-edge rule (section 4). It applies to every image, but changes no held-out frame.

| Holdout (8 unseen tests) | Before fixes 1–2 | v1.3.0 | v1.4.0 | **v1.5.0 to v1.8.0 (current)** |
|---|---|---|---|---|
| False-positive rate | 0.97 [0.89, 1.00] | 0.30 [0.00, 0.65] | 0.30 [0.00, 0.65] | **0.00** (0 of 37 absent frames) |
| Precision | 0.53 [0.30, 0.75] | 0.68 [0.29, 1.00] | 0.72 [0.31, 1.00] | **1.00** |
| Localized recall | 0.37 [0.05, 0.76] | 0.56 [0.22, 0.91] | 0.68 [0.28, 1.00] | **0.68 [0.28, 1.00]** |
| Recall (frame-level) | 1.00, illusory: almost every frame was PRESENT | 0.56 | 0.68 | 0.68 |
| Mean mask IoU | 0.28 [0.04, 0.57] | 0.30 [0.10, 0.55] | 0.32 [0.13, 0.55] | **0.32 [0.13, 0.55]** |
| Mean IoU on detected flames | 0.28 | 0.53 | 0.47 (the recovered T23 flames are tiny, so their masks overlap less) | 0.47 |

Since v1.5.0 the holdout false-positive rate and precision have no spread across bootstrap draws (interval [0.00, 0.00] and [1.00, 1.00]), because no resample of 8 tests can contain a false positive. That is not a guarantee of zero: 37 absent frames from 8 tests cannot rule out a false-positive rate of a few per cent.

| Dev (16 sample tests, tuned on) | Before | v1.3.0 and v1.4.0 (identical) | v1.5.0 | v1.6.0 | v1.7.0 | v1.8.0 |
|---|---|---|---|---|---|---|
| False-positive rate | 0.86 [0.65, 1.00] | 0.41 [0.14, 0.71] | 0.16 [0.03, 0.37] | 0.11 [0.00, 0.28] (5 of 44) | 0.05 [0.00, 0.18] (2 of 44) | 0.00 (0 of 44) |
| Precision | 0.28 [0.05, 0.52] | 0.45 [0.08, 0.80] | 0.68 [0.17, 0.94] | 0.75 [0.25, 1.00] | 0.88 [0.41, 1.00] | 1.00 |
| Localized recall | 0.87 [0.67, 1.00] | 0.93 [0.67, 1.00] | 0.93 [0.67, 1.00] | 0.93 [0.67, 1.00] | 0.93 [0.67, 1.00] | 0.93 [0.67, 1.00] |
| Mean mask IoU | 0.54 [0.32, 0.79] | 0.55 [0.33, 0.79] | 0.55 [0.33, 0.79] | 0.55 [0.33, 0.79] | 0.55 [0.33, 0.79] | 0.55 [0.33, 0.79] |

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
- **Not fixed by this rule:** bright hardware in a **dark** scene (next subsection).
- **Recall cost:** a real flame filmed in a lit scene would now be UNCERTAIN. `cv_gold_v1` has no such frame, so this cost is not measured.

### Hardware in a dark scene and the v1.6.0 camera profiles

At v1.5.0 all 7 dev false positives were bright hardware in a dark scene: 5 FLEX colour frames (`176F001D_01319`, `195F002D_00000`, `195F002D_01061`, `H08M101D_00642`, `H08M101D_01284`) and 2 DSI frames.

- **Why not a shape or colour rule:** on dev, the hardware regions' elongation, circularity, saturation and hue overlap with real flames'. Only position separates the FLEX arc: it sits at the bottom of every FF-PSI-69 colour frame.
- **Fix:** a per-camera exclusion zone (`cv/configs/camera_profiles.json`, profile `flex-colour`: the full-width band below 0.82 of the frame height), applied when the request names the profile. The zone was drawn from the per-sequence median of the 75 committed FLEX colour frames, then widened to the full width because the view shifts within a sequence. That widening was fitted to a dev false positive (`195F002D_00000`).
- **Result on dev:** 2 of the 5 FLEX false positives are gone (`176F001D_01319`, `195F002D_01061`). In the other 3, the next-largest bright region is something else: a bright strip at the top edge (`195F002D_00000`, later found to be a readout artefact; see below)) and droplet point lights (`H08M101D_00642`, `_01284`). The 2 DSI frames are kept as negatives and remain false positives. No dev flame was lost; the real FLEX flame `195F002D_00530` gives the same status and box.
- **Holdout:** unchanged. It has no FLEX frames, so this change has **no held-out validation**: the dev gain is in-sample.
- **Recall risk:** a flame inside the zone is not seen. The highest real flame centroid in dev is at 0.67 of the frame height, above the zone's top at 0.82.

### Droplet glints and the v1.7.0 size floor

Three FLEX false positives were left at v1.6.0. They are glints, not flames:
- `H08M101D_00642` and `_01284`: specular reflections on the droplet. The droplet appears as two point lights that persist in 13 consecutive committed frames, drift slightly, and sit where the lit frame `H08M101D_00092` shows the deployed droplet. The FLEX table records H08M101 as **methanol**, with the flame out at **0.3 s** and the droplet almost unburned (3.56 → 3.54 mm), so the draft label "absent" stands.
- `195F002D_00000`: a bright strip along the top edge. On closer inspection it is not a glint but a **readout artefact**: rows 0–10 of this, the first frame of the sequence, are a green strip from a different exposure, with a one-row step to near-black (row mean 15.6 → 0.6 in green). No other of the 75 committed FLEX colour frames has it.

What was tried, on dev only:
- **Colour does not separate them.** The sensor fringes a point source, so a glint is not neutral white: white-clipped fraction 0–0.011, chroma 0.26–0.48. That overlaps the dim, reddish unclear FLEX blobs (chroma 0.54–0.67).
- **Size does, with physics behind it.** A visible flame encloses its droplet. The scale, measured on two lit frames with a droplet of known size, is 0.12–0.15 mm/px. So the median initial FLEX droplet (3.0 mm) covers about 0.10% of the frame. Every FLEX region in dev below that (0.023–0.060%) is a glint; the one labelled FLEX flame covers 1.73%.
- **Why demote, not drop:** 5% of FLEX tests record extinction at a droplet under 0.13 mm, so a flame near burnout can be that small. The floor reports such a region UNCERTAIN, never ABSENT.

Results:
- **Dev:** strict false positives 5 → 2. The 2 left are the DSI frames, kept as negatives. Precision 0.75 → 0.88, false-positive rate 0.11 → 0.05, no flame lost. Lenient metrics are unchanged, because the frames are UNCERTAIN, not ABSENT.
- **Status changes:** 4 dev items: the three glints and `176F001D_00660` (unclear). Across all 75 committed FLEX colour frames the floor demotes 19 PRESENT frames; each was checked by eye, and each detection is a droplet glint or the top-edge readout artefact. In `176F001D` (methanol, burning for 29.1 s) a faint flame shell may surround the glint in some of those frames, but the pipeline had segmented the glint, not the shell.
- **Holdout:** unchanged; it has no FLEX frames, so this change, too, has **no held-out validation**.
- **Threshold:** chosen from physics and the measured scale, not fitted; it falls in the dev gap between glints (≤ 0.060%) and the FLEX flame (1.73%).
- **`195F002D_00000` stays UNCERTAIN by decision.** It still counts as a false positive in the lenient metric. A rule that masks edge strips is not viable: full-width steps near the frame edge are common and legitimate in the committed data (the SAFFIRE `vlcsnap` letterbox bars at row 22, the DSI vignette, the T25 banner at row 10), and only this one frame has the artefact. Excluding a thin top band in the `flex-colour` profile would fit a zone to one corrupted frame. UNCERTAIN is an honest answer for a frame the pipeline cannot know is corrupt.

### The DSI backlit cell and the v1.8.0 straight-edge rule

The last 2 dev false positives (`DSI_SEQ2_ACTIVITE04_HR1_1018759522_1`, `_1022430520_1`) come from DECLIC's Directional Solidification Insert, a non-combustion experiment. The frames show a backlit transparent sample cell: a bright, flat rectangle filling 14–18% of the frame.

- **Cue:** rectangularity, the region's area over its minimum-area rectangle. Flames are rounded, and a filled ellipse scores π/4 = 0.785. Across the dev split and all 182 committed image samples, real PRESENT flames reach 0.844 at most (`ISS018E030372`, SPICE). The 6 DSI backlit-cell frames score 0.903–0.950.
- **Rule:** a region that would be PRESENT, fills more than 0.875 of its rectangle (the midpoint of that gap) and is at least 20 px across is UNCERTAIN. The 20 px gate is measured, not assumed: digitised ellipses reach 0.958 at 6 px but stay under 0.83 from 20 px. That keeps small flames out of the rule.
- **Dev:** false positives 2 → 0; precision 1.00, no flame lost. This is in-sample: the cut-off was set on these frames.
- **Holdout (scored once):** unchanged. No held-out frame is affected, so this says the rule costs no held-out recall, not that it would catch unseen boxy scenery.
- **Not measured:** a real flame with straight sides (a SAFFIRE flame spreading across the full width of its rectangular sample, or a flame cut on two opposite sides by the frame) would be UNCERTAIN. No committed flame scores above 0.844, and no such frame is labelled.
- **Why not a "non-combustion source" rule:** knowing the frames are from DSI would make the test meaningless. These frames measure whether the detector can tell bright non-flame scenery from a flame without being told, and the shape rule does that from the pixels alone.

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
- **Holdout is 8 BASS-II tests:** there are no held-out SPICE, FLEX or SAFFIRE-I frames, so FLEX-specific changes such as the `flex-colour` profile are only measured in-sample.
- **Masks are approximate,** and the pipeline is scored on its largest region only.
- **Detection confidence is not evaluated:** it is still a heuristic score, not a calibrated probability.
- **No measurement-error evaluation:** there are no calibrated physical reference values.

## Changelog
- **v2.5.1 (2026-11-14):** `195F002D_00000` is a first-frame readout artefact, not a glint; why it stays UNCERTAIN.
- **v2.5.0 (2026-11-14):** Added v1.8.0 results (straight-edge rule): the DSI backlit-cell false positives are UNCERTAIN; dev false positives 2 → 0; holdout scored once, unchanged.
- **v2.4.0 (2026-11-14):** Added v1.7.0 dev results (camera-profile size floor): the three FLEX glint false positives are UNCERTAIN, dev false positives 5 → 2; the H08M101 label checked against the FLEX table (methanol, extinction at 0.3 s).
- **v2.3.0 (2026-11-14):** Added v1.6.0 dev results (camera profiles): dev false positives 7 → 5, holdout unchanged and not informative for this change (no FLEX frames).
- **v2.2.0 (2026-11-14):** Added v1.5.0 results. The lit-scene rule (tuned on dev only) removes all 11 held-out false positives with no recall loss; the blindness caveat and the remaining dark-scene false positives are documented.
- **v2.1.0 (2026-11-13):** Added v1.4.0 results. The small-flame regression is fixed with a contrast rule tuned on dev only; the holdout-blindness caveat is documented.

- **v2.0.0 (2026-11-13):** Replaced the v1.1.0 report (10 flame-only SPICE images, no negatives, no ground truth) with an evaluation on `cv_gold_v1`: a held-out split, negatives, masks, test-level intervals, localized recall, and a before/after comparison of fixes 1–2. Found the T23 small-flame regression.
- **v1.2.0 (2026-10-12):** Initial report from a sample batch.
