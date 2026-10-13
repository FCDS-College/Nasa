# E2-7: Source and dataset quality scoring

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2), with Ziad (E5) | Draft: awaiting the method authority (sign-off: Ziad E5) | 0.3.0 | 2026-10-12 | C4 | registry, `file_record`, `document.payload.ocr`, `evidence` |

**Method authority:** Ziad's `docs/evaluation/quality-rubrics.md` (E5-6, due Week 4). It is not written yet, so the dimensions below are a proposal. When it lands, this document will cite its version and adopt its weights.

## 1. Dimensions, signals and computation (proposal, `quality-v0.1`)

| Dimension | Signals (from data Flame already stores) | Score 0–1 |
|---|---|---|
| Provenance | DOI present; sha256 for every file; `retrieved_at`; `canonical_source_url` | fraction of the 4 present |
| Licence clarity | SPDX licence (1); `null` with reasoning in notes (0.5); `null` without (0) | as stated |
| Completeness | `known_file_count` vs files mirrored; pages with text / total pages | mean of the ratios |
| Extraction quality | 1 − (OCR pages flagged low-confidence / OCR pages); quarantined files / files | mean |
| Verification | `verified` 1, `partially_verified` 0.5, `needs_followup` 0 | as stated |
| Relevance | P0 1, P1 0.7, P2 0.3 (registry priority) | as stated |

Overall score = the mean of the dimensions, until Ziad's rubric sets weights.

## 2. Worked examples (with today's data)

| Source | Provenance | Licence | Completeness | Extraction | Verification | Relevance | Mean |
|---|---|---|---|---|---|---|---|
| `FF-PSI-69` | DOI ✓, sha256 ✓, retrieved ✓, URL ✓ → 1.0 | CC0-1.0 → 1.0 | mirrored subset of 6555 files: Pending (needs the mirror) | Pending | 1.0 | 1.0 | Pending |
| `FF-NTRS-20080034883` | no DOI, sha256 ✓, retrieved ✓, URL ✓ → 0.75 | null + reasoning → 0.5 | 1/1 files; 13/15 pages with text → (1 + 0.867)/2 = 0.93 | no OCR run, 0 quarantined → 1.0 | 0.5 | 0.7 | 0.73 |
| `FF-NIST-WEBBOOK` | DOI ✓, no files → 0.25 | 0.5 | n/a (reference only) | n/a | 0 | 0.7 | 0.36 (over 4 dimensions) |

## 3. Version

`quality-v0.1` (proposal). Every score must record the version used.

## Known limitations
These are not adopted scores: the method authority is pending. Several inputs need the git-ignored mirror to compute.

## Changelog
- 0.3.0 (2026-10-12): proposal with worked examples.
