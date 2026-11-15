# NASA Space Apps 2026: project submission pack (team Aureon)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Ready to paste | 1.0.0 | 2026-11-15 | T7 | whole repository |

Paste-ready text for each field of the project submission form at
https://www.spaceappschallenge.org/2026/find-a-team/aureon/?tab=project.

**Deadline:** project submission closes **Sunday 15 November 2026, 11:59 PM local time**, and a submission is final once sent. Field names below follow the Space Apps project form; if the 2026 form names a field differently, paste the matching block.

Every number below comes from a committed document in this repository (sources in §11). Nothing is claimed that the repository does not show.

---

## 1. Project name

```
Flame in Freefall: fire-safety insights from NASA microgravity combustion data
```

Short form, if the field is limited: `Flame in Freefall`

## 2. Challenge

```
Flame in Freefall: AI-powered fire-safety insights from microgravity combustion data
```

## 3. High-level project summary

**Short (about 70 words):**

```
Flame in Freefall turns 1,950 NASA microgravity combustion flight tests from 19 investigations into answers about one question: what do we know about fire in this spacecraft cabin atmosphere? Pick an atmosphere and the dashboard gives a coverage verdict, ranks NASA's investigations by how directly their data applies, explains what the flights measured with every number linked to its NASA source, and refuses to estimate where no flight data exists.
```

**Long (about 150 words), if the field allows more:**

```
Fire behaves differently without gravity, and the next crewed vehicles plan richer oxygen atmospheres than the ISS: up to 30% O2 on Orion and 34% on lunar-lander designs. NASA has flown decades of combustion experiments, but the results are spread across tables, metadata and hundreds of reports.

Flame in Freefall turns 1,950 flight tests from 19 NASA PSI investigations and 27 NASA technical reports into one answer for a mission designer. Choose a cabin atmosphere and the system (1) states whether any flight test covers it, (2) ranks the investigations by how directly their data applies, (3) explains what the flights measured, with every number one click from its NASA table cell, and (4) estimates droplet-flame outcomes with a validated model that refuses to extrapolate. Given Apollo 1's pure-oxygen atmosphere, it refuses: none of the 1,950 tests cover it.
```

## 4. Link to project demo

The form asks for a short demo: a 7-slide deck or a short video. Use the 7-slide demo deck:

```
https://github.com/FCDS-College/Nasa/blob/main/docs/presentations/demo-deck/flame-in-freefall-demo.pdf
```

The GitHub PDF opens for anyone without signing in. The designed online version, https://claude.ai/artifact/BaR3E388cZyBNbpxKLXnLn, is **private until you share it** from its Share menu. Only paste it if you have shared it and opened it in a private browser window to check.

## 5. Link to final project

```
https://github.com/FCDS-College/Nasa
```

The repository is public. Its README links the status, architecture, test report, demo runbook and model card.

## 6. Project details

```
WHAT IT DOES
Flame in Freefall is a fire-safety evidence platform for spacecraft and habitat designers. The user chooses a cabin atmosphere: ISS air, the pre-EVA campout, Orion's maximum-oxygen design, an Altair-class lunar lander, the historical Apollo 1 pad test, or any O2 and pressure. The system answers in five steps:
1. Coverage verdict: does any flight test lie near this atmosphere? If not, it names the nearest real test and the size of the gap.
2. Ranking: every investigation is scored by how directly its flight data covers the atmosphere, from four visible components: O2 coverage, pressure coverage, nearby tests and outcome data. It is evidence relevance, never presented as a risk score.
3. Summaries in NASA's own words, from the PSI ISA-Tab records, with source links.
4. Explanations: what the flight tests measured there. Every number carries the IDs of the NASA table cells it came from, and each card is labelled Measured, Model estimate or Coverage gap.
5. Estimates: a model trained on 261 FLEX droplet tests from the ISS estimates whether a droplet flame self-extinguishes, breaks up or burns out, shows the most similar real tests, and refuses outside the conditions NASA flew.
A cited chat answers questions over the 27 NASA reports and 24 investigation records, and a knowledge graph (2,304 entities, 25,415 edges) links investigations, tests, fuels, conditions and outcomes, each link citing its NASA cell.

HOW IT WORKS
NASA PSI tables, ISA-Tab metadata, NTRS reports and flight media are ingested with cell-level provenance (SHA-256 and source for every file; OCR recovers 35 pages with broken PDF fonts) into PostgreSQL with pgvector. Fire-safety analytics compute canonical variables, the ranking, insights and the outcome model. A REST API (OpenAPI contract 0.7.0) serves a Next.js dashboard, an outcome explorer, the cited chat, and 16 AI-agent tools.

THE APOLLO 1 TEST
On 27 January 1967 Apollo 1's cabin held 100% oxygen at 16.7 psia during a ground test. Given that atmosphere, Flame in Freefall answers: "None of the 1,950 flight tests cover this atmosphere." Its O2 is 2.5 times the highest ever flown (40%) and it is at 1 g, while every test was in microgravity. The system makes no estimate, lists what NASA changed after the fire with links to NASA pages, and points to where data does exist: Orion's 30% O2 atmosphere, with 8 real flight tests.

BENEFITS
- Mission and habitat designers see which atmospheres have flight evidence, and where testing is missing, before choosing one.
- Materials engineers go from a question to the NASA reports, with citations a review board can check.
- Researchers browse 1,958 experiment rows cell by cell, with provenance and data-quality flags.
- An AI that can say "the data does not cover this" is one an engineering review can trust.

MEASURED QUALITY
- Outcome model: macro-F1 0.54 against a 0.27 baseline, extinction ROC-AUC 0.86, validated by holding out whole test days.
- Retrieval: hit@1 0.88, hit@5 0.96, MRR@10 0.91 on 26 corpus-grounded questions.
- Engineering: automated tests, linting, a secret scan, a database migration check and an 11-step browser journey run in CI on every pull request.

TOOLS AND LANGUAGES
Python (FastAPI, scikit-learn, NumPy, OpenCV, RQ), TypeScript (Next.js, React), PostgreSQL with pgvector, Redis, S3-compatible storage, Docker, GitHub Actions, Playwright. Local models: bge-small-en-v1.5 embeddings and a cross-encoder reranker; optional local LLM through Ollama.

LIMITS WE STATE OPENLY
Outcomes are modelled for droplet flames only; no partial-gravity (Moon or Mars) flight data exists in the sources; the ranking weights are design choices awaiting expert calibration; the evaluation gold sets await human review. The dashboard shows these limits to the user rather than hiding them.

TEAM
Aureon: team lead and data engineering, AI and retrieval, computer vision, frontend, and evaluation, working through reviewed pull requests with documentation and architecture decision records.
```

