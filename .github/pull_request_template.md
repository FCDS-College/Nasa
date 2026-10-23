## Summary
<!-- What changes and why. Link the plan item(s): M#, A#–D#, 2H Task #, G-/L-/H-/E2- doc IDs. -->

## Plan items
- 

## Documentation checklist (G-2)
- [ ] The docs this change affects are updated in this PR. A behaviour change without its docs is not merged.
- [ ] Numbers in docs come from a command or query, and the command is quoted next to them.
- [ ] Each changed doc has its header block (Owner, Status, Version, Last updated, Plan items, Code paths) and a Changelog entry.
- [ ] Each changed doc ends with **Known limitations** (or **Consequences** for an ADR).
- [ ] API change: route + `docs/api/openapi.json` + `docs/api/CHANGELOG.md`; `python docs/tools/render_api_schemas.py` run.
- [ ] Schema change: migration ID named below, and `docs/data/DATA_DICTIONARY.md` updated.
- [ ] New decision: an ADR in `docs/architecture/adr/`.
- [ ] `docs/README.md` index updated if a document was added, renamed or changed status.
- [ ] No secrets, tokens or connection strings (env vars by name only).

## Migration
<!-- e.g. 0004_phase2_tables, or "none" -->

## Validation commands run
```text
python -m pytest
ruff check .
python knowledge/ingestion/validate_registry.py
```

## Reviewer (from the review matrix in docs/README.md)
