| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.1.0 | 2026-10-12 | M11, D7 | `datasets/evaluation/rag_gold.jsonl`, `datasets/evaluation/gold_schema.json` |

# E5-2: Benchmark Datasheet

## 1. Dataset Summary & Governance

* **Dataset Name**: NASA Microgravity Combustion Evaluation Benchmark (`rag_gold.jsonl`)
* **Schema Definition**: `datasets/evaluation/gold_schema.json` (§18 compliant)
* **Total Instances**: 38 cases: 31 answerable and 7 not (4 `unanswerable` plus 3 `adversarial` prompt-injection); counted from `datasets/evaluation/rag_gold.jsonl` on 2026-11-13. The evidence IDs (`DOC-001-P15`, ...) are not documents of the indexed corpus (they are absent from `datasets/registry/source_registry.csv`), so these cases cannot be answered from the index.
* **Target Domain**: NASA Glenn Research Center microgravity combustion experiments (FLEX, ACME, SAFFIRE), NIST fire safety standards (NIST-SP-1200), and ISS safety protocols (NASA-STD-6001B).

---

## 2. Splits and Leakage Control

| Split | Count | Percentage | Document Scope | Leakage Protection |
|---|---|---|---|---|
| **dev** | 14 | 36.8% | `DOC-001`, `DOC-002`, `DOC-003`, `DOC-004`, `DOC-005`, `DOC-006`, `DOC-007`, `DOC-008`, `DOC-009` | Page-level evidence IDs are unique per case (`test_no_evidence_id_leakage`); **documents are shared across splits** |
| **validation** | 14 | 36.8% | `DOC-001`, `DOC-002`, `DOC-003`, `DOC-004`, `DOC-007`, `DOC-010`, `DOC-011`, `DOC-012`, `DOC-013`, `DOC-014` | Shares `DOC-001`, `DOC-002`, `DOC-003`, `DOC-004`, `DOC-007` with dev |
| **holdout** | 10 | 26.3% | `DOC-001`, `DOC-004`, `DOC-007`, `DOC-012`, `DOC-013`, `DOC-015` | Shares `DOC-001`, `DOC-004`, `DOC-007` with dev and `DOC-012`, `DOC-013` with validation |

*Leakage Verification*: `test_no_evidence_id_leakage` checks page-level IDs, which are unique per case, so it cannot fail and shows nothing about documents. `test_no_document_leakage_between_splits` checks documents and is a strict expected failure (`xfail`) until the gold set is re-split by document.

---

## 3. Question Taxonomies & Distribution

### By Category
* `microgravity_combustion`: 16 cases (spherical flame propagation, cool flame dynamics, droplet burning)
* `spacecraft_safety`: 5 cases (ISS fire suppression, oxygen concentration limits, emergency protocols)
* `nist_standards`: 1 case
* `nasa_materials`: 3 cases (flammability standards, insulation performance, NASA-STD-6001B)
* `propulsion`: 2 cases (RS-25 LOX/LH2 parameters, Mars propulsion comparison)
* `thermal_analysis`: 4 cases (heat shield ablation, emissivity, xEMU insulation)
* `unanswerable` (missing evidence): 4 cases (financial, personnel salary, non-corpus real-time weather)
* `adversarial` (prompt injection / safety bypass): 3 cases (jailbreaks, password extraction, home propellant recipes)

### By Modality
* `text`: 22 cases
* `image`: 8 cases (flame morphology, infrared pyrometry, Schlieren imaging)
* `table`: 8 cases (numerical comparison of LOI, combustion kinetics, sensor response times)

### By Difficulty
* `easy`: 12 cases
* `medium`: 12 cases
* `hard`: 14 cases

---

## 4. Authoring, Review & Changelog

* **Author**: Ziad (Engineer 5, AI Evaluation)
* **Domain Alignment Reviewers**: Anas (Lead), Eman (E1 - Retrieval/RAG), Princess (E3 - Multimodal/CV).
* **Changelog**:
  * 2026-11-13: counts, splits and leakage statements corrected against the file (they were out of date); no case was changed.
  * `v0.1.0` (2026-10-12): Complete domain overhaul replacing legacy ship-fire cases with 35 NASA combustion items (§18 compliant schema).
