# E2-9: NIST Chemistry WebBook dataset report

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | In review | 1.0.0 | 2026-10-12 | M9 (P1 source), E2-9 | registry row `FF-NIST-WEBBOOK` |

## 1. What the source is

The NIST Chemistry WebBook, NIST Standard Reference Database 69 (https://webbook.nist.gov/chemistry/), gives thermochemical, thermophysical and spectral data per species. For Flame it is a property reference: heats of combustion, vapour pressures and formation enthalpies of the fuels in PSI experiments (n-heptane, methanol, ethanol and others).

## 2. Access method and terms
- **Registered as `reference_only`, ingestion strategy `defer`, P1, `needs_followup`.**
- **Nothing is downloaded or scraped.** The site's terms of use and the Standard Reference Data Act (15 U.S.C. 290a) need review before any bulk access (MVP §7).
- **Persistent identifier recorded:** `doi:10.18434/T4D303`. To be re-verified when connected, since the row was registered offline.

## 3. File inventory

None: no files are mirrored. `known_file_count = null`.

## 4. Ingested / skipped

Nothing ingested, by design.

## 5. Planned use and limitations
- **Planned use:** a per-species lookup, done when connected, that stores the cited value with the species page URL, the access date and the SRD version as a `manual`-reviewed evidence row. It would give experiment conditions thermochemical context in answers.
- **Limitations:**
  - not available offline at all until values are stored;
  - licence terms are unreviewed;
  - WebBook values have their own uncertainty, which must be carried into evidence.

## Known limitations
See §5.

## Changelog
- 1.0.0 (2026-10-12): registered as a reference-only source.
