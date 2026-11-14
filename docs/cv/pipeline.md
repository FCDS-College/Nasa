| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Princess | Draft | 1.9.0 | 2026-11-14 | MVP §10, M4, CV audit CV-2, CV-3 | `cv/flame_cv.py` |

# CV Pipeline Specification (v1.9.0, auto-adaptive)

## 1. Stage diagram

```text
Image -> Validation (validate_image)
      -> Bit-depth conversion + auto-letterbox preprocessing (_to_rgb8, preprocess_image, compute_auto_target_size)
      -> Auto-adaptive segmentation and contour detection (_find_main, Otsu with an optional offset)
      -> Detection decision (PRESENT / UNCERTAIN / ABSENT, section 4)
      -> Geometry and appearance features (_geometry, _appearance)
      -> Confidence and quality flags (ConfidenceAndQualityFlags)
      -> AnalysisResult (+ _write_artifacts)
```

## 2. Validation limits

- Max file size: 10 MB (`max_file_bytes`).
- Max pixels: 100,000,000 (`max_pixels`).
- Minimum dimensions: 64 × 64 pixels (`min_dim`).
- Allowed formats: JPEG, PNG (`allowed_formats`).
- Rejections raise RFC 7807-style `CVError` envelopes (for example `UnsupportedMediaError`, `ImageTooSmallError`).

## 3. Preprocessing and auto-adaptive parameters (`CVConfig`)

- **Bit depth (v1.3.0).** 16-bit greyscale input (Pillow modes `I;16*` and `I`) is scaled linearly to 8 bits over `0 … 2**input_bit_depth − 1`, by default the full 16-bit range. Before v1.3.0, `convert("RGB")` clipped every value above 255 to 255, so a 16-bit frame became a white rectangle: all 45 16-bit FLEX sample frames (`C021H03C`, `C024M06C`, `H14H101C`) were reported as flames at confidence 0.80, although they are sensor dark frames. Set `input_bit_depth` when a sensor's real depth is known (for example 12). Frames are never stretched to their own maximum, because that would turn a dark frame's readout noise into contrast. The result records `preprocessing.sourceBitDepth`.
- **Target size:** computed by `compute_auto_target_size()` unless given.
- **Blur kernel:** proportional to the image size (`compute_auto_blur_kernel()`).
- **Thresholds and contrast:** Otsu with an optional offset; minimum contrast adapts to the background's standard deviation.
- **Config digest:** every parameter contributes to `configDigest`.
- **Camera profiles (v1.6.0).** A request may name a fixed camera with `metadata.cameraProfile` (API form field `camera_profile`). The profile, from [`cv/configs/camera_profiles.json`](../../cv/configs/camera_profiles.json), lists exclusion zones as `[x0, y0, x1, y1]` fractions of the original image: regions of that camera's view that hold static bright hardware, never a flame. A zone is removed from everything the decision looks at: it is blacked out before thresholding, left out of the Otsu threshold, the scene statistics (the lit-scene test, the no-background test) and the background ring. Removing it from the statistics matters: counting the blacked-out pixels would make a lit frame look dark and turn its UNCERTAIN into PRESENT. The result records `preprocessing.cameraProfile` and `preprocessing.excludedRegions`. An unknown profile is `INVALID_REQUEST`. Without a profile nothing changes (checked on all 368 committed sample items). Zones are drawn by people from measured frames, not learned, and each records its evidence and review state.
- **Size floor (v1.7.0).** A profile may also set `minPresentAreaFraction`. A region smaller than that fraction of the image that would be PRESENT is UNCERTAIN instead, with a warning. The result records `preprocessing.minPresentAreaFraction` (null without a floor). For a droplet camera the floor comes from physics: a visible flame encloses its droplet, so a region smaller than a typical droplet is a glint or a flame in its last moments. It demotes rather than drops, because a flame near burnout can be that small (5% of FLEX tests record extinction at a droplet under 0.13 mm).

  | Profile | Zone | Why | Size floor | Why |
  |---|---|---|---|---|
  | `flex-colour` (FF-PSI-69 colour camera, 640 × 480) | the full-width band below 0.82 of the frame height | a static glowing hardware arc at the bottom of the view, PRESENT in 5 dev frames of `cv_gold_v1`. Its median-frame position is x 0.36–0.60, y 0.86–0.98, but the view shifts within a sequence (x 0.02–0.20 in `195F002D_00000`), so the zone spans the whole width. The highest real flame centroid in the dev split is at 0.67 of the height. | 0.1% of the image | the scale, measured on two lit frames with a droplet of known size, is 0.12–0.15 mm/px (`H08M101D_00092`: 3.56 mm over about 29 px; `176F001D_00000`: 3.69 mm over about 25 px). The median initial FLEX droplet, 3.0 mm, is then 20–25 px across, about 0.10% of the frame. Not fitted: every region under it in dev (0.023–0.060%) is a droplet glint or a readout artefact at the top edge, and the one labelled FLEX flame covers 1.73%. |

