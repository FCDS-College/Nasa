import pytest

from flame_api import vector_index


def test_index_status_unavailable_on_sqlite(session_factory):
    with session_factory() as session:
        assert vector_index.index_status(session)["state"] == "unavailable"


def test_search_chunks_requires_postgres(session_factory):
    with session_factory() as session, pytest.raises(vector_index.VectorUnavailableError):
        vector_index.search_chunks(session, "cool flames")


def test_build_index_requires_postgres(session_factory):
    with session_factory() as session, pytest.raises(vector_index.VectorUnavailableError):
        vector_index.build_index(session)


def test_vector_literal_format():
    assert vector_index._literal([0.5, -1.0, 2.0]) == "[0.5,-1,2]"
