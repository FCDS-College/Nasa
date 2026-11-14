# Final project status: Flame in Freefall

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current | 1.5.4 | 2026-11-14 | final challenge plan T1–T7, I7–I11, ADR-006–009, ADR-013 | whole repository |

**Challenge.** NASA Space Apps 2026, *Flame in Freefall: AI-powered fire-safety insights from microgravity combustion data*: summarize, rank and explain NASA microgravity combustion results to inform fire safety for Moon and Mars missions.

**Answer.** A fire-safety dashboard. You pick a cabin atmosphere, and it:
- ranks NASA's flight investigations by how directly their data covers that atmosphere;
- summarizes each investigation in NASA's own words, with citations;
- states what the flight tests measured there, each number linked to its source cell;
- estimates droplet-flame outcomes with a validated, interpretable model that refuses to extrapolate;
- lists what the data cannot tell you, starting with a coverage verdict before any ranking (ADR-013).

## 1. Completed (verified; evidence in [FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md))

| Feature | Status |
|---|---|
| 1950 NASA flight tests from 19 PSI combustion investigations ingested from committed CC0 tables (1958 ingested experiment rows; 24 ISA-Tab metadata documents) | COMPLETE |
| NASA ISA-Tab summaries (objective, hypothesis, approach, impacts, publications) as citable evidence | COMPLETE |
| 27 public-use NTRS reports in the corpus (3 added for Apollo 1, including the Apollo 204 Review Board report); garbled-font and scanned pages OCRed | COMPLETE |
| Investigation ranking for 4 cited mission atmospheres plus a custom one, with a transparent formula | COMPLETE |
| Computed fire-safety insights with evidence links; coverage gaps stated | COMPLETE |
| FLEX outcome model: grouped validation, model card, strict applicability domain, nearest real tests | COMPLETE |
| Dashboard, investigation page, outcome explorer, flight test browser, video view, navigation | COMPLETE |
| Hybrid retrieval with cross-encoder reranking, measured on a corpus-grounded gold set (hit@1 0.88, hit@5 0.96, MRR@10 0.91) | COMPLETE (gold set needs human review) |
| Cited chat; evidence-only fallback when no model is deployed | COMPLETE (generation not evaluated: no model here) |
| Image and video CV through the API (BASS-II flight video, SPICE photos) | PARTIAL: runs end to end and finds luminous flames. On 8 unseen BASS-II tests (`cv_gold_v1`, labels pending human review): false-positive rate 0.00 (0 of 37 empty frames), localized recall 0.68. Lit scenery is reported UNCERTAIN; dim blue flames are missed, and bright hardware in a dark scene is still called a flame, except the FLEX colour camera's arc and droplet glints when the upload names the `flex-colour` camera profile ([docs/cv/evaluation-report.md](docs/cv/evaluation-report.md)) |
| Contract 0.7.0 (coverage verdict, gravity, scenario history). The AURA Link 2 dry run was last green at 0.6.0 (16 tools); 0.7.0 is checked by the `aura-link2-contract` job | COMPLETE (AURA re-discovery pending) |
| ADR-006 to 009 built (PR #29): one `ai/rag` search stack, knowledge graph from the PSI tables, video checkpoints and cancellation, admin scope | COMPLETE |
| Reranker on by default (fastembed ONNX, top 10) and four reviewed material spellings resolved in the graph (PR #30) | COMPLETE |
| Knowledge Graph page in the web app (`/knowledge`): browse entities, walk links, open the evidence behind each (PR #32) | COMPLETE |
| Apollo 1 historical scenario (ADR-013): verdict "None of the 1950 flight tests cover this atmosphere", envelope map with a red out-of-envelope zone, page-cited timeline, data-covered alternative (Orion 30 % O₂); historical scenarios are data files checked in CI | COMPLETE |
| Gravity as a scenario dimension: any regime other than microgravity gets verdict `none` and no model estimate | COMPLETE |
| Demo runbook, demo data script, browser smoke test (11 steps; `npm run smoke`; CI job `demo-smoke`) | COMPLETE (CI job new; first run on the PR) |
| Knowledge Graph page labels the NLP graph's platform and instrument entities (was a page error on `main` after PR #43) | COMPLETE |

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
| No AURA deployment reachable (both Railway hosts 404 on 2026-11-12) | Medium (AURA is optional, ADR-004) | Nothing to do in Flame. AURA's owner redeploys it. A hosted-only AURA also needs the Link 1 data-ceiling change ([integration README](docs/integration/README.md) §5) |
| Compose and Railway not redeployed or dry-run with this branch | High for a hosted demo | Path B in [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) (verified); Railway needs an account holder |
| No LLM verified in this environment; chat answers not evaluated | Medium | Ollama via compose profile `local-llm`; the UI falls back to cited evidence |
| Lexical-only search is weak for full questions (16/26 return nothing) | Medium (only without embeddings) | Vector index built at start-up |
| Reranking adds about 0.7 s per search on CPU (chat runs up to six searches), and the first search downloads its model (~90 MB) | Medium | `python -m ai.providers.local.cross_encoder prepare` before the demo; `FLAME_RERANKER_ENABLED=false` to turn it off |
| A client key with only write scope gets 403 on `/api/admin/*` | Low (by design, ADR-009) | Create an admin key with `--owner`; the deprecated write token still works |
| Gold set and labels authored with AI assistance | Medium | Human review (Ziad, Eman) |
| `next start` warns about `output: standalone` | Low | Works; or `node .next/standalone/server.js` |
| Garbled-PDF detector is a function-word heuristic tuned on English reports | Low | Flags only the 35 broken-font pages today; review flagged pages in `document.payload.garbled_text_pages` |

## 4. Production readiness (decision 2026-11-13: pitch/demo-grade)

This release is **pitch/demo-grade**. The Apollo 1 flow and the demo journey are tested end to end, in CI and in a local full-stack run (PostgreSQL 16 + pgvector, Redis, an S3 stand-in, API, worker, web: 11/11 steps on 2026-11-13). It is deployable with the existing configuration. These gaps are **documented, not closed**, and must close before a paying pilot ([business plan §9](docs/business/BUSINESS_PLAN.md)):

| Gap | What closes it |
|---|---|
| Railway not redeployed since 2026-10-14 | Someone with Railway access runs, from this branch: `pip install -r .railway/requirements.txt`, `railway config plan`, `railway config apply`, then `railway up` for `flame-api` and `flame-worker`. The pre-deploy step runs migrations, seed, ingest (27 reports) and the vector-index build. Check `/api/health` reports `api_version` 0.7.0, then run `npm run smoke -- https://<web host>` ([RUNBOOK §6](docs/operations/RUNBOOK.md)) |
| Compose never run end to end | Run path A of DEMO_RUNBOOK on a machine with Docker |
| No identity provider; the deprecated write token is still an admin credential | SSO for named users; remove the token (ADR-009 follow-up) |
| No scheduled backups or deployed alerting | Cron `infrastructure/backup/backup.sh`; deploy the OBSERVABILITY.md thresholds |
| Single tenant, no billing | Multi-tenancy and a private-corpus store (business plan §9) |
| LLM answers and the gold set not evaluated by humans | EV-06/EV-10 with a deployed model; human review of the gold set |
| External security review | Week-8 review (SECURITY.md) |

## 5. Decisions taken (approved plan, 2026-11-07)

- Commit the small CC0 PSI tables and metadata.
- Rank by evidence relevance to a cabin atmosphere, never claiming risk.
- Make the outcome model strict, refusing outside the flight-tested domain.
- Run the local demo as primary, with Railway as a bonus.
- Keep uploads disabled in the dashboard: the web tier never holds a write key.

After submission (2026-11-07 to 2026-11-12):
- ADR-001 to 012 signed off; ADR-006 to 009 accepted and built (PR #27, #28, #29).
- Reranking on by default, after it raised hit@1 from 0.81 to 0.88 on the gold set (PR #30).
- Four material spelling variants in the BASS-II and SPICE tables resolved by reviewed aliases, never automatically (PR #30).
- The knowledge graph made browsable in the web app: the Knowledge Graph page (`/knowledge`) replaces the old "not available" placeholder (PR #32).

2026-11-13 (Apollo 1 scenario; [analysis](docs/reports/APOLLO1_SCENARIO_ANALYSIS.md)):
- After refusing Apollo 1, the system shows **Orion 30 % O₂** as the data-covered alternative. Apollo's own post-fire atmospheres are outside the flight envelope. It is worded "covered by data", never "safe".
- First paying customer: **commercial space** (station and habitat teams, materials suppliers); [business plan](docs/business/BUSINESS_PLAN.md).
- Production scope for this round: **pitch/demo-grade** (§4).
- Pitch: an English 3-minute deck with an English script and an Arabic rehearsal script, opening with the Apollo 1 hook.
- Gravity is a scenario field; historical scenarios are data files; a coverage verdict sits beside the unchanged ranking (ADR-013, Proposed).

## Changelog
- 1.5.4 (2026-11-14): CV row notes the v1.7.0 size floor (droplet glints).
- 1.5.3 (2026-11-14): CV row notes the v1.6.0 camera profiles.
- 1.5.2 (2026-11-14): CV row updated with the v1.5.0 held-out figures (lit-scene rule).
- 1.5.1 (2026-11-14): flight-test counts updated from 840 (4 investigations) to 1950 (19 investigations), matching the coverage verdict since 35fc5e0.
- 1.5.0 (2026-11-14): CV row from COMPLETE to PARTIAL, with the held-out evaluation figures.
- 1.4.0 (2026-11-13): the Apollo 1 historical scenario, coverage verdict and gravity (ADR-013, contract 0.7.0); 27 NTRS reports; production-readiness section; 2026-11-13 decisions; the Knowledge Graph page fix.
- 1.0.0 (2026-11-07): final status for submission.
- 1.1.0 (2026-11-12): contract 0.6.0 and the ADR-006 to 009 builds (PR #29).
- 1.2.0 (2026-11-12): PR #30 (reranker default, graph aliases) and AURA-AI #232 merged; new known issues; post-submission decisions.
- 1.3.0 (2026-11-12): the Knowledge Graph page; its known issue removed.
- 1.3.1 (2026-11-12): PR #32 (Knowledge Graph page) merged; recorded in the completed features and post-submission decisions.
- 1.3.2 (2026-11-12): the AURA integration re-checked against AURA `main`; a known issue for the unreachable AURA deployment.
