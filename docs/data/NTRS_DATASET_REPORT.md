# E2-9: NTRS dataset report (24 technical reports)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | In review (peer sign-off: Ziad E5) | 1.1.0 | 2026-11-07 | M9, E2-9 | `docs/research/*.pdf`, registry rows `FF-NTRS-*`, `datasets/metadata/files.jsonl`, `knowledge/ingestion/fetch_ntrs.py` |

## 1. What the source is

The NASA Technical Reports Server (NTRS, https://ntrs.nasa.gov) is NASA's public repository of technical reports. Three reports on spacecraft material flammability and microgravity flame spread were committed to `docs/research/` on 2026-10-03, during the MVP. They were not registered or ingested until now.

| source_id | Title (read from the PDF) | Report / authors | Pages | Bytes | sha256 |
|---|---|---|---|---|---|
| `FF-NTRS-20000034017` | Testing and Selection of Fire-Resistant Materials for Spacecraft Use | NASA/TM-2000-209773; Friedman, Jackson, Olson (GRC), March 2000 | 20 | 1,297,410 | `dc531270ffb646b26503955afb0c1df7bcc47482bbfed4a3d6b922de9629520d` |
| `FF-NTRS-20040053557` | Extinction Criteria for Opposed-Flow Flame Spread in a Microgravity Environment | Bhattacharjee, Paolini (SDSU), Wakai, Takahashi (Gifu); NASA workshop paper, 2003 | 4 | 172,892 | `d237a76afe3aeba50b3ec804522faad75e542c91ceab7b919159edc74c33d3f7` |
| `FF-NTRS-20080034883` | Microgravity Flame Spread in Exploration Atmospheres: Pressure, Oxygen, and Velocity Effects on Opposed and Concurrent Flame Spread | NASA/TM-2008-215260; Olson, Ruff (GRC), Miller (SDSU), August 2008 | 15 | 977,774 | `bb3dd1a5b3a0a6f85e42b5b285f7b191772b72317fe8ba36756d112cba774be2` |

Command: `sha256sum docs/research/*.pdf`; pages from PyMuPDF.

## 2. Access method
- Downloaded manually before 2026-10-03. The `retrieval_timestamp_utc` in `files.jsonl` is the git commit date that added the files (2026-10-03T21:28:17Z), because the original download time wasn't recorded.
- `canonical_source_url` follows the NTRS download pattern `https://ntrs.nasa.gov/api/citations/<id>/downloads/<id>.pdf`. It was **not re-fetched** in this pass (offline-safe registration).
- Licence: `null` in the registry. NTRS states terms per record, so these must be read from each record page before the licence is set.

## 3. What was ingested and what was skipped

`python -m flame_api.ingest` on 2026-10-11, PostgreSQL 16:

| File | Pages | Chunks | Pages without text | OCR |
|---|---|---|---|---|
| 20000034017.pdf | 20 | 20 | — | not needed |
| 20040053557.pdf | 4 | 4 | — | not needed |
| 20080034883.pdf | 15 | 13 | 14, 15 | `unavailable` (Tesseract not installed on that host) |
| **Total** | **39** | **37** | 2 | — |

Then `vector_index build` embedded the 37 chunks (knowledge version `bge-small-en-v1.5-37-20261011`). Nothing was quarantined. Documents are typed `technical_report`, and their title and identifier come from the registry row.

## 4. Scientific relevance and limitations
- **Relevance:**
  - material flammability test methods (NASA-STD-6001 heritage) and spacecraft material selection;
  - an opposed-flow extinction criterion in microgravity;
  - pressure, oxygen and flow effects on opposed and concurrent spread in exploration atmospheres.

  These underpin the questions the chat is meant to answer, and they complement the PSI experiment tables.
- **Limitations:**
  - three documents is a small corpus;
  - figures and tables inside the PDFs are page text only, with no table extraction;
  - pp. 14–15 of the 2008 report need OCR;
  - the licences are unconfirmed.

## 5. Corpus expansion, 2026-11-07: 21 more NTRS reports

**Date:** 2026-11-07. **Script:** `knowledge/ingestion/fetch_ntrs.py` (`--discover` lists the candidates; `--dry-run` re-checks the selection; with no flag it downloads and registers the reports, and skips any that are already registered).

### Selection method
1. **Cited by the PSI investigations.** NTRS citation IDs were taken from `Comment[Study Publication Link]` in the ISA-Tab `i_Investigation.txt` of `datasets/raw/psi_api/PSI-{25,69,98,107}/metadata/*.zip`. Two more were matched on NTRS by a title from the same ISA-Tab files, where the link points elsewhere (ResearchGate or a DOI).
2. **NTRS API searches.** `POST https://ntrs.nasa.gov/api/citations/search` for spacecraft fire safety, Saffire, BASS, FLEX, ACME, SPICE, exploration-atmosphere flammability, NASA-STD-6001, limiting oxygen and fire suppression (the full query list is `DISCOVERY_QUERIES` in the script). Papers and reports were preferred over slide decks.
3. **Gates, all from the record at `GET /api/citations/<id>`:**
   - `distribution == "PUBLIC"`;
   - `copyright.determinationType` is `GOV_PUBLIC_USE_PERMITTED` or `PUBLIC_USE_PERMITTED`;
   - `copyright.containsThirdPartyMaterial == false`;
   - `exportControl.isExportControl == "NO"`;
   - the record has a PDF download of 6 MB or less;
   - PyMuPDF extracts at least 3,000 characters.
4. **Metadata comes from NTRS only.** Title, authors, date, report numbers, provider (author affiliations) and download URL come from the API record. `short_name` is the record's `NASA/...` report number when it has one, otherwise `<first author> [et al.] <year>`. The relevance text and experiment family are curation notes.
5. **Registration.** Each PDF is saved as `docs/research/<id>.pdf`, then appended to `source_registry.csv` (`FF-NTRS-<id>`, `access_status=confirmed_public`, `verification_state=verified`, `P1`), `files.jsonl` (`retrieval_timestamp_utc` = the actual download time) and `sha256.txt`. The `license` column records the NTRS determination. The `notes` column records the authors, STI type, report numbers, every permission field checked, and the selection basis.

### Added reports (21 PDFs, 16,764,137 bytes ≈ 16.8 MB, 245 pages)

| NTRS id | Title (from NTRS) | short_name | Year | Pages | Bytes | Basis | Why relevant | NTRS determination |
|---|---|---|---|---|---|---|---|---|
| `20150019858` | Results from On-Board CSA-CP and CDM Sensor Readings During the Burning and Suppression of Solids II (BASS-II) Experiment in the Microgravity Science Glovebox (MSG) | Olson et al. 2015 | 2015 | 9 | 864,432 | PSI-25 link | BASS-II: on-board CSA-CP/CDM gas-sensor readings during solid burning | `PUBLIC_USE_PERMITTED` |
| `20160012691` | Correlation of Normal Gravity Mixed Convection Blowoff Limits with Microgravity Forced Flow Blowoff Limits | Marcum et al. 2016 | 2016 | 9 | 670,023 | PSI-25 link | BASS-II: links 1-g mixed-convection blowoff limits to BASS microgravity limits | `PUBLIC_USE_PERMITTED` |
| `20130014061` | Methanol Droplet Combustion in Oxygen-Inert Environments in Microgravity | Nayagam et al. 2013 | 2013 | 11 | 2,314,383 | PSI-69 link | FLEX: methanol droplet burning and extinction in oxygen-inert atmospheres | `PUBLIC_USE_PERMITTED` |
| `20120016855` | Methanol Droplet Extinction in Oxygen/Carbon-dioxide/Nitrogen Mixtures in Microgravity: Results from the International Space Station Experiments | Nayagam et al. 2012 | 2012 | 6 | 240,653 | PSI-69 link | FLEX: droplet extinction with CO2 dilution (relevant to suppressants) | `PUBLIC_USE_PERMITTED` |
| `20120015928` | FLEX: A Decisive Step Forward in NASA's Combustion Research Program | Hickman et al. 2012 | 2012 | 44 | 3,693,275 | PSI-69 link | FLEX: programme overview, with its objectives, hardware and principal results | `PUBLIC_USE_PERMITTED` |
| `20170001636` | The Spacecraft Fire Experiment (Saffire) - Objectives, Development and Status | Schoren et al. 2016 | 2016 | 6 | 160,936 | PSI-98 link | SAFFIRE: objectives, development and status | `GOV_PUBLIC_USE_PERMITTED` |
| `20170000230` | Operation and Development Status of the Spacecraft Fire Experiments (Saffire) | Ruff et al. 2016 | 2016 | 9 | 556,175 | PSI-98 link | SAFFIRE: flight operations and development status | `GOV_PUBLIC_USE_PERMITTED` |
| `20150008961` | Microgravity Flammability of PMMA Rods in Concurrent Flow | Olson et al. 2015 | 2015 | 10 | 449,964 | PSI-25 title | BASS-II: flammability of PMMA rods in concurrent flow | `PUBLIC_USE_PERMITTED` |
| `20140006750` | Cool-flame Extinction During N-Alkane Droplet Combustion in Microgravity | Nayagam et al. 2014 | 2014 | 9 | 324,885 | PSI-69 title | FLEX: cool-flame extinction of n-alkane droplets | `PUBLIC_USE_PERMITTED` |
| `20090014827` | Smoke Point in Co-flow Experiment | Urban et al. 2009 | 2009 | 4 | 52,083 | search | SPICE: experiment description (smoke points of coflow flames) | `PUBLIC_USE_PERMITTED` |
| `20130001713` | Large Scale Experiments on Spacecraft Fire Safety | Urban et al. 2012 | 2012 | 6 | 387,761 | search | SAFFIRE: rationale and design of the large-scale fire safety experiments | `PUBLIC_USE_PERMITTED` |
| `19990063738` | Fire Safety in the Low-Gravity Spacecraft Environment | NASA/TM-1999-209285 | 1999 | 18 | 1,338,575 | search | review of fire safety in the low-gravity spacecraft environment | `GOV_PUBLIC_USE_PERMITTED` |
| `20140006580` | Determination of Realistic Fire Scenarios in Spacecraft | Dietrich et al. 2013 | 2013 | 12 | 736,722 | search | realistic spacecraft fire scenarios for design and response | `GOV_PUBLIC_USE_PERMITTED` |
| `20140009169` | Gaseous Non-Premixed Flame Research Planned for the International Space Station | Stocker et al. 2014 | 2014 | 13 | 510,998 | search | ACME: research plan for gaseous non-premixed flames on the ISS | `PUBLIC_USE_PERMITTED` |
| `20210021781` | Recent Research on Flames of Gaseous Fuel Aboard the International Space Station | Stocker 2021 | 2021 | 11 | 1,336,135 | search | ACME: research on gaseous-fuel flames aboard the ISS | `GOV_PUBLIC_USE_PERMITTED` |
| `20150004099` | Applying Flammability Limit Probabilities and the Normoxic Upward Limiting Pressure Concept to NASA STD-6001 Test 1 | Olson et al. 2014 | 2014 | 11 | 926,963 | search | flammability-limit probabilities and normoxic upward limiting pressure (NASA-STD-6001 Test 1) | `PUBLIC_USE_PERMITTED` |
| `20080012607` | Effect of Pressure on Piloted Ignition Delay of PMMA | McAllister et al. 2008 | 2008 | 9 | 159,621 | search | effect of pressure on piloted ignition delay (exploration atmospheres) | `PUBLIC_USE_PERMITTED` |
| `20110008636` | Selected Parametric Effects on Materials Flammability Limits | Hirsch et al. 2011 | 2011 | 9 | 210,436 | search | effects of pressure, oxygen and thickness on material flammability limits | `GOV_PUBLIC_USE_PERMITTED` |
| `20150023467` | Material Ignition and Suppression Test (MIST) in Space Exploration Atmospheres, Summary of Research | Fernandez-Pello 2013 | 2013 | 14 | 725,156 | search | MIST: material ignition and suppression in exploration atmospheres | `PUBLIC_USE_PERMITTED` |
| `20070010766` | Technology Development for Fire Safety in Exploration Spacecraft and Habitats | Ruff et al. 2006 | 2006 | 14 | 285,679 | search | fire detection, suppression and response technology for exploration vehicles | `GOV_PUBLIC_USE_PERMITTED` |
| `20040161216` | Spacecraft Fire Suppression: Testing and Evaluation | Abbud-Madrid et al. 2004 | 2004 | 11 | 819,282 | search | testing and evaluation of spacecraft fire suppressants | `GOV_PUBLIC_USE_PERMITTED` |

All 21 have `distribution=PUBLIC`, `containsThirdPartyMaterial=false` and `exportControl=NO`.

### Skipped candidates
| NTRS id | Title | Reason |
|---|---|---|
| `20070013892` | The Microgravity Science Glovebox (MSG), a Resource for Gravity-Dependent Phenomena Research on the ISS (PSI-107 link) | PDF is 16.8 MB, over the 6 MB limit |
| `20150023456` | Detailed Results from the Flame Extinguishment Experiment (FLEX) March 2009 to December 2011 (PSI-69 link) | PDF is 42.9 MB, over the 6 MB limit |
| `20210011385` | Burning and Suppression of Solids–II (BASS-II) Summary Report | `determinationType=GOV_PERMITTED` (use by the U.S. Government only), so not public use |
| `20130010979` | Dynamics of Water Absorption and Evaporation During Methanol Droplet Combustion (PSI-69 link) | slide deck (presentation), left out in favour of papers |
| `20210015913`, `20180005168` | ACME ISS poster; Saffire un-manned spacecraft presentation | PDFs are 9.1 MB and 9.0 MB, over the limit |
| `20240002981`, `20240007488`, `20210011521`, `20210017780` | Saffire IV–VI results papers and presentations | `MAY_INCLUDE_COPYRIGHT_MATERIAL` |
| `20170007283`, `20150000894` | Spacecraft Fire Safety Research at NASA GRC; Large-Scale Spacecraft Fire Safety Tests | presentations with little text (48 pp / 11 k chars; 1 page) |

### Ingestion check (2026-11-07)
- `python -m flame_api.seed` on the shared PostgreSQL loaded 32 sources and 145 files.
- `python -m flame_api.ingest` then reported `pdf_documents=24`, `pdf_pages=284` and `pdf_chunks=275`, with 0 quarantined.
- All 24 NTRS documents are typed `technical_report` and take their title and identifier from the registry row.
- Pages without a text layer: `19990063738` pp. 17–18 and `20120015928` pp. 24–27 and 44, besides the known pp. 14–15 of `20080034883`. OCR was not available on this host.
- **Licence of the original three reports:** their NTRS records were read in this pass. They are `GOV_PUBLIC_USE_PERMITTED` (20000034017 and 20040053557) and `PUBLIC_USE_PERMITTED` (20080034883). Their registry `license` is still `null`, because their rows were not edited in this pass.

## Known limitations
See §2 and §4. The record pages and licences must be verified when connected.

## Changelog
- 1.1.0 (2026-11-07): 21 more NTRS reports (§5), selected from the PSI ISA-Tab citations and NTRS API searches; every one has a public-use permission determination.
- 1.0.0 (2026-10-12): first report; the sources are registered and ingested.
