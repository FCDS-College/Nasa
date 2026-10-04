# Flame Image Sources for the CV / NN Layers

**Date:** 2026-10-04 · **Purpose:** find enough real microgravity flame imagery to build, train and evaluate the CV pipeline (`cv/contracts/analysis_result.json`, `cv/pipeline.py`) and the PyTorch learning layer (MVP plan §5.7, §5.9, §10).
**Machine-readable inventory:** `datasets/manifests/psi_combustion_file_inventory.csv` (7,514 files, one row per PSI object)

---

## 1. Bottom line

1. **There is far more flame data than we thought, and it is public.** The four P0 combustion investigations on NASA PSI (BASS-II, FLEX, SAFFIRE-I, SPICE) hold **7,514 files and ~1.2 TB**. They are **CC0** (BASS-II verified on its landing page), **none of the files are marked restricted**, and they download **without a login**. The PSI web API hands out a signed S3 link, and this was verified with a ranged download of a BASS-II MP4. This corrects the earlier assumption in `P0_CANDIDATES.md` that these files were not obtainable.
2. **The four screenshots we were sent are good references but poor training data** (§2). We should collect their original, full-resolution frames instead.
3. **NASA's public image library** has only ~22 usable microgravity flame photos. That is enough for a demo and a sanity-check set, not for training.
4. **DSI** (already downloaded) is greyscale solidification imagery. It is useful for testing pipeline plumbing, but **not** for learning flames.
5. **Terrestrial fire datasets** (FLAME, Corsican, D-Fire) can be used for **pre-training only**. They have a strong domain gap and their licences differ (§5).

---

## 2. Assessment of the four supplied screenshots

| # | What it shows | Likely origin (visual match; not confirmed) | Usable for training? |
|---|---|---|---|
| 1 | 6 × 5 time-lapse montage of a flame spreading along a central rod, both sides, growth → extinction | Solid-fuel rod tests (SoFIE-MIST plexiglass rod or BASS-II PMMA rod) | ❌ as-is |
| 2 | 9 × 5 montage of blue cup-shaped flames around a sphere, with green back-lit inserts | **SoFIE-GEL** spherical sample. Matches NASA image `jsc 2024e021222` | ❌ as-is |
| 3 | Fuel in a cylindrical holder with a wavy hot-wire igniter, blue → sooty yellow flame | Solid-fuel ignition test (SoFIE / BASS-type) | ❌ as-is |
| 4 | Same igniter geometry, four stages including a green back-lit frame | Same family as #3 | ❌ as-is |

**Why not as-is:**
- They are browser screenshots of montages, so each tile is only ~60–120 px.
- JPEG re-compression has been applied.
- Overlays (green inserts, a tooltip, an OS notification) cover parts of the image.
- There is no source URL, licence, timestamp or frame rate.

That breaks the provenance rules in `DAY1_DATA_ACQUISITION.md` and MVP §19.

**How to use them:**
- As **qualitative targets**: they show what the UI and segmentation overlays should handle, namely blue low-soot flames, bright sooty flames, igniters, sample holders and back-lit frames.
- As a **checklist of hard cases**. Every one of these needs to be in the evaluation set:
  - dim blue flames on a black background (low-light flag)
  - saturated yellow cores (clipping flag)
  - igniter wire and sample holder occluding the flame (occlusion flag)
  - green back-lit frames that are *not* flames (false-positive test)
  - several flames or tiles in one image (multiple-flames flag)

---

## 3. NASA PSI combustion data (primary training source)

The access route is the PSI API. `GET https://psi.nasa.gov/geode-py/ws/studies/<PSI-ID>/download?file=<file_name>&version=<v>&redirect=false` returns a short-lived signed S3 URL. The full file list comes from `POST https://psi.nasa.gov/geode-py/ws/files/v2` with the body `{"folder":"psi-data/<PSI-ID>/","fileType":"study","studyId":"<PSI-ID>","version":<v>,"obfuscationcode":""}`.

