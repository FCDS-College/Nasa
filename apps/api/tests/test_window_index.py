"""Window index logic with a scripted session (no pgvector here; the SQL mirrors chunk_embedding's, and CI runs the migration)."""
import pytest
from sqlalchemy.exc import SQLAlchemyError

from ai.rag.ingestion.windows import split_windows
from flame_api import vector_index


class Row:
    def __init__(self, **values):
        self.__dict__.update(values)

    def __iter__(self):                  # `for row in result` over rows with .chunk_id etc.
        return iter(self.__dict__.values())


class Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def __iter__(self):
        return iter(self._rows)

    def scalar_one(self):
        return self._rows[0] if self._rows else 0


class FakeSession:
    class bind:
        class dialect:
            name = "postgresql"

    def __init__(self, answers):
        self.answers, self.calls, self.rollbacks, self.commits = answers, [], 0, 0

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params))
        for needle, answer in self.answers.items():
            if needle in sql:
                if isinstance(answer, Exception):
                    raise answer
                return Result(answer)
        return Result([])

    def rollback(self):
        self.rollbacks += 1

    def commit(self):
        self.commits += 1


@pytest.fixture(autouse=True)
def fake_embedding(monkeypatch):
    monkeypatch.setattr(vector_index, "_embed_query", lambda query: "[0.1,0.2]")


def test_window_hits_become_page_hits_above_the_floor():
    session = FakeSession({"from chunk_window_embedding": [Row(chunk_id="c1", sim=0.61), Row(chunk_id="c2", sim=0.9),
                                                           Row(chunk_id="c1", sim=0.80), Row(chunk_id="c3", sim=0.40)]})
    hits = vector_index.search_window_chunks(session, "question", limit=10)
    assert hits == [("c2", 0.9), ("c1", 0.80)]                      # c1 by its best window; c3 below the 0.55 floor
    sql, params = session.calls[0]
    assert "chunk_window_embedding" in sql and params["limit"] == vector_index.WINDOW_HITS


def test_the_page_limit_applies_after_aggregation():
    rows = [Row(chunk_id=f"c{i}", sim=0.9 - i / 100) for i in range(8)]
    assert len(vector_index.search_window_chunks(FakeSession({"from chunk_window_embedding": rows}), "q", limit=3)) == 3


def test_no_windows_falls_back_to_the_page_index(monkeypatch):
    monkeypatch.setattr(vector_index, "search_chunks", lambda session, query, **kw: [("page-hit", 0.7)])
    assert vector_index.search_window_chunks(FakeSession({"from chunk_window_embedding": []}), "q") == [("page-hit", 0.7)]


def test_a_missing_window_table_falls_back_to_the_page_index(monkeypatch):
    monkeypatch.setattr(vector_index, "search_chunks", lambda session, query, **kw: [("page-hit", 0.7)])
    session = FakeSession({"from chunk_window_embedding": SQLAlchemyError("no such table")})
    assert vector_index.search_window_chunks(session, "q") == [("page-hit", 0.7)] and session.rollbacks == 1


def test_window_search_needs_postgresql():
    class Sqlite(FakeSession):
        class bind:
            class dialect:
                name = "sqlite"

    with pytest.raises(vector_index.VectorUnavailableError):
        vector_index.search_window_chunks(Sqlite({}), "q")


def test_build_embeds_only_pages_whose_text_or_model_changed(monkeypatch):
    long_text = ("The flame front moved slowly across the sample. " * 60).strip()
    unchanged = "An unchanged page."
    embedded: list[str] = []

    def embed(texts, *, query=False):
        embedded.extend(texts)
        return [[0.0] * 3 for _ in texts]

    monkeypatch.setattr(vector_index, "embed_texts", embed)
    session = FakeSession({
        "select distinct chunk_id, text_sha, model": [Row(chunk_id="same", text_sha=vector_index._text_sha(unchanged),
                                                          model=vector_index.MODEL_NAME),
                                                      Row(chunk_id="edited", text_sha="0" * 16, model=vector_index.MODEL_NAME)],
        "select chunk_id, text from document_chunk": [Row(chunk_id="edited", text=long_text), Row(chunk_id="new", text="Short."),
                                                      Row(chunk_id="same", text=unchanged)],
    })
    summary = vector_index.build_window_index(session)
    expected_windows = len(split_windows(long_text)) + 1
    assert summary["pages_embedded"] == 2 and summary["windows_embedded"] == expected_windows
    assert unchanged not in embedded and len(embedded) == expected_windows
    deletes = [params["id"] for sql, params in session.calls if sql.startswith("delete from chunk_window_embedding")]
    assert deletes == ["edited", "new"]                                       # old windows of a changed page are removed first
    inserts = [params for sql, params in session.calls if "insert into chunk_window_embedding" in sql]
    ids = [row["wid"] for batch in inserts for row in batch]
    assert ids[0] == "edited#w0" and "new#w0" in ids and len(ids) == expected_windows


def test_a_page_with_no_text_gets_no_windows_and_no_embedding_call(monkeypatch):
    monkeypatch.setattr(vector_index, "embed_texts", lambda texts, **kw: pytest.fail("nothing to embed"))
    session = FakeSession({"select chunk_id, text from document_chunk": [Row(chunk_id="blank", text="  \n ")]})
    assert vector_index.build_window_index(session)["windows_embedded"] == 0
