| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Ziad | In review | 0.2.0 | 2026-10-19 | Phase 2 Plan §7A.8 (13 Scenarios) | `apps/api`, `tests/eval/test_offline_eval.py` |

# E5-11: Offline Evaluation and Air-Gapped Verification Protocol

## 1. Overview and Operational Rationale

NASA mission computing environments—including orbital test racks on the International Space Station (ISS), mobile field test facilities at White Sands, and air-gapped lab nodes—operate under strict physical disconnection from external public networks. The Flame platform must remain functional, deterministic, and verifiable without external API access or outbound internet egress.

---

## 2. Phase 2 Plan §7A.8: 13 Offline Scenarios Mapping

Per §7A.8 of the Phase 2 Plan, the platform must satisfy thirteen discrete offline operational scenarios under enforced network egress blocks (`docker run --network none` or packet-drop firewall rules):

| Scenario ID | Scenario Description | Target Subsystem | Automated Test File | Expected Result | Verification Status |
|---|---|---|---|---|---|
| **SC-OFF-01** | Local Vector Search Retrieval | Retrieval Engine | `tests/eval/test_offline_eval.py` | Return top-k chunks from local FAISS/Qdrant without remote call | **Verified (Automated)** |
| **SC-OFF-02** | Local Heuristic Safety Guardrail | Evaluation Scorer | `tests/eval/test_offline_eval.py` | Heuristic evaluation executes locally with zero socket establishment | **Verified (Automated)** |
| **SC-OFF-03** | Local Ollama Model Inference | Generation Engine | `tests/eval/test_offline_eval.py` | Generate responses using local weights via internal loopback | Planned (Pending Ollama Host) |
| **SC-OFF-04** | Air-Gapped Provenance Generation | Metadata Logger | `tests/eval/master_pipeline.py` | Output complete §18 SHA256 and run metadata locally | **Verified (Automated)** |
| **SC-OFF-05** | Local Citation Validation | Guardrail | `tests/eval/test_rag_metrics.py` | Validate citation locators against local corpus records | **Verified (Automated)** |
| **SC-OFF-06** | Flame CV Segmentation Offline | Computer Vision | `tests/eval/test_cv_and_ranking.py`| Compute mask IoU/Dice using local OpenCV/NumPy | **Verified (Automated)** |
| **SC-OFF-07** | Local Cache Hit Response | Caching Subsystem | `apps/api/tests` | Serve cached query responses without network egress | Planned (Component E1/E2) |
| **SC-OFF-08** | PII Redaction Offline | Security Filter | `tests/eval/test_rag_metrics.py` | Mask sensitive identifiers and classified refs via local regex | **Verified (Automated)** |
| **SC-OFF-09** | Cross-Modal Discrepancy Detection | Multi-modal Engine| `tests/eval/test_rag_metrics.py` | Flag text-visual mismatch without external vision APIs | **Verified (Automated)** |
| **SC-OFF-09B**| Multi-Criteria Model Ranking | Selection Engine | `tests/eval/test_cv_and_ranking.py`| Rank models locally on Pareto frontier | **Verified (Automated)** |
| **SC-OFF-10** | Unanswerable Abstention Offline | Reasoning Engine | `tests/eval/test_provenance.py` | Safe decline on missing evidence under zero connectivity | **Verified (Automated)** |
| **SC-OFF-11** | Adversarial Prompt-Injection Defense | Security Guard | `tests/eval/test_provenance.py` | Block injection strings locally without cloud content filters | **Verified (Automated)** |
| **SC-OFF-12** | Local Report Rendering | Reporting Tool | `render_report.py` | Render JSON runs to Markdown and HTML without CDN assets | **Verified (Automated)** |
| **SC-OFF-13** | Database Integrity Verification | Storage Layer | `knowledge/ingestion` | Verify SHA256 hashes of local dataset files | **Verified (Automated)** |

---

## 3. Physical Network Disconnection & Egress Deny Evidence

Automated air-gap compliance is continuously asserted via `tests/eval/test_offline_eval.py` which intercepts system-level socket instantiation (`socket.socket`) and validates that:
1. All local heuristic checks, provenance generation, and mock connectors operate with zero network calls.
2. In the event of an unhandled external network call, the execution aborts with a strict `OSError`.
3. Recorded run artifacts are written to `tests/eval/runs/` without external logging dependencies.
