"""M9 ingestion completeness: OCR fallback, quarantine, HTML/JSON adapters, NTRS documents, image lineage."""
import hashlib
import json
from datetime import UTC, datetime

import fitz
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from flame_api import ingest
from flame_api.models import (
    Base, DocumentChunk, DocumentRecord, EvidenceRecord, FileRecord, ImageAsset, IngestionRun, KnowledgePublication,
    ModelRecord, SourceRecord,
)
from flame_api.seed import seed_files, seed_image_assets, seed_models, seed_sources


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(SourceRecord(source_id="FF-NTRS-1", title="Flame Spread in Exploration Atmospheres", short_name="NASA/TM-2008-1",
                           repository="NASA NTRS", access_url="https://ntrs.nasa.gov/citations/1"))
        s.commit()
        yield s
    engine.dispose()


def add_file(session, path, *, sha=None):
    data = path.read_bytes()
    record = FileRecord(file_id=f"sha256:{hashlib.sha256(data).hexdigest()[:16]}", source_id="FF-NTRS-1",
                        sha256=sha or hashlib.sha256(data).hexdigest(), original_filename=path.name,
                        media_type="application/octet-stream", size_bytes=len(data), retrieved_at=datetime.now(UTC),
                        local_path=str(path))
    session.add(record)
    session.commit()
    return record


def make_pdf(path, pages):
    pdf = fitz.open()
    for text in pages:
        page = pdf.new_page()
        if text:
            page.insert_text((72, 72), text)
    pdf.save(path)
    pdf.close()
    return path


def test_ocr_reads_pages_without_a_text_layer_and_flags_low_confidence(session, tmp_path, monkeypatch):
    results = iter([("Scanned page about opposed flow flame spread.", 91.0, "tesseract-5.3"),
                    ("blurry scan of a flammability chart", 41.5, "tesseract-5.3")])
    monkeypatch.setattr(ingest, "_ocr_page", lambda page: next(results))
    record = add_file(session, make_pdf(tmp_path / "scan.pdf", ["Native text layer on page one.", None, None]))

    outcome, counts = ingest.ingest_file(session, record)
    session.commit()

    assert outcome == "ingested" and counts["chunks"] == 3 and counts["ocr_pages"] == 2 and counts["ocr_low_confidence"] == 1
    document = session.query(DocumentRecord).one()
    assert document.title == "Flame Spread in Exploration Atmospheres" and document.document_type == "technical_report"
    assert document.identifier == "NASA/TM-2008-1"
    assert document.text_layer == "partial" and document.pages_without_text == [2, 3]
    assert document.payload["ocr"]["page_confidence"] == {"2": 91.0, "3": 41.5}
    assert document.payload["ocr"]["low_confidence_pages"] == [3]
    by_page = {e.locator["page"]: e.payload for e in session.query(EvidenceRecord)}
    assert by_page[1]["extraction_method"] == "verbatim_text"
    assert (by_page[2]["extraction_method"], by_page[2]["extraction_confidence"]) == ("ocr", 0.91)
    assert by_page[3].get("low_confidence") is True and by_page[2].get("low_confidence") is None


def test_reingesting_creates_no_duplicates(session, tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "_ocr_page", lambda page: None)
    record = add_file(session, make_pdf(tmp_path / "a.pdf", ["Page one text here.", "Page two text here."]))
    for _ in range(3):
        ingest.ingest_file(session, record)
        session.commit()
    assert session.query(DocumentChunk).count() == 2 and session.query(EvidenceRecord).count() == 2
    assert session.query(IngestionRun).count() == 1


def test_a_corrupt_pdf_is_quarantined_and_not_parsed_again(session, tmp_path):
    bad = tmp_path / "broken.pdf"
    bad.write_bytes(b"%PDF-1.7 this is not really a pdf")
    record = add_file(session, bad)

    assert ingest.ingest_file(session, record) == ("quarantined", {"reason": "unreadable_pdf"})
    session.commit()
    assert (record.status, record.quarantine_reason) == ("quarantined", "unreadable_pdf")
    assert session.query(DocumentRecord).count() == 0
    assert ingest.ingest_file(session, record) == ("skipped", {"reason": "quarantined"})


def test_a_file_whose_bytes_changed_is_quarantined(session, tmp_path):
    path = make_pdf(tmp_path / "changed.pdf", ["Original text."])
    record = add_file(session, path, sha="0" * 64)

    assert ingest.ingest_file(session, record) == ("quarantined", {"reason": "checksum_mismatch"})


def test_a_missing_local_mirror_is_skipped_not_quarantined(session, tmp_path):
    path = make_pdf(tmp_path / "gone.pdf", ["x" * 20])
    record = add_file(session, path)
    path.unlink()
    assert ingest.ingest_file(session, record) == ("skipped", {"reason": "not_on_disk"})
    assert record.status == "active"


def test_html_is_split_into_sections_without_scripts(session, tmp_path):
    page = tmp_path / "notes.html"
    page.write_text("<html><head><title>t</title><script>alert('x')</script></head><body>"
                    "<p>Intro paragraph about the experiment campaign.</p><h2>Results</h2>"
                    "<p>Flame spread rate fell as oxygen decreased.</p><style>p{}</style></body></html>", encoding="utf-8")
    record = add_file(session, page)

    outcome, counts = ingest.ingest_file(session, record)
    session.commit()

    assert outcome == "ingested" and counts["chunks"] == 2
    chunks = {c.section: c.text for c in session.query(DocumentChunk)}
    assert chunks == {"Untitled section": "Intro paragraph about the experiment campaign.",
                      "Results": "Flame spread rate fell as oxygen decreased."}
    assert all("alert" not in text for text in chunks.values())
    assert session.query(EvidenceRecord).first().locator["type"] == "section"