## 4. Detection decision

The largest bright component (at least `min_area_ratio` = 0.01% of the image) is the candidate. The following terms are used:

- **Contrast:** the mean of the region minus the mean of the background (content outside a dilated ring around the region).
- **Stability:** the IoU of the full binary masks at the threshold ± 10%, compared inside the region's padded bounding box.
- **Score:** 0.5 × contrast/120 + 0.3 × area/0.2% + 0.2 × stability, each term clipped to [0, 1].

| Condition | Status |
|---|---|
| No candidate (nothing above the threshold, or every component is smaller than 0.01% of the image) | `ABSENT` |
| The region is smaller than 0.05% of the image (`small_region_ratio`) and its contrast is below 83 (`small_region_min_contrast`) | `ABSENT`: a speck, not a flame |
| Less than 5% of the image is left as background (`min_background_fraction`) and the image is nearly uniform (under 15 gray levels between the 0.5th and 99.5th percentiles) | `ABSENT` |
| Less than 5% left as background, otherwise | `UNCERTAIN`: contrast is not estimable (`flameContrast: null`) |
| Score ≥ 0.60, contrast ≥ the minimum, stability ≥ 0.5 (`min_present_stability`) | `PRESENT`, unless the region is straight-edged, the scene is lit, or the region is under the camera's size floor (next rows) |
| Would be `PRESENT`, but the region is straight-edged: it fills more than 87.5% of its minimum-area rectangle (`max_present_rectangularity`), judged only when it is at least 20 px across (v1.8.0) | `UNCERTAIN`: a window, panel or backlit sample cell |
| Would be `PRESENT`, but the scene is lit: median gray minus 1st-percentile gray > 11 (`lit_scene_level`) | `UNCERTAIN`: in a lit scene a bright region may be scenery or hardware |
| Would be `PRESENT`, but the region is smaller than the camera profile's `minPresentAreaFraction` (v1.7.0; no floor without a profile) | `UNCERTAIN`: on that camera, a glint or a flame in its last moments |
| Score ≥ 0.60 and contrast ≥ the minimum, but stability < 0.5 | `UNCERTAIN` (warning names the IoU) |
| Contrast ≥ half the minimum | `UNCERTAIN` |
| Otherwise ABSENT, but the scene is dark and a **faint coherent glow** passes (v1.9.0): its largest patch (brightest channel, Gaussian about 3% of the width, > 2 gray levels over the median) covers ≥ 0.15% of the image and stands ≥ 7 noise units above a ring around it | `UNCERTAIN` with `qualityFlags.dimGlow`, confidence ≤ 0.5, the glow as the mask: possibly a dim flame |
| Otherwise | `ABSENT` |

**Confidence** is the score for `PRESENT` and `UNCERTAIN`. For `ABSENT` it is `1 − score`, capped at `absent_confidence_cap` (0.9). With no candidate, the score is the contrast term of the brightest content left in the image (99.5th percentile minus median), so a black frame gives 0.9 and a cluttered one less. No confidence is a fixed constant. None of these values is a calibrated probability (`confidenceBasis: heuristic_uncalibrated`).

**Classification:** `MEASURED` when geometry was measured, otherwise `INFERRED`.

Why these values (measured on every committed sample image and the three BASS-II videos; see `.internal/research/2026-11-13-cv-audit.md`, finding CV-2):

