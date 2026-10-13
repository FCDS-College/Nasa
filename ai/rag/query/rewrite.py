"""Rule-based query rewriting. Original and rewritten queries are both kept."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

DEFAULT_ABBREVIATIONS = {
    "psi": "physical sciences informatics",
    "ntrs": "nasa technical reports server",
    "iss": "international space station",
}


class RewrittenQuery(BaseModel):
    """The original query, the rewritten query, the rules applied and the rewriter version."""
    original: str
    rewritten: str
    rules_applied: list[str] = Field(default_factory=list)
    rewriter_version: str = "1.0.0"

    @property
    def changed(self) -> bool:
        """True when the rewritten query differs from the original."""
        return self.original != self.rewritten


class QueryRewriter:
    """Rule-based rewriter (version 1.0.0): whitespace normalisation and abbreviation expansion. Not LLM-based."""
    VERSION = "1.0.0"

    def __init__(self, abbreviations: dict[str, str] | None = None):
        self.abbreviations = {
            k.lower(): v for k, v in (abbreviations or DEFAULT_ABBREVIATIONS).items()
        }

    def rewrite(self, query: str) -> RewrittenQuery:
        """Normalise whitespace and expand known abbreviations.

        The expansion is appended in parentheses so the original token stays
        searchable (keyword retrieval still matches it).

        Raises:
            ValueError: if the query is empty.
        """
        if query is None or not query.strip():
            raise ValueError("query must not be empty")

        rules: list[str] = []
        text = re.sub(r"\s+", " ", query).strip()
        if text != query:
            rules.append("normalize_whitespace")

        for abbr, expansion in self.abbreviations.items():
            pattern = re.compile(rf"\b{re.escape(abbr)}\b", re.IGNORECASE)
            if pattern.search(text) and expansion.lower() not in text.lower():
                text = pattern.sub(lambda m: f"{m.group(0)} ({expansion})", text, count=1)
                rules.append(f"expand:{abbr}")

        return RewrittenQuery(
            original=query,
            rewritten=text,
            rules_applied=rules,
            rewriter_version=self.VERSION,
        )