def test_json_becomes_path_value_sections(session, tmp_path):
    doc = tmp_path / "meta.json"
    doc.write_text(json.dumps({"experiment": {"fuel": "n-heptane", "pressure_kpa": 101.3}, "notes": ["drop tower run"]}))
    record = add_file(session, doc)

    assert ingest.ingest_file(session, record)[0] == "ingested"
    texts = sorted(c.text for c in session.query(DocumentChunk))
    assert texts == ["experiment.fuel: n-heptane\nexperiment.pressure_kpa: 101.3", "notes[0]: drop tower run"]


def test_invalid_json_is_quarantined(session, tmp_path):
    doc = tmp_path / "broken.json"
    doc.write_text("{not json")
    assert ingest.ingest_file(session, add_file(session, doc)) == ("quarantined", {"reason": "invalid_json"})


def test_the_three_ntrs_reports_and_nist_are_registered_and_the_pdfs_ingest(monkeypatch):
    monkeypatch.setattr(ingest, "_ocr_page", lambda page: None)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_sources(session)
        seed_files(session)
        session.commit()
        sources = {s.source_id: s for s in session.query(SourceRecord)}
        assert {"FF-NTRS-20000034017", "FF-NTRS-20040053557", "FF-NTRS-20080034883", "FF-NIST-WEBBOOK"} <= set(sources)
        assert sources["FF-NIST-WEBBOOK"].license is None, "the literal 'null' is decoded, not stored as text"
        ntrs_files = session.query(FileRecord).filter(FileRecord.source_id.like("FF-NTRS-%")).all()
        # 3 original reports + 21 public-use reports added 2026-11-07 (docs/data/NTRS_DATASET_REPORT.md §5)
        assert len(ntrs_files) == 24
        results = [ingest.ingest_file(session, f) for f in ntrs_files]
        session.commit()
        assert [outcome for outcome, _ in results] == ["ingested"] * 24
        assert sum(c["pages"] for _, c in results) == 284
        titles = {d.title for d in session.query(DocumentRecord)}
        assert "Testing and Selection of Fire-Resistant Materials for Spacecraft Use" in titles
    engine.dispose()


def test_derived_frames_keep_their_parent_and_models_are_registered():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_sources(session)
        seed_files(session)
        session.flush()
        images = seed_image_assets(session)
        models = seed_models(session)
        session.commit()
        dsi = session.query(ImageAsset).filter(ImageAsset.source_id == "FF-PSI-DSI").all()
        assert images >= 180 and len(dsi) == 12
        assert all(a.parent_file_id == "sha256:0473cfa2f03e287e" for a in dsi)
        assert session.query(ImageAsset).filter(ImageAsset.parent_file_id.is_(None)).count() == 0
        assert models == session.query(ModelRecord).count() >= 5
    engine.dispose()


def test_ingest_publishes_a_corpus_version(session, tmp_path, monkeypatch):
    from flame_api.knowledge_version import current_knowledge_version

    monkeypatch.setattr(ingest, "_ocr_page", lambda page: None)
    ingest.ingest_file(session, add_file(session, make_pdf(tmp_path / "a.pdf", ["Some page text."])))
    session.commit()
    ingest._publish_corpus_version(session, {"pdf_documents": 1})
    version = current_knowledge_version(session)
    assert version.startswith("corpus-") and session.query(KnowledgePublication).count() == 1
    ingest._publish_corpus_version(session, {"pdf_documents": 1})
    assert session.query(KnowledgePublication).count() == 1, "same files, same version, no new publication"


def test_real_tesseract_reads_a_scanned_page(session, tmp_path):
    """No mocks: an image-only PDF page goes through PyMuPDF rendering and Tesseract (CI installs it)."""
    import io
    import shutil

    pytest.importorskip("pytesseract")
    if shutil.which("tesseract") is None:
        pytest.skip("tesseract binary not installed")
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1700, 400), "white")
    ImageDraw.Draw(image).text((60, 120), "Opposed flow flame spread", fill="black", font=ImageFont.load_default(size=96))
    png = io.BytesIO()
    image.save(png, format="PNG")
    pdf = fitz.open()
    page = pdf.new_page(width=612, height=144)
    page.insert_image(page.rect, stream=png.getvalue())       # no text layer at all
    path = tmp_path / "scanned.pdf"
    pdf.save(path)
    pdf.close()
    record = add_file(session, path)

    outcome, counts = ingest.ingest_file(session, record)
    session.commit()

    assert outcome == "ingested" and counts["ocr_pages"] == 1 and counts["chunks"] == 1
    document = session.query(DocumentRecord).one()
    assert document.text_layer == "none" and document.payload["ocr"]["status"] == "applied"
    assert document.payload["ocr"]["engine"].startswith("tesseract-")
    evidence = session.query(EvidenceRecord).one()
    assert evidence.payload["extraction_method"] == "ocr" and 0 < evidence.payload["extraction_confidence"] <= 1
    assert "flame" in evidence.excerpt.lower() and "spread" in evidence.excerpt.lower()


def test_ocr_status_stays_applied_when_a_later_page_cannot_be_read(session, tmp_path, monkeypatch):
    results = iter([("Scanned page about opposed flow flame spread.", 88.0, "tesseract-5"), None])
    monkeypatch.setattr(ingest, "_ocr_page", lambda page: next(results))
    record = add_file(session, make_pdf(tmp_path / "mixed.pdf", [None, None]))

    ingest.ingest_file(session, record)
    session.commit()

    assert session.query(DocumentRecord).one().payload["ocr"]["status"] == "applied"
