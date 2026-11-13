# E2-6: Knowledge graph schema and entity registry

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Anas (E2) | Current: built from the PSI tables (peer sign-off: Eman E1) | 0.6.2 | 2026-11-12 | D2, D3, D6, ADR-007 | `apps/api/flame_api/knowledge_graph.py`, `graph.py`; tables `knowledge_entity`, `knowledge_relation` (migration `0004`) |

Storage decision: [ADR-007](../architecture/adr/ADR-007-graph-storage.md) (Accepted). Relational tables in PostgreSQL first.

## 0. What is built (2026-11-12)

`flame_api/knowledge_graph.py` (`psi-tables-graph-1.0.0`) builds the graph from what the ingested tables record. Every edge is a deterministic `table_parse` with confidence 1.0, citing the evidence row it was read from. It runs at the end of every `python -m flame_api.ingest`; a graph failure is logged and counted (`graph_build_failed`) and never undoes the ingestion.

| Edge | Read from | Evidence cited |
|---|---|---|
| experiment `part_of` investigation | `experiment.investigation` | the row's test-ID cell (`flex_identifier`, `test`, `sample_number`); SPICE has no test-ID column, so its fuel cell |
| experiment `uses_fuel` fuel | `experiment.fuel_or_material` | the fuel / material cell |
| experiment `has_condition` condition_variable | every other `experiment_condition` cell; `value_si`, `unit_si`, `value_numeric`, `value_text`, `unit_original`, `origin` on the edge | that cell |
| experiment `observed` phenomenon | FLEX `test_end` (Extinction, Disruption, Completion) | that cell |
| document `describes` investigation | the ISA-Tab investigation record of the same PSI source | its first passage |

From the committed tables and metadata (`python -m flame_api.knowledge_graph build`, 2026-11-12, PostgreSQL 16):

| Entities | Count | Edges | Count |
|---|---|---|---|
| experiment | 840 | `part_of` | 840 |
| fuel (fuels and solid materials) | 55 | `uses_fuel` | 840 |
| condition_variable | 45 | `has_condition` | 8,725 |
| investigation | 4 | `observed` | 274 |
| document | 4 | `describes` | 4 |
| phenomenon | 3 | **total** | **10,683** |

A rebuild of that data takes about 0.6 s and changes nothing. Ingesting the tables into an empty SQLite database and building gives the same counts (`apps/api/tests/test_knowledge_graph.py`).

**From NLP records (D1, `flame_api/nlp_graph.py`, `nlp-cooccurrence-1.0.0`).** `platform` (`ran_on`), `instrument` (`measured_with`) and `describes` links from the NTRS reports are not in the tables. They come from the stored NLP records (`nlp_record`, migration `0010`), always `unreviewed`, `extraction_method = "nlp_extraction"`, confidence the lower of the two records', evidence the page both were read from:

| Edge | When | `properties.basis` |
|---|---|---|
| investigation `ran_on` platform | one investigation and a platform are named on the same page | `co_occurrence_in_chunk` |
| investigation `measured_with` instrument | one investigation and an instrument are named on the same page | `co_occurrence_in_chunk` |
| document `describes` investigation | a document that is not dataset documentation names exactly one investigation on its first page | `named_in_document` |

These are associations, not findings: "FLEX" and "International Space Station" on one page does not say the experiment flew there. A page that names two investigations is ambiguous and yields no edge; an investigation the tables do not know is skipped, never created. A table rebuild never touches these edges and an NLP rebuild never touches table edges (`knowledge_graph._Builder.write_edges(method=…)`). Run `python -m flame_api.nlp_extract run` then `python -m flame_api.nlp_graph build`; `python -m flame_api.ingest` does both after the graph build and a failure is counted (`nlp_extract_failed`), never fatal.

**Reading it.**
- `GET /api/graph/entities?type=&q=` (read scope): live entities, with relation counts.
- `GET /api/graph/entities/{id}?depth=1..3&predicate=…&max_edges=` (read scope): the entity and its neighbourhood, found with one `WITH RECURSIVE` CTE over both edge directions. It follows `merged_into`, skips rejected edges, returns nearest first, and reports `truncated` and `reachable_by_type`. Example: from `extinction`, two hops over `observed` and `uses_fuel` reach the 186 FLEX tests that ended in extinction and their two fuels, heptane and methanol (24 ms on PostgreSQL).
- Both are AURA tools at contract 0.6.0 (`api_list_graph_entities`, `api_get_graph_entity`).
- The web app's **Knowledge Graph** page (`/knowledge`) browses them: filter by type, search names and aliases, open an entity, walk 1–2 hops by link type, and open the evidence cell behind every link.

