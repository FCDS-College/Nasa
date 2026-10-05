# Flame in Freefall: Combustion Dataset Analysis

**Date:** 2026-10-05 · **Analysed:** the local mirror under `datasets/` at `28921c0` (raw files are git-ignored; their provenance is in `datasets/metadata/files.jsonl`).
**Purpose:** a clear, measured picture of what the mirrored NASA data actually contains and supports, as the input to [`../AURA_INTEGRATION_REQUIREMENTS.md`](../AURA_INTEGRATION_REQUIREMENTS.md).
**Method:** every number below was computed from the files themselves (CSV parsing, zip listings, BMP headers, frame-timestamp logs), not taken from READMEs or landing pages.
**Related:** [`CV_IMAGE_SOURCES.md`](CV_IMAGE_SOURCES.md) (where flame images can come from), [`DSI_DATASET_REPORT.md`](DSI_DATASET_REPORT.md) (the non-combustion DSI reference), [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) (canonical fields).

---

## 1. The project in one picture

Flame in Freefall is an **evidence-first scientific intelligence platform for combustion in microgravity**: a curated NASA corpus, cited answers, traceable computer-vision (CV) measurements of flame images, and a dashboard. Its one non-negotiable rule is that **every consequential result traces back to an original, checksummed source file**.

```
 NASA PSI (CC0)                 Flame in Freefall                                      Consumers
 ───────────────     ┌──────────────────────────────────────────────────────────┐
 BASS-II  PSI-25 ─┐  │ datasets/   registry → files.jsonl (sha256) → raw/derived │
 FLEX     PSI-69 ─┼─►│ knowledge/  ingestion (PSI API) + provenance             │
 SAFFIRE  PSI-98 ─┤  │ ── planned ───────────────────────────────────────────── │   Next.js dashboard
 SPICE    PSI-107─┘  │ apps/api    FastAPI, docs/openapi.json (10 operations)    │──► (apps/web)
 DSI (reference)     │ Postgres+pgvector: source, file, document, evidence,      │
 NTRS PDFs (3)       │            experiment, experiment_condition, analysis    │──► AURA AI
                     │ cv/         validate → detect → segment → measure         │    (interpretation,
                     │ ai/         RAG over evidence, claim-class validation     │     conversational
                     └──────────────────────────────────────────────────────────┘     access)
```

| Layer | State (verified 2026-10-05) |
|---|---|
| Source registry + file provenance | **Implemented.** 7 sources, 121 sha256-checked file records. |
| Ingestion scripts | **Implemented.** `psi_download.py`, `record_provenance.py`. |
| Structured experiment data | **Mirrored, not parsed.** 4 experimental tables (§3). |
| Media for CV | **Mirrored, not processed.** 17 BASS-II videos and about 10,460 combustion frames and stills, plus 1,556 SAFFIRE flow-visualisation frames (§4). |
| API, database, CV, RAG | **Not started.** The contract (`docs/openapi.json`) exists, but no implementation does. |

---

## 2. What is on disk

| Source | Investigation | Mirrored files | On disk | Full PSI release | Coverage |
|---|---|---:|---:|---:|---|
| FF-PSI-25 | BASS-II: solid-fuel flame spread and extinction (ISS MSG, 2014) | 25 | 0.52 GB | 695 files / 274.6 GB | 3.6 % of files |
| FF-PSI-69 | FLEX: liquid droplet combustion and extinction (ISS CIR, 2009–2011) | 19 | 2.42 GB | 6,555 files / 923.8 GB | 0.3 % |
| FF-PSI-98 | SAFFIRE-I: large-scale fabric burn (free-flying Cygnus, 2016) | 9 | 0.12 GB | 76 files / 12.3 GB | 12 % |
| FF-PSI-107 | SPICE: laminar smoke points in co-flow (ISS MSG, 2009–2010) | 47 (73 after unzip) | 0.07 GB | 188 files / 6.95 GB | 25 % |
| FF-PSI-DSI | DECLIC-DSI: directional solidification (**not combustion**, P2 reference) | 21 + 4,036 derived | 3.10 + 7.33 GB | 121,811 files / 165 GB | sample run only |

All four combustion sources are **CC0-1.0** and have a DOI (in `datasets/registry/source_registry.csv`). Each one ships the same PSI folder shape: `Experimental table/`, `metadata/` (an ISA-Tab investigation file), `Raw Data/`, `Reports/`, `Science Documents/`, `Engineering Documents/`.

Gaps between the selection and the mirror: `psi_pilot_selection.csv` selects 103 PSI files, but `files.jsonl` records 100 (PSI-25: 27 → 25, PSI-98: 10 → 9). The three NTRS PDFs in `docs/research/` have no provenance records.

---

