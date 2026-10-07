import csv
import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from flame_api.database import SessionLocal
from flame_api.ids import stable_ulid
from flame_api.models import (
    DocumentChunk,
    DocumentRecord,
    EvidenceRecord,
    ExperimentCondition,
    ExperimentRecord,
    FileRecord,
    IngestionRun,
    SourceRecord,
)
from flame_api.seed import seed

PARSER_VERSION = "pymupdf-pages-0.1.0"
TABLE_PARSER_VERSION = "psi-tables-0.1.0"
ROOT = Path(__file__).resolve().parents[3]
MISSING = {"", "-", "â€“", "â€”", "n/a", "na", "none", "null"}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _ulid_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_") or "value"


def parse_cell(raw: str | None) -> tuple[float | None, str | None]:
    value = (raw or "").strip()
    if value.lower() in MISSING:
        return None, None
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value):
        number = float(value)
        return (int(number) if number.is_integer() else number), None
    return None, value


def convert_to_si(header: str, variable: str, value: float | None) -> tuple[float | None, str | None]:
    if value is None:
        return None, None
    normalized = header.lower().replace("Âµ", "u").replace("â‚‚", "2")
    if "mmhg" in normalized:
        return value * 133.322387415, "Pa"
    if "cm/s" in normalized:
        return value * 0.01, "m/s"
    if "mg/s" in normalized:
        return value * 1e-6, "kg/s"
    if "mm" in normalized and "burning rate" not in normalized:
        return value * 0.001, "m"
    if "cm" in normalized:
        return value * 0.01, "m"
    if "%" in normalized and ("o2" in normalized or "oxygen" in normalized):
        return value / 100, "1"
    if "mole fraction" in normalized:
        return value, "1"
    if re.search(r"(?:^|[;,( ])s(?:$|[), ])", normalized):
        return value, "s"
    return None, None


def _source_domain(source_id: str) -> str:
    return "non_combustion" if source_id == "FF-PSI-DSI" else "combustion"


def _source_payload(source: SourceRecord) -> dict:
    return {
        "source_id": source.source_id,
        "title": source.title,
        "short_name": source.short_name,
        "repository": source.repository,
        "persistent_identifier": source.persistent_identifier,
        "license": source.license,
        "access_url": source.access_url,
    }


def _file_payload(file_record: FileRecord) -> dict:
    return {
        "file_id": file_record.file_id,
        "sha256": file_record.sha256,
        "original_filename": file_record.original_filename,
        "media_type": file_record.media_type,
        "size_bytes": file_record.size_bytes,
        "retrieved_at": _ulid_timestamp(file_record.retrieved_at),
        "canonical_source_url": file_record.canonical_source_url,
        "is_original": file_record.is_original,
        "parent_file_id": file_record.parent_file_id,
    }


def _create_document(session: Session, file_record: FileRecord) -> dict[str, int]:
    path = Path(file_record.local_path or "")
    if not path.is_file() or path.suffix.lower() != ".pdf":
        return {"pages": 0, "chunks": 0, "skipped": 1}
    source = session.get(SourceRecord, file_record.source_id)
    if not source:
        return {"pages": 0, "chunks": 0, "skipped": 1}
    content_hash = file_record.sha256
    document_id = stable_ulid(f"document:{file_record.file_id}")
    document = fitz.open(path)
    page_count = len(document)
    blank_pages = []
    extracted: list[tuple[int, str]] = []
    for index, page in enumerate(document, start=1):
        text = page.get_text("text").replace("\x00", "").strip()
        if len(text) < 12:
            blank_pages.append(index)
        else:
            extracted.append((index, text))
    now = _utc_now()
    document_record = DocumentRecord(
        document_id=document_id,
        source_id=source.source_id,
        file_id=file_record.file_id,
        title=path.stem.replace("_", " "),
        document_type=_document_type(path),
        identifier=None,
        persistent_identifier=None,
        page_count=page_count,
        text_layer="none" if not extracted else "full" if not blank_pages else "partial",
        pages_without_text=blank_pages,
        parser_version=PARSER_VERSION,
        ingested_at=now,
        payload={},
    )
    session.merge(document_record)
    chunk_count = 0
    for page_number, page_text in extracted:
        chunk_id = f"{file_record.sha256[:16]}:v1:{page_number}"
        evidence_id = stable_ulid(f"evidence:{content_hash}:page:{page_number}")
        locator = {"type": "page", "page": page_number, "section": None, "row": None, "frame_index": None, "label": f"p. {page_number}"}
        citation = f"{source.short_name or source.title}, {path.name}, p. {page_number}"
        evidence_payload = {
            "citation": citation,
            "source": _source_payload(source),
            "value": None,
            "measurement_or_claim_type": None,
            "extraction_method": "verbatim_text",
            "extraction_confidence": None,
            "review_status": "machine_extracted",
            "transformation_id": PARSER_VERSION,
            "knowledge_version": None,
        }
        session.merge(EvidenceRecord(
            evidence_id=evidence_id,
            source_id=source.source_id,
            file_id=file_record.file_id,
            document_id=document_id,
            experiment_id=None,
            analysis_id=None,
            kind="document_passage",
            origin="source_evidence",
            excerpt=page_text,
            locator=locator,
            payload=evidence_payload,
            created_at=now,
        ))
        session.merge(DocumentChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            source_id=source.source_id,
            file_id=file_record.file_id,
            evidence_id=evidence_id,
            page=page_number,
            section=None,
            text=page_text,
            ingested_at=now,
        ))
        chunk_count += 1
    return {"pages": page_count, "chunks": chunk_count, "skipped": 0}


