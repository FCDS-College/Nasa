# L-10: Security and access control

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Draft until the Week 7 B6 work (sign-off: Belal E4, Anas E2) | 0.5.0 | 2026-10-12 | B6, MVP §19, 2H Task 9 | `apps/api/flame_api/main.py`, `config.py`, `ai_runtime.py`, `ingest.py`, `.gitleaks.toml` |

## 1. Roles and permissions (today; ADR-009 for the target)

| Credential | Grants | Held by |
|---|---|---|
| Read token (`FLAME_READ_API_TOKEN`) | `GET`/`HEAD` on `/api/*`, and `POST /api/chat` | web app server, AURA connector vault |
| Write token (`FLAME_WRITE_API_TOKEN`) | every other method, including `POST /api/analyses` and `PUT /api/admin/ai/mode` | operators only; never AURA |
| Public | `/api/openapi.json`, `/api/docs`, `/health/live` | anyone |

Tokens are compared in constant time, must be distinct, and must be at least 32 characters; the API refuses to start otherwise. Per-person admin roles are Proposed (ADR-009).

## 2. Protected operations and audit
- **Admin endpoints** need the write token. Every mode change writes `audit_event`:

  | Field | Contents |
  |---|---|
  | `event_id` | — |
  | `occurred_at` | — |
  | `actor` | `write-token` |
  | `action` | `ai.mode.changed` |
  | `target_type` | — |
  | `before` / `after` | the mode before and after |
  | `request_id` | — |

- **Ingestion and destructive data operations** are CLI-only today (`python -m flame_api.ingest`, `vector_index build`). The planned admin data operations (E2-8) will use the same audit table.

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
| A stolen read token | Read-only; rotation procedure (L-8 §4) | Corpus and chat abuse until rotated; chat is rate-limited per process |
| A stolen write token | Audit trail | Full admin until rotated (ADR-009 step 2) |
| A poisoned document injects instructions | DATA channel, output validation, no tools | The model can still write a misleading summary; citations stay real |
| AURA compromised | Flame validates every AURA reply; AURA holds only the read token | It can return misleading text inside the schema |
| Data exfiltration while offline | `offline_only` egress guard | Processes outside the router (H-2 §7) |

## 8. Week 8 security review

Pending. It should cover the ADR-009 step 2 implementation, a dependency audit (`pip-audit`, `npm audit`), and a review of the threat model above.

## Known limitations
Single shared admin credential; parsers run in-process; no rate limit except on chat.

## Changelog
- 0.5.0 (2026-10-12): first draft with the controls built in PR #14.