- **Small regions need contrast ≥ 83:** chosen on the dev split of `cv_gold_v1` only. Specks under 0.05% of the frame in dev frames reach contrast 61.6 at most; real dev flames start at 104.9; 83 is the midpoint. v1.3.0 used a 0.05% minimum region instead, which kept the specks out but also missed real small flames: 5 of 9 flame frames of the held-out test T23 (0.019–0.049% of the frame, contrast 100–128). See [evaluation-report.md](evaluation-report.md).
- **0.5 minimum stability:** the lowest real SPICE flame scores 0.86.
- **Stability measured locally:** comparing only the largest component scored a real two-lobed BASS-II flame (`TEST_B1` frame 630) at 0, because the lobes swapped places as the largest.
- **Quality flags do not demote a detection:** `saturationClipping` is set on 100% of the real SPICE flames.
- **Straight-edged regions are never PRESENT (v1.8.0):** flames are rounded; a filled ellipse fills π/4 = 0.785 of its minimum-area rectangle. On the dev split and every committed sample, real flames reach 0.844 (`ISS018E030372`) and the DECLIC DSI backlit sample cell starts at 0.903; 0.875 is the midpoint. Rectangularity is judged only from 20 px across (equivalent diameter on the analysed canvas): over 200 random digitised ellipses per size, a 6 px one can reach 0.958, a 10 px one 0.847, and from 20 px up none exceeds 0.828. That keeps tiny flames (the held-out T23 flames are 0.02–0.05% of the frame) out of the rule. When several demotion rules apply, each adds its own warning.
- **Faint glows are UNCERTAIN, never PRESENT (v1.9.0):** dim blue flames (BASS-II PMMA at low flow) are 4–8 gray levels per pixel, the same as compression noise, so the brightness detector cannot see them. What sets them apart is coherence: one connected patch after heavy smoothing. Chosen on the dev split only (BASS-II M16 and M19, added for this): dim flames cover 0.20–1.05% of the frame at 7.4–16 noise units; FLEX 16-bit dark frames form patches up to 1.9% but at most 1.1 noise units (a smooth sensor gradient); the flame-free frame before ignition peaks at 0.06%. Reported UNCERTAIN, not PRESENT, because a faint glow can also be dim scenery. In video, a glow that does not move is rejected as scenery ([video-ingestion.md §5a](video-ingestion.md)).
- **Lit scenes are never PRESENT (v1.5.0):** the detector assumes a dark background, because luminous flames are filmed in dark chambers. Lighting is measured as the median gray minus the 1st-percentile gray, so a sensor's constant black level does not count as light (a first version used the median alone, which would have called a 12-bit sensor's pedestal "lit"). Chosen on the dev split of `cv_gold_v1` only: dev flame frames reach 4 at most; lit scenery false positives (the `TEST_T25` cabin view, lit FLEX hardware) start at 19; 11 is the midpoint.

## 5. Cache reuse (M4)

- Cache key: input checksum + `PIPELINE_VERSION` + `PREPROCESS_VERSION` + `SEGMENTER_VERSION` + `configDigest` + options + `mmPerPixel`.
- Results are invalidated automatically when any version or configuration value changes.

## 6. Artifacts

Masks and overlays are written to the artifact directories with SHA-256 checksums (`maskUri`, `overlayArtifactUri`).

## Command-line entry point

`python -m cv.flame_cv [image] [--out-dir cv/output]` runs `analyze_image_safe` on an image (or a generated synthetic flame when omitted), writes `analysis_result.json` and `masks/` under the output directory, prints the result JSON, and exits 1 when the result is an error response. See [offline-operation.md](offline-operation.md) for offline use.

## Known limitations and failure modes

- Detection is brightness-based. **Lit scenery** (cabin views, a lit chamber) is UNCERTAIN since v1.5.0, but **bright hardware in a dark scene is still reported as a flame** unless a camera profile excludes it. Measured on the dev split, the hardware's elongation, circularity, saturation and hue overlap with real flames', so no single-image shape or colour rule separates them; only its fixed position in a known camera's view does.
  - The FLEX colour arc is excluded by the `flex-colour` profile (v1.6.0). That fixed 2 of its 5 dev false positives. The other 3 were glints: specular reflections on the droplet (`H08M101D_00642`, `_01284`; H08M101 is a methanol test whose flame went out at 0.3 s) and a readout artefact at the top edge of a sequence's first frame (`195F002D_00000`). v1.7.0's size floor reports them UNCERTAIN. Their colour does not separate them: the sensor fringes a point source, so a glint is not neutral white (white-clipped fraction 0–0.011, chroma 0.26–0.48).
  - The floor costs recall where a FLEX flame is smaller than 0.1% of the frame, near burnout. It demotes such a flame to UNCERTAIN, never to ABSENT. No such labelled frame exists, so the cost is not measured. In `176F001D` (methanol, burning for 29.1 s) a faint flame shell may surround the droplet glint in the frames the floor demotes, but the pipeline segmented only the glint there, never the shell.
  - The profile is applied only when the client names it. A FLEX colour upload without `camera_profile` keeps the arc false positive.
  - A real flame inside an exclusion zone is not seen. For `flex-colour` no dev flame is there, but the zone is fitted to the dev split. The holdout has no FLEX frames, so it is not validated on held-out data.
