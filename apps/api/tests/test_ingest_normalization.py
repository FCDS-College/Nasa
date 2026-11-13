"""Ingest indexes normalised page text but keeps the evidence excerpt verbatim (audit finding R-3)."""
from datetime import UTC, datetime

import fitz
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from flame_api.ingest import PARSER_VERSION, _create_document
from flame_api.models import Base, DocumentChunk, DocumentRecord, EvidenceRecord, FileRecord, SourceRecord


def _pdf(path):
    pdf = fitz.open()
    for number in range(1, 5):
        page = pdf.new_page()
        page.insert_text((72, 72), "American Institute of Aeronautics and Astronautics", fontsize=9)
        if number == 1:
            page.insert_text((72, 120), "The flame spread more slowly. Lean flam-", fontsize=11)         # a word split at the line break
            page.insert_text((72, 135), "mability limits were measured at reduced pressure.", fontsize=11)
        else:
            page.insert_text((72, 120), f"The flammability of PMMA on page {number} depends on pressure.", fontsize=11)
        page.insert_text((72, 150), "Further measurements of the flame front were recorded at each pressure setting.", fontsize=11)
        page.insert_text((72, 760), str(number), fontsize=9)
    pdf.save(path)
    pdf.close()


def _ingest(tmp_path, monkeypatch):
    monkeypatch.setattr("flame_api.ingest._ocr_page", lambda page: None)
    path = tmp_path / "report.pdf"
    _pdf(path)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(SourceRecord(source_id="FF-NTRS-1", title="Report", short_name="R", repository="NASA NTRS", license="CC0-1.0",
                             access_url="https://example.org", domain="combustion"))
    record = FileRecord(file_id="sha256:abcd", source_id="FF-NTRS-1", sha256="ab" * 32, original_filename=path.name,
                        media_type="application/pdf", size_bytes=path.stat().st_size, retrieved_at=datetime.now(UTC),
                        canonical_source_url="https://example.org/r.pdf", is_original=True, parent_file_id=None, local_path=str(path))
    session.add(record)
    session.commit()
    _create_document(session, record)
    session.commit()
    return session, record


def test_the_index_text_is_normalised_and_the_evidence_excerpt_stays_verbatim(tmp_path, monkeypatch):
    session, _ = _ingest(tmp_path, monkeypatch)
    first = session.query(DocumentChunk).filter_by(page=1).one()
    second = session.query(DocumentChunk).filter_by(page=2).one()
    evidence = session.query(EvidenceRecord).filter_by(evidence_id=first.evidence_id).one()
    second_evidence = session.query(EvidenceRecord).filter_by(evidence_id=second.evidence_id).one()

    assert "Lean flammability limits were measured" in first.text                               # indexed: split word rejoined
    assert "American Institute" in first.text and "American Institute" not in second.text    # indexed: header kept once, repeats removed
    assert "American Institute" in second_evidence.excerpt                                    # cited: the repeat is still in the excerpt
    assert "flam-\nmability" in evidence.excerpt and "American Institute" in evidence.excerpt   # cited: exactly as extracted
    assert evidence.payload["extraction_method"] == "verbatim_text"


def test_the_document_records_how_its_text_was_normalised(tmp_path, monkeypatch):
    session, _ = _ingest(tmp_path, monkeypatch)
    document = session.query(DocumentRecord).one()
    assert document.parser_version == PARSER_VERSION and PARSER_VERSION != "pymupdf-pages-0.3.0"
    assert document.payload["text_normalization"].startswith("text-normalize-")


def test_re_ingesting_changes_nothing(tmp_path, monkeypatch):
    session, record = _ingest(tmp_path, monkeypatch)
    before = sorted((c.chunk_id, c.text) for c in session.query(DocumentChunk))
    _create_document(session, record)
    session.commit()
    assert sorted((c.chunk_id, c.text) for c in session.query(DocumentChunk)) == before
    assert session.query(EvidenceRecord).count() == 4
