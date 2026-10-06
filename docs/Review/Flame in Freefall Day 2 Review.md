FLAME IN FREEFALL · DAY 2 REVIEW · 2026-10-06

# Day 2 Engineering Review

A review of each engineer's latest pushed work against `docs/plan/DAY2_TASKS.md`. Every bug listed was reproduced by running the code, not just by reading it. Scores measure progress against the Day 2 plan, not effort.

Reviewer: **Anas (Lead)** Branch reviewed: **main @ d995f71** Next: **Day 3 asks per person, below**

| Engineer | Score | Summary |
| --- | --- | --- |
| [Eman](#eman)E1 · AI / RAG | 5.5 / 10 | Real, tested retrieval code. Missed DTOs, the DSI filter and locators. 4 confirmed bugs. |
| [Princess](#princess)E3 · Computer vision | 4 / 10 | Works on real NASA images. No intake spec or schema, and 16-bit frames come out blank. |
| [Belal](#belal)E4 · Web | 4 / 10 | Clean Day 1 fixes that pass lint, typecheck and build. Day 2 not started. |
| [Ziad](#ziad)E5 · Evaluation | 2 / 10 | 17 mock notebooks. Still the movie domain, nothing measured, provenance check not started. |

### The shared gap

Nobody has wired their work to the real corpus and to each other's contracts yet. Eman's citations have no locators, Ziad's gold set isn't real data, Princess's records don't match the intake fields, and Belal has no API client. Tomorrow starts with a short sync to settle the shared field names: **evidence**, **locator**, **frame record** and the `/api/health` shape.

## Eman · AI / RAG

5.5 / 10

commit ac932e8 · “Add RAG retrieval and evaluation prototype”

A strong first push: a working retrieval pipeline under `src/`, 10 design docs and 17 test files. All 18 collected tests pass. The structure is clean and every stage can be swapped out. It misses most of the specific Day 2 items, though, and it doesn't use our corpus yet. `docs/assumptions-and-boundaries.md` says the NASA dataset isn't available, but `datasets/` already holds the registry and 121 file records.

### Against the plan (§3)

| Partial | Interfaces in `ai/`. ABCs exist for Chunker, EmbeddingService and DocumentLoader. Retriever and Reranker are concrete classes, and LLM, cache, memory and composer are missing. The code is in `src/`, not `ai/`. |
| --- | --- |
| Partial | Prompt registry. `docs/prompts.md` covers the insufficient-evidence and conflicting-evidence prompts, but as prose, not one versioned file per prompt. |
| Missing | Pydantic DTOs (`RetrievalRequest`, `RetrievedChunk`, `EvidenceBundle`). Data is passed around as plain dicts. |
| Partial | Cache-key spec. `docs/cag-policy.md` lists the right inputs, but it has no key format, dependency manifest or TTL values. |
| Missing | DSI/combustion domain filter and its test. |
| Missing | Shared locator fields. The docs specify a `page` locator, but chunks and citations in the code carry only `chunk_id` and `document_id`. |

### Confirmed bugs

1. **The metadata filter breaks vector scores.** `hybrid_search.py` asks the vector index for `top_k = len(filtered_chunks)`, but the index searches every stored chunk. In a test, a combustion chunk that passed the filter got a vector score of **0.0** instead of its real \~0.71, because DSI chunks took the top slots.
2. **No abstention.** The query “chemical composition of Saturn” still returns 3 citations. `test_no_relevant_document` only checks that the keys exist, so it passes anyway.
3. **Keyword search matches substrings.** `word in text` means the query “is a” scores against “plasma”. The reranker adds the same keyword-overlap signal a second time.
4. **Chunker infinite loop** when `overlap >= chunk_size`. It also splits text mid-word.

Reproduced with a fake embedder, so no model download was needed.

### Also

- The evaluation dataset is one paragraph repeated 10 times, and all 4 questions share the same arbitrary relevant chunks, so the Recall and MRR results don't mean anything yet. The metric functions themselves are correct.
- 5 tests load the real MiniLM model (network on first run, \~65 s). A fake-embedder fixture would make them fast and CI-safe.
- `tests/test_pipeline.py` is a print script with no tests in it.

### What's good

The design is clean: ingest → filter → hybrid search → rerank → context → citations, and each stage has its own test. The context builder handles dedup and budgets correctly. The docs cover claim-to-evidence mapping, version-aware cache invalidation, and keeping memory separate from evidence.

### Day 3, in priority order

1. Fix bugs 1 and 2. Score only the filtered chunks, and add a minimum-score threshold that returns an empty “insufficient evidence” bundle. Write the tests that fail today first.
2. Write `ai/rag/dto.py` as Pydantic models with `locator` and version fields. Agree the names with Anas before the end of the day.
3. Make the DSI/combustion filter the default, with a test.
4. Ingest the 3 NTRS PDFs as page-level chunks and evaluate against Ziad's real gold set. Delete the synthetic dataset.
5. Fix the chunker (check that overlap is less than chunk size, split on word boundaries) and add a fake-embedder test fixture.

## Princess · Computer vision

4 / 10

commit 9194e52 · “segmentation prototype & analysis request/response stub”

The pipeline now runs on real NASA images. All 50 manifest checksums match the raw SPICE files (we recomputed them). The OpenCV threshold-and-contour step produces a real mask with geometry, and the Pydantic request and response models are a good start. The written deliverables and the Day 1 contract fixes are still missing.

### Against the plan (§5)

| Missing | `analysis_result.schema.json` plus a valid example. `image_intake_schema.json` and `result.json` are 0-byte files. |
| --- | --- |
| Partial | Contract contradictions. The `[cite: 8]` text is gone. These are still there: `confidence: null` next to `detectorConfidence: 0.96`, `MEASURED` with null measurements, and `saturationScore: 0.85` with null colour means. |
| Missing | Provenance fields (`image_sha256`, `source_file_id`, `schema_version`, units). |
| Missing | Typed stage stubs in `cv/pipeline.py`. The file has been removed. |
| Missing | `docs/data/IMAGE_INTAKE_SPEC.md`: formats and bit depth, sampling rule, labels, quality thresholds, split rule. |
| Partial | \~50 sample frames with records. 177 frames exist, but under `datasets/processed/` instead of `datasets/derived/`, and only 10 have records. |

### Confirmed bugs

1. **About a quarter of the frames are blank white.** FLEX `C021H03C`, `C024M06C` and `H14H101C` are 16-bit mono (`I;16`, values up to 54,832). `convert('RGB')` clips them to 255, so 45 of 177 processed frames are more than 99% white. They need to be normalised from 16-bit first.
2. **Distorted geometry.** 3008×2000 images are squashed to 512×512 before segmentation. That stretches the aspect ratio by 1.5×, so the reported `aspectRatio: 4.07` is wrong, and circularity is skewed too. Measure on the original image, or letterbox it.
3. **The manifest only appends.** It has 50 rows for 10 distinct images, each logged 5 times from notebook re-runs, and the paths are Windows-relative (`..\\`).
4. **Data-layout rule breaks.** 27 MB of derived images are committed to git (the rule is `datasets/derived/`, which git ignores). 12 DSI frames were processed although DSI isn't combustion data. All-black `H08M101D` frames were marked `VALIDATED` because no quality flags are computed.

### Day 3, in priority order

1. Write `IMAGE_INTAKE_SPEC.md` and the contract JSON Schema, with one valid example.
2. Move the notebook code into `cv/*.py`. Handle 16-bit frames and compute real quality flags (blur, clipping, low light).
3. Make the manifest write each image once, keyed by sha256, with repo-relative POSIX paths.
4. Move the frames to `datasets/derived/frames/<source_id>/<test_id>/` and untrack `processed/`.
5. Set your git `user.name`. Commits currently show as “unknown”.

## Belal · Web

4 / 10

commit 8e5e213 · “fix(web): address frontend review feedback” · last push Oct 4

The Day 1 fixes are done and solid. `npm run lint`, `typecheck` and `build` all pass, and all 9 routes prerender. Nothing has been pushed since Oct 4, so the Day 2 work hasn't started.

### Against the plan (§6)

| Done | TopBar status. It shows a grey “Unknown” instead of a fake green “System Online”. |
| --- | --- |
| Done | Fake success card removed, `next/link` in the sidebar, README rewritten, `typecheck` script added. |
| Partial | Placeholder routes. No more 404s, but all 7 pages are copies of the same file. Every one is `function ResearchPage` showing the heading “Research”, including `/status`. |
| Missing | Typed API client in `apps/web/lib/api/`. You aren't blocked: `docs/openapi.json` is already in the repo. |
| Missing | `/status` page showing health, versions, and loading, error and unknown states. |
| Missing | CI lint and typecheck. There's no `.github/workflows/` yet. This one is shared with Anas. |

### Day 3, in priority order

1. Generate the client with `openapi-typescript` from `docs/openapi.json`, plus a mock for `/api/health`. Send `request_id` with every request.
2. Build a real `/status` page, including a “dependency down” state.
3. Give each placeholder page its own component name and title.
4. Pair with Anas on a GitHub Actions workflow for lint and typecheck.

## Ziad · Evaluation

2 / 10

commit d995f71 · “Add evaluation framework components” · `evaluation/eval/day2_ziad/`

The commit adds 17 new notebooks, but every one runs on hard-coded sample inputs. None of them touches our corpus or scores a real system output, and the Day 2 provenance work hasn't started. The topics you chose are the right concerns (abstention, citations, PII, audit logging, drift), and `rag_gold.jsonl` uses the §18 field names. That foundation is worth keeping.

### Against the plan (§7)

| Missing | 30+ real-domain gold cases. All 33 cases are still “movie fire ship”, and only 23 are distinct: TC_024–033 repeat earlier queries under new domain labels. |
| --- | --- |
| Partial | §18 format. `rag_gold.jsonl` has the right fields, but only 6 movie-domain cases, no `filters`, and it's stored in the wrong folder. |
| Missing | Computed metrics. Every scorer still averages the hand-typed `metrics` field. |
| Missing | Gates per case and a non-zero exit code. The 4.5 vs 4 threshold mismatch between `evaluator` and `rag_evaluator` is still there. |
| Missing | pytest modules in `tests/eval/`. The tests are inside `.ipynb` files, so pytest never runs them. |
| Missing | Provenance checklist, `test_provenance.py` and the findings report. The rest of the team is waiting on this. |

### Code that reports passes it never checked

1. **master_evaluator:** `y_true` is always 1 and `y_pred` is 1 whenever `expected_output` is non-empty, so accuracy, recall and F1 are 100% by construction.
2. **llm_judge** isn't an LLM. It gives 5/5 when the answer contains a keyword such as “fire” or “report”, and it never reads the retrieved context.
3. **self_correction_guard** replaces the answer with a fixed sentence that no source supports. That is itself an unsourced claim.
4. **master_pipeline:** the demo input has `damage_detected: True` and the pipeline still returns **APPROVED**.
5. **test_pipeline:** the anti-hallucination test re-asserts its own condition, so it can't fail. The multimodal test asserts nothing.
6. **Committed result files** such as `experiment_history.json` hold invented numbers (accuracy 0.95, F1 0.92) that look like real results.

### Repo hygiene

- A byte-identical copy of the MVP plan PDF was re-added (it was removed on Oct 4), along with a 7.9 MB `.pptx` and a stray `t.py`.
- The plan puts evaluation code in `tests/eval/`, not a new top-level `evaluation/` folder.
- Commit under your own account so the history shows who wrote what.

### Day 3, in priority order

1. `tests/eval/test_provenance.py` and the findings report. It's pure Python over `files.jsonl`, `sha256.txt` and the registry, with no model needed.
2. 30 real gold cases in `datasets/evaluation/rag_gold.jsonl`, with a JSON Schema and a pytest test that validates them. Include the three “no answer” cases from the plan.
3. Delete the movie-domain cases, the files with invented results, the duplicate PDF, `t.py` and the `.pptx` (move it to Drive).
4. Hold off on guardrails and the judge until Eman's retriever produces real outputs to score.

### Lead follow-ups (Anas)

- Decide between `ai/` and `src/` for the AI code. Commit `3e138f5` also deleted `ai/README.md`, which held the evidence rules. Either restore it or update the plan.
- Fix stale `tests/eval/day1_ziad` paths in `DAY2_TASKS.md` and `AURA_INTEGRATION_STATUS.md`. The folder now lives in `evaluation/eval/`.
- Set up CI (GitHub Actions): Python tests plus web lint and typecheck on every PR.
- Run the morning field-name sync: evidence, locator, frame record, `/api/health`.

Reviewed 2026-10-06 against `docs/plan/DAY2_TASKS.md`. Bugs marked “confirmed” were reproduced by running the code; test, lint and build results come from local runs on `main @ d995f71`.