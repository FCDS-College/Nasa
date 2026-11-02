import csv
import hashlib
import json
import re
from html.parser import HTMLParser
from datetime import UTC, datetime
from pathlib import Path

import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session

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

# 0.2.0: OCR fallback for pages without a text layer; quarantine; NTRS titles. Chunk and evidence IDs
# are unchanged from 0.1.0 (they depend on file hash and page only), so re-ingestion is idempotent.
PARSER_VERSION = "pymupdf-pages-0.2.0"
HTML_PARSER_VERSION = "html-sections-0.1.0"
JSON_PARSER_VERSION = "json-paths-0.1.0"
TABLE_PARSER_VERSION = "psi-tables-0.1.0"
OCR_MIN_CONFIDENCE = 60.0        # mean word confidence (0-100) below which an OCR page is flagged
OCR_DPI = 300
MIN_PAGE_CHARS = 12
NOT_INGESTED_SOURCES = frozenset({"FF-PSI-DSI"})   # DSI is non-combustion; its frames are image assets
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


class QuarantineError(Exception):
    """A file that must not be parsed or indexed until an administrator reviews it."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _ocr_page(page) -> tuple[str, float, str] | None:
    """(text, mean confidence 0-100, engine version) for one PDF page, or None when OCR is unavailable.

    Uses Tesseract through pytesseract when both are installed. Rendering happens in-process;
    nothing leaves the machine.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return None
    try:
        version = f"tesseract-{pytesseract.get_tesseract_version()}"
        pixmap = page.get_pixmap(dpi=OCR_DPI)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except Exception:  # tesseract binary missing or failed on this page
        return None
    words = [(w, float(c)) for w, c in zip(data.get("text", []), data.get("conf", [])) if str(w).strip() and float(c) >= 0]
    if not words:
        return "", 0.0, version
    text = " ".join(w for w, _ in words)
    return text, round(sum(c for _, c in words) / len(words), 1), version


def _keep_review(session, evidence_id: str, payload: dict) -> None:
    """Re-ingesting rebuilds evidence rows; an administrator's review (PUT /api/admin/evidence/{id}/review) survives it."""
    existing = session.get(EvidenceRecord, evidence_id)
    status = (existing.payload or {}).get("review_status") if existing is not None else None
    if status in {"human_verified", "rejected"}:
        payload["review_status"] = status


def _store_passage(session, *, source, file_record, document_id, label, locator, text, method, confidence, parser, now, flags=None):
    """One evidence row plus its chunk. IDs depend only on the file hash and the locator."""
    content_hash = file_record.sha256
    key = locator.get("page") if locator["type"] == "page" else f"s{locator['section']}"
    evidence_id = stable_ulid(f"evidence:{content_hash}:page:{key}" if locator["type"] == "page" else f"evidence:{content_hash}:section:{key}")
    chunk_id = f"{content_hash[:16]}:v1:{key}"
    path_name = Path(file_record.local_path or file_record.original_filename).name
    evidence_payload = {
        "citation": f"{source.short_name or source.title}, {path_name}, {label}",
        "source": _source_payload(source),
        "value": None,
        "measurement_or_claim_type": None,
        "extraction_method": method,
        "extraction_confidence": confidence,
        "review_status": "machine_extracted",
        "transformation_id": parser,
        "knowledge_version": None,
        **(flags or {}),
    }
    _keep_review(session, evidence_id, evidence_payload)
    session.merge(EvidenceRecord(
        evidence_id=evidence_id, source_id=source.source_id, file_id=file_record.file_id, document_id=document_id,
        experiment_id=None, analysis_id=None, kind="document_passage", origin="source_evidence", excerpt=text,
        locator=locator, payload=evidence_payload, created_at=now,
    ))
    session.merge(DocumentChunk(
        chunk_id=chunk_id, document_id=document_id, source_id=source.source_id, file_id=file_record.file_id,
        evidence_id=evidence_id, page=locator.get("page"), section=locator.get("label") if locator["type"] == "section" else None,
        text=text, ingested_at=now,
    ))


def _document_identity(source: SourceRecord, path: Path) -> tuple[str, str, str | None]:
    """(title, document_type, identifier). NTRS sources are single reports named by their registry row."""
    if source.repository == "NASA NTRS":
        return source.title, "technical_report", source.short_name
    return path.stem.replace("_", " "), _document_type(path), None


