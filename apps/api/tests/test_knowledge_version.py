"""M4 (E2-5): knowledge-version publication is recorded, idempotent, and visible to the API."""
import pytest

from flame_api import knowledge_version
from flame_api.models import KnowledgePublication


def test_publication_is_recorded_once_and_becomes_current(session_factory):
    with session_factory() as session:
        assert knowledge_version.current_knowledge_version(session) is None
        first = knowledge_version.publish(session, "bge-small-en-v1.5-10-20261011", trigger="vector_index_build",
                                          counts={"chunk_embeddings": 10})
        again = knowledge_version.publish(session, "bge-small-en-v1.5-10-20261011", trigger="vector_index_build")
        second = knowledge_version.publish(session, "bge-small-en-v1.5-12-20261012", trigger="ingestion")

        assert first["publication_id"] == again["publication_id"], "republishing is a no-op"
        assert first["announced"] is False, "no Redis configured: the row is still the record"
        assert second["previous_version"] == "bge-small-en-v1.5-10-20261011"
        assert knowledge_version.current_knowledge_version(session) == "bge-small-en-v1.5-12-20261012"
        assert session.query(KnowledgePublication).count() == 2
        assert set(second) >= {"type", "schema_version", "knowledge_version", "previous_version", "trigger", "published_at", "counts"}


def test_rollback_republishes_an_older_version_as_current(session_factory):
    with session_factory() as session:
        knowledge_version.publish(session, "v1", trigger="manual")
        knowledge_version.publish(session, "v2", trigger="manual")
        event = knowledge_version.publish(session, "v1", trigger="rollback")
        assert event["previous_version"] == "v2"
        assert knowledge_version.current_knowledge_version(session) == "v1"


def test_unknown_triggers_are_refused(session_factory):
    with session_factory() as session, pytest.raises(ValueError):
        knowledge_version.publish(session, "v1", trigger="whenever")


def test_dashboard_reports_the_current_version(client, session_factory):
    with session_factory() as session:
        knowledge_version.publish(session, "kv-test-1", trigger="manual")
    assert client.get("/api/dashboard/counts").json()["knowledge_version"] == "kv-test-1"
