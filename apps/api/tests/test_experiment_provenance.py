"""P2-9 / P2-10: real experiment timestamps, evidence-backed document/experiment links, dashboard chunk counts."""
import hashlib
from datetime import UTC, datetime

import pytest

from api_contract import assert_contract_component
from flame_api.ingest import _create_table_experiments
from flame_api.models import DocumentChunk, DocumentRecord, EvidenceRecord, ExperimentRecord, FileRecord, SourceRecord

DOCUMENT_ID = "01J9Z3M2A7D4F6H8K0N2Q4S6T8"
OTHER_DOCUMENT_ID = "01J9Z3M2A7D4F6H8K0N2Q4S6T9"
LINKED = "01J9Z3P7C2E4G6J8M0Q2S4V6X1"
UNLINKED = "01J9Z3P7C2E4G6J8M0Q2S4V6X2"
NO_RUN = "01J9Z3P7C2E4G6J8M0Q2S4V6X3"
NO_TIMESTAMP = "01J9Z3P7C2E4G6J8M0Q2S4V6X4"
RETRIEVED = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
INGESTED = datetime(2026, 10, 2, 9, 30, tzinfo=UTC)


@pytest.fixture
def records(session_factory):
    with session_factory() as s:
        s.add(SourceRecord(source_id="FF-PSI-69", title="FLEX", short_name="FLEX", repository="NASA PSI", access_url="https://example.org", domain="combustion"))
        s.add(FileRecord(file_id="sha256:1111111111111111", source_id="FF-PSI-69", sha256="1" * 64, original_filename="t.csv", media_type="text/csv", size_bytes=1, retrieved_at=RETRIEVED))
        s.add(FileRecord(file_id="sha256:2222222222222222", source_id="FF-PSI-69", sha256="2" * 64, original_filename="r.pdf", media_type="application/pdf", size_bytes=1, retrieved_at=RETRIEVED))
        s.flush()
        for document_id in (DOCUMENT_ID, OTHER_DOCUMENT_ID):
            s.add(DocumentRecord(document_id=document_id, source_id="FF-PSI-69", file_id="sha256:2222222222222222", title="FLEX report", ingested_at=INGESTED))
        s.add(DocumentChunk(chunk_id="chunk-1", document_id=DOCUMENT_ID, source_id="FF-PSI-69", file_id="sha256:2222222222222222", evidence_id="E" * 26, page=1, text="heptane", ingested_at=INGESTED))
        s.add_all([
            ExperimentRecord(experiment_id=LINKED, source_id="FF-PSI-69", test_id="FLEX-1", table_file_id="sha256:1111111111111111", searchable_text="FLEX-1 heptane", ingested_at=INGESTED),
            ExperimentRecord(experiment_id=UNLINKED, source_id="FF-PSI-69", test_id="FLEX-2", table_file_id="sha256:1111111111111111", searchable_text="FLEX-2 heptane", ingested_at=INGESTED),
            # predates migration 0006 and nothing could be backfilled: falls back to the table file's retrieval
            ExperimentRecord(experiment_id=NO_RUN, source_id="FF-PSI-69", test_id="FLEX-3", table_file_id="sha256:1111111111111111", searchable_text="FLEX-3 heptane"),
            ExperimentRecord(experiment_id=NO_TIMESTAMP, source_id="FF-PSI-69", test_id="FLEX-4", table_file_id=None, searchable_text="FLEX-4 heptane"),
        ])
        s.flush()
        # The only kind of row that ties a document to an experiment: evidence carrying both IDs.
        for index, document_id in enumerate((DOCUMENT_ID, OTHER_DOCUMENT_ID, DOCUMENT_ID)):
            s.add(EvidenceRecord(evidence_id=f"01J9Z3N5B8C1E3G5J7M9P1R3T{index}", source_id="FF-PSI-69", document_id=document_id,
                                 experiment_id=LINKED, kind="document_passage", origin="source_evidence", payload={}, created_at=INGESTED))
        # Evidence of an experiment alone, or a document alone, is not a link.
        s.add(EvidenceRecord(evidence_id="01J9Z3N5B8C1E3G5J7M9P1R3T5", source_id="FF-PSI-69", experiment_id=UNLINKED,
                             kind="experiment_condition", origin="source_evidence", payload={}, created_at=INGESTED))
        s.add(EvidenceRecord(evidence_id="01J9Z3N5B8C1E3G5J7M9P1R3T6", source_id="FF-PSI-69", document_id=OTHER_DOCUMENT_ID,
                             kind="document_passage", origin="source_evidence", payload={}, created_at=INGESTED))
        s.commit()


