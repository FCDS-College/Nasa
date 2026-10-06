# Memory-Augmented Generation (MAG) Policy

## 1. Purpose

MAG provides contextual continuity across interactions and research sessions.

Memory is used to improve context and usability, not to replace authoritative scientific retrieval.

---

## 2. Memory Types

The system may support:

### Session Memory

Information relevant to the current conversation.

### Research Memory

Context about an ongoing research question or investigation.

### Experiment Memory

Context associated with a specific experiment when such an identifier exists in the actual data.

### Team Memory

Shared project decisions, configurations, or workflow information.

---

## 3. Memory Record

Conceptual structure:

```python
Memory = {
    "memory_id": str,
    "memory_type": str,
    "content": str,
    "created_at": str,
    "updated_at": str,
    "expires_at": str | None,
    "provenance": dict,
    "relevance_metadata": dict
}
```

---

## 4. Memory Retrieval

Memory can be ranked using:

* relevance
* recency
* memory type
* current query context
* expiration status

---

## 5. Expiration

Temporary memories should have expiration rules.

Examples:

* session memories may expire after the session
* temporary research context may have a configurable lifetime
* persistent team decisions may remain until explicitly updated

Actual retention periods should be defined during implementation.

---

## 6. Provenance

Where possible, memory should preserve information about how it was created.

If a memory originates from retrieved scientific evidence, the relevant source/citation metadata should be retained.

---

## 7. Contamination Control

Memory must not silently become scientific truth.

If memory conflicts with authoritative retrieved evidence:

```text
Authoritative Retrieved Evidence
            >
          Memory
```

The retrieved evidence has priority.

---

## 8. Memory and Hallucination

The system must not generate scientific claims solely because they exist in memory.

Scientific claims should ultimately be supported by authoritative retrieved evidence.

---

## 9. Deletion and Update

Memory should support:

```text
store
retrieve
update
delete
expire
```

Outdated or incorrect memory should be removable.

---

## 10. Core Rule

Memory improves continuity.

Retrieval provides scientific grounding.

These responsibilities must remain separate.
