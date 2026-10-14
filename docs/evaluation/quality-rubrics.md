| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.1.0 | 2026-10-12 | C4, C5 | `docs/evaluation/provenance_checklist.md` |

# E5-6: Data and Knowledge Quality Rubrics

## 1. Workstream C4: Data Quality Dimensions

| Dimension | Signal / Measurement Method | Required Input Data | Target Threshold |
|---|---|---|---|
| **Provenance** | SHA-256 verification, DOI/NASA-TM locator match | File headers, NTRS metadata | 100% locatable |
| **Completeness** | Non-empty text chunks, table dimension validity | Parsed document AST | Zero empty extractions |
| **Integrity** | Checksum validation against origin repository | Ingestion checksum logs | 100% hash parity |
| **Consistency** | Cross-chunk terminology unification (e.g. LOI vs OI) | Ontology mapping dictionary | $\ge 0.95$ agreement |
| **Scientific Relevance** | Microgravity combustion taxonomy mapping | Keyword & embedding filter | 100% domain relevance |
| **Temporal Relevance** | Publication date vs mission lifecycle | Document date metadata | Current versioning |
| **Label Quality** | IAA score on human annotated gold subsets | Multi-annotator masks | Cohen's $\kappa \ge 0.70$ |
| **Suitability** | OCR confidence and image resolution | Ingestion raw assets | OCR confidence $> 85\%$ |

---

## 2. Workstream C5: Knowledge Record Types

Knowledge extraction records are classified into five explicit typologies:
1. `source-reported`: Explicitly stated facts in peer-reviewed NASA/NIST technical publications.
2. `machine-extracted`: Triples derived by automated LLM or entity recognition pipelines.
3. `derived`: Computational inferences calculated from formulas or tables.
4. `model-generated`: Predictive assertions produced by generative models.
5. `hypothesis`: Speculative or unverified scientific postulates.

---

## 3. Independent Corroboration Rule

To prevent echo-chamber validation where multiple documents cite the same single experiment:
* Duplicate claims originating from identical primary technical reports (e.g., identical author, test campaign, date) are grouped into a single provenance node.
* A claim is corroborated only if supported by $\ge 2$ independent experimental campaigns or distinct research facilities.