| Source | PSI | Files | Size | Image/video content (verified by reading zip indexes over HTTP) | Built-in labels |
|---|---|---:|---:|---|---|
| **BASS-II** (solid fuels, forced flow) | PSI-25 v4 | 695 | 274.6 GB | **244 test MP4s** + 52 "still sequence" MP4s (17.7 GB) · **109 original-video zips** (`.ts`, 2 camera views, ~400 MB each; 24.3 GB) · **91 zips of Nikon RAW `.NEF` stills** (~13 MB/photo, ~54 per zip; 135 GB) · 127 proof-sheet PDFs | **Experimental table, 129 tests**: fuel material/thickness, flow setting, O₂ % (initial/final), CO₂, CO, frames shot |
| **FLEX** (droplets, suppressants) | PSI-69 v5 | 6,555 | 923.8 GB | **1,420 zips of BMP frame sequences**. The sample zip held 1,466 frames of 640×480 24-bit BMP plus a `.txt` log. Also 228 MP4s (38 GB) and 120 calibration files | Fuel × diluent class in the folder name: MeOH or heptane × CO₂/Xe/He/N₂ (e.g. MeOH-CO₂ 280 zips, heptane-CO₂ 219, MeOH-Xe 204 …) + experimental table |
| **SAFFIRE-I** (large fabric fire, Cygnus) | PSI-98 v4 | 76 | 12.3 GB | 62 zips, e.g. `SAFFIRE_I_F2C2_Mapped_jpeg.zip` = 778 JPEG frames | Experimental table + sensor xlsx |
| **SPICE** (co-flow soot/smoke point) | PSI-107 v4 | 188 | 7.0 GB | 101 zips (PNG downlink frame grabs, Nikon NEF stills, JPEGs), 18 MP4s. The 30 "Earth Gravity" files are **ground calibration sheets** (airflow, fuel flow), **not** 1 g flame images | Experimental tables (27 xls), flight flame-length table |

**Scale.** FLEX alone is plausibly on the order of 10⁶ frames (1,420 sequences × ~1,000+ frames, extrapolated from one sampled zip; *estimate*). BASS-II adds ~244 videos and ~5,000 RAW stills. The bottleneck is **labelling and storage, not data availability**.

**Why it is the right data:**
- It is the actual microgravity flame regime the product is about: spherical/oval, low-soot, dim-blue to sooty-yellow flames.
- Each test is paired with measured experimental conditions.
- It is CC0, with DOIs, so every frame can carry full provenance.

---

## 4. NASA Image and Video Library (demo and sanity set)

The search API at `https://images-api.nasa.gov/search?q=…&media_type=image` ran 20 queries. They returned 1,143 unique items. Filtering on flame terms left 181, and after removing rocket launches, firefighter training, wildfire satellite maps, hardware and crew photos, **about 22 genuine microgravity flame photos** remain:

- **Candle flames:** `9902614`, `9902615`, `GRC-1998-C-00485` (1 g vs µg side by side), `sts050-232-011`
- **Co-flow / soot:** `9902616`, `0100162`, `0100163` (soot plume, greyscale)
- **Flame balls (SOFBALL):** `0100147`, `0100151`, `0100153`
- **Flame spread:** `9902618`, `GRC-1999-C-00840`, `jsc2024e016236`, `jsc2024e016238`, `jsc2024e044215`, `jsc2024e044216`
- **BASS-II:** `iss040e086481`, `iss040e088023`
- **Saffire-IV:** `jsc2023e046375`, `jsc2023e046631`
- **SoFIE GEL / MIST:** `jsc2023e002281`, `jsc 2024e021222`, `jsc2024e053516`, `jsc2024e053517`

**Use:** a small, diverse, high-resolution **held-out demo and sanity set**, plus UI demo images.

**Caveat:** NASA media is generally free to use, but some items are partner images. For example, `jsc2024e016236–38` come from JAXA/Japan drop-tower work. Check each image's rights before redistributing it.

---

## 5. Terrestrial fire datasets (pre-training only)

