"""KB audit 2026-11-13, finding 7: a source must be verified and licensed before its files enter the knowledge base.

The registry recorded licence and verification state, but nothing enforced them: three partially verified NTRS reports
with no recorded licence were ingested and cited. Two layers now hold the line: `validate_registry` (CI) rejects a
registry where a source with committed files is not cleared, and `ingest` skips the files of an uncleared source.
"""
import csv
import hashlib
import json
from datetime import UTC, datetime

import fitz
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from flame_api import ingest, registry
from flame_api.models import Base, DocumentRecord, FileRecord, SourceRecord


@pytest.mark.parametrize("row,problem", [
    ({"verification_state": "verified", "license": "NTRS PUBLIC_USE_PERMITTED"}, None),
    ({"verification_state": "partially_verified", "license": "NTRS PUBLIC_USE_PERMITTED"}, "verification_state is partially_verified"),
    ({"verification_state": "needs_followup", "license": None}, "verification_state is needs_followup"),
    ({"verification_state": "verified", "license": None}, "no licence recorded"),
    ({"license": "CC0"}, "verification_state is missing"),
])
def test_a_source_is_cleared_only_when_verified_and_licensed(row, problem):
    found = registry.clearance_problem(row)
    assert found == problem if problem is None else problem in found


def test_every_source_with_committed_files_is_cleared():
    with registry.FILES_JSONL.open(encoding="utf-8") as handle:
        with_files = {json.loads(line)["source_id"] for line in handle if line.strip()}
    blocked = {s: why for s, why in registry.uncleared_sources().items() if s not in registry.KNOWN_UNCLEARED}
    assert not (with_files & blocked.keys()), {s: blocked[s] for s in with_files & blocked.keys()}


def test_a_known_uncleared_source_is_never_ingested():
    assert set(registry.KNOWN_UNCLEARED) <= ingest.NOT_INGESTED_SOURCES


def _write_registry(tmp_path, rows):
    source = registry.REGISTRY_CSV
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, template = reader.fieldnames, next(reader)
    path = tmp_path / "registry.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for overrides in rows:
            writer.writerow({**template, **overrides})
    return path


def test_the_registry_validator_rejects_an_uncleared_source_that_has_files(tmp_path):
    csv_path = _write_registry(tmp_path, [
        {"source_id": "FF-NTRS-1", "verification_state": "partially_verified"},
        {"source_id": "FF-NTRS-2", "verification_state": "needs_followup", "license": "null"},   # no files: allowed
    ])
    files = tmp_path / "files.jsonl"
    files.write_text(json.dumps({"source_id": "FF-NTRS-1", "file_id": "f1"}) + "\n", encoding="utf-8")
    problems = registry.validate_registry(csv_path, files_path=files)
    assert [p for p in problems if "not cleared" in p] == [
        "FF-NTRS-1: verification_state: has committed files but is not cleared for ingestion "
        "(verification_state is partially_verified)"]


def _pdf(path, text):
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), text)
    pdf.save(path)
    pdf.close()
    return path


def test_ingest_skips_the_files_of_an_uncleared_source(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    now = datetime.now(UTC)
    with factory() as session:
        for source_id in ("FF-NTRS-OK", "FF-NTRS-HOLD"):
            session.add(SourceRecord(source_id=source_id, title=source_id, repository="NASA NTRS", access_url="https://ntrs.nasa.gov"))
            path = _pdf(tmp_path / f"{source_id}.pdf", f"Opposed flow flame spread report {source_id}. " * 4)
            data = path.read_bytes()
            session.add(FileRecord(file_id=f"sha256:{source_id}", source_id=source_id, sha256=hashlib.sha256(data).hexdigest(),
                                   original_filename=path.name, media_type="application/pdf", size_bytes=len(data),
                                   retrieved_at=now, local_path=str(path)))
        session.commit()
    monkeypatch.setattr(ingest, "seed", lambda: None)
    monkeypatch.setattr(ingest, "SessionLocal", factory)
    monkeypatch.setattr(ingest, "uncleared_sources", lambda: {"FF-NTRS-HOLD": "verification_state is partially_verified"})

    totals = ingest.ingest()

    assert totals["not_cleared"] == 1 and totals["pdf_documents"] == 1
    with factory() as session:
        assert [d.source_id for d in session.query(DocumentRecord)] == ["FF-NTRS-OK"]
    engine.dispose()
