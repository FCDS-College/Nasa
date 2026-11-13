"""Rule-based query rewriting. Original and rewritten queries are both kept."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

DEFAULT_ABBREVIATIONS = {
    "psi": "physical sciences informatics",
    "ntrs": "nasa technical reports server",
    "iss": "international space station",
}
# Abbreviations that are also unit symbols: `14.7 psi` is a pressure, not NASA's PSI programme. In the committed NTRS
# papers a number followed by `psi` occurs 53 times and the uppercase programme name twice (audit finding R-1), so a
# match directly after a number is never expanded.
UNIT_LIKE = frozenset({"psi"})
_AFTER_NUMBER = re.compile(r"\d[\s\-]*$")


class RewrittenQuery(BaseModel):
    """The original query, the rewritten query, the rules applied and the rewriter version."""
    original: str
    rewritten: str
    rules_applied: list[str] = Field(default_factory=list)
    rewriter_version: str = "1.0.1"

    @property
    def changed(self) -> bool:
        """True when the rewritten query differs from the original."""
        return self.original != self.rewritten


class QueryRewriter:
    """Rule-based rewriter (version 1.0.1): whitespace normalisation and abbreviation expansion. Not LLM-based.

    1.0.1: a unit symbol (`psi`) directly after a number is not expanded.
    """
    VERSION = "1.0.1"

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
            if expansion.lower() in text.lower():
                continue
            match = next((m for m in pattern.finditer(text)
                          if not (abbr in UNIT_LIKE and _AFTER_NUMBER.search(text[:m.start()]))), None)
            if match is not None:
                text = f"{text[:match.end()]} ({expansion}){text[match.end():]}"
                rules.append(f"expand:{abbr}")

        return RewrittenQuery(
            original=query,
            rewritten=text,
            rules_applied=rules,
            rewriter_version=self.VERSION,
        )
