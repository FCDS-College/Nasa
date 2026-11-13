| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.1.0 | 2026-10-12 | C1, C2, C3, M11 | `tests/eval/metrics.py`, `tests/eval/master_pipeline.py` |

# E5-1: Evaluation Plan and Metric Definitions

## 1. Overview and Quality Taxonomy

In Phase 2 of the NASA Advanced Scientific Intelligence Platform, evaluation is decoupled into four distinct, non-overlapping quality dimensions:
1. **Data Quality**: Ingestion fidelity, locator resolution, schema validity, and document provenance.
2. **Knowledge Quality**: Claim veracity, entity linkage, triple consistency, and corroboration score.
3. **Model Quality**: Task-level algorithmic performance (retrieval precision, generation faithfulness, segmentation IoU/Dice).
4. **Answer Quality**: End-to-end user experience (citation precision, latency, abstention correctness, format compliance).

No single aggregate metric is used to promote a model or declare a release gate passed.

---

## 2. Metric Specifications

### 2.1 Retrieval Metrics

#### Recall@K
* **Definition**: Fraction of expected ground-truth evidence items found in the top-K retrieved documents.
* **Formula**:
  $$\text{Recall@K} = \frac{|\text{Retrieved}_{1..K} \cap \text{Expected}|}{|\text{Expected}|}$$
* **Inputs**: `retrieved_ids: List[str]`, `expected_ids: List[str]`, $K \in \{3, 5, 10\}$.
* **Code Implementation**: `tests.eval.metrics.compute_recall_at_k(retrieved_ids, expected_ids, k=5)`
* **Provisional Threshold**: $\ge 0.80$ at $K=5$.

#### Mean Reciprocal Rank (MRR)
* **Definition**: Reciprocal of the rank position of the first relevant document.
* **Formula**:
  $$\text{MRR} = \frac{1}{\min \{r : \text{Retrieved}[r] \in \text{Expected}\}}$$
* **Code Implementation**: `tests.eval.metrics.compute_mrr(retrieved_ids, expected_ids)`
* **Provisional Threshold**: $\ge 0.70$.

#### Normalized Discounted Cumulative Gain (nDCG@K)
* **Definition**: Ranking quality accounting for position discount under binary relevance.
* **Formula**:
  $$\text{DCG@K} = \sum_{i=1}^K \frac{rel_i}{\log_2(i+1)}, \quad \text{nDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}$$
* **Code Implementation**: `tests.eval.metrics.compute_ndcg_at_k(retrieved_ids, expected_ids, k=5)`
* **Provisional Threshold**: $\ge 0.75$.

---

### 2.2 Generation and Groundedness Metrics

#### Citation Precision, Recall, and F1
* **Definition**: Extent to which cited evidence matches the ground truth locators, and all necessary claims are attributed.
* **Code Implementation**: `tests.eval.metrics.compute_citation_metrics(cited_ids, expected_ids)`
* **Provisional Threshold**: F1 $\ge 0.75$.

#### Unsupported-Claim Rate (Hallucination)
* **Definition**: Percentage of atomic assertions in the response not supported by retrieved context.
* **Provisional Threshold**: $\le 0.05$ (strict safety limit).

#### Abstention Correctness
* **Definition**: Binary compliance when query is unanswerable or adversarial (must decline without hallucinating).
* **Code Implementation**: `tests.eval.master_pipeline.MasterSafetyPipeline.process_and_validate`
* **Provisional Threshold**: $100\%$ on holdout missing-evidence/injection cases.

---

### 2.3 Computer Vision Metrics (with Princess / E3)

#### Intersection over Union (IoU) and Dice Coefficient
* **Definition**: Flame/soot boundary segmentation overlap against annotated ground-truth masks.
* **Formula**:
  $$\text{IoU} = \frac{|A \cap B|}{|A \cup B|}, \quad \text{Dice} = \frac{2 |A \cap B|}{|A| + |B|}$$
* **Provisional Threshold**: IoU $\ge 0.70$, Dice $\ge 0.80$.

---

## 3. Human vs Deterministic Evaluation Protocol

* **Deterministic**: Recall@K, MRR, nDCG@K, citation locator match, latency, schema compliance. The unit tests of these metrics run in CI (`python -m pytest`); `run_evaluation.py` itself is not run in CI.
* **Human Review Required**: Answer clarity, cross-document reasoning subtlety, visual anomaly interpretation, and subtle hallucination detection.

---

## 4. Known Limitations and Threats to Validity

1. **Synthetic & Heuristic Proxies**: Until production annotations from E1/E3 are ingested, heuristics approximate human judgements.
2. **Gold Set Sample Size**: Currently 38 cases (35 curated plus 3 adversarial); target is $\ge 100$ cases in Phase 2 Week 2.
3. **Judge Bias**: Prompt-based judges may favor verbose responses unless strictly penalized.
