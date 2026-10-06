# Context Builder Design

## 1. Purpose

The Context Builder converts retrieved and reranked evidence into a compact, ordered, and traceable context for the LLM.

---

## 2. Input

The Context Builder receives:

```text
User Query
+
Reranked Chunks
+
Citation Metadata
+
Token Budget
```

---

## 3. Processing Pipeline

```text
Retrieved Chunks
      ↓
Relevance Filtering
      ↓
Deduplication
      ↓
Evidence Selection
      ↓
Ordering
      ↓
Token Budget Check
      ↓
Optional Compression
      ↓
Final Context
```

---

## 4. Evidence Selection

Evidence should be selected based on:

* relevance to the query
* retrieval/reranking score
* source quality
* diversity of evidence
* availability of supporting information

The system should avoid filling the context with many nearly identical chunks.

---

## 5. Deduplication

Duplicate or highly overlapping evidence should be removed where possible.

Deduplication must not remove distinct evidence merely because the sources discuss the same topic.

---

## 6. Ordering

Evidence should generally be ordered by relevance.

When appropriate, supporting information can follow the primary evidence.

The ordering strategy may be changed after evaluation.

---

## 7. Token Budget

The Context Builder must enforce a configurable token budget.

Conceptually:

```text
All candidate evidence
        ↓
Calculate context cost
        ↓
Select highest-value evidence
        ↓
Fit within token budget
```

The exact token budget depends on the selected LLM and configuration.

---

## 8. Context Compression

Compression may be used when retrieved evidence is too large.

Compression must:

* preserve scientific meaning
* preserve uncertainty
* preserve numerical values
* preserve conditions and limitations
* preserve citation references

Compression must not transform uncertain findings into certain claims.

---

## 9. Scientific Uncertainty

Statements such as:

* may
* might
* suggests
* approximately
* under certain conditions
* limited evidence
* inconclusive

must not be removed when they materially affect the interpretation.

---

## 10. Source Preservation

Every context item must retain its citation/provenance metadata.

The LLM should therefore be able to associate generated claims with retrieved evidence.

---

## 11. Output

The Context Builder produces:

```python
{
    "context": str,
    "items": list,
    "token_count": int,
    "citations": list
}
```

The output must remain traceable to the original documents and chunks.