| Dataset | Content | Labels | Licence / access | Fit |
|---|---|---|---|---|
| [FLAME](https://ieee-dataport.org/comment/1623) (NAU, IEEE DataPort, DOI 10.21227/qad6-r683) | Drone video of prescribed pile burns, RGB + thermal | **2,003 pixel-wise fire masks** | Listed as Open Access; exact licence **not verified** | Segmentation pre-training; aerial wildfire domain |
| Corsican Fire Database ([summary](https://arxiv.org/pdf/2503.14552)) | 500+ visible wildfire images, visible/NIR pairs | Expert pixel masks (~640 pairs) | **Research only; no redistribution or modification**, licence agreement required | Segmentation pre-training; must stay out of any shipped artefact |
| D-Fire ([GitHub, GAIA](https://github.com/wizbeans/FireDataset); [Roboflow mirror](https://universe.roboflow.com/uweeaai/d-fire-ehbj2)) | 21,527 images at 416×416 (fire, smoke, both, none) | 26,557 bounding boxes | Reported as public domain; **confirm on the official repo** | Detection pre-training; the 9,838 "none" images are useful hard negatives |

**Domain gap.** Earth flames are buoyant, flickering and teardrop-shaped. Microgravity flames are spherical or oval, dimmer and bluer, and lie on dark backgrounds. Use these datasets only to initialise weights, then fine-tune and evaluate **only** on PSI microgravity frames. Never report metrics measured on terrestrial data as microgravity performance.

---

## 6. Recommended plan for the CV / NN layers

1. **Pilot download (103 files, 3.13 GB)**, selected in `datasets/manifests/psi_pilot_selection.csv` (each row has a `reason`), downloaded with `knowledge/ingestion/psi_download.py`, and recorded with `record_provenance.py <PSI-ID> <SOURCE_ID> psi_api`:
   - BASS-II: all documents and the experimental table, plus **17 test MP4s** (≤ 80 MB each; the median BASS-II test video is ~42 MB). Up to 2 per fuel family: PMMA rod, film, slab, spherical section, other PMMA, SIBAL and Nomex fabric, wax candle. Initial O₂ spans 13.6–22.2 %.
   - FLEX: documents, the experimental table, and **1 BMP-sequence zip per fuel × diluent class** (8 classes, nearest to 300 MB).
   - SAFFIRE-I: documents, plus the F2C2 camera's raw and mapped JPEG frames.
   - SPICE: documents, flight JPEGs, one downlink frame-grab zip, the flight flame-length table and the ground calibration sheets.

   **Result (2026-10-04):**
   - 100 of 103 files were mirrored to `datasets/raw/psi_api/`. All 100 are recorded in `datasets/metadata/files.jsonl`, sizes match the inventory, SHA-256 verifies, every zip opens, and all 17 MP4s have valid headers.
   - Frame counts: FLEX ≈ 9,200 frames across 8 sequences (BMP and TIFF, depending on camera); SAFFIRE-I 1,556 JPEG frames; SPICE 65 PNG/JPEG frames.
   - Three documents are **unavailable on NASA's side**: BASS-II `Test.Matrices.xlsx` and `ReadMe.docx`, and SAFFIRE `Offgassing Testing Strategy.pdf`. The API returns links to removed legacy objects (S3 404 for every version), so they cannot be downloaded until PSI fixes them.
2. **Frame extraction** into derived storage, never touching the originals:
   - Sample every *k*-th frame per test, so near-duplicate frames don't dominate.
   - Each frame record keeps `parent_file_id`, its frame index or timecode, and the test ID from the experimental table.
3. **Pseudo-labels, then human review:**
   - Flames are self-luminous on dark backgrounds, so a deterministic baseline (luminance/HSV threshold + Otsu + morphology) yields first-pass masks.
   - A person reviews ~200–300 frames across all classes. These become the **gold evaluation set** (MVP §18 IoU/F1).
4. **Splits by test, not by frame.** All frames from one test go into the same split; otherwise near-identical frames leak between train and evaluation. Keep a holdout of whole tests per investigation.
5. **Model:** an ImageNet-pretrained segmentation backbone (optionally warmed up on FLAME/D-Fire), fine-tuned on the PSI frames. The CV contract's quality flags (low light, clipping, occlusion, multiple flames, scale absent, calibration absent) should be predicted or computed and evaluated as well.
6. **Conditions as weak labels:** BASS-II O₂ %, flow and material, and FLEX fuel/diluent class, support later regression/classification heads and the "experiment comparison" feature. Image-derived values must stay labelled *measured in pixels* unless calibration files (FLEX ships 120) are applied.

## 7. What not to do

- Don't train on the montage screenshots or on DSI and call it flame learning.
- Don't mix frames from one test across train and evaluation splits.
- Don't download whole investigations up front: FLEX alone is 924 GB.
- Don't infer temperature from RGB without the calibration path required by the MVP's scientific-integrity rules.
