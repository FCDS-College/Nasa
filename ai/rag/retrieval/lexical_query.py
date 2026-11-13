"""Lexical leg without the AND wall (audit roadmap item 10).

The served search ANDs every term of the question (`plainto_tsquery`), so a sentence rarely matches and the chat path has
to search each word separately. This module builds an OR query over the question's distinctive terms and weights each term
by its inverse document frequency, so a chunk matching the rare terms outranks one matching only common words.

Pure functions only: the SQL that applies them is in `apps/api/flame_api/lexical.py`.
Known limit: PostgreSQL's `english` configuration drops stopwords on both sides, so a lone `He` cannot match until the
indexed vector uses a configuration that keeps it. The term is kept here so that change is only a configuration switch.
"""
from __future__ import annotations

import math
import re

from ai.rag.retrieval.evidence_window import STOPWORDS

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-]*[A-Za-z0-9]|[A-Za-z0-9]")
# Chemical symbols that are also stopwords, kept only in this spelling ("He" the gas, not "he"). Others that collide with
# a word ("In", "As", "No", "Be") are far more often the word.
STOPWORD_SYMBOLS = frozenset({"He"})
DEFAULT_MAX_TERMS = 8
_UNSAFE = re.compile(r"[^A-Za-z0-9.\-]+")


def query_terms(question: str, max_terms: int = DEFAULT_MAX_TERMS) -> list[str]:
    """Distinctive lower-cased terms of a question, longest kept when there are more than `max_terms`, in question order."""
    seen: dict[str, str] = {}
    for token in _TOKEN.findall(question):
        word = token.lower()
        if word in seen:
            continue
        if word in STOPWORDS and token not in STOPWORD_SYMBOLS:
            continue
        seen[word] = token
    terms = list(seen)
    if len(terms) > max_terms:
        keep = set(sorted(terms, key=lambda t: (-len(t), terms.index(t)))[:max_terms])
        terms = [t for t in terms if t in keep]
    return terms


def bm25_idf(document_frequency: int, documents: int) -> float:
    """The BM25 idf, which stays positive: ln(1 + (N - n + 0.5) / (n + 0.5))."""
    return math.log(1 + (documents - document_frequency + 0.5) / (document_frequency + 0.5))


def or_tsquery_text(terms: list[str]) -> str:
    """Text for `to_tsquery`: each term quoted, joined by `|`. Operator characters in a term become spaces."""
    parts = []
    for term in terms:
        clean = _UNSAFE.sub(" ", term).strip()
        if clean:
            parts.append(f"'{clean}'")
    return " | ".join(parts)
