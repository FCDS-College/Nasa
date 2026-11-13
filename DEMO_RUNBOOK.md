# Demo runbook: Flame in Freefall

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current: path B verified end to end on 2026-11-07 and again on 2026-11-13 (with an S3 stand-in); the 11-step browser journey passed on 2026-11-13; path A (Docker) not run, no Docker daemon was available | 1.3.0 | 2026-11-13 | T7, ADR-013 | `infrastructure/`, `apps/api/`, `apps/web/` |

The demo is a 6-minute walk through the Fire Safety Dashboard. It needs:
- the API with PostgreSQL + pgvector, Redis and S3/MinIO;
- the RQ worker;
- the Next.js web app;
- optionally Ollama, for generated answers. Without a model, chat shows the retrieved evidence instead (see §5).

## 1. Prerequisites

| Need | Why |
|---|---|
| Git checkout of this branch | All demo data is committed: 1950 flight tests from 19 PSI investigations, 24 NASA metadata records, 27 NTRS reports, BASS-II video and SPICE images |
| Python 3.12+, Node 22 | API/worker, web |
| PostgreSQL 16 with pgvector, Redis 7, S3-compatible storage | path B only (path A runs them in containers) |
| ~3 GB disk, 8 GB RAM; +4 GB RAM for the 3B local model | CPU-only is fine |
| Internet **once** | embedding model (`bge-small-en-v1.5`) and search reranker (`Xenova/ms-marco-MiniLM-L-6-v2`, ~90 MB) downloads; Ollama model pull |

Create two random keys of 32+ characters that differ: `python -c "import secrets;print(secrets.token_urlsafe(36))"`, twice. Use them as `FLAME_READ_API_TOKEN` and `FLAME_WRITE_API_TOKEN`. Never paste them into slides or chat.

## 2. Path A: Docker Compose (recommended on the demo laptop; not dry-run yet)

```bash
cd infrastructure && cp .env.example .env
```

Edit `.env` and set `FLAME_READ_API_TOKEN` and `FLAME_WRITE_API_TOKEN`. For generated answers, also add:

```text
COMPOSE_PROFILES=local-llm
FLAME_OLLAMA_BASE_URL=http://ollama:11434
```

```bash
docker compose up -d --build
```

```bash
docker compose --profile local-llm-setup run --rm ollama-pull
```

The API container runs migrations, seed, ingest (1958 table experiments, of which 1950 are combustion flight tests; 51 documents, OCR included) and the vector-index build on start. The first start takes a few minutes. Watch it with:

```bash
docker compose logs -f api
```

Then continue with §4.

## 3. Path B: without Docker (verified 2026-11-07)

These are the commands of the verified run. Ports are examples. Start PostgreSQL 16 (with pgvector) and Redis, plus an S3 stand-in such as MinIO, or `moto_server -p 59000` for a demo; create bucket `flame-artifacts`.

```bash
python -m venv .venv && . .venv/bin/activate
```

```bash
pip install -e "apps/api[cv,ingestion,ocr,vector]"
```

`apt-get install tesseract-ocr` is needed for OCR of scanned or garbled pages.

```bash
export FLAME_DATABASE_URL=postgresql+psycopg://flame:flame@127.0.0.1:5432/flame
export FLAME_REDIS_URL=redis://127.0.0.1:6379/0
export FLAME_S3_ENDPOINT_URL=http://127.0.0.1:9000 FLAME_S3_ACCESS_KEY=... FLAME_S3_SECRET_KEY=...
export FLAME_READ_API_TOKEN=... FLAME_WRITE_API_TOKEN=...
export PYTHONPATH=$PWD:$PWD/apps/api
```

```bash
cd apps/api && alembic upgrade head && python -m flame_api.seed && python -m flame_api.ingest
```

```bash
python -m flame_api.vector_index build
```

```bash
uvicorn flame_api.main:app --host 127.0.0.1 --port 8000 &
```

```bash
(python -m flame_api.worker recover; rq worker --url "$FLAME_REDIS_URL" flame-analysis) &
```

Expected ingest summary (2026-11-13, Tesseract installed): `"experiments": 1958, "pdf_documents": 27, "pdf_pages": 486, "pdf_chunks": 480, "text_documents": 24, "quarantined": 0, "graph_entities": 951, "graph_relations": 10683`. The vector index embeds 515 chunks. `experiments` and `text_documents` are the counts the ingestion tests assert for the 19 committed PSI tables and 24 metadata documents; `graph_entities`, `graph_relations` and the embedded-chunk count were last measured with 4 tables and may now be higher.