## 3. Structured data: the four experimental tables

These four small CSV files (73 KB in total) are **the most valuable machine-readable asset in the project**: 876 rows of real flight-test conditions and, for FLEX, outcomes.

### 3.1 FLEX (PSI-69): 274 droplet tests. The richest table.

| Field (as published) | Canonical variable | Observed range / values | Notes |
|---|---|---|---|
| `FLEX Test #`, `FLEX Identifier` | `test_id` | `20CAL08` … `H15M102` | Identifier joins to raw-run folder names (§4). |
| `Test Date`, `Test GMT` | `test_datetime_utc` | 2009-03-05 → 2011-12-08 | US date format `M/D/YYYY`. |
| `Fuel` | `fuel_or_material` | Methanol 157 · Heptane 117 | |
| `Ambient pressure; mmHg` | `pressure` | clusters at ≈ 70, 100, 206, 276, 309 kPa | **One row is 0 mmHg** (`C11M201`), which is physically impossible and must be treated as missing. |
| `O initial ambient composition; mole fraction` | `o2_fraction` | 0.12 – 0.34 | The header lost its subscript: "O" means **O₂**. |
| `N initial …` | `n2_fraction` | | means N₂ |
| `CO initial …` | `co2_fraction` | 0 – 0.70; non-zero in 123 tests | means **CO₂** (diluent), not CO |
| `He initial …` | `he_fraction` | 0 – 0.45; non-zero in 50 tests | |
| `Droplet initial diameter; mm` | `droplet_diameter_initial` | 1.10 – 4.67 mm | |
| `Visible flame extinction diameter; mm` | `extinction_diameter` | 0 – 4.6 mm; 197 numeric | |
| `Burning rate; mm` | `burning_rate` | 0.05 – 1.06 | **The unit label is wrong.** The magnitude matches a burning-rate constant in mm²/s. Confirm against `FLEX_Test_Plan.pdf` before normalising. |
| `Burn time; s` | `burn_time` | 0.3 – 39.2 s | Two values are approximate (`~6`, `~9`). |
| `Test end` | `extinction_event` / `flame_state_end` | Extinction 186 · Disruption 61 · Completion 27 | A clean three-class outcome label. |

**Encoding:** the file is **Windows-1252, not UTF-8**. Byte `0x96` (an en dash) is used as a "not available" marker in 34 cells. Decoding the file as UTF-8 turns it into `U+FFFD`, which then fails numeric parsing silently.

### 3.2 BASS-II (PSI-25): 129 solid-fuel tests. Conditions only, no outcomes.

