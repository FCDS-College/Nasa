# DSI Dataset Report — Directional Solidification on the ISS (NASA PSI)

**Source ID:** `FF-PSI-DSI` · **Priority:** P2 (reference, non-combustion) · **Report date:** 2026-10-04
**Canonical location:** `s3://nasa-psi/DSI/` (public, anonymous access, `us-west-2`)
**Local mirror:** `datasets/raw/nasa_psi/DSI/` (git-ignored) · **Provenance:** `datasets/metadata/files.jsonl`, `datasets/checksums/sha256.txt`

---

## 1. Summary

| Question | Answer |
|---|---|
| What is it? | ISS flight data from **DECLIC-DSI**: directional solidification of a transparent **succinonitrile–0.24 wt% camphor** alloy, filmed in situ to study how cellular/dendritic solid–liquid interface patterns form without convection. |
| Is it combustion data? | **No.** It contains no flames, fuels, oxygen, extinction or soot measurements. It does **not** satisfy any P0 data need of Flame in Freefall. |
| Full size in the bucket | 121,811 objects · **164.97 GB** (of which ~43 GB are `.zip` duplicates of the unzipped folders) |
| Mirrored locally | **21 files · 3.10 GB**: all documentation + 4 flight plans + one complete run (`S1 activity 4.zip`) |
| Integrity | 21/21 sizes match the S3 listing · 21/21 SHA-256 verified · zip `testzip()` clean |
| Licence / access | Public PSI open data, no AWS account needed (`--no-sign-request`) |
| Best use for this project | (1) A real microgravity image set to **exercise the CV pipeline** (segmentation, geometry, quality flags, provenance) before flame images arrive; (2) a small **RAG test corpus** on microgravity/convection-free physics; (3) a dry run of the **ingestion + provenance contract**. |

**Verdict:** the data is complete, well-structured and verified, but it is the *wrong science domain* for the MVP. Treat it as infrastructure test data, not as evidence for flame-behaviour answers.

---

## 2. The experiment

| Field | Value | Source |
|---|---|---|
| Full title | Dynamical Selection of Three-Dimensional Interfacial Patterns in Directional Solidification (DSIP / DSI) | SRD, taskbook |
| Principal Investigator | Prof. Rohit Trivedi, Iowa State University (Dept. Materials Science & Engineering) | taskbook 2001–2013 |
| Co-Investigator | Prof. Alain Karma, Northeastern University (phase-field modelling) | taskbook |
| CNES partner | Dr. Bernard Billia — PI of the CNES side of DECLIC | taskbook 2008 |
| Facility | **DECLIC** (DEvice for the study of Critical LIquids and Crystallization), a CNES-built multi-user facility on the ISS; DSI = Directional Solidification Insert | DoD, taskbook 2013 |
| NASA programme | Physical Sciences → Materials Science; flight project; solicitation 98-HEDS-05; grants NAG8-1681 → NNX07AK69G; monitored by NASA MSFC | taskbook |
| Alloy | Succinonitrile (SCN) – 0.24 wt% camphor (transparent, so the interface can be imaged in situ) | taskbook 2012–2013 |
| Sample | Pyrex ampoule, 10 mm inner diameter, ≥150 mm long, ~100 mm processing length (requirement) | SRD §7.2–7.3 |
| Flight campaign | First activity 2010-04-26; last planned run ends 2011-01-19 | flight plans |
| Runs | "29 experiments over 100 days" (FY2012 report) / "39 experiments … two thermal gradients and several growth rates" (FY2013 report) — **the two reports disagree** | taskbook |

**Scientific goal.** On Earth, buoyancy-driven convection distorts the solidification front (cell spacing shrinks towards the wall; the front goes planar at the edge). In microgravity, growth is purely diffusive, so the 3-D arrangement of cells and dendrites can be measured as a clean benchmark for phase-field models used in casting and welding.

**Key results reported (FY2012–2013 taskbook).**
- No convection effects were seen, and the microstructure was uniform across the whole cross-section. All hardware (translation stage, thermal profile, optical and interferometric imaging) worked.
- Primary cell spacing decreases **continuously** with velocity through the cell-to-dendrite transition, unlike thin 1-g samples.
- The final arrays are roughly hexagonal with disorder. Mixed hexagonal/square regions are linked to a small-angle grain boundary in the seed.
- These were the first observations of **3-D multiplets**, where cells split into sub-cells.
- A new **oscillatory mode** appeared at V = 1.0 µm/s: three groups of three cells oscillate 120° out of phase with a period of about 45 min. GPU phase-field simulations reproduced it with a period of about 49 min.

