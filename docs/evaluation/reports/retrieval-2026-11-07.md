# Retrieval evaluation on the real corpus (2026-11-07)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas), built with Claude Code | Current (gold set needs human review: Ziad, Eman) | 1.0.0 | 2026-11-07 | I7, P1-6 | `ai/rag/evaluation/flame_retrieval_benchmark.py`, `datasets/evaluation/retrieval_gold_v1.jsonl` |

This replaces nothing in `tests/eval/`. Those numbers score a mock and must not be quoted (see `docs/reviews/SYSTEM_STATUS_AUDIT.md` §2). This report measures Flame's own live `/api/search`.

## Method

**Corpus.** 28 documents (24 NTRS reports plus 4 NASA ISA-Tab investigation records), 315 chunks, embeddings `bge-small-en-v1.5`, knowledge version `bge-small-en-v1.5-315-20261107`.

**Gold set (`retrieval_gold_v1.jsonl`).**
- 26 questions, written as paraphrases that avoid the labelled document's key phrase.
- Each question lists every corpus document that answers it (document-level labels, 1–4 per question).
- Each label carries a phrase that is checked against the ingested text of that document; all 54 labels pass.
- **Authored with an AI assistant that had read the corpus.** Paraphrasing limits lexical bias, but a human review is still pending.

**Scoring.** Each document's rank is the first time its chunks appear in the top 30 hits. The metrics are:
- hit@k: a relevant document is in the top k;
- MRR@10;
- recall@5: the share of a question's relevant documents found in the top 5.

**Configurations.** The same code and database were used for both runs:
- **hybrid**: the deployed configuration, PostgreSQL full-text search plus pgvector fused with RRF;
- **lexical**: a second API instance with the embedding model unavailable, which falls back to full-text search only.

**Commands.**

```text
FLAME_API_ORIGIN=http://127.0.0.1:8000 python -m ai.rag.evaluation.flame_retrieval_benchmark --label hybrid  --out docs/evaluation/reports/retrieval-hybrid-2026-11-07.json
FLAME_API_ORIGIN=http://127.0.0.1:8001 python -m ai.rag.evaluation.flame_retrieval_benchmark --label lexical --out docs/evaluation/reports/retrieval-lexical-2026-11-07.json
```

## Results

| Configuration | hit@1 | hit@3 | hit@5 | MRR@10 | recall@5 | p50 latency |
|---|---|---|---|---|---|---|
| **hybrid (deployed)** | **0.81** | **0.88** | **0.96** | **0.86** | **0.83** | 32 ms |
| lexical only | 0.31 | 0.31 | 0.31 | 0.31 | 0.21 | 9 ms |

- **Lexical returns nothing for 16 of 26 questions.** `plainto_tsquery` requires every term of a natural-language question to match. Without embeddings, for example in an offline deployment with no embedding cache, document search for full questions is therefore weak. Chat mitigates this by also searching up to 5 key terms (`_retrieve_passages`).
- **Hybrid misses one question outright.** RG-22 asks about the BASS-II hypothesis; FLEX metadata ranks above it.
- **Four questions find a relevant document only at rank 2–4:** RG-07, RG-11, RG-13 and RG-24.

Per-question results are in the two JSON files next to this report.

## Known limitations

- 26 questions is small; differences of one question move hit@1 by 0.04.
- Labels are document-level, not passage-level, and were not reviewed by a human annotator.
- Answer quality (faithfulness, citation precision of generated answers) is **not** measured here: this environment had no language model available (see `FINAL_TEST_REPORT.md`).

## Changelog
- 1.0.0 (2026-11-07): first run.