- A real flame with straight sides is reported UNCERTAIN: for example one cut off on two opposite sides by the frame, or burning along a rectangular sample (SAFFIRE). No committed flame scores above 0.844, but a SAFFIRE flame spreading over the whole width of its sample could; no such frame is labelled, so this cost is not measured.
- Dim flames are at best UNCERTAIN, and the faint-glow pass found **none** of the 9 held-out M10 dim flame frames (scored once; it did find one held-out B3 frame). It works on the two dev tests it was built from (7 of 7, in-sample). Why it fails on M10 is not investigated, because looking at M10 would spend the holdout.
- A real flame filmed in a lit scene is reported UNCERTAIN, not PRESENT. No such frame is in `cv_gold_v1`, so this recall cost is not measured.
- The thresholds were chosen on the committed samples and the dev split of `cv_gold_v1`. Their held-out performance is in [evaluation-report.md](evaluation-report.md), measured against labels that are not yet verified by a person.
- A small flame with contrast below 83 is treated as a speck. Dev data has no small flames, so the 83 cut-off is set from the specks and from larger flames only.
- 16-bit input from a sensor with fewer real bits appears dark unless `input_bit_depth` is set; dim flames in such data can be missed.
- Spatial measurements are 2D projections unless calibrated with `mmPerPixel`.

## Changelog
- **v1.9.0 (2026-11-14):** Faint-glow pass: in a dark frame where the brightness detector finds nothing, a faint coherent glow is UNCERTAIN (`dimGlow`), never PRESENT. Tuned on dev only (M16/M19 added for it). Dev: 7 of 7 dim flames UNCERTAIN, lenient recall 0.76 → 1.00, strict unchanged. Holdout (scored once): M10 still missed (0 of 9); one B3 frame found; lenient recall 0.756 → 0.780, no new held-out false positive. No committed image sample triggers it. Result schema 1.6.0 (`qualityFlags.dimGlow`).
- **v1.8.0 (2026-11-14):** A straight-edged region (rectangularity > 0.875, at least 20 px across) is UNCERTAIN, not PRESENT; tuned on dev and the committed samples only. Removes the DSI backlit-cell false positives: dev false positives 2 → 0, holdout unchanged (no held-out frame affected). Of the 182 committed image samples, only the 6 DSI backlit-cell frames change. Each demotion rule now gives its own warning when several apply.
- **v1.7.0 (2026-11-14):** Camera profiles may set a size floor (`minPresentAreaFraction`); `flex-colour` sets 0.1%, from droplet physics and the measured scale. A smaller region is UNCERTAIN, not PRESENT. Dev false positives 5 → 2 (FPR 0.11 → 0.05, precision 0.75 → 0.88), no flame lost; holdout unchanged (no FLEX frames). Result schema 1.5.0. Segmenter version 1.7.0: v1.6.0 had left it at 1.5.0.
- **v1.6.0 (2026-11-14):** Camera profiles: per-camera exclusion zones for static hardware, selected per request (`metadata.cameraProfile`, API `camera_profile`). First profile `flex-colour`. Dev false positives 7 → 5 (FPR 0.16 → 0.11, precision 0.68 → 0.75) with no flame lost. Holdout unchanged (it has no FLEX frames). No change without a profile.
- **v1.5.0 (2026-11-14):** In a lit scene a detection is UNCERTAIN, never PRESENT (cut-off tuned on dev only). Held-out false-positive rate 0.30 → 0.00, with no held-out flame lost.
- **v1.4.0 (2026-11-13):** Minimum region back to 0.01%; regions under 0.05% are specks unless their contrast is ≥ 83 (tuned on dev only). Fixes the v1.3.0 regression on small flames. No status changed on any committed sample.

- **v1.3.0 (2026-11-13):** 16-bit input is scaled instead of clipped; a region with no background is never `PRESENT`; `PRESENT` requires region-local stability ≥ 0.5; minimum region 0.05% of the image; `ABSENT` confidence is computed; classification follows what was measured (section 4). Fixed this page's unclosed code block.
- **Unreleased (2026-10-14):** Documented the CLI entry point.
- **v1.2.0 (2026-10-12):** Upgraded to auto-adaptive target sizes, dynamic blur kernels and statistical contrast thresholds.
- **v1.1.0:** Initial Otsu/contour baseline.
