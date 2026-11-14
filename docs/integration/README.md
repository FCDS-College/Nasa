# AURA integration

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current for Flame contract 0.8.0 and AURA `b655421` | 1.3.0 | 2026-11-14 | L-12, ADR-004 | `docs/api/openapi.json`, `ai/providers/cloud/aura.py`, `apps/api/flame_api/{ai_runtime,aura_integration,worker,clients}.py`, `tests/integration/aura_blueprint_dryrun.py`, `.github/workflows/aura-link2-contract.yml` |

This is the entry point for connecting **AURA** (`anasibrahimgnedy-collab/AURA-AI`, a self-hosted AI platform) to **Flame in Freefall**: what the integration is, what is proven, how to set it up, and how to keep it working. The detailed records are linked in §9.

## 1. What the integration is

Flame and AURA are separate systems. They meet at two narrow, versioned links, and both are optional (ADR-004: AURA is never a core dependency of Flame):

```
                    Link 2: AURA reads Flame (read-only tools compiled from Flame's OpenAPI)
  AURA agent  ──── GET /api/{health, search, documents, experiments, evidence, analyses,
  (orchestrator)        investigations, insights, …}  with a Flame read key ───────────────▶  Flame API

                    Link 1: Flame asks AURA to write text (optional external LLM behind Flame's router)
  Flame API / worker ── POST /api/v3/chat  with the svc-flame service key;
                        tools, memory and knowledge off; evidence in `context` ─────────────▶  AURA
```

- **Link 2 lets AURA users ask about NASA combustion data.** AURA discovers Flame's OpenAPI contract and compiles each eligible GET into an agent tool. AURA's own model then answers from Flame's evidence, citing Flame `evidence_id`s.
- **Link 1 lets Flame use AURA's model as one more text provider.** It is used for chat answers and analysis interpretation, next to Flame's local models (Ollama, llama.cpp, vLLM). Flame does its own retrieval and validates everything AURA returns.
- **What never crosses either link:** databases, vector indexes, object storage, model weights and Firebase identities. AURA's Flutter client has no Flame code; it reaches Flame only through the AURA backend.

## 2. Status: built, tested, proven

| | Link 2 (AURA → Flame) | Link 1 (Flame → AURA) |
|---|---|---|
| Built | Yes: 16 tools | Yes: `AuraProvider`, interpretation and chat through the router |
| Contract-tested | **Yes, 2026-11-14.** Dry run of contract 0.8.0 vs AURA `b655421` (AURA `main`, the CI pin since 2026-11-14; before that `667c7c4`, then `d696fad`): 18 tools ACCEPTED, 10 operations excluded, every query parameter reachable on its own route, exit 0. Runs in CI as the `flame-openapi` job. | **Flame side:** 17 tests in `apps/api/tests/test_aura_integration.py` against mocked AURA HTTP (schema-failure fallback, idempotency, context cap, readiness incl. `local_healthy`, `capability_unavailable`, outage). **AURA side, at `667c7c4`:** AURA's own 389 tests for caller context, service keys, structured output, idempotency, data classification, degradation and its OpenAPI adaptation pipeline pass in AURA's locked environment. AURA's context guards accept all 10,562 of Flame's evidence excerpts (§5) |
| Live, end to end | Once, on Railway, 2026-10-07, with an older contract (8 tools). AURA's report `docs/reports/flame-link2-live.md` lacks items its runbook §2.6 requires. **Not re-run with contract 0.5.0 or 0.6.0.** | **Never run live** (needs an AURA service key, and an AURA model allowed to read Flame's evidence: §5) |
| Live target today | **None reachable.** On 2026-11-12 at 15:54 UTC, both `aureon-ai.tech` and `aura-ai-production-03a4.up.railway.app` answered `/health/ready` with Railway's 404 "Application not found". | Same |
| Proven | **No.** It needs a complete live report (AURA runbook §2.6). | **No.** It needs a live report (AURA runbook §3.4). |

"Built" and "tested" are not "proven". Do not describe either link as working end to end until its live report exists.

## 3. Link 2: what AURA can call

AURA compiles **GET operations only**, and skips any operation marked `x-aura-exclude: true` in `docs/api/openapi.json`.

**Compiled tools (16).** AURA prefixes each with its blueprint id, e.g. `bp3_api_search`.