Fetch the search reranker before the demo. Search reranks its top 10 results by default, and otherwise the first search downloads the model on stage (about 5–7 s). Add `--cache-dir "$FLAME_EMBEDDING_CACHE_DIR"` if you set that variable:

```bash
python -m ai.providers.local.cross_encoder prepare
```

Optional local model (Ollama 0.5+):

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
```

Then start the API with `FLAME_OLLAMA_BASE_URL=http://127.0.0.1:11434`.

## 4. Web app and demo data (both paths)

```bash
cd apps/web && npm ci && npm run build
```

```bash
FLAME_API_ORIGIN=http://127.0.0.1:8000 FLAME_READ_API_TOKEN=<read key> npx next start -p 3000
```

`next start` prints a warning about `output: standalone`; it works. For the container-style server, use `node .next/standalone/server.js`.

Submit the demo analyses: the committed BASS-II flight video and two SPICE ISS photos. The command is idempotent:

```bash
FLAME_API_ORIGIN=http://127.0.0.1:8000 FLAME_WRITE_API_TOKEN=<write key> FLAME_READ_API_TOKEN=<read key> python infrastructure/demo/submit_demo_analyses.py
```

Expected: three `completed` lines within about a minute.

Pre-flight check (needs Playwright + Chromium; `npx playwright install chromium` once):

```bash
cd apps/web && npm run smoke -- http://127.0.0.1:3000
```

Add a directory as a second argument to save a screenshot per step. Expected: `PASS` on 11 steps and `Demo journey passed.`
- Steps 02b and 02c are the Apollo 1 refusal and its Orion alternative.
- Step 08 is the Knowledge Graph page.
- CI runs the same journey on every PR (job `demo-smoke`). With no S3/MinIO running, the steps still pass, but `/api/health` answers 503 (`object_storage_health=down`) and image artifacts cannot load, so the script exits non-zero.

## 5. Demo sequence (~7 minutes; the 3-minute pitch uses only 1 and 2a–2c, see `docs/presentations/PITCH_SCRIPT_3MIN.md`)

