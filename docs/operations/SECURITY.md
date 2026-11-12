# L-10: Security and access control

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current (sign-off: Belal E4, Anas E2) | 0.7.0 | 2026-11-12 | B6, MVP §19, 2H Task 9, P2-1, P2-2, P2-6, ADR-009 | `apps/api/flame_api/main.py`, `clients.py`, `admin.py`, `rate_limit.py`, `config.py`, `ai_runtime.py`, `ingest.py`, `.gitleaks.toml` |

## 1. Roles and permissions (ADR-009)

| Credential | Grants | Held by |
|---|---|---|
| Client key with `read` scope (`api_client`) | `GET`/`HEAD` on `/api/*`, and `POST /api/chat` | one key each: `web` (web app server), `aura` (AURA connector vault) |
| Client key with `write` scope | every other method outside `/api/admin/`, e.g. `POST /api/analyses` | callers that upload; never AURA |
| Client key with `admin` scope | every `/api/admin/` operation, reads included: files, ingestion runs, audit log, reprocess, evidence review, `PUT /api/admin/ai/mode` | one key per operator, created with `--owner`; never AURA or the web app |
| Read token (`FLAME_READ_API_TOKEN`), **deprecated** | the same as `read` scope; identity `legacy-read` | until every caller has its own key |
| Write token (`FLAME_WRITE_API_TOKEN`), **deprecated** | the same as `write` **and** `admin` scope, as before ADR-009 step 2; identity `legacy-write` | until operators have their own admin keys |
| Public | `/api/openapi.json`, `/api/docs`, `/health/live` | anyone |

**Client keys (P2-1, ADR-009 step 2).** `python -m flame_api.clients create NAME --scopes read[,write][,admin] [--owner PERSON]` prints a `flk_…` key once; only its SHA-256 is stored, and the stored hash is compared in constant time. `list` shows names, scopes, owners, `created_at`, `last_used_at` (refreshed at most once a minute per client) and `revoked_at`, never keys. `revoke NAME` takes effect on the next request. To rotate, create a second client (e.g. `web-2026-11`), deploy its key, then revoke the old one; revoked names are not reused. There is no HTTP endpoint for any of this: issuing a credential needs database access. A key without the needed scope gets 403 `FORBIDDEN`; an unknown or revoked key gets 401. The authenticated identity is on `request.state.api_client`, in every request log line (`client=…`) and, for admin changes, in `audit_event.actor`.

**Scopes are independent.** `admin` implies neither `read` nor `write`, so an operator who also browses or uploads asks for `--scopes read,admin` or similar. An `admin` key cannot be created without `--owner` (the person who holds it, 1–128 printable characters). Audit rows carry the client name, and names are never reused, so `clients list` maps every audited admin action to one person, also after the key is revoked. Upgrading to migration `0008_api_client_owner` gives no existing client the `admin` scope: a `write` client that used `/api/admin/` gets 403 until its operator creates an admin key. The deprecated write token keeps working there meanwhile.

**Legacy tokens.** Both are now optional. When set they keep their old meaning (a read token on a write gets 401, as before), must be at least 32 characters and must be distinct. Remove them once `web` and `aura` have their own keys.

**Rate limits (P2-2).** Every authenticated `/api/*` request except `/api/health` takes a token from its client's bucket in Redis (`FLAME_REDIS_URL`); buckets are per identity and per class, so one client cannot spend another's budget:

| Class | Setting | Default per minute |
|---|---|---|
| reads (`GET`/`HEAD`) | `FLAME_READ_RATE_LIMIT_PER_MINUTE` | 600 |
| writes | `FLAME_WRITE_RATE_LIMIT_PER_MINUTE` | 60 |
| `POST /api/chat` | `FLAME_CHAT_RATE_LIMIT_PER_MINUTE` | 30 |

A bucket holds one minute's allowance, so short bursts pass. Over budget: 429 `RATE_LIMITED`, `Retry-After` in seconds. `FLAME_RATE_LIMIT_ENABLED=false` turns it off. If Redis is unreachable the API **fails open** (one `rate_limit_backend_unavailable` warning a minute, Redis retried every 5 s) and chat falls back to the old process-wide `FLAME_CHAT_RATE_LIMIT_PER_MINUTE`. With authentication disabled every caller shares the identity `anonymous`.

**Production settings (P2-6).** With `FLAME_ENVIRONMENT=production` the API refuses to start on the local defaults: the `change-me-local-only` / `flame-local-only-change-me` S3 secret (or any containing `change-me`), the `flame-local` access key, and the `flame` / `flame-local-only` database passwords. The error names the setting, never its value, and settings errors never echo their input.

