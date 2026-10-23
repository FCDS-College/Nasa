| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.1.0 | 2026-10-12 | M11, D7 | `datasets/evaluation/rag_gold.jsonl`, `datasets/evaluation/gold_schema.json` |

# E5-2: Benchmark Datasheet

## 1. Dataset Summary & Governance

* **Dataset Name**: NASA Microgravity Combustion Evaluation Benchmark (`rag_gold.jsonl`)
* **Schema Definition**: `datasets/evaluation/gold_schema.json` (§18 compliant)
* **Total Instances**: 38 cases (35 curated cases plus 3 adversarial prompt-injection cases; verified against `datasets/evaluation/rag_gold.jsonl` on 2026-10-14)
* **Target Domain**: NASA Glenn Research Center microgravity combustion experiments (FLEX, ACME, SAFFIRE), NIST fire safety standards (NIST-SP-1200), and ISS safety protocols (NASA-STD-6001B).

---

## 2. Splits and Leakage Control

| Split | Count | Percentage | Document Scope | Leakage Protection |
|---|---|---|---|---|
| **dev** | 12 | 34.3% | `DOC-001`, `DOC-002`, `DOC-003`, `DOC-004`, `DOC-005`, `DOC-006`, `DOC-007`, `DOC-008`, `DOC-009` | Strict locator isolation verified by `test_no_document_leakage` in CI |
| **validation** | 12 | 34.3% | `DOC-004`, `DOC-007`, `DOC-010`, `DOC-011`, `DOC-012`, `DOC-013`, `DOC-014` | Disjoint document locators |
| **holdout** | 11 | 31.4% | `DOC-001`, `DOC-004`, `DOC-007`, `DOC-012`, `DOC-013`, `DOC-015` | Zero locator overlap with dev split |

*Leakage Verification*: Enforced via pytest assertion ensuring $\text{Evidence}(\text{dev}) \cap \text{Evidence}(\text{val}) = \emptyset$.

---

## 3. Question Taxonomies & Distribution

### By Category
* `microgravity_combustion`: 17 cases (spherical flame propagation, cool flame dynamics, droplet burning)
* `spacecraft_safety`: 5 cases (ISS fire suppression, oxygen concentration limits, emergency protocols)
* `nasa_materials`: 3 cases (flammability standards, insulation performance, NASA-STD-6001B)
* `propulsion`: 2 cases (RS-25 LOX/LH2 parameters, Mars propulsion comparison)
* `thermal_analysis`: 4 cases (heat shield ablation, emissivity, xEMU insulation)
* `unanswerable` (missing evidence): 4 cases (financial, personnel salary, non-corpus real-time weather)
* `adversarial` (prompt injection / safety bypass): 3 cases (jailbreaks, password extraction, home propellant recipes)

### By Modality
* `text`: 20 cases
* `image`: 8 cases (flame morphology, infrared pyrometry, Schlieren imaging)
* `table`: 7 cases (numerical comparison of LOI, combustion kinetics, sensor response times)

### By Difficulty
* `easy`: 12 cases
* `medium`: 12 cases
* `hard`: 11 cases

---

## 4. Authoring, Review & Changelog

* **Author**: Ziad (Engineer 5, AI Evaluation)
* **Domain Alignment Reviewers**: Anas (Lead), Eman (E1 - Retrieval/RAG), Princess (E3 - Multimodal/CV).
* **Changelog**:
  * `v0.1.0` (2026-10-12): Complete domain overhaul replacing legacy ship-fire cases with 35 NASA combustion items (§18 compliant schema).
