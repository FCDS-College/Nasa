# Session MAG implementation (E1-5)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Eman | Draft | 0.1.0 | 2026-10-12 | M5 | `ai/rag/memory/session_mag.py`, `ai/rag/service.py` |

Session Memory-Augmented Generation (MAG) stores short conversation context per user and conversation, and supplies it to the answer prompt as **context only, never as evidence**. This document describes the code at commit `9319d65` (memory module) and `0fc94c3` (service wiring). **Planned** marks behaviour not in code.

## 1. What is implemented

| Capability | Status | Code | Test |
|---|---|---|---|
| Memory record schema with validation | Implemented | `MemoryRecord` | `test_validation` |
| Conversation ids | Implemented | `new_conversation_id` | `test_conversation_ids_unique` |
| Scoped search (user + conversation) | Implemented | `InMemorySessionMemory.search` | `test_cross_user_and_cross_conversation_leakage_blocked` |
| Expiry, supersede, delete, purge | Implemented | `search`, `supersede`, `delete_conversation`, `purge_expired` | `test_expiry_supersede_and_delete` |
| Disclosure of memory used | Implemented in the response model | `memory_disclosure`, `FlameResponse.memory_used` | `test_disclosure_lists_memory_used`, `test_memory_is_disclosed_and_bypasses_cache` |
| Memory conflicting with evidence is dropped | Implemented | `flag_conflicts`, `FlameResponse.memory_conflicts` | `test_contamination_memory_conflicting_with_evidence_is_dropped` |
| Memory never merged into evidence | Implemented | `render_memory_block` is a separate prompt section; composer keeps citations to evidence only | `test_memory_never_enters_evidence_block` |
| Persistent storage (database/Redis) | **Planned** | only `InMemorySessionMemory` exists | - |
| Showing `memory_used` in the UI | **Planned** | response field exists; no UI work | - |
| Automatic extraction of memory from conversations (origin `extracted`, `system_summary`) | **Planned** | no extractor exists; the schema allows the origins | - |
| Conversation id issued by the API on `/api/chat` | **Planned** | function exists; the endpoint does not call it yet (Lead) | - |

Test command: `python -m pytest -q tests/unit`. Result on Eman's machine at `0fc94c3` (2026-10-12): **81 passed**; sandbox run of `test_session_mag.py` + `test_flame_service.py` + `test_cag.py` after the service fix: **25 passed** (before adding the metrics test).

## 2. Memory record schema (v1)

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `mem_` + 12 hex characters, generated |
| `user_id` | string | Owner; required |
| `conversation_id` | string | Conversation scope; required |
| `scope` | string | `session` (the only scope implemented) |
| `actor` | string | Who wrote it (`user` by default) |
| `origin` | `user` / `extracted` / `system_summary` | Where the content came from (validated) |
| `text` | string | The memory content |
| `confidence` | float 0..1 | Used to rank (validated) |
| `created_at`, `expires_at` | epoch seconds | `expires_at` must be after `created_at` |
| `superseded_by` | id or null | Set when replaced; superseded records are no longer returned |
| `evidence_refs` | list of ids | Evidence the memory refers to (provenance) |
| `claim_key`, `claim_value` | optional strings | Lets the conflict check compare memory with evidence facts |

Ranking: number of query words shared with the memory text, multiplied by `confidence`; newest first on ties. It is a keyword heuristic, not semantic search.

## 3. Conversation id and `memory_used` disclosure

- `new_conversation_id()` returns `conv_` + 16 random hex characters (UUID4 based).
- Every answer from `FlameRAGService.answer` carries `memory_used`: for each memory record that reached the prompt, its `id`, `origin`, a 120-character `snippet` and `created_at`. Records dropped by the conflict check are listed in `memory_conflicts` instead.
- The answer object also lists the used IDs in `GroundedAnswer.memory_used`.
- **Planned:** the API issuing/accepting the conversation id and the UI showing the disclosure.

## 4. Retention, deletion and expiry

- Default lifetime is 24 hours (`DEFAULT_TTL_SECONDS = 86400`), set per record by `ttl_seconds`.
- Expired records are never returned by `search`; `purge_expired()` deletes them.
- `delete_conversation(user_id, conversation_id)` deletes all records of that conversation for that user and returns the count.
- `supersede(old_id, new_record)` hides the old record and stores the new one.
- Storage is process memory: everything is lost on restart. There is no endpoint yet for a user to ask for deletion (**Planned**, needs the API).

## 5. Leakage and contamination tests

- **Cross-user leakage:** `tests/unit/test_session_mag.py::test_cross_user_and_cross_conversation_leakage_blocked` stores a memory for `alice` / `conv_1` and checks that `bob` in `conv_1`, and `alice` in `conv_2`, get no results. Also `tests/unit/test_flame_service.py::test_memory_is_disclosed_and_bypasses_cache` checks that a second user receives `memory_used == []`.
- **Contamination:** `test_contamination_memory_conflicting_with_evidence_is_dropped` stores a memory claiming `ignition_delay_ms = 5` while a retrieved chunk's `metadata["facts"]` says `12`; the memory is dropped and the conflict reported. Evidence always wins.
- Both passed in the runs listed in section 1.

## 6. Memory is never evidence

1. The composer receives memory separately and renders it in its own `<memory>` section of the prompt; evidence lives in `<evidence>` tags (`render_evidence_block` vs `render_memory_block`).
2. The system prompt states that memory is never the sole support for a scientific claim.
3. Citations can only name retrieved evidence chunks (see `grounded-generation.md`); a memory id cannot become a citation.
4. `test_memory_never_enters_evidence_block` checks that a marker string stored in memory is absent from the evidence part of the prompt and that citations list only evidence chunk IDs.
5. Answers that used memory are not cached (see `cag-policy.md`).

## 7. Known limitations

- In-memory storage only; no persistence, no sharing between workers.
- `user_id` is supplied by the caller. Deriving it from authentication is the API's job (Lead); a wrong id from the caller would break isolation.
- Ranking is word overlap; synonyms are missed.
- The conflict check only works for records with `claim_key`/`claim_value` and chunks that carry `metadata["facts"]`; other conflicts are not detected.
- No code creates `extracted` or `system_summary` memories yet.
- Graph-based session memory (D5) is not implemented (**Planned**, see E1-9).

## 8. Changelog

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-10-12 | First version: rewrite of `mag-policy.md` to match `ai/rag/memory/session_mag.py`; unimplemented items marked Planned. |

## 9. ملخص بالعربي

الـ memory متقسّمة على user وconversation، وفيها expiry وsupersede وdelete، وبتتعرض في الـ response كـ `memory_used`. عمرها ما بتتحط جوه الـ evidence ولا بتتعمل لها citation، والـ memory اللي بتتعارض مع الـ evidence بتتشال. لسه التخزين في الذاكرة بس، ومفيش UI ولا endpoint للحذف (Planned).