**Design requirements (SRD, 2003 draft).**
- Axial thermal gradient of 1–5 K/mm, preferably up to 7 K/mm.
- Pulling rate of 0.1–100 µm/s, controlled within ±0.1 µm/s.
- Hot zone at 50–120 °C and cold zone at −20 to 50 °C, both stable to ±0.03 °C.
- Two digital cameras at 670 nm:
  - **Top (axial) view:** 10 mm wide field plus a 3 mm microscopy mode, resolving about 3 µm.
  - **Side view:** 10 mm field, resolving about 8 µm.
- Laser interferometry to reconstruct tip shapes in 3-D.

> ⚠️ The SRD is a **2003 draft** that names SCN-water as the selected alloy. The later taskbook reports state that SCN-camphor was chosen for flight because the other systems had problems for space use. Trust the taskbook for the flight alloy.

---

## 3. What is in the bucket

```
s3://nasa-psi/DSI/
├── DECLIC-DSI DoD.docx                  data-organisation note (how PSI groups the activities)
├── SRD/Final_SRD_1_101203.{pdf,doc}     Science Requirements Document (156 pages)
├── Taskbook Downloads/  (13 PDFs)       NASA Task Book annual reports FY2001–FY2013 (no FY2009)
└── Data/
    ├── DSI-{INIT,S1,S2,HD} Solidification Plan.xlsx   flight command plans (EN + FR sheets)
    ├── <activity>.zip   × 8             zipped originals, one per activity (≈43 GB)
    └── <activity>/      × 8             unzipped copies + JPG previews (≈122 GB)
```

### Activity inventory (unzipped folders)

Sequence numbers come from the file names: `SEQ1`=INIT, `SEQ2`=S1, `SEQ3`=S2, `SEQ5`=HD. There is no SEQ4 in the bucket.

| Activity | Seq | Files | Size | BMP | JPG | Camera subfolders | Science `.dat` |
|---|---|---:|---:|---:|---:|---|---:|
| INIT activity 4 | SEQ1 | 41,491 | 41.01 GB | 20,725 | 20,725 | HR1 + HR2_1…HR2_9 | 4 |
| S1 activity 1 | SEQ2 | 15,967 | 19.25 GB | 10,628 | 5,314 | HR1, HR2_1–3 (+ a duplicate "extracted by cbp" folder) | 6 |
| S1 activity 2 | SEQ2 | 9,484 | 8.80 GB | 4,734 | 4,734 | HR1, HR2_1–3 | 3 |
| S1 activity 3 | SEQ2 | 9,080 | 7.91 GB | 4,402 | 4,663 | HR1, HR2_1–2 | 3 |
| **S1 activity 4** ✅ mirrored | SEQ2 | 8,073 | 8.11 GB | 4,027 | 4,027 | HR1, HR2_1–2 | 5 |
| S2 activity 4 | SEQ3 | 9,563 | 9.39 GB | 4,773 | 4,773 | HR1, HR2_1–3 | 4 |
| S2 activity 11 | SEQ3 | 12,018 | 11.51 GB | 5,999 | 5,999 | HR1, HR2_1–3 | 6 |
| HD activity 9 | SEQ5 | 16,107 | 16.28 GB | 8,037 | 8,037 | HR1, HR2_1–4 | 18 |

- Every activity also exists as a single `.zip` (2.9–15.7 GB). The zip holds the **original BMPs + `.dat` only**. The unzipped folders add one **JPG preview per BMP** plus housekeeping files (`Thumbs.db`, `.txt`, `.xlsx`). Mirror **either** the zip **or** the folder, never both.
- All objects were uploaded to S3 on 2023-02-01/02. The flight data dates from 2010–2011.

---

## 4. Experimental conditions per activity (from the flight plans)

The values come from the English sheets of the four `*Solidification Plan.xlsx` files. Dates are converted from Excel serial dates and are the **planned command times (UTC assumed)**. Pulling speeds are converted from mm/s to µm/s. For every activity, speed × duration matches the commanded travel (`Z_mlt_fin − Z_sol_fin`), which cross-checks the table.