| # | Screen | Do | Say / point at |
|---|---|---|---|
| 1 | `/` Fire Safety Dashboard | Open it. | The question in the headline. Moon and Mars cabins run lower pressure and higher O₂ than the ISS (NASA/TM-2008-215260). 1950 real flight tests from 19 NASA PSI investigations. |
| 2a | Scenario picker → step 2 card | Click **ISS cabin**. | **The system solves:** "310 of the 1950 flight tests lie near this atmosphere", the closest test cited, and the envelope map with ISS inside the green box. |
| 2b | **Apollo 1: pure-O₂ ground test (1967)** (red, dashed) | Click it. | **The system knows when not to answer:** "None of the 1950 flight tests cover this atmosphere." 2.5× the highest O₂ ever flown (40 %), at 1 g against microgravity; nearest real test ACME CFI-G 21162A1 (40 % O₂, 101 kPa); red zone on the sweep; no estimate. Read the lesson quote (Review Board, p. 189), then scroll the cited timeline. |
| 2c | "Where flight data does exist" | Click **Show the flight data for Orion crew vehicle**. | Orion's 30 % O₂ is inside the flight envelope: 8 real tests and an estimate. "Covered by data does not mean safe." |
| 2d | Scenario picker | Click **Lunar lander (34 % O₂, 62.7 kPa)**. | The ranking re-orders: ACME CFI-G, flown down to 43 kPa, moves to #1 ahead of FLEX. The verdict is "covered": 20 tests lie near it (11 CFI-G gas-jet flames, 9 FLEX droplets), none of them burning solids. Open "How is this scored?": a transparent formula, not a black box. |
| 3 | "What the flight data says here" | Read the first card. | **94 % of 48 droplet flames below 0.16 O₂ self-extinguished, against 8 % of 24 at ≥ 0.30.** Click a test ID → the exact NASA table cell. |
| 4 | Coverage-gap cards | Point at the amber cards. | The system says what it cannot tell you: solids at 34 % O₂, partial gravity, tables without outcomes. |
| 5 | FLEX row → investigation page | Click FLEX. | NASA's own objective, hypothesis and approach, verbatim, each with a source link. 51 publications. |
| 6 | `/explorer` | Presets **ISS air** → **Pre-EVA** → **Lunar lander**. | The probabilities, the O₂ sweep, and the 8 most similar real ISS tests with what actually happened. Lunar lander → **"No estimate: these conditions were never flown"**: the model refuses to extrapolate. Model quality: macro-F1 0.54 vs 0.27 baseline, ROC-AUC 0.86, split by test day. |
| 7 | "Explain with cited sources" on any insight | Click it, then press send. | With a model: a grounded answer whose citations must be in the retrieved set. Without one: the retrieved NTRS passages, labelled "nothing below was generated". |
| 8 | `/analysis` | Scroll to **Video flame analysis**. | The BASS-II flight video: flame area over time, measured in pixels. Flicker is "not estimable" below the Nyquist rate. No temperature from RGB. |
| 9 | `/status` | — | Every dependency's health, the AI mode and the local-only providers. |
| 10 (optional) | `/knowledge` Knowledge Graph | **Outcomes** → **Extinction**, then **Hops 2** and links **ended in** + **burned**; open any evidence chip. | Two hops from "extinction" reach the 186 FLEX tests that ended that way and their two fuels, heptane and methanol. Every link opens the NASA table cell it was read from. |

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Dashboard: "not connected to a Flame API" | `FLAME_API_ORIGIN` unset for the web server | Restart `next start` with it set |
| Every call 401 | Read key wrong or missing on the web server | Same key as the API's `FLAME_READ_API_TOKEN` |
| "No investigation has ingested data yet" | Ingest not run, or not from this checkout | Run `python -m flame_api.ingest`; expect `"experiments": 1958` |
| Search finds little for full questions | No vector index (lexical only) | `python -m flame_api.vector_index build` (needs the embedding model once) |
| First search takes several seconds; `/api/search` shows `reranking.status: "unavailable"` | Reranker model not cached (and offline), or still downloading | `python -m ai.providers.local.cross_encoder prepare`; or set `FLAME_RERANKER_ENABLED=false` |
| An admin call (`/api/admin/*`) gets 403 with a client key | The key has `write` but not `admin` scope (ADR-009) | `python -m flame_api.clients create NAME --scopes admin --owner PERSON`, or use the deprecated write token |
| Chat shows evidence only | No language model configured (`/api/health` → `llm: disabled`) | Expected fallback; configure Ollama for generated answers |
| Explorer: "No estimate" | Conditions outside the flight-tested domain | By design; use a preset inside it (ISS air, Pre-EVA) |
| No Apollo 1 preset in the picker | The API predates contract 0.7.0, or runs from an old image | `/api/health` must report `api_version` 0.7.0; redeploy from this branch |
| Apollo 1 timeline links open NTRS instead of the evidence page | The three new reports are not ingested yet | Re-run `python -m flame_api.ingest`; links fall back to NTRS by design |
| Knowledge Graph page error "reading 'toLowerCase'" | Web build older than 2026-11-13 meets NLP graph types (platform, instrument) | Rebuild the web app from this branch |
| Video panel empty | Demo analyses not submitted, or the worker is not running | Run `submit_demo_analyses.py`; check the worker log |
| Pages blank after a rebuild | An old `next-server` process is still serving | Kill every `next-server` process and start again |

**Fallback if the network or Docker fails on stage:** run path B on the presenter's laptop (all data is in git). If even that fails, use the screenshots in `docs/presentations/screenshots/`, which come from the verified run.

## Known limitations
- Path A (Compose) has not been run end to end in this environment (no Docker daemon). The image layout was checked by reproducing its `COPY` lines and serving the app from them.
- The Railway deployment has not been redeployed with this branch; it needs someone with Railway access.
- The browser smoke test (11 steps) passed end to end on 2026-11-13 against PostgreSQL 16 + pgvector, Redis, `moto_server` as S3, the reranker and the ingested 27-report corpus. The CI job `demo-smoke` is new and runs on the PR.

## Changelog
- 1.0.0 (2026-11-07): first runbook for the final demo.
- 1.2.0 (2026-11-12): the Knowledge Graph page replaces the API-only step; smoke test has 9 steps.
- 1.3.0 (2026-11-13): the Apollo 1 scenario (demo rows 2a–2c, smoke steps 02b–02c, `npm run smoke`, CI job), 27 reports and new ingest numbers, three troubleshooting rows.
- 1.1.0 (2026-11-12): reranker model preparation, graph counts in the ingest summary, optional knowledge-graph step, two troubleshooting rows (reranker, admin scope).