| Field | Observed | Notes |
|---|---|---|
| `PI`, `Test #` | 6 PIs (T'ien 29, Olson 27, Fernandez-Pello 27, Bhattacharjee 22, Miller 20, Ferkul 4); IDs `B…`, `F…`, `M…`, `O…`, `P…`, `T…`, with `a`/`b` sub-tests | The test-ID prefix encodes the PI's test series. |
| `Date`, `GMT` | 2014-02-19 → 2014-08-04; GMT is **day-of-year** | |
| `Sample #` | e.g. `147`, `39M`, `182m` | Inconsistent `M`/`m` suffix. Strip it to join to video filenames. |
| `Fuel Sample Material` | Free text: PMMA films, rods (clear/black, 1/4"–1/2"), slabs, SIBAL fabric, Nomex III, Japan wax candle, spherical sections | Needs parsing into `material`, `geometry` and `thickness`/`width` (mixed inch, mm and micron). |
| `Calibrated initial O2 % by vol` | 13.6 – 22.2 % | Clean. |
| `Calibrated final O2 % by vol` | 0.6 – 40.4 % | Test `T28b` reads 40.4 % from a 20.7 % start, which is implausible. Flag it, don't drop it. |
| `Initial/Final CO2 % by vol`, `Initial/Final CO (ppm)` | CO up to 950 ppm; text values `OR`, `over`, `>500` | `OR` and `over` mean sensor over-range. Keep them as censored values, not null. |
| `Fan display`, `Air display`, `Flow restrictor` | **Free text** such as `5 down to ext`, `55  47  etc (pot 1  2  1  2   etc)`, `80122` | Flow velocity is **not** in cm/s. Converting it needs `Reference Data/Fan calibration data.xlsx` (not parsed yet). `80122` (test `T15`) is a data-entry error. |
| `Radiometer gain`, `Total Frames Shot` | multi-value text (`250>50>250`); frames 2–316, or `video` | |

**Important:** the BASS-II table has **no outcome columns**: no spread rate and no extinction flag. Outcomes exist only in the videos and in `BASS-II Summary Report.pdf`. Any BASS-II "result" therefore needs either CV measurement from video or extraction from the report, and both must carry evidence.

### 3.3 SPICE (PSI-107): 469 smoke-point flame settings

| Field | Observed | Notes |
|---|---|---|
| `GMT date` | day-of-year only (45 … 174), **no year** | The year has to come from file names (e.g. `GMT045 2009 jpegs`) or reports. |
| `GMT ignition`, `GMT Flame Off` | times | |
| `Fuel` | Propylene 122, `75 % Propylene` 119 and `75% Propylene` 16 (the same fuel spelled two ways), 50 % Propylene 111, Propane 50, Ethylene 47, Methane 4 | Normalise to `fuel` + `dilution_fraction`. |
| `Nozzle (mm)` | 0.406, 0.762, 1.600 mm (three nozzles) | Clean. |
| `Fuel Rate (sccm / mg/s)`, `HC Fuel Rate (mg/s)`, `Air Rate (cm/s)` | air −5.92 … 85.28 cm/s | **8 negative air rates.** Flag them as sensor offset, not as reverse flow. |
| Duplicates | **34 exact duplicate rows** | Deduplicate with a recorded transformation, never silently. |

The measured outcome, the smoke-point flame length, is **not in this CSV**. It is in `Raw Data/Spice_Flight_Flamelength.xls`, which is not parsed yet (no `xlrd`/`openpyxl` in the current toolchain).

### 3.4 SAFFIRE-I (PSI-98): 2 burns

| Sample | Material | Size (cm) | Flow | O₂ | Burn time | Direction |
|---|---|---|---|---|---|---|
| S1 | SIBAL fabric | 94 × 40.6 × 0.37 | 20 cm/s | 21.5–21.7 % (range) | 420 s | Concurrent |
| S2 | SIBAL fabric | 94 × 40.6 × 0.37 | 20 cm/s | `~ 21.5` (approximate) | 70 s | Opposed |

Two of the table's four rows are **not tests**. They are legend rows: `F1C1/F1C2` and `F2C1/F2C2` are "pre-test flow visualisation". The sensor data (thermocouples, radiometers, O₂/CO₂) referenced by the registry is in `SAFFIRE-1_MergeResult-jpeg_Update_Final_v2.xlsx` (12 MB, not parsed yet).

### 3.5 Investigation metadata (ISA-Tab)

Each `metadata/*.zip` holds `i_Investigation.txt` (ISA-Tab) plus a stub `s_PSI-nn.txt`. It provides, in machine-readable form: the DOI, hypothesis, objectives, approach, hardware (MSG/CIR), research area, **publication DOIs** (BASS-II lists more than a dozen), and PI names. This is the right source for `document` and `source` records and for the dashboard's "about this investigation" text. It is free text from NASA, so it is **untrusted text** for any AI layer (requirements doc, SR-1).

---

## 4. Media: what CV can and cannot use

| Source | Mirrored media | Format | Joins to a table row? | Usable for flame CV? |
|---|---|---|---|---|
| BASS-II | 17 MP4 videos (470 MB), including 5 second-view cameras | MP4 (no `ffprobe` installed, so codec and resolution are unverified) | **17/17** by `TEST_<id>` in the filename (sample # matches after stripping `M`/`m`) | **Yes.** Real flame-spread footage with known O₂ and material. |
| FLEX | 8 runs, 10,397 frames (about 7.8 GB unzipped); 4 runs are 640×480 24-bit BMP, 4 are TIFF | each run has a `<run>.txt` frame log (ms timestamps, ≈ 30 fps) | **4/8** (`176F001D`, `195F002D`, `H08M101D`, `H14H101C`). `C021H03C`, `C024M06C`, `X168M03D` and `X177H10D` have **no row** in the table. | **Yes**, and time-resolved: frame timestamps allow d(t) and d²(t) curves. |
| SPICE | 26 PNG downlink frame grabs, 39 ISS JPEGs (GMT045 2009) | stills | Only via day-of-year + `SPICE Image Organization Guide.docx` (not parsed) | Yes for flame-length or appearance, once linked. |
| SAFFIRE-I | 778 frames + 778 "Mapped" frames, camera `F2C2`, 27 s at 33 ms | JPEG | Yes, but **`F2C2` is pre-test flow visualisation** (table legend) | **No.** This is not flame imagery. The burn imagery (`S1C*`/`S2C*`) has not been mirrored. |
| DSI | 4,027 BMP | solidification interfaces | n/a | **No.** Non-combustion. Keep it out of the flame CV and out of combustion search. |

---

## 5. Cross-dataset canonical model and normalisation rules

All four tables map onto the existing `experiment` + `experiment_condition` design (`DATA_DICTIONARY.md`, `ExperimentCondition` in `docs/openapi.json`). Keep the original value **and** the SI value. Never overwrite the original.

| Canonical variable | FLEX | BASS-II | SPICE | SAFFIRE-I | SI unit | Rule |
|---|---|---|---|---|---|---|
| `o2_fraction` | mole fraction | % by vol | (air) | % (range/approx.) | mole fraction | % ÷ 100; ranges → min/max; `~` → approximate |
| `pressure` | mmHg | n/a | n/a | n/a | Pa | × 133.322; 0 → null + flag |
| `flow_velocity` | n/a | display units (needs fan calibration) | cm/s | cm/s | m/s | BASS-II: **null until calibrated**, original kept as text |
| `fuel_or_material` | Methanol/Heptane | free text | fuel + % | SIBAL | n/a | controlled vocabulary + parsed geometry |
| `droplet_diameter_initial`, `extinction_diameter` | mm | n/a | n/a | n/a | m | `0x96` → null |
| `burning_rate` | "mm" (sic) | n/a | n/a | n/a | m²/s (pending confirmation) | unit **unresolved**: blocks numeric comparison until confirmed (DATA_DICTIONARY null policy) |
| `flame_state_end` | Extinction/Disruption/Completion | n/a (video/report) | n/a | n/a | enum | |
| `gravity_regime` | µg | µg | µg | µg | enum | constant `microgravity` per source |

**Missing-value markers to recognise:** empty, `0x96` (en dash), `none`, `video`. **Censored markers:** `OR`, `over`, `>500`. **Approximate markers:** `~`. None of them may become `0`.

---

## 6. What this data can and cannot support (scientific honesty)

**Can support, with full provenance:**
- FLEX: condition → outcome questions, for example "Which heptane tests extinguished below 0.15 O₂?" or "How does extinction diameter vary with He dilution?". 274 labelled tests is enough for descriptive statistics and simple models.
- Cross-experiment condition search: O₂, pressure, diluent, fuel and material across all four investigations.
- CV on BASS-II video and FLEX frames, measuring pixel geometry over time. Physical millimetres only with a stated scale source.
- Citations to investigation metadata, reports and publication DOIs.

**Cannot support (and no AI layer may claim):**
- **Flame temperature from images.** No calibrated radiometry is in the mirrored media (the contract already enforces `TEMPERATURE_NOT_AVAILABLE`).
- BASS-II spread rates or extinction from the table alone (there are no outcome columns).
- SAFFIRE-I flame CV from the mirrored files (they are flow visualisation).
- Statistics across all of BASS-II/FLEX: the mirror holds 3.6 % and 0.3 % of their files. Results describe **the mirrored subset**, and the UI must say so.

---

## 7. Data issues to fix (input to requirement FR-2)

| # | Issue | Where | Fix |
|---|---|---|---|
| D1 | cp1252 encoding; `0x96` used as missing | FLEX CSV | Decode as cp1252; map `–` → null + `missing_marker` |
| D2 | Subscripts lost in headers (O₂, N₂, CO₂) | FLEX CSV | Explicit column map; do not infer from header text |
| D3 | Wrong unit label on burning rate | FLEX CSV | Mark unit `unresolved`; confirm from the test plan |
| D4 | Impossible pressure 0 mmHg | FLEX `C11M201` | null + quality flag |
| D5 | 4 of 8 FLEX runs do not join to the table | FLEX raw data | Find their identifiers (likely another campaign's naming); otherwise label them `unlinked` |
| D6 | Free-text flow settings, no SI velocity | BASS-II | Parse `Fan calibration data.xlsx`; keep text otherwise |
| D7 | Material free text, mixed inch/mm/micron | BASS-II | Parser to `material`, `geometry`, thickness and width in m |
| D8 | Outliers (`80122` fan, 40.4 % final O₂) | BASS-II `T15`, `T28b` | Keep + quality flag |
| D9 | Censored sensor values (`OR`, `over`, `>500`) | BASS-II CO | `censored: "above_range"` |
| D10 | 34 duplicate rows | SPICE | Dedupe as a recorded transformation |
| D11 | Day-of-year without a year; fuel spelling variants; negative air rates | SPICE | Year from file names/reports; vocabulary; flag negatives |
| D12 | Legend rows mixed with test rows | SAFFIRE-I | Parse only `S\d+` rows |
| D13 | Mirrored SAFFIRE imagery is flow visualisation | SAFFIRE-I | Mirror `S1C*`/`S2C*` burn imagery if SAFFIRE CV is wanted |
| D14 | Outcome workbooks not parsed (`Spice_Flight_Flamelength.xls`, `MergeResult…xlsx`) | SPICE, SAFFIRE | Add `openpyxl`/`xlrd` ingestion |
| D15 | 3 selected files not mirrored; NTRS PDFs unregistered | manifests | Re-run download; register the PDFs |
