# ADR-012: Commit the PSI experimental tables and ISA-Tab metadata to Git

- **Status:** Accepted (2026-11-07). Decision owner: Anas (E2, data / knowledge base), with the Lead. Signed off by Princess (E3, the CV team also relies on `datasets/raw/`) and Ziad (E5, reproducible evaluation) on 2026-11-07, as confirmed by the Lead (ADR index 1.2.0).
- **Date:** 2026-11-07
- **Implemented in:** commits `a187292` and `bade1f2` (PR #24): `.gitignore`, `.gitattributes`, `.dockerignore`, `apps/api/Dockerfile`, `knowledge/ingestion/install_datasets.py` (`--only tables`).

## Context

Until 2026-11-07, all mirrored NASA data lived outside Git. The rule was "`datasets/raw/` is git-ignored; immutable originals live outside Git" (`docs/data/DAY1_DATA_ACQUISITION.md`, `OFFLINE_DATA_AND_SYNC.md` §1). `install_datasets.py` rebuilt the mirror from psi.nasa.gov and verified each file against `datasets/checksums/sha256.txt`. The rule is right for media: BASS-II and FLEX raw data are 274.6 GB and 923.8 GB in full, and the pilot mirror alone is about 3.1 GB.

It had one consequence nobody had measured. **The experiment workflow depends on four small CSV files that only arrived inside that 3.1 GB download.** The 2026-11-07 audit found:

- **A fresh clone, CI's migration job and the API image all ingested 0 experiments.** `ingest._create_table_experiments` reads `datasets/raw/psi_api/*/Experimental table/*.csv`, and `ingest_file` skips missing files as `not_on_disk`.
- **The test that covers table ingestion skipped itself** ("PSI table mirror … is not present on this machine"), so CI never exercised it.
- **The new fire-safety features need these files.** The investigation ranking (ADR-011), the computed insights and the FLEX outcome model all need the 876 flight-test rows. The summaries need the ISA-Tab metadata zips, which hold NASA's objective, hypothesis, approach and publication list per investigation.
- **The outcome model's training data must be reproducible from the repository**, so that `python -m ai.fire_safety.train_flex_outcome --check` can prove the committed artefact.
- **Demo-day risk.** A demo machine without network access to psi.nasa.gov would show an empty dashboard.

## Decision

Commit exactly these eight NASA originals, byte-for-byte as published, and keep every other file under `datasets/raw/` out of Git:

| Investigation | Experimental table | ISA-Tab metadata zip |
|---|---|---|
| BASS-II (FF-PSI-25) | `PSI-25_Experimental table_BASS-II.csv`, 16,590 B | 13,439 B |
| FLEX (FF-PSI-69) | `PSI-69_Experimental table_FLEX.csv`, 24,776 B | 24,780 B |
| SAFFIRE-I (FF-PSI-98) | `PSI-98_Experimental table_SAFFIRE-1.csv`, 469 B | 10,031 B |
| SPICE (FF-PSI-107) | `PSI-107_Experimental table_Spice.csv`, 31,205 B | 9,313 B |

That is **130,603 bytes in total**. All four sources are **CC0-1.0** with a DOI (`datasets/registry/source_registry.csv`).

How the exception is made safe:

1. **Narrow allow-list, not a broad un-ignore.** `.gitignore` ignores `datasets/raw/**`, re-includes directories so Git can traverse them, and then re-includes only `psi_api/*/Experimental table/*.csv` and `psi_api/*/metadata/*.zip`. A full local mirror (media, documents, 3+ GB) stays ignored. `.dockerignore` uses the same two exceptions, so the API image ships the tables and never a raw mirror.
2. **Byte-exact on every OS.** `.gitattributes` marks `datasets/raw/** -text`. The CSVs are published with CRLF line endings, and FLEX is Windows-1252. Without this, a checkout with `core.autocrlf` could rewrite them, and their SHA-256 would no longer match `sha256.txt`, the provenance records or the model's `training_data.sha256`.
3. **Provenance unchanged.** Each file keeps its existing records:
   - its record in `datasets/metadata/files.jsonl` (source URL, retrieval time, size, SHA-256);
   - its line in `datasets/checksums/sha256.txt`.

   The committed bytes were checked against both before committing. `install_datasets.py --verify-only` verifies them like any other mirrored file.
4. **Immutability preserved.** The files are originals, never edited. Parsing rules live in code (`ingest.py`, `ai/fire_safety/flex.py`); the CSVs are not cleaned. Examples: cp1252 decoding, the en dash as a missing value, 0 mmHg treated as not physical, and duplicate SPICE rows removed as a recorded transformation.
5. **Re-fetchable.** `python knowledge/ingestion/install_datasets.py --only tables` downloads just these eight files from psi.nasa.gov and verifies them. If NASA publishes a new version, the update is an ordinary reviewed commit that changes the file, its provenance record and its checksum together.
6. **Shipped in the image.** `apps/api/Dockerfile` copies `datasets/raw/psi_api`, so the Railway pre-deploy and compose start-up ingest all 840 experiments without network access.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Keep everything out of Git; tell people to run `install_datasets.py` | That is the status quo, which produced 0 experiments in CI, in the image and on fresh clones. Each environment needs network access to psi.nasa.gov at build or start time, and demo machines are exactly where that can fail. |
| Download the tables in CI and at image build | It adds a network dependency to every build. It does not help a laptop clone, and an outage of psi.nasa.gov (whose signed URLs expire) would break builds that have nothing to do with data. |
| Commit a cleaned or normalized derivative (e.g. Parquet with SI units) instead of the originals | That breaks the "originals are immutable; derived artefacts have a parent" rule and the checksum chain to NASA's published bytes. Parsing decisions belong in reviewed code, where they are tested. |
| Git LFS | It is unnecessary at 130 KB, adds a tool every contributor and CI job must install, and LFS objects are not in a plain clone or a GitHub archive. |
| Commit the whole pilot mirror | 3.1 GB, over GitHub's limits, and mostly media the experiment workflow does not need. |
| Embed the tables as Python or JSON fixtures | It duplicates the data in a second format and loses the byte-level link to the published file. |

## Consequences

- **Positive.**
  - Every clone, CI job and image ingests the same 840 flight tests and 4 investigation records.
  - The table-ingestion test now runs in CI instead of skipping.
  - The FLEX model can be retrained and checked from the repository alone.
  - The demo works offline.
- **Repository size.** It grows by about 128 KiB, which is negligible against a 105 MiB pack.
- **Two places hold these files:** Git and any local full mirror. Paths are identical (`datasets/raw/psi_api/…`), so the installer's resume-and-verify logic treats a committed file as already installed.
- **Licence obligation.** CC0 imposes none, but the registry `license` field must stay CC0 for any file added under this exception. A non-CC0 or restricted source needs its own decision.
- **Scope discipline.** The exception covers experimental tables and ISA-Tab metadata only. Adding another file class under `datasets/raw/`, or a file over about 1 MB, needs a new ADR that supersedes or extends this one. The `.gitignore`, `.dockerignore` and `.gitattributes` patterns must change together.
- **Updates are visible.** A changed NASA table appears as a diff with changed checksums. Because the experiment, evidence and condition IDs include the file hash, re-ingesting a new version creates new IDs rather than silently overwriting old evidence.

## Links

- Data: `datasets/registry/source_registry.csv`, `datasets/metadata/files.jsonl`, `datasets/checksums/sha256.txt`, `docs/data/COMBUSTION_DATASET_ANALYSIS.md` §3, `docs/data/OFFLINE_DATA_AND_SYNC.md`
- Code: `apps/api/flame_api/ingest.py` (`_create_table_experiments`, `parse_isatab`), `knowledge/ingestion/install_datasets.py`, `ai/fire_safety/flex.py`
- Tests: `apps/api/tests/test_ingestion.py` (`test_committed_psi_tables_are_present_so_a_fresh_clone_has_experiments`, `test_mirrored_psi_tables_are_ingested_with_provenance_and_stable_ids`, `test_isatab_metadata_becomes_a_citable_investigation_document`), `apps/api/tests/test_fire_safety_api.py` (`test_committed_artefact_matches_its_evaluation_report_and_training_table`)
- Related: [ADR-001](ADR-001-monorepo-layout.md) (monorepo layout), [ADR-011](ADR-011-scenario-relevance-ranking.md) (ranking that consumes these tables)

## Note (2026-11-14): current counts

The decision is unchanged. The counts above (840 flight tests, 4 investigation records, "eight files", about 130 KB) describe the four tables committed on 2026-11-07. Under the same exception, `main` now commits 22 experimental tables and 24 ISA-Tab metadata files from 24 PSI sources (513,175 B, measured with `git ls-files` and `stat`), still CC0 and still well under the 1 MB per-file limit. A fresh clone, CI job or image now ingests:

- **1958 table experiments**: `apps/api/tests/test_ingestion.py` (`after == before == 1958`);
- of which **1950 flight tests from 19 PSI investigations**: `apps/api/tests/test_fire_safety_api.py` (`totals == {"investigations": 19, "with_data": 19, "flight_tests": 1950}`). The other 8 rows are the Cool-flame transitions ground study (FF-PSI-142), which the coverage verdict does not count as flight tests.

The original text above is kept as written, per the ADR index rule on dated notes.
