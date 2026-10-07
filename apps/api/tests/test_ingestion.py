from pathlib import Path

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


def test_pdf_ingestion_records_page_evidence_and_non_text_pages(tmp_path):
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

        assert counts == {"pages": 2, "chunks": 1, "skipped": 0}
        assert document.text_layer == "partial"
        assert document.pages_without_text == [2]
        assert chunk.page == 1
        assert "combustion flame spread" in chunk.text
        assert evidence.locator["type"] == "page"
        assert evidence.locator["page"] == 1
        assert evidence.payload["extraction_method"] == "verbatim_text"
        assert evidence.payload["review_status"] == "machine_extracted"
    engine.dispose()