"""The gold runner against the real /api/search payload (SQLite test database, lexical substring matching)."""
from datetime import UTC, datetime

import pytest

from ai.rag.evaluation.passage_gold import PassageCase
from ai.rag.evaluation.run_passage_gold import calibrate, rankings_from_body, run
from flame_api.models import DocumentChunk, DocumentRecord, FileRecord, SourceRecord


@pytest.fixture
def corpus(session_factory):
    now = datetime.now(UTC)
    with session_factory() as session:
        for n in range(1, 21):
            source_id, doc_id = f"FF-NTRS-{n:03d}", f"01J9Z3M2A7D4F6H8K0N2Q4S{n:03d}"[:26].ljust(26, "0")
            session.add(SourceRecord(source_id=source_id, title=f"Report {n}", repository="NASA NTRS", access_url="https://example.org", domain="combustion"))
            session.add(FileRecord(file_id=f"file-{n}", source_id=source_id, sha256=f"{n:064d}", original_filename=f"{n}.pdf",
                                   media_type="application/pdf", size_bytes=1, retrieved_at=now))
            session.flush()
            session.add(DocumentRecord(document_id=doc_id, source_id=source_id, file_id=f"file-{n}", title=f"Report {n}", ingested_at=now))
            session.flush()
            session.add(DocumentChunk(chunk_id=f"chunk-{n}", document_id=doc_id, source_id=source_id, file_id=f"file-{n}", evidence_id=f"{n:026d}",
                                      page=3, text=f"Passage number {n:03d} describes the burning of sample {n:03d} in microgravity.", ingested_at=now))
        session.commit()


def _case(gold_id, question, *, source_id=None, page=3, kind=None):
    evidence = [{"document_id": source_id, "page": page, "char_start": 0, "char_end": 7, "text": "Passage"}] if source_id else []
    return PassageCase.from_dict({"gold_id": gold_id, "split": "dev", "question": question, "answerable": bool(source_id), "evidence": evidence,
                                  "question_type": "other", "unanswerable_kind": kind, "author": "Author", "verified_by": ["Verifier"],
                                  "status": "verified"})


def test_the_runner_reads_source_id_page_and_score_from_the_real_search_response(client, corpus):
    body = client.get("/api/search", params={"q": "Passage number 007", "type": "document", "page_size": 30, "domain": "all"}).json()
    assert rankings_from_body(body) == [("FF-NTRS-007", 3)]
    assert body["results"][0]["score"] > 0


def test_a_full_run_and_calibration_over_the_real_endpoint(client, corpus):
    cases = [_case(f"PG-{n:03d}", f"Passage number {n:03d}", source_id=f"FF-NTRS-{n:03d}") for n in range(1, 21)]
    cases += [_case(f"PG-{100 + i}", f"quantum zebra {i} unrelated", kind="out_of_domain") for i in range(8)]

    def fetch(question):
        return client.get("/api/search", params={"q": question, "type": "document", "page_size": 30, "domain": "all"}).json()

    report = run(cases, fetch, label="sqlite-lexical")
    assert report["retrieval"]["hit@1"] == 1.0 and report["n_answerable"] == 20 and report["n_unanswerable"] == 8
    assert {q["n_results"] for q in report["per_question"] if not q["answerable"]} == {0}      # nothing matches the unanswerable ones
    result = calibrate(report)
    assert result["auc"]["value"] == 1.0 and result["unanswerable_abstained"] == 1.0 and result["answerable_abstained"] == 0.0