| Activity | Solidification start (planned) | Pulling velocity V | Travel (mm) | Duration | Image rate HR2 | Planned images |
|---|---|---|---|---|---|---:|
| INIT 4 | 2010-04-27 13:49 | 1.0 µm/s | 69 → 9 (60) | 16.6 h | 0.35 img/s | 20,202 |
| S1 1 | 2010-05-26 10:05 | 6 µm/s | 69 → 9 (60) | 2.8 h | 3 img/s | 5,040 |
| S1 2 | 2010-05-27 12:23 | 12 µm/s | 69 → 9 (60) | 1.4 h | 6 img/s | 4,520 |
| S1 3 | 2010-05-28 13:52 | 16 µm/s | 69 → 9 (60) | 1.0 h | 8 img/s | 4,272 |
| **S1 4** | **2010-05-29 14:10** | **0.5 µm/s** | **69 → 29 (40)** | **22.2 h** | **0.25 img/s** | **3,798** |
| S2 4 | 2010-10-10 01:01 | 1.0 µm/s | 72 → 30 (42) | 11.7 h | 0.5 img/s | 4,310 |
| S2 11 | 2010-10-16 21:23 | 0.5 µm/s | 72 → 12.5 (59.5) | 33.1 h | 0.25 img/s | 5,690 |
| HD 9 | 2011-01-18 08:11 | **0.35 → 0.75 µm/s** (velocity jump at Z = 43 mm) | 73 → 13 (60) | 34.9 h | 0.175 / 0.375 img/s | 7,695 |

**Common protocol for each run.**
1. **Partial melt** (`DSI1_MLT`) at 30 µm/s (15 µm/s in S2-4) to Z ≈ 69–73 mm.
2. **Homogenisation** (`DSI1_HOM`) for 21–29 h, imaging every 15 min.
3. **Directional solidification** (`DSI1_SOL`, or `DSI1_SOL_VV` for a velocity change).

**Furnace set-points** (thermalisation `DSI1_TRM_ON`): HZ1 = 85 °C, HZ2 = 89 °C, HZ3 = 90–93 °C, Peltier cold zone = 20 °C. The plans give **no thermal-gradient value**. The taskbook only says "two different thermal gradient values".

**Coverage:** velocities of 0.35–16 µm/s, which spans cellular through dendritic growth. This includes steady runs and one velocity-jump run (HD 9).

---

## 5. File formats (verified on the mirrored run)

### 5.1 Images: `DA_TC_DSI_SEQ<n>_ACTIVITE<nn>_HR{1,2}[_k].zip`
- Each image is a **BMP, 1024 × 1024, 8-bit greyscale (palettised)** of 1,049,654 bytes. The JPG copies in the unzipped folders are derived previews.
- Name pattern: `DSI_SEQ2_ACTIVITE04_HR1_<SL2 counter>_<n>.bmp`. The number is the on-board **SL2 time counter**, not a Unix time.
- In the plans, the SL2 counter rises at about **23 counts per second** of plan time. This is an *estimate* from the plan's SL2 and date columns and should be confirmed before precise timing work.
- There are two image streams, **HR1** and **HR2**:
  - The plans give a ratio `R_hr2axial_hr1` (7–25 HR2 frames per HR1 frame) and set the HR2 frame rate (`f_acq_hr2`).
  - The SRD specifies a top (axial) camera and a side camera.
  - The exact mapping of HR1/HR2 to the physical cameras is **not documented in the mirrored files**. Confirm it with the PSI record before labelling views.
- **No pixel-size or scale calibration** is embedded in the images. Spatial measurements stay in **pixels** unless a scale is taken from DECLIC documentation. This matches the CV contract's `scaleAbsent` and `calibrationAbsent` flags.

### 5.2 Science telemetry: `DA_TC_DSI_SEQ<n>_ACTIVITE<nn>_SCIENCE.zip` → `*.dat`
- These are tab-separated text files with CRLF line endings. The name gives the SL2 range covered: `…_SCIENCE_<SL2 start>_<SL2 end>.dat`.
- Header:
  ```
  SL2_COUNTER_VALUE  MOTORPOSITION  AZ_CURRENT  T_HZ1  T_HZ2  T_HZ3  T_HZ3_RED  T_PEL
  ```
- Rows **alternate between two record types that share the same SL2 value**:
  - Thermal rows have empty motor columns and carry `T_HZ1, T_HZ2, T_HZ3, T_HZ3_RED, T_PEL` in °C.
  - Motor rows carry `MOTORPOSITION` in mm and `AZ_CURRENT`.