## 2. Protected operations and audit
- **Admin endpoints** (`/api/admin/*`) need the `admin` scope or the deprecated write token, enforced twice: by the auth middleware and again by the admin router (`require_admin_scope`). Every change writes one `audit_event` in the same transaction as the change:

  | Field | Contents |
  |---|---|
  | `event_id` | — |
  | `occurred_at` | — |
  | `actor` | the client name; `write-token` for the deprecated write token |
  | `action` | `ai.mode.changed`, `file.reprocess`, `evidence.review` |
  | `target_type` | — |
  | `before` / `after` | the mode before and after |
  | `request_id` | — |

- **Ingestion and index builds** stay CLI-only (`python -m flame_api.ingest`, `vector_index build`): they need database access, not a credential. The data operations an administrator can do over HTTP are listed in `docs/data/ADMIN_DATA_OPERATIONS.md`; none deletes scientific source data.

## 3. Upload and parsing isolation
- **Images:** 10 MiB, ≥ 64 px, ≤ 50 MP (`FLAME_MAX_UPLOAD_BYTES`, `FLAME_MAX_IMAGE_PIXELS`). The image is decoded with Pillow before it is queued. Uploaded content is never executed.
- **Documents:**
  - parsed only from files registered in `files.jsonl` with a matching sha256; a mismatch is quarantined;
  - PDFs that are unreadable or encrypted are quarantined;
  - in HTML, `<script>`, `<style>`, `<noscript>` and `<template>` are dropped;
  - JSON is parsed with the stdlib only;
  - no parser runs in a separate process yet. That is a known limitation for untrusted uploads, which documents currently are not.

## 4. Prompt-injection defences (with Eman)
- **Retrieved text never goes in the instruction message.** It travels as a DATA channel: AURA's `context`, or a separate system message fenced and labelled as untrusted for local models (`contracts/chat.py:render_context`).
- **The model's output is validated by Flame:**
  - JSON-schema shape;
  - length;
  - control characters;
  - citations must be in the retrieved set, otherwise they are dropped;
  - interpretations must not mention temperature or outcome claims, and claim classes are enforced.
- **No tools run.** AURA's tools, knowledge and memory are off for Flame's calls. Flame's own model path has no tools.
- **AURA can't loop back:** `x-aura-exclude` (ADR-004).
- Adversarial prompt-injection cases in the evaluation set are Ziad's M11 work.

## 5. Model servers and egress (2H Task 9)
- Compose's `ollama` has no published port: only containers on the project network reach it. vLLM on the L40S must be firewalled to the API and worker hosts.
- No cloud credential is needed for local inference.
- `offline_only` blocks all external AI providers before any connection (H-2 §7).

## 6. Secrets
- No secrets are in the repository. CI runs gitleaks over the full history on every PR; the only allowlist is for 64-hex CV cache keys (`.gitleaks.toml`). History scan on 2026-10-12: no leaks.
- Environment variables are documented by name only (`infrastructure/.env.example`).

## 7. Threat model summary

| Threat | Mitigation | Residual |
|---|---|---|
| A stolen read key or token | Read-only; per-client revocation (`clients revoke`); per-client rate limits | Corpus and chat abuse within that client's budget until revoked |
| A stolen write key | Audit trail with the client's name; revocation; no access to `/api/admin/` | Uploads within the write budget until revoked |
| A stolen admin key or the legacy write token | Audit trail naming the client (and through it the owner); revocation | Admin data operations until revoked; still no deletion of source data over HTTP |
| A poisoned document injects instructions | DATA channel, output validation, no tools | The model can still write a misleading summary; citations stay real |
| AURA compromised | Flame validates every AURA reply; AURA holds only the read token | It can return misleading text inside the schema |
| Data exfiltration while offline | `offline_only` egress guard | Processes outside the router (H-2 §7) |

## 8. Week 8 security review

Pending. It should cover the ADR-009 step 2 implementation (built 2026-11-12), a dependency audit (`pip-audit`, `npm audit`), and a review of the threat model above.

## Known limitations
The deprecated write token is still an admin credential until it is removed; owners are free text, not verified identities (no identity provider, by ADR-009, so it works offline); parsers run in-process; rate limits fail open while Redis is down (chat keeps a per-process limit); unauthenticated requests are not rate-limited.

## Changelog
- 0.7.0 (2026-11-12): ADR-009 step 2 completed: an `admin` scope for `/api/admin/*`, admin keys name their owner (migration `0008_api_client_owner`); §2 lists the audited admin actions.
- 0.6.0 (2026-11-02): per-client API keys with scopes and revocation (P2-1), per-client Redis rate limits on all of `/api/*` (P2-2), production refuses local default secrets (P2-6). The env tokens are deprecated.
- 0.5.0 (2026-10-12): first draft with the controls built in PR #14.
