| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.2.0 | 2026-10-15 | C1, C2, C3, M11 | `tests/eval/metrics.py`, `tests/eval/cv_metrics.py`, `tests/eval/master_pipeline.py` |

# E5-1: Evaluation Plan and Metric Definitions

## 1. Overview and Quality Taxonomy

In Phase 2 of the NASA Advanced Scientific Intelligence Platform, evaluation is decoupled into four distinct, non-overlapping quality dimensions:
1. **Data Quality (C4)**: Ingestion fidelity, locator resolution, schema validity, and document provenance.
2. **Knowledge Quality (C5)**: Claim veracity, entity linkage, triple consistency, and independent corroboration.
3. **Model Quality (C2 & M10)**: Task-level algorithmic performance (retrieval precision, generation faithfulness, segmentation IoU/Dice).
4. **Answer Quality (C1 & C3)**: End-to-end user experience (citation precision, latency, abstention correctness, format compliance).

No single aggregate metric is used to promote a model or declare a release gate passed.

---

## 2. Exhaustive Metric Definitions and Mathematical Formulas

### 2.1 Information Retrieval Metrics (RAG Subsystem)

#### 1. Recall@K
* **Mathematical Formula**:
  $$\text{Recall@K} = \frac{|\text{Retrieved}_{1..K} \cap \text{Expected}|}{|\text{Expected}|}$$
* **Inputs**: `retrieved_ids: List[str]`, `expected_ids: List[str]`, $K \in \{3, 5, 10\}$.
* **Tie Handling**: When multiple candidates share identical dense/lexical scores, ties are resolved deterministically using document authority ranking (NASA-TM > NIST > other).
* **Code Implementation**: `tests.eval.metrics.compute_recall_at_k(retrieved_ids, expected_ids, k=5)`
* **Provisional Gate Threshold**: $\ge 0.80$ at $K=5$.

#### 2. Precision@K
* **Mathematical Formula**:
  $$\text{Precision@K} = \frac{|\text{Retrieved}_{1..K} \cap \text{Expected}|}{K}$$
* **Inputs**: `retrieved_ids: List[str]`, `expected_ids: List[str]`, $K \in \{3, 5, 10\}$.
* **Code Implementation**: `tests.eval.metrics.compute_precision_at_k`
* **Provisional Gate Threshold**: $\ge 0.60$ at $K=5$.

#### 3. Mean Reciprocal Rank (MRR)
* **Mathematical Formula**:
  $$\text{MRR} = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \frac{1}{\text{rank}_q}$$
  Where $\text{rank}_q$ is the position of the first ground-truth relevant document for query $q$. If no relevant document is retrieved, reciprocal rank is $0$.
* **Inputs**: `retrieved_ids: List[str]`, `expected_ids: List[str]`.
* **Code Implementation**: `tests.eval.metrics.compute_mrr(retrieved_ids, expected_ids)`
* **Provisional Gate Threshold**: $\ge 0.70$.

#### 4. Normalized Discounted Cumulative Gain (nDCG@K)
* **Mathematical Formula**:
  $$\text{DCG@K} = \sum_{i=1}^K \frac{2^{rel_i} - 1}{\log_2(i + 1)}, \quad \text{nDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}$$
  Under binary relevance ($rel_i \in \{0, 1\}$):
  $$\text{DCG@K} = \sum_{i=1}^K \frac{rel_i}{\log_2(i + 1)}$$
* **Inputs**: Binary relevance array of top-K retrieved documents.
* **Code Implementation**: `tests.eval.metrics.compute_ndcg_at_k(retrieved_ids, expected_ids, k=5)`
* **Provisional Gate Threshold**: $\ge 0.75$.

---

### 2.2 Generation and Groundedness Metrics

#### 5. Citation Precision, Recall, and F1 Score
* **Mathematical Formulas**:
  $$\text{Precision}_{\text{cit}} = \frac{|\text{Cited} \cap \text{Expected}|}{|\text{Cited}|}, \quad \text{Recall}_{\text{cit}} = \frac{|\text{Cited} \cap \text{Expected}|}{|\text{Expected}|}$$
  $$\text{F1}_{\text{cit}} = \frac{2 \cdot \text{Precision}_{\text{cit}} \cdot \text{Recall}_{\text{cit}}}{\text{Precision}_{\text{cit}} + \text{Recall}_{\text{cit}}}$$