def _document_type(path: Path) -> str:
    parent = path.parent.name.lower()
    name = path.name.lower()
    if "test plan" in name or "test plan" in parent:
        return "test_plan"
    if "final report" in name or "final report" in parent:
        return "final_report"
    if "report" in parent:
        return "technical_report"
    if "science documents" in parent:
        return "publication"
    return "other"


def _test_id(source_id: str, row: dict[str, str], row_number: int) -> str:
    candidates = {
        "FF-PSI-25": ("Test #",),
        "FF-PSI-69": ("FLEX Identifier", "FLEX Test #"),
        "FF-PSI-98": ("Sample Number",),
        "FF-PSI-107": ("Test ID", "Test #"),
    }.get(source_id, ())
    for key in candidates:
        if row.get(key, "").strip():
            return row[key].strip()
    return f"row-{row_number:05d}"


def _fuel_column(source_id: str) -> str:
    return {
        "FF-PSI-25": "Fuel Sample Material",
        "FF-PSI-69": "Fuel",
        "FF-PSI-98": "Material",
        "FF-PSI-107": "Fuel",
    }.get(source_id, "")


def _unit(header: str) -> str | None:
    match = re.search(r"[;(]\s*([^;)]+)\s*[)]?$", header)
    if match:
        return match.group(1).strip()
    if ";" in header:
        return header.rsplit(";", 1)[1].strip()
    normalized = header.lower().replace("â‚‚", "2")
    if "mole fraction" in normalized:
        return "mole fraction"
    if "%" in normalized:
        return "%"
    for unit in ("mmhg", "mg/s", "cm/s", "sccm", "ppm", "mm", "cm", "um"):
        if unit in normalized:
            return unit
    return None


def _table_file_encoding(source_id: str) -> str:
    return "cp1252" if source_id == "FF-PSI-69" else "utf-8-sig"


def _is_legend_row(source_id: str, row: dict[str, str], test_column: str) -> bool:
    if source_id != "FF-PSI-98":
        return False
    test_id = row.get(test_column, "").strip()
    return not test_id or "/" in test_id or not test_id[0].isalpha() or not test_id[1:].isdigit()


