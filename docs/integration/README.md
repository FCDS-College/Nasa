# AURA integration

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current for Flame contract 0.5.0 and AURA `d696fad` | 1.0.0 | 2026-11-07 | L-12, ADR-004 | `docs/api/openapi.json`, `ai/providers/cloud/aura.py`, `apps/api/flame_api/{ai_runtime,aura_integration,worker,clients}.py`, `tests/integration/aura_blueprint_dryrun.py`, `.github/workflows/aura-link2-contract.yml` |

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
| Built | Yes: 14 tools | Yes: `AuraProvider`, interpretation and chat through the router |
| Contract-tested | **Yes, 2026-11-07.** Dry run on `main` `cd185e3` vs AURA `d696fad`: 14 tools ACCEPTED, 8 operations excluded, exit 0. Runs in CI as the `flame-openapi` job. | Yes, against mocked AURA HTTP: 9 tests in `apps/api/tests/test_aura_integration.py` (schema-failure fallback, idempotency, context cap, readiness, outage) |
| Live, end to end | Once, on Railway, 2026-10-07, with an older contract (fewer tools). AURA's report `docs/reports/flame-link2-live.md` lacks items its runbook §2.6 requires. **Not re-run with contract 0.5.0.** | **Never run live** (needs an AURA service key) |
| Proven | **No.** It needs a complete live report (AURA runbook §2.6). | **No.** It needs a live report (AURA runbook §3.4). |

"Built" and "tested" are not "proven". Do not describe either link as working end to end until its live report exists.

## 3. Link 2: what AURA can call

AURA compiles **GET operations only**, and skips any operation marked `x-aura-exclude: true` in `docs/api/openapi.json`.

**Compiled tools (14).** AURA prefixes each with its blueprint id, e.g. `bp3_api_search`.

| Tool | Flame operation | Answers |
|---|---|---|
| `api_get_health` | `GET /api/health` | Is Flame up? Which AI providers and mode? |
| `api_get_dashboard_counts` | `GET /api/dashboard/counts` | Corpus size and knowledge version |
| `api_search` | `GET /api/search` | Hybrid search over 24 NASA reports, NASA investigation metadata and 840 flight tests; every hit has an `evidence_id` and a page or row locator |
| `api_list_documents`, `api_get_document` | `GET /api/documents[/{id}]` | Corpus documents |
| `api_list_experiments`, `api_get_experiment` | `GET /api/experiments[/{id}]` | Flight tests with their published conditions, each cell with an `evidence_id` |
| `api_get_evidence` | `GET /api/evidence/{id}` | The citation: source, file checksum, locator and excerpt |
| `api_list_analyses`, `api_get_analysis` | `GET /api/analyses[/{id}]` | Image and video flame analyses (pixel measurements; never temperature) |
| `api_list_investigations` | `GET /api/investigations` | Investigations ranked by evidence relevance to a cabin atmosphere ([ADR-011](../architecture/adr/ADR-011-scenario-relevance-ranking.md)) |
| `api_get_investigation` | `GET /api/investigations/{id}` | NASA's own summary of one investigation, cited, plus its data envelope |
| `api_list_insights` | `GET /api/insights` | Computed fire-safety statements for an atmosphere, with evidence IDs and coverage gaps |
| `api_estimate_flex_outcome` | `GET /api/insights/flex-outcome` | FLEX droplet-flame outcome estimate (claim class `estimated`). Refuses outside the flight-tested domain and returns the nearest real tests. |

**Excluded on purpose (8, `x-aura-exclude`).**

- `POST /api/chat`. Flame's chat may itself call AURA (Link 1); a tool for it would let AURA call back into its own caller.
- `GET /api/ai/providers` and `PUT /api/admin/ai/mode`: operator views and controls.
- The five `/api/admin/*` data operations: files, ingestion runs, reprocess, evidence review, audit.

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
3. Check compatibility offline against the AURA revision you will deploy. Expect 14 `ACCEPTED`, 8 excluded and exit 0:

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

Two parts of AURA's runbook predate Flame contract 0.5.0:
- It expects **10** tools and **3** exclusions; the correct figures are **14** and **8**.
- It names the shared `FLAME_READ_API_TOKEN`; use a per-client key instead.

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
| `FLAME_AURA_REQUIRE_LOCAL` | `true` (default): AURA must answer with a model on its own host. Set `false` only if AURA's model is remote by design; otherwise every call is 503 while AURA's health still says up. |

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
- Failures fall back to the next permitted provider; 422 `output_invalid` is fallback-eligible.
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
  - the pin (`ref:` in `.github/workflows/aura-link2-contract.yml`, now `d696fad`) should move when AURA changes its connector or compiler.
- **Additive Flame changes** (new GET operations) need **re-discovery on AURA** before its agents see them. Run snapshot → compile → evaluate → approve → deploy (AURA runbook §4). Until then, AURA keeps the tools it had.
- **Breaking Flame changes** need a minor contract bump (pre-1.0), a `docs/api/CHANGELOG.md` entry, and a dry run against AURA before merging.

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| AURA tool calls return 401 | Wrong, missing or revoked Flame key, or the connector is not on https | `python -m flame_api.clients list`; re-issue and update the connector secret |
| AURA tool calls return 403 | The key has the wrong scope | Issue a `read`-scoped key |
| AURA tool calls return 429 | Per-client read limit reached | Honour `Retry-After`; raise `FLAME_READ_RATE_LIMIT_PER_MINUTE` if needed |
| Dry run shows fewer tools or `not reachable by AURA` | The contract changed, or the AURA revision differs | Read the dry run's per-tool verdicts; fix the contract or bump the pin |
| AURA agents do not see `api_list_investigations` or the other new tools | AURA has not re-discovered since contract 0.5.0 | Re-discovery (§7) |
| Every Link 1 call falls back; AURA health says "up" | `require_local` is true, but AURA has no healthy local provider (`/health/ready` → `local_healthy: false`) | Run a local model on AURA, or set `FLAME_AURA_REQUIRE_LOCAL=false` |
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

- Neither link is proven end to end. Link 2's only live run predates contract 0.5.0 and is incomplete; Link 1 has never run live.
- Flame's AURA health probe reads `/health/ready` but not `local_healthy`, so with `require_local=true` Flame may show AURA "up" while every call falls back.
- AURA's runbook still describes contract 0.3.0 (10 tools, 3 exclusions, the shared read token).
- Search and chat history are not persisted by Flame; AURA's research history covers only what AURA itself records.
- AURA cannot start analyses (writes are not compiled) and cannot read artifacts as tool output (binary).

## Changelog

- 1.0.0 (2026-11-07): first README. It reflects contract 0.5.0 (14 tools, 8 exclusions), per-client keys, and a fresh dry run.
