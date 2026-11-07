# ADR-009: Authentication and RBAC

- **Status:** Accepted (2026-11-07). Decision owner: Lead, with Belal (E4). Accepted by the Lead; Belal's approval is recorded in ADR index 1.2.0. Partly implemented: see ADR index 1.3.0.
- **Date:** 2026-10-12

## Context
The MVP uses two bearer tokens: a read token for `GET`/`HEAD` and `POST /api/chat`, and a write token for every other method. They are compared in constant time, must be distinct, and must be at least 32 characters (`flame_api/config.py`). Phase 2 B6 needs roles (read / write / admin), per-person audit, and authenticated admin endpoints that also work offline.

## Decision (proposed)
1. **Now (built in PR #14).** Admin endpoints (`/api/admin/*`) require the write token. Every configuration change writes an `audit_event` row with `actor`, `action`, before/after and `request_id`. The actor is recorded as `write-token` until per-person identity exists.
2. **Week 7 (B6).** Add per-user API keys stored hashed (`api_key` table: owner, role ∈ {read, write, admin}, created/revoked). `admin` is required for `/api/admin/*` and destructive data operations. Tokens keep working as service credentials. No external identity provider is needed, so it works offline.

## Alternatives considered
- **OIDC with an external IdP.** Doesn't work offline (2H). It could be added later as an optional login in front of the same roles.
- **Session cookies in the web app only.** The API is also called by AURA and by scripts, so bearer credentials stay.

## Consequences
- Until step 2, anyone with the write token is an admin. L-10 lists this as a known limitation.
- The audit schema is already final (`audit_event`); step 2 only fills `actor` with a real identity.

## Links
[L-10 security](../../operations/SECURITY.md); `apps/api/flame_api/ai_runtime.py:set_mode`.
