# 🚀 NASA RAG Evaluation Pipeline

A comprehensive evaluation system for **Retrieval-Augmented Generation (RAG)** quality assessment, designed for NASA's microgravity combustion research data.

## Overview

This pipeline evaluates the quality, reliability, and safety of AI-generated responses in NASA's research intelligence system. It covers:

- **RAG Metrics**: Relevancy, faithfulness, context precision, completeness
- **LLM-as-Judge**: Gemini-powered answer quality assessment
- **Multimodal Evaluation**: Text, image, and table response assessment
- **Citation Verification**: Source reference validation against NASA/NIST documents
- **Cross-Modal Consistency**: Text–visual agreement detection
- **PII Masking**: Automatic redaction of sensitive information
- **Drift Monitoring**: Quality degradation detection over time
- **Self-Correction**: Auto-correction for low-quality responses
- **XAI Reporting**: Explainable evaluation reports
- **Provenance Tracking**: §18-compliant metadata (git commit, dataset SHA256, model version)

## Setup

```bash
pip install -r requirements.txt
```

Set your Gemini API key:
```bash
export GEMINI_API_KEY="your-key-here"       # Linux/Mac
set GEMINI_API_KEY=your-key-here             # Windows CMD
$env:GEMINI_API_KEY="your-key-here"          # PowerShell
```

## Running Tests

```bash
# Run all evaluation tests
pytest tests/eval/ -v

# Run provenance/data quality tests only
pytest tests/eval/test_provenance.py -v

# Run RAG metric tests
pytest tests/eval/test_rag_metrics.py -v
```

## Running the Pipeline

```bash
python tests/eval/master_pipeline.py
```

## Project Structure

```
NASA/
├── README.md
├── requirements.txt
├── .gitignore
├── datasets/
│   └── evaluation/
│       ├── gold_schema.json          # JSON Schema for gold test cases
│       └── rag_gold.jsonl            # 38 gold test cases (NASA domain)
├── docs/
│   └── evaluation/
│       └── provenance_checklist.md   # §18 data provenance checklist
├── tests/
│   ├── __init__.py
│   └── eval/
│       ├── __init__.py
│       ├── test_provenance.py        # Data quality pytest gates
│       ├── test_rag_metrics.py       # RAG evaluation pytest gates
│       ├── test_api_contracts.py     # API contract test stubs
│       ├── evaluator.py             # Baseline evaluator
│       ├── audit_logger.py          # Audit logging system
│       └── master_pipeline.py       # Master evaluation pipeline
├── evaluation_report.json           # Latest evaluation report
├── audit_log.json                   # Audit event log
├── experiment_history.json          # Experiment tracking
└── archive/                         # Archived scratch files
    └── day3_scratch/
```

## Technology Stack

| Technology | Usage |
|---|---|
| Python 3.13 | Core language |
| scikit-learn | TF-IDF, Cosine Similarity |
| google-generativeai | Gemini API (LLM Judge, Self-Correction) |
| pytest | Test framework |
| jsonschema | Gold data validation |
| pandas | Data manipulation |

## Gold Dataset

The evaluation gold set contains **38 test cases** (35 curated plus 3 adversarial) about NASA microgravity combustion research:
- **Splits**: dev (14), validation (14), holdout (10) — no document leakage
- **Difficulty**: easy (12), medium (12), hard (14)
- **Modality**: text (22), image (8), table (8)
- **Special cases**: 4 unanswerable + 3 adversarial/prompt-injection

## License

Internal NASA research project — not for public distribution.