| Tool | Flame operation | Answers |
|---|---|---|
| `api_get_health` | `GET /api/health` | Is Flame up? Which AI providers and mode? |
| `api_get_dashboard_counts` | `GET /api/dashboard/counts` | Corpus size and knowledge version |
| `api_search` | `GET /api/search` | Hybrid search over 27 NASA reports, NASA investigation metadata and 1958 PSI table experiments (1950 flight tests from 19 investigations, plus 8 ground-study rows; `apps/api/tests/test_ingestion.py`, `test_fire_safety_api.py`); every hit has an `evidence_id` and a page or row locator |
| `api_list_documents`, `api_get_document` | `GET /api/documents[/{id}]` | Corpus documents |
| `api_list_experiments`, `api_get_experiment` | `GET /api/experiments[/{id}]` | Flight tests with their published conditions, each cell with an `evidence_id` |
| `api_get_evidence` | `GET /api/evidence/{id}` | The citation: source, file checksum, locator and excerpt |
| `api_list_analyses`, `api_get_analysis` | `GET /api/analyses[/{id}]` | Image and video flame analyses (pixel measurements; never temperature) |
| `api_list_investigations` | `GET /api/investigations` | Investigations ranked by evidence relevance to a cabin atmosphere ([ADR-011](../architecture/adr/ADR-011-scenario-relevance-ranking.md)) |
| `api_get_investigation` | `GET /api/investigations/{id}` | NASA's own summary of one investigation, cited, plus its data envelope |
| `api_list_insights` | `GET /api/insights` | Computed fire-safety statements for an atmosphere, with evidence IDs and coverage gaps |
| `api_estimate_flex_outcome` | `GET /api/insights/flex-outcome` | FLEX droplet-flame outcome estimate (claim class `estimated`). Refuses outside the flight-tested domain and returns the nearest real tests. |
| `api_list_graph_entities` | `GET /api/graph/entities` | Knowledge-graph entities (investigations, experiments, fuels, condition variables, phenomena, documents) by type or name ([ADR-007](../architecture/adr/ADR-007-graph-storage.md)) |
| `api_get_graph_entity` | `GET /api/graph/entities/{id}` | An entity and its neighbourhood up to 3 hops, every edge with the evidence cell it was read from (e.g. which fuels the FLEX tests that ended in extinction burned) |

**Excluded on purpose (10, `x-aura-exclude`).**

- `POST /api/chat`. Flame's chat may itself call AURA (Link 1); a tool for it would let AURA call back into its own caller.
- `GET /api/ai/providers` and `PUT /api/admin/ai/mode`: operator views and controls.
- The six `/api/admin/*` data operations: files, ingestion runs, reprocess, evidence review, audit, graph consistency.
- `POST /api/analyses/{id}/cancel`: AURA never changes a user's jobs.

**Not compiled.**
- `POST /api/analyses`: a write. AURA never holds a write key.
- `GET /api/analyses/{id}/artifacts/{kind}`: a binary response. AURA can link to it.

## 4. Setting up Link 2

**On Flame:**

1. Serve the API over **https** where the AURA gateway can reach it. AURA sends credentials only over https; `GET /api/openapi.json` needs no token.
2. Issue AURA its own **read-scoped** key. Per-client keys replace the deprecated shared `FLAME_READ_API_TOKEN`, and AURA can then be revoked and rate-limited on its own:

   ```bash
   cd apps/api && python -m flame_api.clients create aura --scopes read
   ```

   The key (`flk_…`) is printed once and stored only as a SHA-256 hash.
   - **Never give AURA a `write` key.**
   - Rotate by creating `aura-2026-12`, deploying it on AURA's side, then running `python -m flame_api.clients revoke aura`.
   - Reads are rate-limited per client (`FLAME_READ_RATE_LIMIT_PER_MINUTE`, default 600). Over the limit, AURA gets 429 with `Retry-After`.
3. Check compatibility offline against the AURA revision you will deploy. Expect 16 `ACCEPTED`, 10 excluded and exit 0:

   ```bash
   AURA_BACKEND=/path/to/AURA-AI/aura_backend python tests/integration/aura_blueprint_dryrun.py
   ```