## 7. Use of artificial intelligence

Space Apps asks teams to state how they used AI. This disclosure is complete and honest.

```
AI inside the product:
- Retrieval: local bge-small-en-v1.5 embeddings and a local cross-encoder reranker find passages in the 27 NASA reports.
- Cited chat: an optional local LLM (through Ollama) may only cite retrieved NASA evidence; citations outside the retrieved set are dropped. Without a model, the chat shows the evidence itself. Generated answers have not yet been formally evaluated.
- Outcome model: a multinomial logistic regression (classical machine learning) trained on 261 FLEX flight tests, with a strict applicability domain.
- Computer vision: OpenCV image processing of NASA flight video and photos (pixel measurements only; no temperatures inferred from colour).

AI used to build the project:
- The team used an AI coding assistant (Claude Code) to help write and review code, tests, documentation and the demo deck. Every change went through pull requests, automated tests and CI.
- Parts of the evaluation gold sets and labels were drafted with AI assistance and are marked as awaiting human review.

AI-generated content:
- No NASA data, measurement or result in the project is AI-generated: every number traces to a NASA table cell or report page.
- The cover illustration of a spherical flame in the demo deck was drawn as code with AI assistance, and is labelled "Illustration" on the slide. All screenshots are of the real application.
```

## 8. NASA data

```
NASA Physical Sciences Informatics (PSI) system, CC0 — flight-test tables and ISA-Tab metadata from 19 combustion investigations, 1,950 flight tests:
- Gas flames: SPICE (435 tests), ACME CFI-G (333), ACME Flame Design (327), ACME-CLD (32), ACME E-FIELD (31), ACME BRE (18), ACME s-Flame (18), SLICE (12)
- Droplets: FLEX (274), CFI (79), FLEX-2 (8)
- Solids: BASS-II (129), BASS (122), SAFFIRE-II (9), SAFFIRE-I (2), SAFFIRE-III (2)
- Smoke: SAME-R (109), SAME (8), DAFT (2)

NASA Technical Reports Server (NTRS) — 27 reports with public-use status, including the Report of Apollo 204 Review Board, NASA-STD-6001 materials testing, Saffire, FLEX and exploration-atmosphere flammability studies.

Flight media — a BASS-II flight video and SPICE ISS photographs, for computer vision.

Every file's source and SHA-256 hash is recorded in the repository (datasets/metadata/files.jsonl, datasets/checksums/sha256.txt).
```

## 9. Space agency partner and other data

```
No partner space agency data is used. All data comes from NASA (PSI and NTRS). Open-source software used: FastAPI, Next.js, PostgreSQL/pgvector, scikit-learn, OpenCV, fastembed (bge-small-en-v1.5 embeddings and a cross-encoder reranker), Tesseract OCR.
```

## 10. References

