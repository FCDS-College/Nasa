# PSI combustion datasets from the Space Apps resources page

Date: 2026-11-13. Source: the **Resources** tab of the 2026 Space Apps challenge
[Flame in Freefall](https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/?tab=resources).

## 1. What the resources page points to

The page lists one data source and nine background links.

| Resource | Kind | What we did |
|---|---|---|
| **PSI Data Repository: Combustion Science** (`psi.nasa.gov/physci/repo/search?q=combustion`) | The challenge's data | Inventoried all 26 hits, installed tables + metadata + document PDFs for the 24 combustion ones, ingested them |
| NASA Combustion Science (GRC page) | Overview of the investigations | Background; the same investigations are in PSI |
| ScienceCasts video (2018) | Video | Background only |
| A Researcher's Guide to ISS Combustion Science (2015) | Document | Already inside PSI: published as a Science Document of ACME E-FIELD (PSI-22), so it is now installed and ingested |
| Apollo 1, Apollo 13, Mir 1997 fire | History / lessons learned | Background for the fire-safety narrative; no data |
| Fireman's Air Tanks, Fire Detector, Fire Attire | NASA spinoffs | Background; no data |

## 2. The 26 PSI investigations behind the search

Inventory: `datasets/manifests/psi_combustion_investigations.csv` (one row per investigation: DOI, version, size)
and `datasets/manifests/psi_all_combustion_inventory.csv` (every file: 61,227 unique objects, **≈14 TB**).
Rebuild both with `python knowledge/ingestion/psi_inventory.py`.

| PSI | Investigation | Kind | Size on PSI | Experimental table | Registry |
|---|---|---|---:|---|---|
| PSI-10 | ACME Flame Design | ISS gaseous flames | 2,180 GB | 2 (207 normal + 120 inverse flames) | FF-PSI-10, P0 |
| PSI-20 | ACME BRE (Burning Rate Emulator) | ISS gaseous flames | 2,036 GB | 1 (18 test days) | FF-PSI-20, P0 |
| PSI-21 | ACME CLD Flame | ISS gaseous flames | 2,006 GB | 1 (32 test days) | FF-PSI-21, P0 (was FF-NASA-CLD) |
| PSI-22 | ACME E-FIELD Flames | ISS gaseous flames | 950 GB | 1 (32 test days) | FF-PSI-22, P0 |
| PSI-23 | ACME s-Flame | ISS gaseous flames | 782 GB | 1 (18 test days) | FF-PSI-23, P0 |
| PSI-25 | BASS-II | ISS solids | 275 GB | 1 (129 tests) | FF-PSI-25, P0 (since 2026-10) |
| PSI-26 | BASS | ISS solids | 164 GB | 1 (122 tests) | FF-PSI-26, P0 |
| PSI-39 | CFI (Cool Flames Investigation) | ISS droplets | 719 GB | 1 (87 rows, 79 distinct tests) | FF-PSI-39, P1 |
| PSI-47 | DAFT / DAFT-2 | ISS aerosol | 0.04 GB | 1 (2 sessions) | FF-PSI-47, P1 |
| PSI-60 | SPICE data analysis | Ground study | <0.01 GB | — | FF-PSI-60, P2, documentation |
| PSI-62 | Concurrent flame-spread modelling | Ground study | <0.01 GB | — | FF-PSI-62, P2, documentation |
| PSI-68 | FLEX-2 | ISS droplets | 1,225 GB | 1 (8-row test matrix) | FF-PSI-68, P0 (was FF-NASA-FLEX2) |
| PSI-69 | FLEX | ISS droplets | 924 GB | 1 (274 tests) | FF-PSI-69, P0 (since 2026-10) |
| PSI-98 | SAFFIRE-I | Large-scale spacecraft fire | 12 GB | 1 (2 samples) | FF-PSI-98, P0 (since 2026-10) |
| PSI-99 | SAFFIRE-II | Large-scale spacecraft fire (Cygnus) | 17 GB | 1 (9 samples) | FF-PSI-99, P0 |
| PSI-100 | SAFFIRE-III | Large-scale spacecraft fire | 35 GB | 1 (2 samples) | FF-PSI-100, P0 |
| PSI-101 | SAME-R (Smoke Aerosol, reflight) | ISS smoke | 6 GB | 1 (109 tests) | FF-PSI-101, P0 |
| PSI-102 | SAME (Smoke and Aerosol) | ISS smoke | 0.7 GB | 1 (8 samples) | FF-PSI-102, P0 |
| PSI-106 | SLICE | ISS lifted flames | 73 GB | 1 (12 test dates) | FF-PSI-106, P1 |
| PSI-107 | SPICE | ISS smoke point | 7 GB | 1 (469 rows, 435 distinct) | FF-PSI-107, P0 (since 2026-10) |
| PSI-108 | STDCE-1 | Shuttle, surface-tension convection | 24 GB | 2 | **not registered**: fluid physics, not combustion |
| PSI-115 | SAME data for smoke modelling | Ground study | 0.3 GB | — | FF-PSI-115, P2, documentation |
| PSI-117 | Cool-flame CFD (thermo-convective perturbation) | Ground study | 0.07 GB | — | FF-PSI-117, P2, documentation |
| PSI-142 | Cool-flame transitions | Ground study | <0.01 GB | 1 (index of figures) | FF-PSI-142, P2, documentation |
| PSI-159 | ACME CFI-G (cool flames, gaseous) | ISS gaseous flames | 2,086 GB | 2 (179 normal + 154 inverse flames) | FF-PSI-159, P0 |
| PSI-181 | Pb-Sn / Sn-Ag-Cu solders | Ground, materials | 523 GB | 1 | **not registered**: materials science, not combustion |

