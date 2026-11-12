# Final project status: Flame in Freefall

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | 1.3.0 | 2026-11-12 | final challenge plan T1–T7, I7–I11, ADR-006–009 | whole repository |

**Challenge.** NASA Space Apps 2026, *Flame in Freefall: AI-powered fire-safety insights from microgravity combustion data*: summarize, rank and explain NASA microgravity combustion results to inform fire safety for Moon and Mars missions.

**Answer.** A fire-safety dashboard. You pick a cabin atmosphere, and it:
- ranks NASA's flight investigations by how directly their data covers that atmosphere;
- summarizes each investigation in NASA's own words, with citations;
- states what the flight tests measured there, each number linked to its source cell;
- estimates droplet-flame outcomes with a validated, interpretable model that refuses to extrapolate;
- lists what the data cannot tell you.

## 1. Completed (verified; evidence in [FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md))

| Feature | Status |
|---|---|
| 840 NASA flight tests (FLEX, BASS-II, SPICE, SAFFIRE-I) ingested from committed CC0 tables | COMPLETE |
| NASA ISA-Tab summaries (objective, hypothesis, approach, impacts, publications) as citable evidence | COMPLETE |
| 24 public-use NTRS reports in the corpus; garbled-font pages OCRed | COMPLETE |
| Investigation ranking for 4 cited mission atmospheres plus a custom one, with a transparent formula | COMPLETE |
| Computed fire-safety insights with evidence links; coverage gaps stated | COMPLETE |
| FLEX outcome model: grouped validation, model card, strict applicability domain, nearest real tests | COMPLETE |
| Dashboard, investigation page, outcome explorer, flight test browser, video view, navigation | COMPLETE |
| Hybrid retrieval with cross-encoder reranking, measured on a corpus-grounded gold set (hit@1 0.88, hit@5 0.96, MRR@10 0.91) | COMPLETE (gold set needs human review) |
| Cited chat; evidence-only fallback when no model is deployed | COMPLETE (generation not evaluated: no model here) |
| Image and video CV through the API (BASS-II flight video, SPICE photos) | COMPLETE |
| Contract 0.6.0, AURA Link 2 dry run (16 tools); AURA's own runbook updated to match (AURA-AI #232) | COMPLETE |
| ADR-006 to 009 built (PR #29): one `ai/rag` search stack, knowledge graph from the PSI tables, video checkpoints and cancellation, admin scope | COMPLETE |
| Reranker on by default (fastembed ONNX, top 10) and four reviewed material spellings resolved in the graph (PR #30) | COMPLETE |
| Knowledge Graph page in the web app (`/knowledge`): browse entities, walk links, open the evidence behind each | COMPLETE |
| Demo runbook, demo data script, browser smoke test | COMPLETE |

## 2. Remaining limitations

- **Droplets only for outcomes.** Spacecraft fires are mostly solids, and BASS-II's table has no outcome column. Its spread and extinction data live in videos and a report that is not public-use on NTRS.
- **Microgravity only.** No partial-gravity (Moon 1/6 g, Mars 3/8 g) data exists here; the dashboard says so.
- **Not ingested.** SAME (named by the challenge), ACME and FLEX-2 data have not been acquired; they are listed as not covered.
- **Subset.** The tables are complete, but the media mirror holds a fraction of each investigation's raw files.
- **Model size.** 261 tests on 80 days; the Completion class (27) is weak (precision 0.29 on the hold-out).
- **Ranking weights.** The ranking is an evidence-relevance score with design-choice weights, not a validated risk score.
- **Knowledge graph from tables only.** It holds what the PSI tables and ISA-Tab records state (951 entities, 10,683 cited edges). Platforms, instruments and links from the NTRS reports would need NLP extraction, which is not built; nor is Graph RAG in chat.

## 3. Known issues

| Issue | Severity | Workaround |
|---|---|---|
| Compose and Railway not redeployed or dry-run with this branch | High for a hosted demo | Path B in [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) (verified); Railway needs an account holder |
| No LLM verified in this environment; chat answers not evaluated | Medium | Ollama via compose profile `local-llm`; the UI falls back to cited evidence |
| Lexical-only search is weak for full questions (16/26 return nothing) | Medium (only without embeddings) | Vector index built at start-up |
| Reranking adds about 0.7 s per search on CPU (chat runs up to six searches), and the first search downloads its model (~90 MB) | Medium | `python -m ai.providers.local.cross_encoder prepare` before the demo; `FLAME_RERANKER_ENABLED=false` to turn it off |
| A client key with only write scope gets 403 on `/api/admin/*` | Low (by design, ADR-009) | Create an admin key with `--owner`; the deprecated write token still works |
| Gold set and labels authored with AI assistance | Medium | Human review (Ziad, Eman) |
| `next start` warns about `output: standalone` | Low | Works; or `node .next/standalone/server.js` |
| Garbled-PDF detector is a function-word heuristic tuned on English reports | Low | Flags only the 35 broken-font pages today; review flagged pages in `document.payload.garbled_text_pages` |

## 4. Decisions taken (approved plan, 2026-11-07)

- Commit the small CC0 PSI tables and metadata.
- Rank by evidence relevance to a cabin atmosphere, never claiming risk.
- Make the outcome model strict, refusing outside the flight-tested domain.
- Run the local demo as primary, with Railway as a bonus.
- Keep uploads disabled in the dashboard: the web tier never holds a write key.

After submission (2026-11-07 to 2026-11-12):
- ADR-001 to 012 signed off; ADR-006 to 009 accepted and built (PR #27, #28, #29).
- Reranking on by default, after it raised hit@1 from 0.81 to 0.88 on the gold set (PR #30).
- Four material spelling variants in the BASS-II and SPICE tables resolved by reviewed aliases, never automatically (PR #30).

## Changelog
- 1.0.0 (2026-11-07): final status for submission.
- 1.1.0 (2026-11-12): contract 0.6.0 and the ADR-006 to 009 builds (PR #29).
- 1.3.0 (2026-11-12): the Knowledge Graph page; its known issue removed.
- 1.2.0 (2026-11-12): PR #30 (reranker default, graph aliases) and AURA-AI #232 merged; new known issues; post-submission decisions.