- A new pair arrives every 24 SL2 counts (about 1 s).
- Example: `1019560105 | — | — | 84.99998 | 88.99998 | 89.99998 | 44.84086 | 20.00109`, followed by `1019560105 | 69.0 | 0.0527`.
- Parsing needs: split by record type, join on SL2, and treat empty fields as **null, not 0**, as `DATA_DICTIONARY.md` requires.

### 5.3 Flight plans: `DSI-*-Solidification Plan.xlsx`
- Bilingual: `English` and `French`/`Feuil1` sheets with identical numbers, plus an empty `Feuil3`.
- This is a semi-structured layout. A step row (step id, description, script/TC name, chaining flag, wait, shipped date, SL2, duration, estimated image count, end date, SL2) is followed by indented parameter rows (`name (unit) | value`).
- Dates are **Excel serial numbers**, and some values carry float noise (e.g. `6.0000000000000001E-3`).

### 5.4 Documents
| File | Pages | Text layer | Notes |
|---|---:|---|---|
| `SRD/Final_SRD_1_101203.pdf` | 156 | yes | 2003 draft. Some symbols (µ, ±) extract as private-use glyphs. |
| `SRD/Final_SRD_1_101203.doc` | — | binary Word 97 | Same document as the PDF. |
| `Taskbook Downloads/*.pdf` × 13 | 2–3 each | yes | FY2001–2008 and 2010–2013. FY2006 appears twice under two grant labels. FY2009 is missing. |
| `DECLIC-DSI DoD.docx` | 1 | yes | Explains the PSI web layout (Raw Data → `.dat`, Images → gallery + zip). |

---

## 6. Deep dive: the mirrored run `S1 activity 4.zip`

| Item | Value |
|---|---|
| Archive | 3,076,946,537 bytes, stored (uncompressed) zip, `testzip()` OK |
| Contents | `HR1.zip` (261 BMP, 122 MB) · `HR2_1.zip` (1,951 BMP, 1.51 GB) · `HR2_2.zip` (1,815 BMP, 1.44 GB) · `SCIENCE.zip` (5 `.dat`, 21.9 MB unpacked) |
| Total frames | **4,027 BMP** (plan estimated 3,798) |
| Conditions | V = 0.5 µm/s, 40 mm solidified, ~22 h solidification after 22.25 h homogenisation |
| Telemetry span | SL2 1,018,677,769 → 1,022,446,633 (≈ 45 h at ~23 counts/s, which matches homogenisation plus solidification) |
| Sample frame check | HR1 frame 0: pixel min/max/mean = 0 / 235 / 47.8, not saturated |
| Why this run | It is the smallest complete low-velocity run (3.1 GB), and V = 0.5 µm/s is in the cellular regime where the taskbook reports oscillations and multiplets |

The archive is kept zipped as the immutable original. Any extraction must go to a derived location (for example `datasets/derived/DSI/…`) with `parent_file_id` set, per `DAY1_DATA_ACQUISITION.md` §3.

---

## 7. Local mirror and provenance

| Path | Files | Bytes |
|---|---:|---:|
| `DSI/DECLIC-DSI DoD.docx` | 1 | 19,914 |
| `DSI/SRD/` | 2 | 24,094,635 |
| `DSI/Taskbook Downloads/` | 13 | 911,710 |
| `DSI/Data/*.xlsx` | 4 | 79,743 |
| `DSI/Data/S1 activity 4.zip` | 1 | 3,076,946,537 |
| **Total** | **21** | **≈ 3.10 GB** |

- `datasets/metadata/files.jsonl` holds one record per file. Fields: `file_id`, `source_id`, `original_filename`, `remote_object_key`, `canonical_source_url`, `local_path`, `content_type`, `size_bytes`, `listing_size_bytes`, `sha256`, `retrieval_timestamp_utc`, `remote_last_modified_utc`, `is_original`, `parent_file_id`.
- `datasets/checksums/sha256.txt` is in `sha256sum` format with LF endings, which `.gitattributes` enforces.
- Status against the `DAY1_DATA_ACQUISITION.md` §8 acceptance criteria:

| Criterion | DSI status |
|---|---|
| Registry row exists | ✅ `FF-PSI-DSI` in `source_registry.csv` |
| Persistent identifier | ⚠️ none recorded. A PSI DOI for DSI was not looked up. |
| SHA-256 for every mirrored file | ✅ 21/21 |
| Originals immutable | ✅ read-only use; `datasets/raw/` is git-ignored |
| Metadata ↔ file records joinable | ✅ via `sha256` / `remote_object_key` |
| Fact → exact source file/location | ⚠️ possible at file level; no evidence records extracted yet |
| No unverified S3 path hard-coded | ✅ every key comes from the bucket listing |

To reproduce:
```bash
aws s3 cp --no-sign-request --recursive "s3://nasa-psi/DSI/" datasets/raw/nasa_psi/DSI/ \
  --exclude "*" --include "DECLIC-DSI DoD.docx" --include "SRD/*" \
  --include "Taskbook Downloads/*" --include "Data/*Solidification Plan.xlsx" \
  --include "Data/S1 activity 4.zip"
python knowledge/ingestion/record_provenance.py DSI FF-PSI-DSI
(cd datasets && sha256sum -c checksums/sha256.txt)
```

---

## 8. Caveats and data-quality issues

1. **Not combustion.** Nothing here can back a claim about flames. If the RAG layer ingests these documents, retrieval must tag them `domain=materials_science` so they never appear as evidence for combustion questions.
2. **No spatial or intensity calibration** is in the image files. Report geometry in pixels and do not infer temperature from grey levels.
3. **Time base.** Images and telemetry use the SL2 counter. Plans use Excel dates. Converting to UTC needs the SL2↔date pairs from the plans, and the ~23 counts/s figure above is an estimate.
4. **Camera identity.** HR1 and HR2 are not labelled as top or side in the mirrored files.
5. **Inconsistent run counts** in the source: 29 (FY2012) vs 39 (FY2013) experiments. The bucket holds only **8 activities**, so it is a subset of the campaign.
6. **Duplication** in the bucket: zips vs folders, the `S1 activity 1` "extracted by cbp" duplicate folder, two FY2006 taskbook PDFs, and the SRD in both PDF and DOC.
7. **Bilingual and semi-structured plans.** French headers and float noise mean the plans need a small custom parser. They are not tabular.
8. **SRD is a draft.** Its alloy choice (SCN-water) differs from what flew (SCN-camphor).
9. **Telemetry format.** The two record types interleave in one table, and empty fields mean "not in this record type", not zero.

---

## 9. How this fits Flame in Freefall

| MVP component | Usable? | How |
|---|---|---|
| Combustion evidence / RAG answers | ❌ | Wrong domain |
| RAG infrastructure testing | ✅ limited | 15 clean, text-layer documents (SRD plus 13 taskbook reports) for chunking, citation-locator and abstention tests. Abstention example: "Does DSI say anything about flame spread?" should return evidence-insufficient. |
| CV pipeline (`cv/contracts/analysis_result.json`) | ✅ as a stand-in | 4,027 real microgravity greyscale frames to test validation, preprocessing, segmentation and geometry features, plus the `scaleAbsent`/`calibrationAbsent` flags. The cellular interface is a structured, segmentable pattern. **It does not train flame detection**, because flames are RGB, self-luminous objects. |
| Experiment Explorer / data model | ✅ | The flight plans map directly to `Experiment` and `ExperimentCondition` (velocity, travel, furnace set-points, image rate) and are a good first exercise of the units policy (mm/s → µm/s, °C). |
| Ingestion / provenance contract | ✅ | Already exercised end to end. Repeat the same path for BASS-II and FLEX once they are obtained. |

---

## 10. Recommendations

1. **Keep DSI at P2.** Do not mirror more of it unless the CV work needs a second regime. If it does, the best next run is **S1 activity 1** (6 µm/s, dendritic), whose zip is 3.67 GB.
2. **Write two small parsers** that create derived artefacts, never touching the originals:
   - `.dat` → Parquet, with SL2, record type, motor position and temperatures
   - plan `.xlsx` → `ExperimentCondition` rows
3. **Look up the PSI DOI** for DSI and add it to `persistent_identifier` in the registry.
4. **Get the real P0 data.** BASS-II (PSI-25) and FLEX (PSI-69) are **not** in this bucket. They are, however, downloadable anonymously through the psi.nasa.gov API (CC0, no files restricted). See `CV_IMAGE_SOURCES.md` for the inventory, the access method and a pilot download plan.
