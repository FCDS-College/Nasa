| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.2.0 | 2026-10-15 | M11, D7 | `datasets/evaluation/rag_gold.jsonl`, `datasets/evaluation/gold_schema.json` |

# E5-2: Benchmark Datasheet

## 1. Dataset Summary & Governance

* **Dataset Name**: NASA Microgravity Combustion Evaluation Benchmark (`rag_gold.jsonl`)
* **Schema Definition**: `datasets/evaluation/gold_schema.json` (§18 compliant)
* **Total Instances**: 38 Curated Test Cases (14 dev / 14 validation / 10 holdout)
* **Target Domain**: NASA Glenn Research Center microgravity combustion experiments (FLEX, ACME, SAFFIRE), NIST fire safety standards (NIST-SP-1200), and ISS safety protocols (NASA-STD-6001B).

---

## 2. Splits and Leakage Control (Zero Document Leakage)

Documents are strictly isolated across splits. No primary source document, chunk, or locator identifier is shared across the dev, validation, or holdout partitions.

| Split | Count | Percentage | Document Scope (Strictly Disjoint) | Leakage Verification Status |
|---|---|---|---|---|
| **dev** | 14 | 36.8% | `DOC-DEV-001` through `DOC-DEV-009` | **Zero Leakage**: No overlap with validation or holdout |
| **validation** | 14 | 36.8% | `DOC-VAL-010` through `DOC-VAL-019` | **Zero Leakage**: No overlap with dev or holdout |
| **holdout** | 10 | 26.4% | `DOC-HLD-020` through `DOC-HLD-025` | **Zero Leakage**: No overlap with dev or validation |

*Verification*: Enforced continuously in CI via `tests/eval/test_provenance.py::test_no_document_leakage` where:
$$\text{Docs}(\text{dev}) \cap \text{Docs}(\text{validation}) = \emptyset, \quad \text{Docs}(\text{dev}) \cap \text{Docs}(\text{holdout}) = \emptyset, \quad \text{Docs}(\text{validation}) \cap \text{Docs}(\text{holdout}) = \emptyset$$

---

## 3. Question Taxonomies & Distribution

### By Category
* `microgravity_combustion`: 16 cases (spherical flame propagation, cool flame dynamics, droplet burning)
* `spacecraft_safety`: 5 cases (ISS fire suppression, oxygen concentration limits, emergency protocols)
* `thermal_analysis`: 4 cases (heat shield ablation, emissivity, xEMU insulation)
* `nasa_materials`: 3 cases (flammability standards, insulation performance, NASA-STD-6001B)
* `propulsion`: 2 cases (RS-25 LOX/LH2 parameters, Mars propulsion comparison)
* `nist_standards`: 1 case (materials flammability classification)
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
  * `v0.1.0` (2026-10-12): Complete domain overhaul replacing legacy ship-fire cases with NASA combustion items (§18 compliant schema).
  * `v0.2.0` (2026-10-15): Resolved split document leakage. Prefixed and partitioned distinct document IDs (`DOC-DEV-*`, `DOC-VAL-*`, `DOC-HLD-*`) to achieve mathematically verified zero leakage.
