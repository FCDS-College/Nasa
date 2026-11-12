"""ADR-007 / E2-6: the knowledge graph built from the committed PSI tables, traversed, checked and merged."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api_contract import assert_contract_component
from flame_api import knowledge_graph as kg
from flame_api.database import get_session
from flame_api.ingest import ingest_file
from flame_api.main import app
from flame_api.models import AuditEvent, Base, EvidenceRecord, FileRecord, KnowledgeEntity, KnowledgeRelation
from flame_api.seed import seed_files, seed_sources

READ = {"Authorization": f"Bearer {os.environ['FLAME_READ_API_TOKEN']}"}
WRITE = {"Authorization": f"Bearer {os.environ['FLAME_WRITE_API_TOKEN']}"}
TABLES_AND_METADATA = ("%Experimental table%", "%metadata%")


def _ingested(patterns=TABLES_AND_METADATA, sources=None):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with sessions() as session:
        seed_sources(session)
        session.commit()   # autoflush is off, as in conftest: seed_files must see the sources
        seed_files(session)
        session.commit()
        for pattern in patterns:
            query = session.query(FileRecord).filter(FileRecord.original_filename.like(pattern),
                                                     FileRecord.source_id != "FF-PSI-DSI")
            if sources:
                query = query.filter(FileRecord.source_id.in_(sources))
            for record in query.order_by(FileRecord.file_id).all():
                ingest_file(session, record)
        session.commit()
        counts = kg.build_graph(session, knowledge_version="kv-test")
    return engine, sessions, counts


@pytest.fixture(scope="module")
def graph():
    engine, sessions, counts = _ingested()
    yield sessions, counts
    engine.dispose()


@pytest.fixture
def small():
    """SAFFIRE-I only (2 experiments): cheap enough to mutate in each test."""
    engine, sessions, _ = _ingested(sources=("FF-PSI-98",))
    yield sessions
    engine.dispose()


@pytest.fixture
def api(graph):
    sessions, _ = graph

    def override():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _count(session, model, *where):
    return session.scalar(select(func.count()).select_from(model).where(*where))


def test_every_table_row_becomes_an_experiment_with_cited_edges(graph):
    sessions, counts = graph
    with sessions() as session:
        types = dict(session.execute(select(KnowledgeEntity.entity_type, func.count()).group_by(KnowledgeEntity.entity_type)).all())
        predicates = dict(session.execute(select(KnowledgeRelation.predicate, func.count()).group_by(KnowledgeRelation.predicate)).all())
        assert types["experiment"] == 840 and types["investigation"] == 4 and types["document"] == 4
        assert types["phenomenon"] == 3   # FLEX test_end: Extinction, Disruption, Completion
        assert types["fuel"] == 59 and types["condition_variable"] == 45   # as documented in E2-6 §0
        assert predicates["part_of"] == predicates["uses_fuel"] == 840 and predicates["has_condition"] == 8725
        assert predicates["observed"] == 274 and predicates["describes"] == 4
        assert counts["relations"] == sum(predicates.values())
        # Every edge cites an evidence row that exists, and is a deterministic table parse.
        assert _count(session, KnowledgeRelation, KnowledgeRelation.evidence_id.notin_(select(EvidenceRecord.evidence_id))) == 0
        assert {r for r, in session.execute(select(KnowledgeRelation.extraction_method).distinct())} == {"table_parse"}
        assert {c for c, in session.execute(select(KnowledgeRelation.confidence).distinct())} == {1.0}


def test_a_condition_edge_carries_the_cell_it_was_read_from(graph):
    sessions, _ = graph
    with sessions() as session:
        pressure = kg.entity_id("condition_variable", "ambient_pressure_mmhg")
        edge = session.scalars(select(KnowledgeRelation).where(KnowledgeRelation.object_id == pressure)
                               .order_by(KnowledgeRelation.relation_id)).first()
        evidence = session.get(EvidenceRecord, edge.evidence_id)
        assert evidence.kind == "experiment_condition"
        assert edge.properties["unit_si"] == "Pa" and edge.properties["value_si"] > 0
        assert session.get(KnowledgeEntity, edge.subject_id).properties["experiment_id"] == evidence.experiment_id


def test_a_rebuild_is_idempotent(graph):
    sessions, counts = graph
    with sessions() as session:
        again = kg.build_graph(session, knowledge_version="kv-test")
    assert again["entities"] == counts["entities"] and again["relations"] == counts["relations"]
    assert again.get("relations_created", 0) == 0 and again.get("relations_removed", 0) == 0
    assert not any(key.startswith("entities_created") for key in again)


def test_the_neighbourhood_is_a_recursive_traversal_in_both_directions(graph):
    sessions, _ = graph
    with sessions() as session:
        extinction = kg.entity_id("phenomenon", "Extinction")
        found = kg.neighbourhood(session, extinction, depth=2, predicates=["observed", "uses_fuel"], max_edges=1000)
        fuels = {e.canonical_name for e in found["entities"] if e.entity_type == "fuel"}
        assert fuels == {"heptane", "methanol"}   # FLEX's two fuels; extinction is recorded only for FLEX
        assert found["reachable_by_type"]["experiment"] == 186 and not found["truncated"]
        assert {e.predicate for e in found["edges"]} == {"observed", "uses_fuel"}
        capped = kg.neighbourhood(session, extinction, depth=2, max_edges=5)
        assert capped["truncated"] and len(capped["edges"]) == 5
        with pytest.raises(kg.GraphError):
            kg.neighbourhood(session, extinction, depth=4)


def test_consistency_checks_pass_and_list_spelling_variants_for_review(graph):
    sessions, _ = graph
    with sessions() as session:
        report = kg.check_consistency(session)
    assert report["ok"] is True
    assert {name: report[name]["count"] for name in ("orphan_edges", "edges_with_dead_evidence", "conflicting_relations")} == {
        "orphan_edges": 0, "edges_with_dead_evidence": 0, "conflicting_relations": 0}
    names = [{e["canonical_name"] for e in group["entities"]} for group in report["duplicate_entities"]["examples"]]
    assert {'1/4" black rod', "1/4 black rod"} in names   # BASS-II writes the same rod two ways
    assert report["duplicate_entities"]["blocking"] is False


def test_the_graph_api_lists_and_walks_entities(api):
    listed = api.get("/api/graph/entities", params={"type": "fuel", "q": "heptane"}, headers=READ)
    assert listed.status_code == 200
    assert_contract_component(listed.json(), "GraphEntityListResponse")
    [heptane] = listed.json()["items"]
    assert heptane["display_name"] == "Heptane" and heptane["relation_count"] == 117

    walked = api.get(f"/api/graph/entities/{heptane['entity_id']}", params={"depth": 2, "max_edges": 50}, headers=READ)
    assert walked.status_code == 200
    assert_contract_component(walked.json(), "GraphEntityResponse")
    body = walked.json()
    assert body["resolved_from"] is None and body["neighbourhood"]["truncated"] is True
    depths = {e["entity_id"]: e["depth"] for e in body["neighbourhood"]["entities"]}
    assert depths[heptane["entity_id"]] == 0 and max(depths.values()) <= 2
    # heptane -> its 117 FLEX experiments -> FLEX itself and the FLEX conditions, two hops out
    assert body["neighbourhood"]["reachable_by_type"]["investigation"] == 1
    assert body["neighbourhood"]["reachable_by_type"]["experiment"] == 117

    missing = api.get("/api/graph/entities/01J9Z3Q9D3F5H7K9N1R3T5W7Y9", headers=READ)
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "ENTITY_NOT_FOUND"
    assert api.get(f"/api/graph/entities/{heptane['entity_id']}", params={"depth": 4}, headers=READ).status_code == 400
    assert api.get("/api/graph/entities", params={"type": "planet"}, headers=READ).status_code == 400


def test_the_consistency_report_is_admin_data(api):
    assert api.get("/api/admin/graph/consistency", headers=READ).status_code == 401
    report = api.get("/api/admin/graph/consistency", headers=WRITE)
    assert report.status_code == 200
    assert_contract_component(report.json(), "GraphConsistencyResponse")
    assert report.json()["ok"] is True and report.json()["extractor_version"] == kg.EXTRACTOR_VERSION


def test_a_merge_re_points_edges_keeps_the_old_id_resolving_and_is_audited(small):
    with small() as session:
        experiments = session.scalars(select(KnowledgeEntity).where(KnowledgeEntity.entity_type == "experiment")
                                      .order_by(KnowledgeEntity.entity_id)).all()
        assert len(experiments) == 2
        # Pretend an operator found that a material name is a variant of another: merge the fuels.
        fuel = session.scalars(select(KnowledgeEntity).where(KnowledgeEntity.entity_type == "fuel")).one()
        twin = KnowledgeEntity(entity_id=kg.entity_id("fuel", "sibal fabric (variant)"), entity_type="fuel",
                               canonical_name="sibal fabric (variant)", aliases=[], properties={}, evidence_ids=[],
                               review_status="unreviewed", created_at=fuel.created_at, updated_at=fuel.updated_at)
        session.add(twin)
        session.commit()
        edges_before = _count(session, KnowledgeRelation, KnowledgeRelation.object_id == fuel.entity_id)

        event = kg.merge_entities(session, fuel.entity_id, twin.entity_id, actor="Anas (E2)")

        assert _count(session, KnowledgeRelation, KnowledgeRelation.object_id == twin.entity_id) == edges_before
        assert _count(session, KnowledgeRelation, KnowledgeRelation.object_id == fuel.entity_id) == 0
        assert kg.resolve(session, fuel.entity_id).entity_id == twin.entity_id
        assert fuel.canonical_name in session.get(KnowledgeEntity, twin.entity_id).aliases
        audit = session.get(AuditEvent, event.event_id)
        assert audit.action == "graph.entity.merge" and audit.actor == "Anas (E2)" and audit.after["edges_moved"] == edges_before
        assert kg.check_consistency(session)["ok"] is True
        with pytest.raises(kg.GraphError):
            kg.merge_entities(session, fuel.entity_id, twin.entity_id, actor="again")

        # A rebuild follows the merge instead of recreating the loser's edges.
        kg.build_graph(session, knowledge_version="kv-test")
        assert _count(session, KnowledgeRelation, KnowledgeRelation.object_id == fuel.entity_id) == 0
        assert _count(session, KnowledgeRelation, KnowledgeRelation.object_id == twin.entity_id) == edges_before


def test_a_rebuild_keeps_human_review_and_rejected_edges_are_never_walked(small):
    with small() as session:
        edge = session.scalars(select(KnowledgeRelation).where(KnowledgeRelation.predicate == "uses_fuel")
                               .order_by(KnowledgeRelation.relation_id)).first()
        edge.review_status = "rejected"
        session.commit()
        kg.build_graph(session, knowledge_version="kv-test")
        assert session.get(KnowledgeRelation, edge.relation_id).review_status == "rejected"
        walked = kg.neighbourhood(session, edge.subject_id, depth=1, max_edges=500)
        assert edge.relation_id not in {e.relation_id for e in walked["edges"]}


def test_a_rebuild_drops_entities_it_no_longer_produces_unless_someone_reviewed_them(small):
    with small() as session:
        template = session.scalars(select(KnowledgeEntity).where(KnowledgeEntity.entity_type == "fuel")).one()
        for name, status in (("stale spelling", "unreviewed"), ("curated material", "human_verified")):
            session.add(KnowledgeEntity(entity_id=kg.entity_id("fuel", name), entity_type="fuel", canonical_name=name,
                                        aliases=[], properties={}, evidence_ids=[], review_status=status,
                                        created_at=template.created_at, updated_at=template.updated_at))
        session.commit()

        counts = kg.build_graph(session, knowledge_version="kv-test")

        assert counts["entities_removed"] == 1
        assert session.get(KnowledgeEntity, kg.entity_id("fuel", "stale spelling")) is None
        assert session.get(KnowledgeEntity, kg.entity_id("fuel", "curated material")) is not None


def test_the_cli_builds_checks_and_refuses_bad_merges(small, monkeypatch, capsys):
    from flame_api import database

    monkeypatch.setattr(database, "SessionLocal", small)
    assert kg.main(["build"]) == 0
    assert '"relations":' in capsys.readouterr().out
    assert kg.main(["check"]) == 0
    assert kg.main(["merge", "01J9Z3Q9D3F5H7K9N1R3T5W7Y9", "01J9Z3Q9D3F5H7K9N1R3T5W7Y8", "--actor", "x"]) == 2