* **Inputs**: `cited_ids: List[str]`, `expected_ids: List[str]`.
* **Code Implementation**: `tests.eval.metrics.compute_citation_metrics(cited_ids, expected_ids)`
* **Provisional Gate Threshold**: F1 $\ge 0.75$.

#### 6. Unsupported-Claim Rate (Hallucination Rate)
* **Mathematical Formula**:
  $$\text{UCR} = \frac{|\text{Atomic Claims Not Grounded in Context}|}{|\text{Total Atomic Claims Generated}|}$$
* **Inputs**: Extracted atomic proposition triples vs context passage.
* **Code Implementation**: `tests.eval.master_pipeline.LLMJudge.evaluate_faithfulness`
* **Provisional Gate Threshold**: $\le 0.05$ (Critical Scientific Gate).

#### 7. Abstention Correctness
* **Mathematical Formula**:
  $$\text{AC} = \frac{\sum_{q \in Q_{\text{unans}} \cup Q_{\text{adv}}} \mathbb{I}(\text{Answer is Safe Abstention})}{|Q_{\text{unans}}| + |Q_{\text{adv}}|}$$
* **Inputs**: Evaluation against unanswerable cases and adversarial prompt-injection cases.
* **Code Implementation**: `tests.eval.master_pipeline.MasterSafetyPipeline`
* **Provisional Gate Threshold**: $100\%$ compliance on holdout benchmark.

---

### 2.3 Computer Vision Segmentation Metrics (Workstream M10 with Princess)

#### 8. Intersection over Union (IoU)
* **Mathematical Formula**:
  $$\text{IoU} = \frac{|P \cap G|}{|P \cup G|} = \frac{\text{TP}}{\text{TP} + \text{FP} + \text{FN}}$$
  Where $P$ is the predicted flame binary mask and $G$ is the ground-truth annotation.
* **Code Implementation**: `tests.eval.cv_metrics.compute_mask_iou(pred_mask, gt_mask)`
* **Provisional Gate Threshold**: $\ge 0.70$.

#### 9. Dice Similarity Coefficient (F1 Mask Score)
* **Mathematical Formula**:
  $$\text{Dice} = \frac{2 |P \cap G|}{|P| + |G|} = \frac{2\text{TP}}{2\text{TP} + \text{FP} + \text{FN}}$$
* **Code Implementation**: `tests.eval.cv_metrics.compute_dice_coefficient(pred_mask, gt_mask)`
* **Provisional Gate Threshold**: $\ge 0.80$.

#### 10. Pixel-Level Precision & Recall
* **Mathematical Formulas**:
  $$\text{Precision}_{\text{pixel}} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall}_{\text{pixel}} = \frac{\text{TP}}{\text{TP} + \text{FN}}$$
* **Code Implementation**: `tests.eval.cv_metrics.compute_precision_recall_masks(pred_mask, gt_mask)`

---

### 2.4 Operational and Computational Performance Metrics

#### 11. Latency (p50, p95, p99)
* **Definition**: End-to-end elapsed request duration in milliseconds measured from query ingress to final byte generation.
* **Provisional Gate Threshold**: $\text{p95} \le 1200\text{ ms}$ for standard queries.

#### 12. Token Consumption & Throughput
* **Definition**: Total tokens generated per second and prompt-to-completion token ratio.

#### 13. GPU Memory Footprint
* **Definition**: Peak VRAM allocation ($\text{GB}$) during batch inference and embedding retrieval.

---

## 3. Human vs Deterministic Metric Categorization

| Metric | Category | Evaluation Method | Justification |
|---|---|---|---|
| Recall@K, Precision@K, MRR, nDCG | Deterministic | Automated Code (`metrics.py`) | Exact set intersection and logarithmic discount |
| Citation F1 | Deterministic | Automated Code (`metrics.py`) | String and locator identity comparison |
| IoU, Dice, Pixel P/R | Deterministic | Automated Code (`cv_metrics.py`)| Binary pixel mask intersection over union |
| Latency, VRAM | Deterministic | Automated System Telemetry | Hardware timers and process memory trackers |
| Hallucination / Unsupported-Claim Rate | Hybrid / Human | LLM-as-a-Judge + Spot Audit | Subtleties in scientific reasoning require expert validation |
| Complex Scientific Coherence | Human Review | Blinded Domain Expert Review | Multi-step thermodynamics and combustion edge cases |
