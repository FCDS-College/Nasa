# E2-6: Knowledge graph schema and entity registry

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | Draft: tables built, no extractor yet (peer sign-off: Eman E1) | 0.5.0 | 2026-10-12 | D2, D3, D6 | tables `knowledge_entity`, `knowledge_relation` (migration `0004`); ADR-007 |

Storage decision: [ADR-007](../architecture/adr/ADR-007-graph-storage.md) (Proposed). Relational tables in PostgreSQL first.

## 1. Entity types used in Phase 2 (a subset of D2)

| Type | Definition | Required properties | Synthetic example |
|---|---|---|---|
| `investigation` | A flight/ground investigation | `psi_id` or registry `source_id` | `FLEX` (`FF-PSI-69`) |
| `experiment` | One test/run | `experiment_id` (table `experiment`) | `FLEX-001` |
| `fuel` | Fuel or material | canonical name; formula when known | `n-heptane` (C7H16) |
| `condition_variable` | A controlled variable | unit dimension | `pressure` (Pa) |
| `phenomenon` | An observed behaviour | — | `cool flame`, `extinction` |
| `instrument` | Measurement hardware | — | `color camera` |
| `platform` | Where the experiment ran | — | `ISS`, `drop tower` |
| `document` | A source document | `document_id` | NASA/TM-2008-215260 |

## 2. Relationship types

| Predicate | Subject → object | Example |
|---|---|---|
| `part_of` | experiment → investigation | FLEX-001 → FLEX |
| `uses_fuel` | experiment → fuel | FLEX-001 → n-heptane |
| `has_condition` | experiment → condition_variable (value on the edge's `properties`, with `evidence_id`) | FLEX-001 → pressure {value_si: 101325} |
| `observed` | experiment → phenomenon | FLEX-001 → cool flame |
| `ran_on` | investigation → platform | FLEX → ISS |
| `measured_with` | investigation → instrument | |
| `describes` | document → investigation / experiment | |

## 3. Edge provenance fields

| Field | Meaning |
|---|---|
| `evidence_id` | the evidence row that supports the edge. Required for anything other than `manual` |
| `extraction_method` | `table_parse` (from experiment conditions), `nlp_extraction` (D1), `manual` |
| `extractor_version` | e.g. `psi-tables-0.1.0`, or the D1 pipeline version |
| `confidence` | 0–1. `1.0` for deterministic table parses; the model probability for NLP; `null` for manual |
| `review_status` | `unreviewed`, `human_verified`, `rejected`. Rejected edges are kept and excluded from retrieval. |
| `knowledge_version` | the version at extraction time |

## 4. Entity resolution, merge and ID stability
- **ID.** `entity_id = stable_ulid(entity_type + ":" + canonical_name)`, with the name lower-cased and whitespace-normalized. The same rule applies wherever the entity is referenced, including vector metadata ([L-5](../architecture/index-sync-contract.md)).
- **Aliases.** Spellings, formulas and acronyms go in `aliases`. Resolution matches the canonical name, then aliases, then (for fuels) the formula.
- **Merge.** Set the losing entity's `merged_into` to the winner, and re-point its edges in one transaction. Writes an `audit_event`. The merged row is kept, so old IDs still resolve.
- **Uniqueness.** `(entity_type, canonical_name)` is unique, and so is the edge `(subject, predicate, object, evidence_id)`.

## 5. Consistency checks (run after each publication; nightly once D2 writes)

| Check | Query sketch |
|---|---|
| Orphan edges | relations whose subject or object entity is missing, or is merged but not re-pointed |
| Edges with dead evidence | `evidence_id` not in `evidence` |
| Duplicate entities | same type, and normalized names or aliases colliding |
| Conflicting relations | same experiment, same `has_condition` variable, different `value_si` from different evidence |
| Unreviewed low-confidence edges | `confidence < 0.5 and review_status = 'unreviewed'` |

## Known limitations
No extractor writes these tables yet (D1/D2 are Weeks 4–5). The types above are a first subset; D2 may add more through a migration.

## Changelog
- 0.5.0 (2026-10-12): schema and rules; tables created by `0004`.
