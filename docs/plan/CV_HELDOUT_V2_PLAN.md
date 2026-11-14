# CV held-out cohort 2: dim flames and FLEX — plan

| Owner | Status | Created | Depends on |
|---|---|---|---|
| Princess (CV) with Lead (Anas) | Proposed: decisions D1–D4 open | 2026-11-14 | CV pipeline `cv-opencv-v1.9.0-auto`, `cv-video-v1.2.0`; `cv_gold_v1` ([evaluation report](../cv/evaluation-report.md)) |

## 1. Goal

Close the two gaps the 2026-11-14 summary left open, with numbers nobody tuned on:

1. **Dim flames.** The faint-glow pass (v1.9.0) finds all 7 dim flame frames in the dev tests it was built from (M16, M19), but **0 of 9** in the held-out test M10. Work out whether that is a real limit, a threshold fitted too tightly to two tests, or something specific to M10. Then improve it.
2. **FLEX.** The `flex-colour` profile (arc exclusion zone, v1.6.0; size floor, v1.7.0) is measured only on the 5 FLEX colour sequences of the dev split. The holdout has no FLEX frames. Measure it on sequences it has never seen, including other campaigns where the camera set-up may differ.

## 2. Why a new held-out cohort

- **M10 can't be studied without spending the current holdout.** Looking at its frames to find out why the glow pass misses them would make every later M10 score in-sample.
- **FLEX has no held-out frames at all.**

So both need a **fresh held-out cohort**: tests never viewed, selected by a rule written down before any frame is opened, scored once with the pipeline frozen. Only after that cohort has been scored can M10 move to the dev split for diagnosis, disclosed as such.

## 3. Rules for every step (pre-registration)

1. **Select from metadata only.** Test IDs come from the experimental tables and the PSI inventory, using the rules in §4.1 and §5.1 with a fixed random seed. No frame of a candidate test is opened before it is labelled.
2. **Freeze the pipeline.** Cohort 2 is first scored with the pipeline as it is on `main` at selection time (v1.9.0), with no threshold changes. That number is the baseline and is reported whatever it is.
3. **A person verifies the labels before scoring.** Every cv_gold_v1 label so far is Claude-drafted and unverified. For cohort 2, Claude drafts labels and masks, and a person checks every item with the existing review sheet and `adopt` step before the cohort is scored. Unverified cohort-2 items are not scored.
4. **One score per release.** A change tuned after the baseline is scored on cohort 2 once, when it ships, never repeatedly while tuning. Tuning uses dev, including M10 once it moves there (§4.4).
5. **Report everything.** Every number goes in the evaluation report with its test-level 95% interval and the list of items that changed. That includes the baseline, failures, and any label change made after a score was seen.

## 4. Workstream A: dim flames

### 4.1 Select the dim-flame cohort (A1)

- **Pool:** BASS-II Miller PMMA flame-spread tests not used anywhere: M1, M2, M4–M9, M11–M14, M17, M18, M20 (15 tests; M3 and M15 are not on PSI). Main-view videos only, 60–212 MB each.
- **Rule:** stratify by test day (GMT 51: M1, M2, M5, M14; 192: M7, M8, M9, M11; 196: M17, M18; 212: M4, M6, M12, M13; 213: M20) and draw **6 tests** with `random.Random(20261114)`, at least one per day where available. Same-day tests share the flow schedule, so stratifying stops the cohort from being six copies of one condition.
- **Sampling:** the served grid, 10 frames per video, with `sampling.maxDurationS` for videos over 600 s, as for M16 and M19.
- **Expected size:** 60 frames. Judging by M16 and M19, about 15–25 of them will be dim-phase frames.
- **Download:** about 0.8 GB, SHA-256 checked through `python -m cv.gold fetch`.

### 4.2 Label (A2)

