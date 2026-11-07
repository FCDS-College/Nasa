from pathlib import Path

import pytest

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session
import fitz

from flame_api.ingest import _create_document, _create_table_experiments
from flame_api.models import DocumentChunk, DocumentRecord, EvidenceRecord, ExperimentRecord, FileRecord, SourceRecord, Base
from flame_api.seed import seed_files, seed_sources


def test_mirrored_psi_tables_are_ingested_with_provenance_and_stable_ids():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        sources = seed_sources(session)
        files, skipped = seed_files(session)
        session.commit()
        assert sources >= 7
        assert files >= 100
        assert skipped == 0

        table_files = session.query(FileRecord).filter(
            FileRecord.original_filename.like("%Experimental table%")
        ).all()
        if not any(Path(f.local_path or "").is_file() for f in table_files):
            pytest.skip("PSI table mirror (git-ignored datasets/raw/) is not present on this machine")
        counts = {}
        for file_record in table_files:
            source_id = file_record.source_id
            if source_id == "FF-PSI-DSI":
                continue
            counts[source_id] = _create_table_experiments(session, file_record)
        session.commit()

        assert counts["FF-PSI-25"]["experiments"] == 129
        assert counts["FF-PSI-69"]["experiments"] == 274
        assert counts["FF-PSI-98"]["experiments"] == 2
        assert counts["FF-PSI-107"]["experiments"] == 435
        assert counts["FF-PSI-107"]["duplicates"] == 34
        assert session.query(EvidenceRecord).filter(EvidenceRecord.kind == "experiment_condition").count() > 5000

        before = session.query(func.count(ExperimentRecord.experiment_id)).scalar()
        for file_record in table_files:
            if file_record.source_id != "FF-PSI-DSI":
                _create_table_experiments(session, file_record)
        session.commit()
        after = session.query(func.count(ExperimentRecord.experiment_id)).scalar()
        assert after == before == 840
    engine.dispose()


def test_pdf_ingestion_records_page_evidence_and_non_text_pages(tmp_path, monkeypatch):
    monkeypatch.setattr("flame_api.ingest._ocr_page", lambda page: None)   # no OCR engine: deterministic
    pdf_path = tmp_path / "NASA PSI Report.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Microgravity combustion flame spread experiment report.")
    pdf.new_page()
    pdf.save(pdf_path)
    pdf.close()

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        source = SourceRecord(
            source_id="FF-PSI-25",
            title="Burning and Suppression of Solids-II",
            short_name="BASS-II",
            repository="NASA PSI",
            persistent_identifier="doi:10.60555/4qc4-de67",
            license="CC0-1.0",
            access_url="https://psi.nasa.gov/physci/repo/data/investigations/PSI-25",
            domain="combustion",
        )
        file_record = FileRecord(
            file_id="sha256:1234567890abcdef",
            source_id=source.source_id,
            sha256="1234567890abcdef" * 4,
            original_filename=pdf_path.name,
            media_type="application/pdf",
            size_bytes=pdf_path.stat().st_size,
            retrieved_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            canonical_source_url="https://psi.nasa.gov/sample.pdf",
            is_original=True,
            parent_file_id=None,
            local_path=str(pdf_path),
        )
        session.add_all([source, file_record])
        session.commit()

        counts = _create_document(session, file_record)
        session.commit()
        document = session.query(DocumentRecord).one()
        chunk = session.query(DocumentChunk).one()
        evidence = session.query(EvidenceRecord).filter_by(evidence_id=chunk.evidence_id).one()

        assert counts == {"pages": 2, "chunks": 1, "skipped": 0, "ocr_pages": 0, "ocr_low_confidence": 0}
        assert document.payload["ocr"]["status"] == "unavailable"
        assert document.text_layer == "partial"
        assert document.pages_without_text == [2]
        assert chunk.page == 1
        assert "combustion flame spread" in chunk.text
        assert evidence.locator["type"] == "page"
        assert evidence.locator["page"] == 1
        assert evidence.payload["extraction_method"] == "verbatim_text"
        assert evidence.payload["review_status"] == "machine_extracted"
    engine.dispose()

def test_committed_psi_tables_are_present_so_a_fresh_clone_has_experiments():
    """The 4 CC0 experimental tables and 4 ISA-Tab zips are committed (.gitignore exception)."""
    root = Path(__file__).resolve().parents[3] / "datasets" / "raw" / "psi_api"
    tables = sorted(root.glob("PSI-*/Experimental table/*.csv"))
    metadata = sorted(root.glob("PSI-*/metadata/*.zip"))
    assert [p.parent.parent.name for p in tables] == ["PSI-107", "PSI-25", "PSI-69", "PSI-98"]
    assert len(metadata) == 4


def test_isatab_metadata_becomes_a_citable_investigation_document():
    from flame_api.ingest import ISATAB_PARSER_VERSION, ingest_file

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_sources(session)
        seed_files(session)
        session.commit()
        record = session.query(FileRecord).filter(FileRecord.original_filename.like("PSI-69_metadata%")).one()
        outcome, counts = ingest_file(session, record)
        session.commit()
        assert outcome == "ingested" and counts["chunks"] >= 6
        document = session.query(DocumentRecord).filter(DocumentRecord.file_id == record.file_id).one()
        assert document.parser_version == ISATAB_PARSER_VERSION
        assert document.document_type == "dataset_documentation"
        assert document.payload["isatab"]["acronym"] == "FLEX"
        assert document.payload["isatab"]["doi"] == "10.60555/mbq8-0451"
        assert any("ntrs.nasa.gov" in link for link in document.payload["isatab"]["publications"])
        sections = {e.locator["label"]: e for e in session.query(EvidenceRecord).filter(EvidenceRecord.document_id == document.document_id)}
        assert {"Objective", "Hypothesis", "Approach"} <= set(sections)
        assert "flammability limits" in sections["Objective"].excerpt
        # Stable IDs: a second ingest creates nothing new.
        before = session.query(func.count(EvidenceRecord.evidence_id)).scalar()
        ingest_file(session, record)
        session.commit()
        assert session.query(func.count(EvidenceRecord.evidence_id)).scalar() == before
    engine.dispose()


def test_flex_en_dash_is_missing_and_sccm_is_not_a_length():
    from flame_api.ingest import convert_to_si, parse_cell

    assert parse_cell("–") == (None, None)       # FLEX cp1252 0x96 "not available"
    assert parse_cell("—") == (None, None)
    assert convert_to_si("Fuel Rate (sccm)", "fuel_rate_sccm", 12.0) == (None, None)
    assert convert_to_si("Air Rate (cm/s)", "air_rate_cm_s", 10.0) == (0.1, "m/s")
    assert convert_to_si("Ambient pressure; mmHg", "ambient_pressure_mmhg", 760.0)[1] == "Pa"