def _create_table_experiments(session: Session, file_record: FileRecord) -> dict[str, int]:
    path = Path(file_record.local_path or "")
    if not path.is_file() or path.suffix.lower() != ".csv" or "experimental table" not in str(path).lower():
        return {"rows": 0, "experiments": 0, "evidence": 0, "duplicates": 0, "skipped": 1}
    source = session.get(SourceRecord, file_record.source_id)
    if not source or source.source_id == "FF-PSI-DSI":
        return {"rows": 0, "experiments": 0, "evidence": 0, "duplicates": 0, "skipped": 1}
    with path.open("r", encoding=_table_file_encoding(source.source_id), newline="") as stream:
        reader = csv.DictReader(stream)
        headers = [header.strip() for header in (reader.fieldnames or [])]
        test_column = {
            "FF-PSI-25": "Test #",
            "FF-PSI-69": "FLEX Identifier",
            "FF-PSI-98": "Sample Number",
        }.get(source.source_id, "")
        seen_rows: set[tuple[str, ...]] = set()
        experiments = evidence_count = duplicates = valid_rows = 0
        for row_number, raw_row in enumerate(reader, start=1):
            row = {key.strip(): (value or "").strip() for key, value in raw_row.items() if key}
            if _is_legend_row(source.source_id, row, test_column):
                continue
            signature = tuple(row.get(header, "") for header in headers)
            if source.source_id == "FF-PSI-107" and signature in seen_rows:
                duplicates += 1
                continue
            seen_rows.add(signature)
            valid_rows += 1
            test_id = _test_id(source.source_id, row, row_number)
            experiment_id = stable_ulid(f"experiment:{source.source_id}:{file_record.sha256}:{test_id}:{hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:12]}")
            fuel_header = _fuel_column(source.source_id)
            fuel = row.get(fuel_header) or None
            condition_ids = []
            searchable_values = [test_id, source.short_name or "", fuel or ""]
            # Evidence and conditions reference the experiment, so it must exist before they are inserted.
            session.merge(ExperimentRecord(
                experiment_id=experiment_id, source_id=source.source_id, test_id=test_id,
                investigation=source.short_name, gravity_regime="microgravity", fuel_or_material=fuel,
                table_file_id=file_record.file_id, searchable_text="",
            ))
            session.flush()
            for header in headers:
                raw_value = row.get(header, "")
                if raw_value:
                    searchable_values.extend((header, raw_value))
                variable = _slug(header)
                value_numeric, value_text = parse_cell(raw_value)
                value_si, unit_si = convert_to_si(header, variable, value_numeric)
                evidence_id = stable_ulid(f"evidence:{file_record.sha256}:row:{row_number}:column:{header}")
                locator = {"type": "table_row", "page": None, "section": header, "row": row_number, "frame_index": None, "label": f"row {row_number}"}
                evidence = EvidenceRecord(
                    evidence_id=evidence_id,
                    source_id=source.source_id,
                    file_id=file_record.file_id,
                    document_id=None,
                    experiment_id=experiment_id,
                    analysis_id=None,
                    kind="experiment_condition",
                    origin="source_evidence",
                    excerpt=f"{header}: {raw_value}",
                    locator=locator,
                    payload={
                        "citation": f"{source.short_name or source.title}, {path.name}, row {row_number}, {header}",
                        "source": _source_payload(source),
                        "value": {"numeric": value_numeric, "text": value_text, "unit": _unit(header)},
                        "measurement_or_claim_type": variable,
                        "extraction_method": "table_parse",
                        "extraction_confidence": None,
                        "review_status": "machine_extracted",
                        "transformation_id": TABLE_PARSER_VERSION,
                        "knowledge_version": None,
                    },
                    created_at=_utc_now(),
                )
                session.merge(evidence)
                condition_id = stable_ulid(f"condition:{evidence_id}")
                condition_ids.append(ExperimentCondition(
                    condition_id=condition_id,
                    experiment_id=experiment_id,
                    variable=variable,
                    value_numeric=value_numeric,
                    value_text=value_text,
                    unit_original=_unit(header),
                    value_si=value_si,
                    unit_si=unit_si,
                    origin="derived" if value_si is not None else "reported",
                    evidence_id=evidence_id,
                ))
                evidence_count += 1
            session.flush()
            experiment = ExperimentRecord(
                experiment_id=experiment_id,
                source_id=source.source_id,
                test_id=test_id,
                investigation=source.short_name,
                gravity_regime="microgravity",
                fuel_or_material=fuel,
                table_file_id=file_record.file_id,
                searchable_text=" ".join(searchable_values),
                conditions=condition_ids,
            )
            session.merge(experiment)
            experiments += 1
    return {"rows": valid_rows, "experiments": experiments, "evidence": evidence_count, "duplicates": duplicates, "skipped": 0}


def ingest() -> dict[str, int]:
    seed()
    session = SessionLocal()
    totals = {"pdf_documents": 0, "pdf_pages": 0, "pdf_chunks": 0, "experiments": 0, "table_evidence": 0, "spice_duplicates": 0, "skipped": 0}
    try:
        files = session.query(FileRecord).filter(FileRecord.source_id.in_(["FF-PSI-25", "FF-PSI-69", "FF-PSI-98", "FF-PSI-107"])).all()
        for file_record in files:
            if not file_record.local_path:
                totals["skipped"] += 1
                continue
            path = Path(file_record.local_path)
            if not path.is_file():
                totals["skipped"] += 1
                continue
            if path.suffix.lower() == ".pdf":
                counts = _create_document(session, file_record)
                totals["pdf_documents"] += int(counts["chunks"] > 0)
                totals["pdf_pages"] += counts["pages"]
                totals["pdf_chunks"] += counts["chunks"]
            elif path.suffix.lower() == ".csv" and "experimental table" in str(path).lower():
                counts = _create_table_experiments(session, file_record)
                totals["experiments"] += counts["experiments"]
                totals["table_evidence"] += counts["evidence"]
                totals["spice_duplicates"] += counts["duplicates"]
                now = _utc_now()
                session.merge(IngestionRun(
                    run_id=stable_ulid(f"ingestion:{file_record.file_id}:{TABLE_PARSER_VERSION}:{file_record.sha256}"),
                    source_id=file_record.source_id,
                    file_id=file_record.file_id,
                    transformation_id=TABLE_PARSER_VERSION,
                    input_sha256=file_record.sha256,
                    started_at=now,
                    finished_at=now,
                    counts=counts,
                ))
        session.commit()
        return totals
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print(json.dumps(ingest(), sort_keys=True))