def _create_document(session: Session, file_record: FileRecord) -> dict[str, int]:
    path = Path(file_record.local_path or "")
    if not path.is_file() or path.suffix.lower() != ".pdf":
        return {"pages": 0, "chunks": 0, "skipped": 1}
    source = session.get(SourceRecord, file_record.source_id)
    if not source:
        return {"pages": 0, "chunks": 0, "skipped": 1}
    document_id = stable_ulid(f"document:{file_record.file_id}")
    try:
        document = fitz.open(path)
    except Exception as exc:
        raise QuarantineError("unreadable_pdf") from exc
    if document.needs_pass:
        raise QuarantineError("encrypted_pdf")
    page_count = len(document)
    if page_count == 0:
        raise QuarantineError("empty_pdf")
    now = _utc_now()
    blank_pages: list[int] = []
    passages: list[tuple[int, str, str, float | None, bool]] = []   # page, text, method, confidence, low_confidence
    ocr_pages: dict[str, float] = {}
    ocr_engine: str | None = None
    ocr_status = "not_needed"
    for index, page in enumerate(document, start=1):
        text = page.get_text("text").replace("\x00", "").strip()
        if len(text) >= MIN_PAGE_CHARS:
            passages.append((index, text, "verbatim_text", None, False))
            continue
        blank_pages.append(index)
        ocr = _ocr_page(page)
        if ocr is None:
            # "applied" wins once any page was OCRed; "unavailable" only if none could be.
            if ocr_status != "applied":
                ocr_status = "unavailable"
            continue
        ocr_text, confidence, ocr_engine = ocr
        ocr_status = "applied"
        ocr_pages[str(index)] = confidence
        if len(ocr_text) >= MIN_PAGE_CHARS:
            passages.append((index, ocr_text, "ocr", round(confidence / 100, 3), confidence < OCR_MIN_CONFIDENCE))
    title, document_type, identifier = _document_identity(source, path)
    session.merge(DocumentRecord(
        document_id=document_id,
        source_id=source.source_id,
        file_id=file_record.file_id,
        title=title,
        document_type=document_type,
        identifier=identifier,
        persistent_identifier=source.persistent_identifier,
        page_count=page_count,
        # text_layer describes the PDF itself; OCR text is recorded separately with its confidence.
        text_layer="none" if len(blank_pages) == page_count else "full" if not blank_pages else "partial",
        pages_without_text=blank_pages,
        parser_version=PARSER_VERSION,
        ingested_at=now,
        payload={"ocr": {
            "status": ocr_status if blank_pages else "not_needed",
            "engine": ocr_engine,
            "dpi": OCR_DPI if ocr_pages else None,
            "page_confidence": ocr_pages,
            "low_confidence_pages": sorted(int(p) for p, c in ocr_pages.items() if c < OCR_MIN_CONFIDENCE),
            "min_confidence": OCR_MIN_CONFIDENCE,
        }},
    ))
    for page_number, page_text, method, confidence, low in passages:
        locator = {"type": "page", "page": page_number, "section": None, "row": None, "frame_index": None, "label": f"p. {page_number}"}
        _store_passage(session, source=source, file_record=file_record, document_id=document_id, label=f"p. {page_number}",
                       locator=locator, text=page_text, method=method, confidence=confidence, parser=PARSER_VERSION, now=now,
                       flags={"low_confidence": True} if low else None)
    return {"pages": page_count, "chunks": len(passages), "skipped": 0, "ocr_pages": len(ocr_pages),
            "ocr_low_confidence": sum(1 for _, _, m, _, low in passages if m == "ocr" and low)}