**On AURA** (Super Admin, following AURA's `docs/guides/flame-integration-runbook.md` §1–§2):

1. Set `AURA_ADAPTATION_ENABLED=true` and `AURA_PROJECT_DATA_ROLES=<role>`.
2. Register an `openapi` connector:
   - `endpoint`: `https://<flame-host>/api/openapi.json`;
   - `secret`: the `flk_…` key from step 2 above;
   - `options.read_only_attested`: `true`.
3. Approve the connector (ideally a second person), then activate it.
4. Snapshot, compile and evaluate the blueprint; approve and deploy it.
5. Ask a question as a user in the project-data role, then keep the evidence report the runbook asks for (§2.6).

AURA's runbook matches contract 0.6.0: 16 tools and 10 exclusions (AURA-AI #232). AURA-AI #234 adds preparing Flame's reranker model before AURA probes `api_search`, and checking graph answers on Flame's Knowledge Graph page.

## 5. Setting up Link 1

**On AURA:**

```bash
curl -X POST "$AURA/api/v3/admin/service-keys" -H "$ADMIN" -d '{"name": "svc-flame", "rate_per_minute": 6}'
```

The token is shown once. It reaches `POST /api/v3/chat` only.

**On Flame** (API *and* worker; never commit the token):

| Setting | Value |
|---|---|
| `FLAME_AURA_ENABLED` | `true` |
| `FLAME_AURA_SERVICE_TOKEN` | the `svc-flame` token, from the secret store |
| `FLAME_AURA_BASE_URL` | AURA's **https origin only** (no path, query or credentials; validated at start-up) |
| `FLAME_AURA_TIMEOUT_S` | ≤ 120 (default 120) |
| `FLAME_AURA_REQUIRE_LOCAL` | `true` (default): AURA must answer with a model on its own host. When AURA reports no healthy local model (`local_healthy: false`), Flame marks AURA down and skips it without calling. Set `false` only if AURA's model is remote by design, and read "What AURA needs to answer" below first. |

**What AURA needs to answer.** AURA classifies every turn that carries caller `context` as **SENSITIVE** (AURA ADR-030 §4). Flame always sends evidence in `context`, so every Link 1 call is SENSITIVE, and AURA sends it only to a model whose data ceiling allows that:

| AURA model | Default ceiling | Can answer Flame? |
|---|---|---|
| A local model (Ollama, vLLM, llama.cpp on AURA's host) | `sensitive` | **Yes.** This is what `FLAME_AURA_REQUIRE_LOCAL=true` relies on |
| A hosted open-weight API (ADR-030 slot, e.g. `hosted1`) | `internal` | Only if AURA's operator sets `AURA_PROVIDER_<NAME>_MAX_DATA_CLASSIFICATION=sensitive` **and** Flame sets `FLAME_AURA_REQUIRE_LOCAL=false`. AURA refuses `sensitive` for a slot that may train on prompts (`:free` models). |
| Claude (ADR-033, opt-in) | `internal` | Only under the same two changes as a hosted slot. AURA allows `sensitive` here and logs a warning when it is set. |

Otherwise AURA answers 503 `capability_unavailable` (`retryable: false`): AURA is up, but no model it may use for this content answered. Flame treats it like any 503, falling back to its own models or to interpretation `unavailable`, and logs `upstream=capability_unavailable`. A hosted-only AURA, which is what served `aureon-ai.tech` when AURA last recorded it (2026-10-28), therefore cannot answer Flame until one of the two changes above is made. Raising a hosted slot's ceiling sends Flame's evidence to that third party. NASA's data is public, but AURA's rule covers all caller evidence, so the decision belongs to AURA's operator.

**AURA's guards on Flame's evidence.** AURA runs caller `context` through its context guards, and a flagged entry is dropped and taints the turn. Every evidence excerpt in Flame's database (10,562: 10,244 table cells, 315 PDF passages, 3 measurements) passes the guards at both AURA `d696fad` and `667c7c4`. 67 PDF passages are Unicode-normalised (NFKC: ligatures and soft hyphens), not dropped.

**Where AURA sits in Flame's routing** (`FLAME_AI_EXECUTION_MODE`, or the audited `PUT /api/admin/ai/mode`):

| Mode | AURA's place |
|---|---|
| `cloud_preferred` | Tried first; local models are the fallback |
| `local_first` (default) | Fallback after local models |
| `offline_only` | **Never contacted** (the egress guarantee) |

**What Flame sends** (`ai/providers/cloud/aura.py`):
- `use_tools`, `use_memory`, `use_knowledge` and `plan` are all false: Flame does its own retrieval.
- Evidence goes **only** in `context`, AURA's DATA channel: at most 16 entries of at most 2000 characters each. NASA text never goes in `message`.
- A `response_schema`. For interpretations, `claim_class` is limited to `inferred`, `hypothesized` or `unsupported`.
- `Idempotency-Key: <id>:<16 hex of the body's SHA-256>` and `X-Correlation-Id: <id>`.

**What Flame does with the answer:**
- It validates the answer again (`flame_api/generation.py`) and drops citations outside the retrieved evidence.
- AURA's text is stored as interpretation (`aura_interpretation`), **never as evidence**.
- Failures fall back to the next permitted provider; 422 `output_invalid` and 503 `capability_unavailable` are fallback-eligible. AURA's error slug appears in the error message and in the `routing_attempt_failed … upstream=<slug>` log line.
- If no provider answers, chat returns the retrieved evidence with `generation_unavailable`, and an analysis keeps its measurements with interpretation `unavailable`.

## 6. Rules that keep the integration safe

1. AURA holds a Flame **read** key only. Link 1 uses a separate AURA service key limited to `/api/v3/chat`.
2. Every request between the systems uses https and a bearer credential. Firebase identities are not mapped across.
3. `x-aura-exclude` must stay on chat, provider and admin operations. `test_operations_that_reach_flames_model_path_or_change_config_are_excluded_from_aura` fails if chat, the provider view or the mode switch lose it, or if any write other than `POST /api/analyses` becomes visible to AURA. The admin GETs are excluded in the contract but not pinned by that test.
4. Model text is never evidence on either side. AURA must cite Flame `evidence_id`s, and Flame validates AURA's citations against its own retrieved set.
5. Scientific display rules travel with the data (`API_INTEGRATION_REFERENCE.md` §8):
   - no temperatures;
   - show `claim_class` and `classification`;
   - pass on `warnings`;
   - `null` means not recorded, not zero.

## 7. Keeping the two in sync

- **Any change to Flame's contract** (`docs/api/openapi.json`, `apps/api/**`) triggers the `AURA Link 2 Contract` workflow. Its `flame-openapi` job compiles AURA's tools at the pinned AURA revision. Two things keep it running:
  - it needs the `AURA_REPO_TOKEN` repository secret to check out AURA;
  - the pin (`ref:` in `.github/workflows/aura-link2-contract.yml`, now `b655421`) should move when AURA changes its connector or compiler. Between `d696fad` and `667c7c4` (218 AURA commits), AURA's OpenAPI connector, adaptation pipeline, service keys, caller-context handling, idempotency and `/api/v3/chat` request model did not change. The one new request field, `workspace_root`, is optional and only for AURA's desktop IDE. `667c7c4` → `b655421` changes one compiler constant: AURA compiles up to 12 optional query parameters per tool instead of 8 (AURA #235), because `GET /api/insights/suppression-advice` declares 10.
  - the check counts a query parameter as reachable only if the tool for its own route exposes it. Before 2026-11-14 it matched names across all tools, which hid `droplet_diameter_mm` on the suppression route behind the flex-outcome tool's parameter of the same name.
- **Additive Flame changes** (new GET operations) need **re-discovery on AURA** before its agents see them. Run snapshot → compile → evaluate → approve → deploy (AURA runbook §4). Until then, AURA keeps the tools it had.
- **Breaking Flame changes** need a minor contract bump (pre-1.0), a `docs/api/CHANGELOG.md` entry, and a dry run against AURA before merging.

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| AURA tool calls return 401 | Wrong, missing or revoked Flame key, or the connector is not on https | `python -m flame_api.clients list`; re-issue and update the connector secret |
| AURA tool calls return 403 | The key has the wrong scope | Issue a `read`-scoped key |
| AURA tool calls return 429 | Per-client read limit reached | Honour `Retry-After`; raise `FLAME_READ_RATE_LIMIT_PER_MINUTE` if needed |
| Dry run shows fewer tools or `not reachable by AURA` | The contract changed, or the AURA revision differs | Read the dry run's per-tool verdicts; fix the contract or bump the pin |
| AURA agents do not see `api_list_investigations`, `api_get_graph_entity` or the other new tools | AURA has not re-discovered since contract 0.5.0 / 0.6.0 | Re-discovery (§7) |
| `/api/health` says "AURA has no healthy local model and FLAME_AURA_REQUIRE_LOCAL is true" | AURA's `/health/ready` reports `local_healthy: false` | Run a local model on AURA, or follow "What AURA needs to answer" (§5) |
| Link 1 calls fail with 503 and the log says `upstream=capability_unavailable` | No AURA model allowed to receive SENSITIVE content answered (§5) | A local model on AURA, or a hosted slot raised to `sensitive` with `FLAME_AURA_REQUIRE_LOCAL=false` |
| AURA's URL answers 404 "Application not found" | The Railway domain is not attached to a running AURA service | AURA's owner redeploys or reattaches the domain; update `FLAME_AURA_BASE_URL` and the Link 2 connector if the host changed |
| `/api/health` shows `aura: disabled` | `FLAME_AURA_ENABLED` is false or the service token is unset | Set both on API **and** worker |
| AURA is never called | Mode is `offline_only`, or a local model answered first under `local_first` | Expected; check `execution.provider` in chat responses |

## 9. Document map

| Document | Use it for |
|---|---|
| [AURA_INTEGRATION_AUDIT.md](AURA_INTEGRATION_AUDIT.md) | Defects found and fixed on both sides (I1–I8, A1–A5) and test evidence, as of 2026-10-30 (contract 0.3.0) |
| [API_INTEGRATION_REFERENCE.md](API_INTEGRATION_REFERENCE.md) | Per-endpoint behaviour: errors, timeouts, retries, examples and scientific display rules. Written for contract 0.3.0; for the fire-safety operations and per-client keys, use `docs/api/openapi.json` and §3–§4 here |
| [AURA_INTEGRATION_REQUIREMENTS.md](AURA_INTEGRATION_REQUIREMENTS.md) | The original requirements (FR/AR/SR/CR/NR); partly superseded |
| [AURA_INTEGRATION_STATUS.md](AURA_INTEGRATION_STATUS.md) | History only |
| `docs/api/openapi.json`, [CHANGELOG](../api/CHANGELOG.md) | The contract (source of truth) |
| [ADR-004](../architecture/adr/ADR-004-aura-boundary.md) | Why AURA is optional and never a core dependency |
| AURA repo: `docs/guides/flame-integration-runbook.md`, `docs/reports/flame-link2-live.md` | AURA-side setup steps and the live Link 2 report |

## Known limitations

- Neither link is proven end to end. Link 2's only live run predates contracts 0.5.0 and 0.6.0 and is incomplete; Link 1 has never run live. On 2026-11-12 no AURA deployment was reachable to run either.
- Flame's health check sees `local_healthy` but not whether any AURA model may receive SENSITIVE content, so with `FLAME_AURA_REQUIRE_LOCAL=false` a hosted-only AURA still looks "up" until a call returns `capability_unavailable`.
- The guard check (§5) used AURA's default context guards and thresholds; a deployment that changes them needs to re-check.
- Search and chat history are not persisted by Flame; AURA's research history covers only what AURA itself records.
- AURA cannot start analyses (writes are not compiled) and cannot read artifacts as tool output (binary).

## Changelog

- 1.1.0 (2026-11-12): contract 0.6.0: 16 tools (two knowledge-graph reads) and 10 exclusions (cancel, graph consistency); fresh dry run.
- 1.2.0 (2026-11-12): re-checked against AURA `main` `667c7c4`, and the CI pin moved there. Link 1 now has a section on what AURA needs to answer (SENSITIVE caller evidence, data ceilings, `capability_unavailable`) and the guard check over Flame's evidence. Flame now reads `local_healthy` and names AURA's error slug. Also: the live AURA hosts were unreachable on 2026-11-12, and the stale runbook notes and test count are fixed.
- 1.2.1 (2026-11-14): `api_search` row: 1958 table experiments from the 19 PSI investigations on `main`, not 840.
- 1.3.0 (2026-11-14): CI pin moved to AURA `b655421` (up to 12 optional query parameters per tool), so the suppression-advice route's `delivery_fraction` and `droplet_diameter_mm` reach AURA; the dry run checks reachability per route. Contract-tested row updated to contract 0.8.0 (18 tools).
- 1.0.0 (2026-11-07): first README. It reflects contract 0.5.0 (14 tools, 8 exclusions), per-client keys, and a fresh dry run.
