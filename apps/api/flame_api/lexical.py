"""OR-with-IDF lexical match for document chunks (audit roadmap item 10; `FLAME_LEXICAL_MODE=or_idf`, default `and`).

PostgreSQL only: it reads the stored `document_chunk.search_tsv` (migration 0007), or `search_tsv_keep` (migration 0012, the
`flame_english` configuration: English stemming without a stopword list, so "He" the gas is searchable) when that column exists. Each question term is matched on its own;
a chunk's score is the sum of the BM25 idf of the terms it contains (no term-frequency or length part: PostgreSQL's full-text
search does not expose them), with `ts_rank_cd` of the OR query as a tie-break. Document frequencies are counted with the
GIN index and cached for a few minutes.
"""
from __future__ import annotations

import time

from sqlalchemy import case, func, literal_column, text
from sqlalchemy.orm import Session

from ai.rag.retrieval.lexical_query import bm25_idf, or_tsquery_text, query_terms

CACHE_SECONDS = 300
_CACHE: dict[str, tuple[float, int | None]] = {}     # term -> (when, document frequency; None = the term is a stopword)
_TOTAL: list = [None, 0]                               # [when counted (None = never), chunk count]
_KEEP: list = [None]                                   # has migration 0012 been applied? (None = not asked yet)
STANDARD = ("search_tsv", "english")
KEEP = ("search_tsv_keep", "flame_english")


def _vector(session: Session) -> tuple[str, str]:
    """(stored vector column, text search configuration): the stopword-free pair once migration 0012 exists, else the standard one."""
    if _KEEP[0] is None:
        _KEEP[0] = bool(session.execute(text(
            "SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() "
            "AND table_name = 'document_chunk' AND column_name = 'search_tsv_keep'")).first())
    return KEEP if _KEEP[0] else STANDARD


def _total_chunks(session: Session) -> int:
    now = time.monotonic()
    # `None`, not 0.0: time.monotonic() counts from boot, so on a freshly started machine 0.0 would look recent.
    if _TOTAL[0] is None or now - _TOTAL[0] > CACHE_SECONDS:
        _TOTAL[:] = [now, session.execute(text("SELECT count(*) FROM document_chunk")).scalar_one()]
    return _TOTAL[1]


def _document_frequency(session: Session, term: str) -> int | None:
    """Chunks containing `term`, or None when the `english` configuration drops it (a stopword: it can never match)."""
    now = time.monotonic()
    cached = _CACHE.get(term)
    if cached and now - cached[0] <= CACHE_SECONDS:
        return cached[1]
    column, config = _vector(session)          # fixed names from this module, never from the request
    row = session.execute(text(
        f"SELECT numnode(q), (SELECT count(*) FROM document_chunk WHERE {column} @@ q) "
        f"FROM (SELECT to_tsquery('{config}', :t) AS q) s"), {"t": or_tsquery_text([term])}).one()
    value = None if row[0] == 0 else int(row[1])
    _CACHE[term] = (now, value)
    return value


def clear_cache() -> None:
    _CACHE.clear()
    _TOTAL[:] = [None, 0]
    _KEEP[0] = None


def match(session: Session, query: str):
    """(filter, score) over `document_chunk.search_tsv`, or None when no term of the question can match."""
    terms = [(term, df) for term in query_terms(query) if (df := _document_frequency(session, term)) is not None]
    if not terms:
        return None
    documents = max(_total_chunks(session), 1)
    column, config = _vector(session)
    vector = literal_column(f"document_chunk.{column}")
    english = literal_column(f"'{config}'")
    anywhere = func.to_tsquery(english, or_tsquery_text([term for term, _ in terms]))
    score = sum((case((vector.op("@@")(func.to_tsquery(english, or_tsquery_text([term]))), bm25_idf(df, documents)), else_=0.0)
                 for term, df in terms), start=literal_column("0.0"))
    return vector.op("@@")(anywhere), score + func.ts_rank_cd(vector, anywhere) * 0.001