class _TextExtractor(HTMLParser):
    """Visible text, split into sections at h1-h3 headings. Script, style and template content is dropped."""

    _SKIP = {"script", "style", "noscript", "template", "head"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[list[str]] = [["", ""]]   # [heading, text]
        self._skip = 0
        self._heading: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip += 1
        elif tag in {"h1", "h2", "h3"} and not self._skip:
            self._heading = []

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip:
            self._skip -= 1
        elif tag in {"h1", "h2", "h3"} and self._heading is not None:
            self.sections.append([" ".join(self._heading).strip(), ""])
            self._heading = None

    def handle_data(self, data):
        if self._skip:
            return
        if self._heading is not None:
            self._heading.append(data.strip())
        elif data.strip():
            self.sections[-1][1] += " " + " ".join(data.split())


def parse_html(raw: bytes) -> list[tuple[str, str]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise QuarantineError("html_not_utf8") from exc
    extractor = _TextExtractor()
    extractor.feed(text)
    extractor.close()
    return [(heading or "Untitled section", body.strip()) for heading, body in extractor.sections if len(body.strip()) >= MIN_PAGE_CHARS]


def _flatten(value, prefix: str = ""):
    if isinstance(value, dict):
        for key in sorted(value):
            yield from _flatten(value[key], f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _flatten(item, f"{prefix}[{index}]")
    else:
        yield prefix or "$", value


def parse_json(raw: bytes) -> list[tuple[str, str]]:
    """One section per top-level key (or per item of a top-level array), as `path: value` lines."""
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QuarantineError("invalid_json") from exc
    if isinstance(data, dict):
        groups = [(str(key), data[key]) for key in sorted(data)]
    elif isinstance(data, list):
        groups = [(f"[{index}]", item) for index, item in enumerate(data)]
    else:
        groups = [("$", data)]
    sections = []
    for label, value in groups:
        lines = [f"{path}: {item}" for path, item in _flatten(value, label)]
        body = "\n".join(lines)[:20000]
        if len(body) >= MIN_PAGE_CHARS:
            sections.append((label, body))
    return sections


def _create_text_document(session: Session, file_record: FileRecord, *, kind: str) -> dict[str, int]:
    """HTML and JSON adapters: sections become chunks with `section` locators."""
    path = Path(file_record.local_path or "")
    source = session.get(SourceRecord, file_record.source_id)
    if not path.is_file() or not source:
        return {"pages": 0, "chunks": 0, "skipped": 1}
    raw = path.read_bytes()
    sections, parser = (parse_html(raw), HTML_PARSER_VERSION) if kind == "html" else (parse_json(raw), JSON_PARSER_VERSION)
    if not sections:
        raise QuarantineError(f"no_text_in_{kind}")
    now = _utc_now()
    document_id = stable_ulid(f"document:{file_record.file_id}")
    title, document_type, identifier = _document_identity(source, path)
    session.merge(DocumentRecord(
        document_id=document_id, source_id=source.source_id, file_id=file_record.file_id, title=title,
        document_type=document_type if kind == "html" else "dataset_documentation", identifier=identifier,
        persistent_identifier=source.persistent_identifier, page_count=None, text_layer="full", pages_without_text=[],
        parser_version=parser, ingested_at=now, payload={"sections": len(sections)},
    ))
    for number, (heading, body) in enumerate(sections, start=1):
        locator = {"type": "section", "page": None, "section": number, "row": None, "frame_index": None, "label": heading[:120]}
        _store_passage(session, source=source, file_record=file_record, document_id=document_id, label=f"§ {heading[:80]}",
                       locator=locator, text=body, method="verbatim_text", confidence=None, parser=parser, now=now)
    return {"pages": 0, "chunks": len(sections), "skipped": 0}


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
                _keep_review(session, evidence_id, evidence.payload)
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def quarantine(session: Session, file_record: FileRecord, reason: str) -> None:
    file_record.status = "quarantined"
    file_record.quarantine_reason = reason
    session.add(file_record)


def _record_run(session: Session, file_record: FileRecord, transformation_id: str, counts: dict) -> None:
    now = _utc_now()
    session.merge(IngestionRun(
        run_id=stable_ulid(f"ingestion:{file_record.file_id}:{transformation_id}:{file_record.sha256}"),
        source_id=file_record.source_id,
        file_id=file_record.file_id,
        transformation_id=transformation_id,
        input_sha256=file_record.sha256,
        started_at=now,
        finished_at=now,
        counts=counts,
    ))


def ingest_file(session: Session, file_record: FileRecord) -> tuple[str, dict]:
    """Parse one file. Returns (outcome, counts); outcome is ingested | skipped | quarantined.

    A quarantined file is never parsed again until an administrator resets its status
    (docs/data/ADMIN_DATA_OPERATIONS.md). A missing local copy is skipped, not quarantined:
    git-ignored mirrors are legitimately absent on some machines.
    """
    if file_record.status == "quarantined":
        return "skipped", {"reason": "quarantined"}
    if not file_record.local_path or not Path(file_record.local_path).is_file():
        return "skipped", {"reason": "not_on_disk"}
    path = Path(file_record.local_path)
    suffix = path.suffix.lower()
    is_table = suffix == ".csv" and "experimental table" in str(path).lower()
    if suffix not in {".pdf", ".html", ".htm", ".json"} and not is_table:
        return "skipped", {"reason": "no_parser"}
    if _sha256(path) != file_record.sha256:
        quarantine(session, file_record, "checksum_mismatch")
        _record_run(session, file_record, "quarantine", {"reason": "checksum_mismatch"})
        return "quarantined", {"reason": "checksum_mismatch"}
    try:
        with session.begin_nested():
            if suffix == ".pdf":
                counts, transformation = _create_document(session, file_record), PARSER_VERSION
            elif suffix in {".html", ".htm"}:
                counts, transformation = _create_text_document(session, file_record, kind="html"), HTML_PARSER_VERSION
            elif suffix == ".json":
                counts, transformation = _create_text_document(session, file_record, kind="json"), JSON_PARSER_VERSION
            else:
                counts, transformation = _create_table_experiments(session, file_record), TABLE_PARSER_VERSION
    except QuarantineError as exc:
        quarantine(session, file_record, exc.reason)
        _record_run(session, file_record, "quarantine", {"reason": exc.reason})
        return "quarantined", {"reason": exc.reason}
    _record_run(session, file_record, transformation, counts)
    return "ingested", counts


def ingest() -> dict[str, int]:
    seed()
    session = SessionLocal()
    totals = {"pdf_documents": 0, "pdf_pages": 0, "pdf_chunks": 0, "ocr_pages": 0, "ocr_low_confidence": 0,
              "text_documents": 0, "text_chunks": 0, "experiments": 0, "table_evidence": 0, "spice_duplicates": 0,
              "skipped": 0, "quarantined": 0}
    try:
        files = (
            session.query(FileRecord)
            .filter(FileRecord.source_id.notin_(NOT_INGESTED_SOURCES))
            .order_by(FileRecord.source_id, FileRecord.file_id)
            .all()
        )
        for file_record in files:
            outcome, counts = ingest_file(session, file_record)
            if outcome != "ingested":
                totals[outcome] += 1
                continue
            suffix = Path(file_record.local_path).suffix.lower()
            if suffix == ".pdf":
                totals["pdf_documents"] += int(counts["chunks"] > 0)
                totals["pdf_pages"] += counts["pages"]
                totals["pdf_chunks"] += counts["chunks"]
                totals["ocr_pages"] += counts.get("ocr_pages", 0)
                totals["ocr_low_confidence"] += counts.get("ocr_low_confidence", 0)
            elif suffix in {".html", ".htm", ".json"}:
                totals["text_documents"] += 1
                totals["text_chunks"] += counts["chunks"]
            else:
                totals["experiments"] += counts["experiments"]
                totals["table_evidence"] += counts["evidence"]
                totals["spice_duplicates"] += counts["duplicates"]
        session.commit()
        _publish_corpus_version(session, totals)
        return totals
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _publish_corpus_version(session: Session, totals: dict[str, int]) -> None:
    """Announce a new corpus version when the set of ingested files changed (E2-5)."""
    from flame_api.config import get_settings
    from flame_api.knowledge_version import publish

    rows = session.execute(
        select(IngestionRun.file_id, IngestionRun.input_sha256, IngestionRun.transformation_id)
        .where(IngestionRun.transformation_id != "quarantine")
        .order_by(IngestionRun.file_id, IngestionRun.transformation_id)
    ).all()
    if not rows:
        return
    digest = hashlib.sha256("\n".join(f"{f}:{h}:{t}" for f, h, t in rows).encode()).hexdigest()[:12]
    publish(session, f"corpus-{digest}", trigger="ingestion", counts=totals, redis_url=get_settings().redis_url)


if __name__ == "__main__":
    print(json.dumps(ingest(), sort_keys=True))