- Same protocol as M16/M19 ([annotation protocol](../cv/annotation-protocol.md)): ×8–×12 contrast-stretched views, `grabcut-from-box` masks for visible flames and `coherent-blue-patch` masks for dim ones.
- `unclear` where a trace is at noise level.
- **Defined before labelling:** a frame is `present` if a coherent blue patch at least 2× the largest patch in that test's pre-ignition frame lies on the flame's track. This is the same criterion as M16/M19, written down now so it cannot drift.
- A person verifies all items (rule 3).

### 4.3 Score the baseline (A3)

- **Command:** `python -m cv.gold evaluate`, with cohort-2 items reported as their own block (§6).
- **Pre-registered success criterion for v1.9.0:** lenient recall on cohort-2 dim frames at least 0.5, with no new false positive on its absent frames. If it falls below that, the M16/M19 thresholds are fitted too tightly. That is a finding, not a failure to hide.

### 4.4 Diagnose, using M10 (A4)

- **Only after A3:** move M10 from holdout to dev, disclosed in the report as "seen after cohort 2 was scored".
- **Measure on M10, M16, M19 and the cohort-2 tests together** (all dev by then, except the cohort itself): glow area, local contrast, colour and the ring noise.
- **Likely causes to test, each with a measurement:**
  - a different camera gain (M10's radiometer gain changes 250 → 50 → 250);
  - a different video encode for the LOS clip (M10's source is a 10.8 MB LOS portion, M16/M19 full videos);
  - a dimmer flame than the 2-gray-level floor.
- **Possible changes:** a noise-adaptive level instead of the fixed 2 gray levels; a temporal stack (sum the glow over neighbouring frames, which video allows); a blue-dominance condition. Each is tuned on dev only.

### 4.5 Ship and re-score (A5)

- One release (v1.10.0) with whatever A4 supports, scored once on cohort 2 and once on the original holdout without M10.
- If nothing in A4 helps, the report gives the faintest cohort-2 dim flame that was found and the brightest that was missed, in noise units, as the limit of a brightness method. This is a valid outcome.

## 5. Workstream B: FLEX

### 5.1 Select the FLEX cohort (B1)

- **Pool:** the 247 FLEX colour sequences (`…D.zip`, PSI-69) that match a row of the FLEX experimental table, minus the 5 already in dev.
  - By fuel: 141 methanol, 106 heptane.
  - By ID series: numeric (FLEX-1), C, H, N, which may correspond to campaigns with different camera set-ups.
- **Rule:** stratify by ID series × fuel and draw **12 sequences** with `random.Random(20261114)`, proportionally, with at least one per non-empty stratum.
- **Download:** each zip is about 340 MB, so about 4 GB in total. Only the sampled frames are extracted and kept: 15 per sequence, the same spacing as the committed samples.
- **Expected size:** 180 frames, mostly absent (lights off before ignition, dark after extinction). That suits a false-positive test.
- **Recorded per sequence before labelling:** the date and campaign from the table, the fuel, the initial droplet diameter, the burn time and how the test ended. Burn time and test end tell whether a frame is during or after the flame, as for H08M101 (methanol, out at 0.3 s).

### 5.2 Check the profile's assumptions on each sequence (B2)

The profile rests on two measured facts. B2 measures both on every cohort sequence, from frames the labeller looks at anyway:

- **Arc position:** the hardware arc sat below 0.82 of the frame height in all 5 dev sequences. Measure where it is in each cohort sequence from the per-sequence median frame.
- **Scale:** 0.12–0.15 mm/px from two lit frames with a droplet of known size. Measure it in each cohort sequence from its lit frame and the table's initial droplet diameter. The size floor (0.1% of the frame) assumes that scale.

These are measurements of the camera, not tuning. They are recorded before scoring and used to explain the scores, not to change thresholds before A3/B3.

### 5.3 Label and score the baseline (B3)

- **Label:** same protocol, with a person verifying every item (rule 3).
- **Score:** v1.9.0 with the `flex-colour` profile, once, with and without the profile.
- **Pre-registered success criteria:**
  - strict false-positive rate on cohort-2 FLEX absent frames: upper end of the 95% interval at most 0.10;
  - no labelled flame lost to the zone or the floor (each demotion listed).
- If a campaign's arc or scale differs (B2), its frames are reported separately, and a failure there is expected rather than surprising.

### 5.4 Respond (B4)

- **If the arc or scale differs by campaign:** split `flex-colour` into per-campaign profiles (for example `flex-colour-flex1` and `flex-colour-flex2`), each with its measured zone and floor. Only metadata the client already has (the test ID) picks the profile.
- **If the floor costs flames** (end-of-burn flames under 0.1%): consider a per-test floor from the table's droplet diameter, or keep demoting with the cost documented.
- **Ship and score:** one release, scored once on cohort 2.

## 6. Tooling changes (T)

| ID | Change | Where |
|---|---|---|
| T1 | `cohort` field on items (`v1`, `v2-dim`, `v2-flex`); reports break metrics out per cohort as well as per split | `cv/gold.py`, `datasets/evaluation/cv_gold_v1.schema.json`, `cv_gold_v1_sources.json` |
| T2 | FLEX zip sources: extract only the sampled frames from a downloaded zip (as images, with `cameraProfile`) | `cv/gold.py` (`fetch`, `extract_frames`) |
| T3 | A `select` command that writes the cohort from metadata with the fixed seed, so the selection is reproducible and reviewable before any download | `cv/gold.py` |
| T4 | Unverified items excluded from cohort-2 scoring (rule 3), with a count of how many are excluded | `cv/gold.py` (`evaluate`) |

## 7. Order and effort

| Step | Depends on | Effort | Blocks on a person |
|---|---|---|---|
| T1–T4 tooling | — | 1 session | no |
| A1 + B1 selection (metadata only, committed before download) | T3 | small | no |
| Downloads (about 0.8 + 4 GB) and frame extraction | A1, B1, T2 | small | no |
| A2 + B2/B3 draft labels and masks (about 240 frames), B2 measurements | downloads | 1–2 sessions | no |
| **Verification of all cohort-2 labels** | drafts | **about 2 hours of a person's time** | **yes** |
| A3 + B3 baseline scores (once) | verification | small | no |
| A4 M10 diagnosis, B4 response (dev only) | A3, B3 | 1–2 sessions | no |
| A5 / B4 release, scored once | A4, B4 | 1 session | no |

## 8. Decisions needed

- **D1 Who verifies cohort-2 labels?** Rule 3 needs a named person. Without one, cohort 2 is scored as "Claude-drafted, unverified", like cohort 1, and the plan says so.
- **D2 Download and storage budget:** about 5 GB of raw data in the working area. Only extracted frames and masks are committed (a few MB); the raw files stay out of Git like the current holdout.
- **D3 Retire M10 from the holdout after A3?** Recommended: it is the only way to diagnose it. The original holdout keeps 7 tests and its earlier scores stay in the report.
- **D4 Cohort sizes:** 6 dim-flame tests and 12 FLEX sequences are a balance between interval width and labelling time. More tests narrow the intervals (they are test-level), at roughly 10–15 minutes of verification each.

## 9. Known limitations

- **Small cohort-2 intervals stay wide:** with 6 and 12 tests, one test moves every number.
- **The dim-flame cohort shares hardware and flow schedules** with the dev tests M16 and M19 (same apparatus, same campaign). It tests generalisation across tests, not across apparatus. A dim flame from a different experiment would be a stronger test, and none is in scope here.
- **Selection by metadata cannot guarantee dim phases:** some drawn M tests may have little or no dim phase. The cohort then has fewer dim frames than expected, and the report gives the count.
- **This plan does not verify cohort 1.** The existing 170 cv_gold_v1 items stay unverified unless a person reviews them too. D1 could cover both.

## Changelog

- 2026-11-14: Proposed.
