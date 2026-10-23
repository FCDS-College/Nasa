# E2-9: NTRS dataset report (3 technical reports)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | In review (peer sign-off: Ziad E5) | 1.0.0 | 2026-10-12 | M9, E2-9 | `docs/research/*.pdf`, registry rows `FF-NTRS-*`, `datasets/metadata/files.jsonl` |

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

## Known limitations
See §2 and §4. The record pages and licences must be verified when connected.

## Changelog
- 1.0.0 (2026-10-12): first report; the sources are registered and ingested.