**Checking and merging.**
- `python -m flame_api.knowledge_graph check`, or `GET /api/admin/graph/consistency` (admin scope), runs §5. Today all five checks find nothing. The check first found 4 duplicate candidates, which are real spelling variants in the source tables. The Lead approved resolving them on 2026-11-12 (`CURATED_ALIASES` below).
- `python -m flame_api.knowledge_graph merge LOSER WINNER --actor NAME` applies §4 to one database and writes `audit_event` (`graph.entity.merge`). Nothing is merged automatically.
- **Reviewed spelling variants** are resolved in code, not in one database, so every deployment agrees. `knowledge_graph.CURATED_ALIASES` maps a variant's canonical name to the reviewed one. The build resolves the variant to that entity, keeps the variant's spelling as an alias, and still cites the variant's own cell. The four approved on 2026-11-12, each keeping the spelling with more tests:

  | Variant (tests) | Resolved to (tests) | Table |
  |---|---|---|
  | `1/4 black rod` (2) | `1/4" black rod` (12) | BASS-II |
  | `1/4 clear rod` (1) | `1/4" clear rod` (15) | BASS-II |
  | `3/8"clear rod` (2) | `3/8" clear rod` (5) | BASS-II |
  | `75% Propylene` (16) | `75 % Propylene` (115) | SPICE |

  The graph therefore has 55 fuel entities, not 59, and 951 entities in all. Applying this to an existing database re-pointed 21 edges and dropped the 4 variant entities on the next rebuild. A new variant needs the same review: add a row and say why.


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
| `extraction_method` | `table_parse` (from experiment conditions and ISA-Tab records; the only one in use), `nlp_extraction` (D1: `flame_api/nlp_graph.py`, unreviewed associations), `manual` |
| `extractor_version` | `psi-tables-graph-1.0.0` for table edges, `nlp-cooccurrence-1.0.0` for NLP edges |
| `confidence` | 0–1. `1.0` for deterministic table parses; the model probability for NLP; `null` for manual |
| `review_status` | `unreviewed`, `human_verified`, `rejected`. Rejected edges are kept and excluded from retrieval. |
| `knowledge_version` | the version at extraction time |

## 4. Entity resolution, merge and ID stability
- **ID.** `entity_id = stable_ulid(entity_type + ":" + canonical_name)`, with the name lower-cased and whitespace-normalized. The same rule applies wherever the entity is referenced, including vector metadata ([L-5](../architecture/index-sync-contract.md)).
- **Aliases.** Spellings, formulas and acronyms go in `aliases`. Resolution matches the canonical name, then aliases, then (for fuels) the formula.
- **Merge.** Set the losing entity's `merged_into` to the winner, and re-point its edges in one transaction (an edge the winner already has is dropped). The loser's names become the winner's aliases. Writes an `audit_event`. The merged row is kept, so old IDs still resolve, and a rebuild resolves to the winner instead of recreating the loser's edges (edges are matched by subject, predicate, object and evidence, not by ID).
- **Uniqueness.** `(entity_type, canonical_name)` is unique, and so is the edge `(subject, predicate, object, evidence_id)`.

## 5. Consistency checks (`knowledge_graph check`; `GET /api/admin/graph/consistency`)

| Check | Query sketch |
|---|---|
| Orphan edges | relations whose subject or object entity is missing, or is merged but not re-pointed |
| Edges with dead evidence | `evidence_id` not in `evidence` |
| Duplicate entities | same type, names or aliases equal once everything but letters and digits is dropped (non-blocking: candidates for a human merge) |
| Conflicting relations | same experiment, same `has_condition` variable, different `value_si` from different evidence |
| Unreviewed low-confidence edges | `confidence < 0.5 and review_status = 'unreviewed'` (non-blocking) |

`ok` is false when a blocking check (orphans, dead evidence, conflicts) finds anything; `check` then exits 1. Checks run on demand, not on a schedule.

## Known limitations
Table edges are only what the tables record. NLP edges (platforms, instruments, report links) are co-occurrence on one page and stay unreviewed until a person confirms them. Condition variables are the tables' own column names (`ambient_pressure_mmhg`, `percent_o2`), not unified physical quantities, so "pressure" in FLEX and SPICE are different entities. Fuels keep the tables' spellings unless a reviewed alias says otherwise; new variants are flagged, never merged automatically. Graph RAG (using the graph in chat retrieval, `docs/ai/graph-rag.md`) is not built. The consistency checks are not scheduled.

## Changelog
- 0.6.2 (2026-11-12): the web Knowledge Graph page reads the graph API.
- 0.6.1 (2026-11-12): the four spelling variants resolved by reviewed aliases (Lead's approval); 55 fuels, 951 entities.
- 0.6.0 (2026-11-12): built (ADR-007): extractor, recursive-CTE traversal, consistency checks, audited merge, read API; §0 records what is extracted and the counts.
- 0.5.0 (2026-10-12): schema and rules; tables created by `0004`.
