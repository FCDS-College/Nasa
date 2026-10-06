# Flame in Freefall × AURA AI: Integration Requirements

**Date:** 2026-10-05 · **Revisions checked:**

- Flame in Freefall: `28921c0` (`FCDS-College/Nasa` main).
- AURA AI: `3a60bca` (`anasibrahimgnedy-collab/AURA-AI` main) for the findings in §2.
- AURA AI state column in §3: re-checked against `main` at `25cc5b8` plus AURA PR [#156](https://github.com/anasibrahimgnedy-collab/AURA-AI/pull/156), merged 2026-10-06.
**Inputs:** [`data/COMBUSTION_DATASET_ANALYSIS.md`](data/COMBUSTION_DATASET_ANALYSIS.md) (what the data is), [`AURA_INTEGRATION_STATUS.md`](AURA_INTEGRATION_STATUS.md) (boundary design and status audit), [`openapi.json`](openapi.json) (the contract).
**Evidence script:** [`../tests/integration/aura_blueprint_dryrun.py`](../tests/integration/aura_blueprint_dryrun.py) runs AURA's own discovery → twin → planner → compiler over `openapi.json` with no network.

This document turns the status audit into a numbered, testable list of requirements. Each one names its owner, its acceptance evidence and its current state. **A requirement is met only when its acceptance evidence exists.** That is the rule both repositories already follow: "built" and "tested" are not "proven".

---

## 1. The integration in one paragraph

Flame owns the science: NASA files, provenance, experiment conditions, CV measurements and evidence. AURA owns general reasoning and conversation. The two meet at two links, each through a published API and never through each other's databases:

```
                     ┌───────────────────────── Flame in Freefall ──────────────────────────┐
 Dashboard ─────────►│ /api/* (docs/openapi.json)                                            │
                     │   search · documents · experiments · evidence · analyses · health     │
                     │                                    ▲                    │             │
                     │  Postgres+pgvector · MinIO · Redis  │ LINK 2 (read)      │ LINK 1      │
                     └─────────────────────────────────────┼────────────────────┼─────────────┘
                                                           │ OpenAPI connector  │ async, after CV
                                                           │ generated read     │ measurements are
                     ┌──────────────────────── AURA AI ────┴──────┐             │ final
                     │ Track AP: discovery → twin → blueprint →   │◄────────────┘
                     │ bpN_api_* tools (DATA channel, read-only)   │  POST /api/v3/chat
                     │ AIKernel · ProviderRouter · RAG/memory      │  (interpretation only;
                     └────────────────────────────────────────────┘   Flame validates output)
```

- **Link 1: Flame → AURA (interpretation).** After an analysis is measured, Flame asks AURA to interpret it. Flame validates every returned statement (claim class, evidence IDs, no temperature claims) before storing it. AURA is optional; its failure never fails an analysis.
- **Link 2: AURA → Flame (conversational access).** AURA registers Flame's `openapi.json` as a read-only connector and compiles read tools from it. An AURA user can then ask "which FLEX heptane tests extinguished below 0.15 O₂?" and get an answer grounded in Flame's evidence API.

---

## 2. Proven findings that drive the requirements

These were run, not inferred. Each finding is as found at AURA `3a60bca`; the **Status now** column records what has changed since. Re-run them with:

```bash
AURA_BACKEND="E:/AURA AI/aura_backend" python tests/integration/aura_blueprint_dryrun.py
```

| # | Finding | Evidence | Consequence | Status now |
|---|---|---|---|---|
| P1 | AURA compiles **8 read tools** from Flame's contract: `api_search`, `api_get_experiment`, `api_get_evidence`, `api_get_document`, `api_get_analysis`, `api_list_analyses`, `api_get_dashboard_counts`, `api_get_health`. `POST /api/analyses` and the binary artefact route are correctly excluded. | dry-run output | The Link 2 design works in principle. | Still true. |
| P2 | **All 8 tools would reject every contract-conformant response.** Every object-valued property (`meta`, `pagination`, `experiment`, `evidence`, `services`, …) is compiled as `{"type":"string"}`, and AURA's tool registry rejects any result that breaks its declared schema (`aura_core/tools/registry.py:375-390`, ADR-025). | dry-run: `REJECTED: $.meta: expected string …` on 8/8, exit code 1 | **Link 2 is blocked today.** Root cause: AURA's OpenAPI discovery records `$ref`, `anyOf`/`oneOf` and OpenAPI 3.1 type-array properties without a JSON type, and `json_type()` (`aura_core/adaptation/factories/common.py:45-67`) defaults them to `string`. → AR-1 | **Fixed and merged:** AR-1 (AURA #154). The dry run now reports 8/8 ACCEPTED, exit 0. |
| P3 | Generated tools expose **only required query parameters**. 14 optional parameters are unreachable, including `domain`, `source_id`, `type`, `experiment_id`, `page` and `page_size` on `/api/search`. | dry-run: `not reachable by AURA: …`; `aura_core/adaptation/factories/tools.py:353-358` | AURA cannot filter by investigation or page through results, and it depends on the server's default `domain`. → AR-2, FR-3, FR-4 | **Merged in AURA #156 (AR-2); built and tested, not proven live.** The dry run now prints no `not reachable` lines: all 14 parameters are exposed, `source_id`/`status` arrays included. |
| P4 | An OpenAPI connector **with a credential is refused at activation**: health reports `write_capable=None` (`credential_scope_unknown`), and activation requires `False`. | `aura_core/adapters/connectors/openapi.py:18-21, 355-360`; `aura_core/adaptation/connectors.py:169` | AURA can read Flame today only if Flame's read endpoints are **anonymous**. → AR-3 or FR-5 | **Merged in AURA #156 (AR-3); built and tested, not proven live.** The connector option `read_only_attested: true` is bound into the approval digest. |
| P5 | AURA accepts **only user or device JWTs**. There is no service credential for Flame to call `/api/v3/chat`. | `aura_service.py:34-110`; roadmap AP12a = DOCUMENTED | Link 1 needs a human account's token, which is unacceptable beyond a demo. → AR-4 | **Merged in AURA #156 (AR-4); built and tested, not proven live.** The service key is `svc-flame`. |
| P6 | `ChatRequest` has no caller-context field and no structured-output mode. | `aura_core/api/v3.py:107-125` | Flame cannot pass evidence safely (putting it in `message` lands on the USER channel, ADR-006), and it must parse free text. → AR-5, AR-6 | **Merged in AURA #156 (AR-5 `context`, AR-6 `response_schema`); built and tested, not proven live.** |
| P7 | AURA's production model runs at about 5–10 tokens/s on CPU. | AURA `CLAUDE.md` "Deploy" | Interpretation must be asynchronous, short (≤ 400 tokens) and planning-off. → NR-1 | Unchanged. A structured turn can cost one repair generation as well (§7 NR-1). |
| P8 | The mirrored data supports condition-and-outcome questions (FLEX: 274 tests with an outcome label) and CV on BASS-II/FLEX media. It does **not** support temperature from images, BASS-II outcomes from its table, or SAFFIRE-I flame CV from the mirrored frames (those are flow visualisation). | dataset analysis §3, §4, §6 | These boundaries become validation rules (FR-7) and disclosures (FR-8). | Unchanged. |

---

## 3. AURA-side requirements (AR)

| ID | Requirement | Acceptance evidence | Priority | State |
|---|---|---|---|---|
| **AR-1** | **Type fidelity for OpenAPI-derived output schemas.** Discovery must record a JSON type for every property: `$ref` → the target's type (`object` for component schemas); `anyOf`/`oneOf` of `X` and `null` → `[X, "null"]`; OpenAPI 3.1 `type: [X, "null"]` → the same; `array` keeps its `items` type. Nested objects may stay shallow (`{"type":"object"}`), but they must never be `string`. | (a) `aura_blueprint_dryrun.py` exits 0 with 8/8 ACCEPTED; (b) a new AURA unit test with an OpenAPI 3.1 envelope fixture (`{data, meta}` + nullable `$ref`); (c) the hr/ecommerce pilot goldens regenerated, with the diff reviewed. | **P0, blocker for Link 2** | **Merged (AURA #154); dry-run re-confirmed on `25cc5b8`.** (a) dry-run 8/8 ACCEPTED, exit 0; (b) 13 discovery cases + 1 end-to-end compiler test, failing before the fix; (c) the HR golden changed for exactly one property (`Employee.department`, `string` → `object`): the pilot had the same latent bug. Ecommerce unchanged. |
| **AR-2** | **Optional query parameters on generated GET tools**: emit declared optional `query` parameters as optional tool parameters, carrying their `enum`, `minimum`/`maximum` and `default` from the spec. Absent arguments are omitted (this is already how `render_http` behaves). Cap the count per tool. | Dry-run lists no `not reachable` lines for `domain`, `source_id`, `type`, `page_size`; a hostile-value test shows values are percent-encoded and enum-checked. | P1 | **Merged in AURA #156; built and tested, not proven live.**<br>• Exposes up to 8 optional query parameters per tool, typed, with enum and bounds.<br>• Arrays render as repeated keys.<br>• Server defaults are described, never sent.<br>• Dry run: no `not reachable` lines.<br>• Hostile-value test: `TestOptionalQueryParameters`. |
| **AR-3** | **Credentialed read-only OpenAPI connectors.** Lets a connector carry a Flame bearer token without being refused. Either (a) the operator attests read-only scope at registration, bound into the approval digest, with GET-only templates kept as the enforcement; or (b) a scope probe the target API declares. | Activation test: a credentialed connector becomes ACTIVE; the token is never present in the descriptor, digest, audit or logs (existing redaction tests extended). | P1 (P0 if Flame's API cannot be anonymous) | **Merged in AURA #156 (option a); built and tested, not proven live.**<br>• Option `read_only_attested: true`, which is digest-bound and audited.<br>• Activation test with a real OpenAPI adapter: the token never appears in the descriptor, digest, audit or logs (`TestAttestedReadOnlyOpenApi`). |
| **AR-4** | **Service credential for Flame → AURA** (AP12a "scoped API keys per surface", narrowed): a non-human principal `svc-flame` limited to `POST /api/v3/chat` (and `/knowledge/documents` only if Option B is chosen), with its own rate limit, revocation, audit actor, and **no memory writes**. | Tests: the key reaches `/chat` and gets 403 elsewhere; revocation takes effect immediately; rate limit returns 429 with `Retry-After`; the audit trail names `svc-flame`. | **P0, blocker for Link 1** | **Merged in AURA #156; built and tested, not proven live.**<br>• Reaches `/chat` only by default. Every other route gets a 403; WebSockets are refused.<br>• Revocation applies on the next request.<br>• Own rate limit: 429 with `Retry-After`.<br>• Audit actor is `svc-flame`, carrying Flame's correlation id.<br>• No memory, no tools, no session.<br>• Postgres store verified on PostgreSQL 16. |
| **AR-5** | **Caller context on the DATA channel**: `ChatRequest.context: [{id, text, source}]` (bounded count and size). Entries are fenced with the per-turn nonce as DATA, exactly like retrieved chunks. A turn with context is treated as tainted for side-effecting tools. Citations may name a context `id`. | Test: an injection string inside `context` cannot trigger a side-effecting tool or change the persona; a citation of a context id is returned verbatim; an unknown id is never returned. | P1 (removes the need for the Option B corpus mirror) | **Merged in AURA #156; built and tested, not proven live.**<br>• At most 16 entries of up to 2000 characters each.<br>• Guarded like retrieved chunks and fenced as DATA.<br>• Sending any context taints the turn.<br>• Citations are the caller's ids; an id that was never sent cannot appear.<br>• Injection, fencing and citation tests: `tests/security/test_caller_context.py`. |
| **AR-6** | **Structured output**: `ChatRequest.response_schema` (a JSON Schema in the subset already supported by `output_schema.py`). AURA validates the model output, retries a repair once, and otherwise returns `422 output_invalid`. It never returns unvalidated JSON as valid. | Tests with the echo provider: valid output passes; invalid output triggers one repair and then a 422; the token budget is respected. | P2 (Flame can parse free text until then) | **Merged in AURA #156; built and tested, not proven live.**<br>• One repair that sees error paths only, and only within the turn's budget; otherwise `422 output_invalid`.<br>• Success adds `data`.<br>• Echo-provider tests cover valid, repaired, twice-invalid and budget-spent cases. |
| **AR-7** | **Prove Track AP on a live target.** AP3/AP7 are "IMPLEMENTED, CI pending". Run the connector → discover → compile → approve → deploy flow against a running Flame API on the dev stack. | A report in AURA `docs/reports/` showing a deployed `bpN_api_search` answering a real question with a Flame `evidence_id` in its result. | P1 | Built, not proven. **Procedure ready:** AURA `docs/guides/flame-integration-runbook.md` §2 (names the report). **Not run**: needs FR-1/FR-2. |
| **AR-8** | **Contract drift handling.** Until AP11 (drift/impact) exists, re-run discovery and recompile whenever Flame's `info.version` changes. A tool whose output schema no longer matches must fail closed (it already does, per P2). | Runbook entry plus a dry-run in Flame CI on every `openapi.json` change (see CR-4). | P2 | Manual by design until AURA AP11. **Runbook written:** AURA runbook §4. The Flame-side CI job (CR-4) does not exist yet. |

No AURA work is needed for: `/health/ready` probing, `Idempotency-Key` on `/chat`, `X-Correlation-Id` propagation, the SSRF policy (Flame on a private network needs the connector option `allow_private_network: true`), or the 2 MiB read and 5 MiB spec caps (Flame's paginated responses fit within them).

---

## 4. Flame-side requirements (FR)

| ID | Requirement | Acceptance evidence | Priority | State |
|---|---|---|---|---|
| **FR-1** | **Implement the read API AURA consumes**: `GET /api/health`, `/api/search`, `/api/experiments/{id}`, `/api/evidence/{id}`, `/api/documents/{id}`, and serve `/api/openapi.json` equivalent to `docs/openapi.json` (status audit B1–B9, B12). | Contract diff test green; Prism/Schemathesis validation of live responses. | **P0** | 0 of 10 operations implemented |
| **FR-2** | **Ingest the four experimental tables into `experiment` / `experiment_condition` / `evidence`**, applying dataset-analysis fixes D1–D12: cp1252 decoding, explicit column map, unresolved-unit flags, null/censored/approximate markers, deduplication as a recorded transformation, quality flags for outliers. **One `evidence` row per source cell**, with a `table_row`/`cell` locator and the `file_id` sha256. | Golden test per table: row counts (FLEX 274; BASS-II 129; SPICE 469, which is 435 after dedupe; SAFFIRE-I 2); no `0` where the source held a missing marker; every condition resolves to an evidence id, then a file id, then a sha256 present in `checksums/sha256.txt`. | **P0** | Not started |
| **FR-3** | **A condition query AURA can call**: `GET /api/experiments?source_id=&fuel=&o2_min=&o2_max=&pressure_min_pa=&pressure_max_pa=&outcome=&page_size=` returning a paginated list with `evidence_ids` per condition. If AR-2 is not done first, give this endpoint **one required parameter** (`source_id`) so that AURA's current compiler exposes it. | Contract updated (`x-implementation-status`); dry-run shows an `api_list_experiments` tool; the example query "FLEX, heptane, o2_max=0.15, outcome=extinction" returns rows with evidence ids. | P1 | Missing from contract. *Since AURA #156 merged, the "one required parameter" workaround is unnecessary: optional filters are exposed.* |
| **FR-4** | **Honour the contract's search default on the server**: `domain` defaults to `combustion`, which keeps `FF-PSI-DSI` out. AURA cannot pass `domain` until AR-2, so it relies entirely on this default. | Test: a query without `domain` returns no DSI hits. | P0 | Specified in contract; not implemented. *Since AURA #156 merged, AURA can also pass `domain` explicitly, but the server default is still the safe one.* |
| **FR-5** | **AURA's access identity to Flame.** Until AR-3 lands, serve the read endpoints in FR-1/FR-3 **anonymously on the private network only** (no public route), with mutation routes requiring auth. After AR-3, issue a read-only bearer token scoped to `GET /api/*`. | Network test: the read API is not reachable from the public interface; `POST /api/analyses` without a token returns 401. | P0 | Missing. *Since AURA #156 merged, the anonymous-read workaround can be replaced by a read-only bearer token with `read_only_attested`.* |
| **FR-6** | **`InterpretationProvider` port + `AuraInterpreter` adapter** (status audit A2) behind `FLAME_AURA_ENABLED=false` by default. It runs in the analysis worker after `result` is final, with a 120 s timeout. On any failure it sets `interpretation.status="unavailable"` and adds the warning `INTERPRETATION_UNAVAILABLE`. | Tests with a fake AURA: success, timeout, 429, 5xx and malformed output; the analysis remains `completed` in every case. | P1 (after AR-4) | Not started |
| **FR-7** | **Statement validator** (A3): only `inferred`/`hypothesized`/`unsupported` are allowed from AURA; every `evidence_id` must exist; statements mentioning temperature, or claiming outcomes the data cannot support (P8), are dropped and counted in `rejected_statement_count`. | Table-driven tests including adversarial statements. | P1 | Not started |
| **FR-8** | **Honest coverage disclosure**: responses about BASS-II or FLEX carry the mirrored-subset coverage (3.6 % / 0.3 % of release files) in `meta`, so neither the UI nor AURA can present subset statistics as investigation-wide. | Field present in the contract + example. | P2 | Missing |
| **FR-9** | **AURA health entry**: `services.aura` reports `disabled` / `up` / `down` from AURA `GET /health/ready` with a 2 s timeout (A4). | Test for each state. | P1 | Not started |
| **FR-10** | **Data completeness for CV**: mirror the SAFFIRE-I burn imagery (`S1C*`/`S2C*`) if SAFFIRE CV is in scope; resolve the 4 unlinked FLEX runs; parse `Spice_Flight_Flamelength.xls` and the SAFFIRE `MergeResult` workbook (D13–D15). | New `files.jsonl` records + joins verified. | P2 | Open |

---

## 5. Shared contract requirements (CR)

| ID | Requirement | Acceptance |
|---|---|---|
| **CR-1** | **Identifiers**: Flame entity ids are ULIDs (as in the contract), and AURA never invents them. Under Option B (corpus mirror), AURA `document_id` = Flame document ULID, so `"{id}@v{n} (page p)"` citations resolve to Flame evidence. | The FR-7 validator resolves 100 % of accepted citations. |
| **CR-2** | **Correlation**: Flame sends `X-Request-ID`/`X-Correlation-Id`, and AURA echoes `correlation_id`. Both log it, so one interpretation can be traced across both systems. | Log query by one id returns entries from both services. |
| **CR-3** | **Claim classes**: AURA output maps onto Flame's `ClaimClass`. AURA may never produce `observed`/`measured`/`estimated`; those belong only to the CV pipeline. | Enforced by FR-7. |
| **CR-4** | **Contract change control**: any change to `docs/openapi.json` runs `aura_blueprint_dryrun.py` in Flame CI against a pinned AURA revision. A semver bump of `info.version` is required for breaking changes. | CI job green on the PR that changes the contract. |
| **CR-5** | **Errors**: AURA errors map to Flame's envelope (`AURA 429 → retryable=true`, `503 → INTERPRETATION_UNAVAILABLE`). Flame's `ErrorResponse` is JSON, so an AURA tool reports it as a tool error rather than a schema failure (this needs AR-1). | Fake-AURA tests (FR-6). |

---

## 6. Security requirements (SR)

| ID | Requirement |
|---|---|
| **SR-1** | All NASA-originated text (ISA metadata, PDF passages, table free text) is **untrusted**. It reaches AURA only as DATA: through AURA tool results (Link 2, already DATA-channel) or `context[]` (AR-5). **Never in `message`.** The status audit's Option C stays rejected. |
| **SR-2** | AURA's access to Flame is **read-only** end to end: GET-only templates (AURA), read-only identity (FR-5), no mutation route reachable with that identity. |
| **SR-3** | No AURA output is stored in Flame without validation (FR-7), and no AURA output is ever labelled as evidence. |
| **SR-4** | Credentials live only in AURA's vault (`secret_ref`) and Flame's secret store. They never appear in `openapi.json`, blueprints, logs or committed `.env` files. |
| **SR-5** | AURA never touches Flame's Postgres, MinIO or Redis directly. **Not** a Postgres connector, even though AURA supports one: that would bypass Flame's evidence and provenance layer. |

---

## 7. Non-functional requirements (NR)

| ID | Requirement |
|---|---|
| **NR-1** | Interpretation: ≤ 400 output tokens, `plan=false`, `use_memory=false`, `use_tools=false`, `require_local=true`, timeout 120 s, at most 1 concurrent call per Flame worker. Never on the dashboard request path. |
| **NR-2** | Link 2 reads: Flame read endpoints p95 < 1 s at `page_size ≤ 50`; responses < 2 MiB (AURA's cap). |
| **NR-3** | Availability independence: Flame's 10 operations work with AURA down; AURA works with Flame down (its tools return tool errors, and the turn continues). |
| **NR-4** | Licensing: data is CC0. Citations still carry the PSI DOI and file path (the provenance policy, not a legal requirement). |

---

## 8. Order of work

| Step | Work | Unblocks | Owner |
|---|---|---|---|
| 1 | **AR-1** (type fidelity, ✅ merged) + **FR-4** (default DSI exclusion) | Any Link 2 tool call | AURA · Flame |
| 2 | **FR-1** read endpoints + **FR-2** table ingestion + **FR-5** private anonymous read | Real data behind the tools | Flame |
| 3 | **AR-7** live proof: register Flame, discover, compile, deploy, ask a FLEX question | **Link 2 proven** | AURA + Flame |
| 4 | **AR-2** optional parameters (merged, AURA #156), or **FR-3** with a required `source_id` | Filtered condition queries | AURA or Flame |
| 5 | **AR-4** service credential (merged, AURA #156) → **FR-6/FR-7/FR-9** | **Link 1** (interpretation) | AURA → Flame |
| 6 | **AR-5**, **AR-6**, **AR-3** (all merged, AURA #156), **CR-4** in CI, **FR-8/FR-10** | Hardening, grounded interpretation, public deploy | both |

**Where this leaves the critical path (2026-10-06):** every AURA-side item is merged (AURA #156); AR-7 still needs a live run. Integration now waits on two things:

- Flame's own P0 work: **FR-1, FR-2, FR-4, FR-5**;
- for Link 1, **FR-6, FR-7, FR-9**.

AURA's runbook (`docs/guides/flame-integration-runbook.md`) gives the exact interpretation request body (NR-1 flags, `context`, `response_schema` with the `inferred`/`hypothesized`/`unsupported` enum) and the error mapping for CR-5.

**Definition of integrated:** Link 2 is integrated when step 3's report exists. Link 1 is integrated when an analysis on the dev stack carries `interpretation.status="completed"` with validated statements, and an AURA outage leaves the analysis `completed` with `INTERPRETATION_UNAVAILABLE`. Until then, the status in `AURA_INTEGRATION_STATUS.md` §1 stays accurate: designed, not implemented.