def test_experiment_hits_report_the_ingestion_time_not_the_response_time(client, records):
    body = client.get("/api/search", params={"q": "heptane", "type": "experiment"}).json()
    by_id = {r["result_id"]: r["ingested_at"] for r in body["results"]}
    assert by_id[LINKED] == by_id[UNLINKED] == "2026-10-02T09:30:00Z"
    assert by_id[NO_RUN] == "2026-09-01T08:00:00Z", "falls back to the table file's retrieved_at"
    assert NO_TIMESTAMP not in by_id, "a row with no provenance time is not given an invented one"
    assert body["pagination"]["total_items"] == 3
    assert_contract_component(body, "SearchResponse")


def test_experiment_document_ids_come_from_evidence_links(client, records):
    linked = client.get(f"/api/experiments/{LINKED}").json()
    unlinked = client.get(f"/api/experiments/{UNLINKED}").json()
    assert linked["experiment"]["document_ids"] == [DOCUMENT_ID, OTHER_DOCUMENT_ID]
    assert unlinked["experiment"]["document_ids"] == []
    assert_contract_component(linked, "ExperimentResponse")
    assert_contract_component(unlinked, "ExperimentResponse")


def test_document_experiment_ids_come_from_evidence_links(client, records):
    linked = client.get(f"/api/documents/{DOCUMENT_ID}").json()
    other = client.get(f"/api/documents/{OTHER_DOCUMENT_ID}").json()
    assert linked["document"]["experiment_ids"] == [LINKED], "two link rows to one experiment list it once"
    assert other["document"]["experiment_ids"] == [LINKED]
    assert_contract_component(linked, "DocumentResponse")


def test_dashboard_counts_chunks_and_reports_no_index_on_sqlite(client, records):
    body = client.get("/api/dashboard/counts").json()
    assert body["chunks"] == 1
    assert body["indexed_chunks"] == 0, "SQLite cannot hold a vector index"
    assert_contract_component(body, "DashboardCountsResponse")


def test_table_ingestion_stamps_every_experiment(session_factory, tmp_path):
    table = tmp_path / "Experimental table" / "PSI-25_Experimental table_BASS-II.csv"
    table.parent.mkdir()
    table.write_text("Test #,Fuel Sample Material,Pressure (kPa)\nB1,PMMA,101\nB2,Cotton,95\n", encoding="utf-8")
    with session_factory() as s:
        s.add(SourceRecord(source_id="FF-PSI-25", title="BASS-II", short_name="BASS-II", repository="NASA PSI", access_url="https://example.org"))
        file_record = FileRecord(file_id="bass", source_id="FF-PSI-25", sha256=hashlib.sha256(table.read_bytes()).hexdigest(),
                                 original_filename=table.name, media_type="text/csv", size_bytes=table.stat().st_size,
                                 retrieved_at=RETRIEVED, local_path=str(table))
        s.add(file_record)
        s.flush()
        before = datetime.now(UTC)
        assert _create_table_experiments(s, file_record)["experiments"] == 2
        s.commit()
        stamps = [e.ingested_at for e in s.query(ExperimentRecord).filter_by(source_id="FF-PSI-25")]
    assert len(stamps) == 2 and all(stamps)
    assert all(stamp.replace(tzinfo=stamp.tzinfo or UTC) >= before for stamp in stamps)