```
NASA PSI investigations (CC0), https://psi.nasa.gov/physci/repo/data/investigations/:
- ACME CFI-G, doi:10.60555/cyt1-kh64
- ACME-CLD, doi:10.60555/23e1-9950
- ACME Flame Design, doi:10.60555/w4zy-bt45
- ACME BRE, doi:10.60555/vb93-3y72
- ACME E-FIELD, doi:10.60555/se5a-8c73
- ACME s-Flame, doi:10.60555/k57n-p030
- BASS, doi:10.60555/58h4-dy80
- BASS-II, doi:10.60555/4qc4-de67
- CFI, doi:10.60555/m6pj-a914
- DAFT, doi:10.60555/ztgj-d202
- FLEX, doi:10.60555/mbq8-0451
- FLEX-2, doi:10.60555/byp8-h018
- SAFFIRE-I, doi:10.60555/0t15-1z43
- SAFFIRE-II, doi:10.60555/2chp-m469
- SAFFIRE-III, doi:10.60555/040q-4h36
- SAME, doi:10.60555/gd4k-8h62
- SAME-R, doi:10.60555/2np7-jv14
- SLICE, doi:10.60555/pm12-rg61
- SPICE, doi:10.60555/9kbh-e962

Key NASA NTRS reports:
- Report of Apollo 204 Review Board — https://ntrs.nasa.gov/citations/19930078717
- Crew Exploration Vehicle Environmental Control and Life Support Fire Protection Approach — https://ntrs.nasa.gov/citations/20070021223
- FLEX: A Decisive Step Forward in NASA's Combustion Research Program — https://ntrs.nasa.gov/citations/20120015928
- The Spacecraft Fire Experiment (Saffire): Objectives, Development and Status — https://ntrs.nasa.gov/citations/20170001636
- Microgravity Flame Spread in Exploration Atmospheres — https://ntrs.nasa.gov/citations/20080034883
- Fire Safety in the Low-Gravity Spacecraft Environment — https://ntrs.nasa.gov/citations/19990063738
- Testing and Selection of Fire-Resistant Materials for Spacecraft Use — https://ntrs.nasa.gov/citations/20000034017
The full list of 27 reports is in datasets/registry/source_registry.csv.

Software: FastAPI, Next.js, PostgreSQL + pgvector, scikit-learn, OpenCV, fastembed (BAAI bge-small-en-v1.5), Tesseract OCR, Playwright.
```

## 11. Tags

```
#FireSafety #Microgravity #Combustion #SpacecraftSafety #ISS #Artemis #NASAOpenData #ExplainableAI #RAG #KnowledgeGraph #MachineLearning #DataProvenance
```

## 12. Before you press Submit

- [ ] Every team member is a confirmed participant at the same local event (needed for award eligibility).
- [ ] The demo link opens in a private browser window without signing in.
- [ ] The GitHub repository opens without signing in (checked 2026-11-15: public).
- [ ] The Terms and Conditions box is ticked.
- [ ] No minor appears in any photo, video or voice in the demo without the consent the terms require.
- [ ] Optional, worth doing: add a LICENSE file. The README says the code is "internal to the team" while the repository is public, which judges may read as a contradiction.

## 13. Sources for every number

| Claim | Source |
|---|---|
| 1,950 flight tests, 19 investigations, per-investigation counts, 27 reports, 24 ISA-Tab records | `README.md` “Data”; `FINAL_PROJECT_STATUS.md` §1 |
| Orion 30 %, lunar lander 34 %, ISS 21 % O₂ | `FINAL_CHALLENGE_PRESENTATION.md` §1 (NASA/TM-2008-215260); `ai/fire_safety/scenarios.py` |
| Apollo 1 verdict, 2.5×, 40 % highest O₂ flown, Orion 8 tests | `FINAL_CHALLENGE_PRESENTATION.md` §3a |
| Model: 261 tests, macro-F1 0.54 vs 0.27, ROC-AUC 0.86 | `FINAL_CHALLENGE_PRESENTATION.md` §5; `docs/evaluation/reports/flex-outcome-model.md` |
| Retrieval hit@1 0.88, hit@5 0.96, MRR@10 0.91 | `FINAL_CHALLENGE_PRESENTATION.md` §5 |
| Knowledge graph 2,304 entities, 25,415 edges; 16 agent tools | `FINAL_CHALLENGE_PRESENTATION.md` §3 and §5 |
| 35 OCR-recovered pages; 1,958 experiment rows | `FINAL_CHALLENGE_PRESENTATION.md` §5 and §7 |
| DOIs and NTRS links | `datasets/registry/source_registry.csv` |

## Known limitations
- The submission page itself could not be opened from the session that wrote this pack (the site answered 503 to automated requests), so the field names follow the published Space Apps form rather than a reading of the 2026 page. Match each block to the field with the same purpose.
- No public live deployment exists today (the Railway API answered 404 "Application not found" on 2026-11-15), so the pack links the repository and the demo deck, not a running app.
- Character limits were not visible; the short summary is the safe choice if a field cuts text off.

## Changelog
- 1.0.0 (2026-11-15): first version for the 2026 submission.