All 24 registered investigations are CC0-1.0 with a PSI DOI (`persistent_identifier` in the registry).
PSI-10's landing record leaves the licence blank; PSI's policy is CC0, recorded with a note.

## 3. What is installed, and why not everything

Mirroring everything is not possible: ≈14 TB against ~280 GB free on the data disk, and ACME Flame Design alone is 2.2 TB.
Following the Lead's choice (2026-11-13), the install is **what the pipeline ingests**:

* **Experimental tables** (CSV): 22 files from 20 investigations. Committed to git (ADR-012 `.gitignore` exception).
* **ISA-Tab metadata** (zip): 24 files, one per investigation. Committed to git.
* **Document PDFs** from the Engineering Documents, Presentations, Reports, Science Documents and Reference Data
  folders. Local only (git-ignored), ~0.74 GB. "Raw Data" PDFs (hundreds per large investigation) are per-test data
  sheets, not documents, and are not included.

Selection: `datasets/manifests/psi_docs_tables_selection.csv` (339 files). Download and verify:

```bash
python knowledge/ingestion/install_datasets.py --only combustion   # pilot media + this selection
python knowledge/ingestion/install_datasets.py --only tables       # just the committed tables + metadata
```

Result on 2026-11-13: **327 of 339 files installed**; checksums and provenance recorded in
`datasets/checksums/sha256.txt` and `datasets/metadata/files.jsonl` (`record_provenance.py`).
Media (video, frames) for any investigation can still be pulled on demand with a selection CSV and `psi_download.py`.

### Not available from NASA (12 files)

| File | Problem |
|---|---|
| SAFFIRE Offgassing Testing Strategy.pdf (PSI-98, 99, 100) | HTTP 404 on every attempt (PSI-98's already failed in 2026-10) |
| SAFFIRE 45th / 46th / 47th ICES presentation.pdf (PSI-99, 100) | HTTP 404 |
| PSI-26 BASS_FinalReport.pdf, SPICE_FinalReport.pdf | HTTP 404 |
| PSI-20 ACME_engineering_20210328.pdf | Served as 6,843,254 bytes; PSI lists 5,794,678. Not installed (size check fails) |

### Same document under several investigations

PSI publishes shared documents under every investigation that uses them (the ACME SORD and engineering documents,
the SAME manuals, the SAFFIRE overview paper). `file_id` is content-addressed, so `files.jsonl` keeps **one record
per content** (370 records) and lists the other copies in that record's `also_published_as` (70 copies). Every copy
is still checksummed in `sha256.txt` (440 lines). This also keeps the RAG index from holding the same PDF 2–4 times.

## 4. How it is connected to the system

| Layer | Change |
|---|---|
| Registry | 20 new PSI rows (15 flight investigations + 5 ground studies), 2 of which replace the FF-NASA-CLD / FF-NASA-FLEX2 placeholders: 50 sources, valid against the schema |
| Ingestion (`flame_api/ingest.py`, `psi-tables-0.2.0`) | Test-ID and fuel/material column per investigation (`TEST_ID_COLUMNS`, `FUEL_COLUMNS`); blank spreadsheet rows skipped (861 in the CFI-G inverse table); SAFFIRE-II/III legend rows skipped. The original four tables parse exactly as before |
| Knowledge graph | Uses the same per-investigation columns: 1,958 experiments, 20 investigations, 20 ISA-Tab documents, 25,415 cited edges. One new curated spelling alias (`100%C2H4` → `100% C2H4`, ACME BRE), pending the Lead's review |
| Fire-safety analytics (`ai/fire_safety/investigations.py`) | O₂, pressure, flow, end state and duration read for ACME Flame Design, ACME CFI-G, CFI, SAFFIRE-II/III, SAME, SAME-R |
| Dashboard API | 19 flight investigations, 1,950 flight tests; `not_acquired` is now empty (SAME was the last challenge-named one) |

### Reading the new tables correctly

* **Inverse flames** (ACME Flame Design, CFI-G): XO₂ is the oxidiser stream from the burner (up to 0.85), not the
  atmosphere. These tests get no cabin O₂ and the flag `inverse_flame_o2_is_burner_stream`.
* **CFI-G end state**: `SE` = the flame self-extinguished, `FT` = flow terminated the run.
* **ACME BRE / CLD / E-FIELD / s-Flame, SLICE, DAFT, FLEX-2** tables summarise test days or the test matrix, not
  individual tests with O₂ and pressure. They are ingested and cited, but score 0 on the atmosphere match.
* **SAFFIRE-II O₂** is derived from CO₂ production (its Note 1), so it is marked approximate like SAFFIRE-I.

## 5. Open items

1. The Lead to review the fifth curated alias (`flame_api/knowledge_graph.py`).
2. Ask PSI about the 11 missing documents and the mis-sized ACME PDF.
3. CV/video work (E3) can now choose clips from 20 investigations; select them from `psi_all_combustion_inventory.csv`.
4. PSI-107 has an in-place extraction of `Downlink Frame Grabs 36f.zip` (26 PNGs) that is derived data; it is
   deliberately not recorded as an original.
