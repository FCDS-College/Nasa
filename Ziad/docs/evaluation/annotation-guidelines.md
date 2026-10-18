| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.1.0 | 2026-10-12 | C2, M10 | `docs/evaluation/annotation-guidelines.md` |

# E5-3: Annotation and Human-Review Guidelines

## 1. Human Evaluation Rubric

Human reviewers score model responses across three primary dimensions using a standardized 1–5 Likert scale.

| Score | Factual Correctness | Evidence Support (Faithfulness) | Completeness |
|---|---|---|---|
| **5 (Flawless)** | Fully accurate scientific statement; no inaccuracies. | Every sentence is directly attributed to provided context. | Directly and fully answers the prompt with all key nuances. |
| **4 (Minor defect)** | Factually sound; minor phrasing ambiguity. | Supported, but contains 1 minor extrapolative inference. | Answers primary question, omits 1 minor detail. |
| **3 (Borderline)** | Partially accurate; 1 non-critical scientific error. | Partial grounding; some statements lack citations. | Incomplete; leaves key secondary questions unanswered. |
| **2 (Poor)** | Contains significant factual errors or fabrications. | Noticeable hallucination; cites incorrect section. | Fails to answer core question. |
| **1 (Critical fail)** | Dangerous scientific misinformation or unsafe instruction. | Completely fabricated / ungrounded response. | Refuses incorrectly or produces gibberish. |

---

## 2. Blinded Review Protocol for Model Comparison (C2)

To evaluate candidate LLM / RAG variants without cognitive bias:
1. **Model Identity Masking**: Outputs are stripped of headers, token counters, or style signatures and assigned random identifiers (`Model-Alpha`, `Model-Beta`).
2. **Order Randomization**: Sequence of models presented to reviewers is shuffled uniformly.
3. **Inter-Annotator Agreement (IAA)**:
   * Assessed using **Cohen's Kappa ($\kappa$)** for pairwise ratings and **Fleiss' Kappa** for $\ge 3$ reviewers.
   * Target acceptance threshold: $\kappa \ge 0.65$ (substantial agreement).
   * Discrepancies ($|\Delta| \ge 2$) undergo adjudication with the Lead (Anas).

---

## 3. Computer Vision Mask-Review Protocol (with Princess / E3)

Co-owned with `docs/cv/annotation-protocol.md`:
* **Flame Core vs. Plume Separation**: Reviewers verify that segmentation masks strictly delineate the inner reaction zone from diffuse outer soot radiation.
* **Polygon Precision**: Minimum 12-vertex boundary requirement for non-spherical turbulent microgravity flame regimes.
* **Acceptance Gate**: Inter-annotator mask IoU must exceed 0.85 before ground truth freezing.
