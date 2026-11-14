import csv
import hashlib
import json
import logging
import re
import zipfile
import zlib
from html.parser import HTMLParser
from datetime import UTC, datetime
from pathlib import Path

import fitz
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from flame_api.database import SessionLocal
from flame_api.ids import stable_ulid
from flame_api.registry import uncleared_sources
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
from ai.rag.ingestion.normalize import NORMALIZER_VERSION, normalize_document
from flame_api.seed import seed

logger = logging.getLogger("flame_api.ingest")

# 0.2.0: OCR fallback for pages without a text layer; quarantine; NTRS titles. Chunk and evidence IDs
# are unchanged from 0.1.0 (they depend on file hash and page only), so re-ingestion is idempotent.
# 0.3.0: a page whose text layer is unreadable (broken font encoding) is OCRed like a page without text.
# 0.4.0: the INDEXED text of a text-layer page is normalised (ligatures, hyphen splits, running headers, stacked words;
# ai/rag/ingestion/normalize.py). The evidence excerpt stays verbatim. Chunk and evidence IDs are unchanged, so
# re-ingestion updates chunk text in place; run `python -m flame_api.vector_index build` afterwards to re-embed it.
# 0.5.0: OCR render size capped for large-format pages (ocr_dpi) and a per-page Tesseract timeout. Letter/A4
# pages render exactly as in 0.4.0.
PARSER_VERSION = "pymupdf-pages-0.5.0"
HTML_PARSER_VERSION = "html-sections-0.1.0"
JSON_PARSER_VERSION = "json-paths-0.1.0"
# 0.2.0: per-investigation test-ID/fuel columns for all 24 PSI combustion investigations; blank spreadsheet rows
# skipped; SAFFIRE-II/III legend rows skipped. Rows of the original four tables parse exactly as in 0.1.0.
TABLE_PARSER_VERSION = "psi-tables-0.2.0"
ISATAB_PARSER_VERSION = "isatab-investigation-0.1.0"
OCR_MIN_CONFIDENCE = 60.0        # mean word confidence (0-100) below which an OCR page is flagged
OCR_DPI = 300
OCR_MAX_SIDE_PX = 6600           # 2x a letter page's long side at 300 DPI
OCR_TIMEOUT_S = 300              # per page; a page Tesseract cannot finish counts as not OCR-able
MIN_PAGE_CHARS = 12
NOT_INGESTED_SOURCES = frozenset({"FF-PSI-DSI"})   # DSI is non-combustion; its frames are image assets
ROOT = Path(__file__).resolve().parents[3]
# "\u2013"/"\u2014" are the real en/em dash (FLEX, cp1252 byte 0x96); the "â€" forms are their mojibake.
MISSING = {"", "-", "\u2013", "\u2014", "â€“", "â€”", "n/a", "na", "none", "null"}


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
    normalized = header.lower().replace("\u00b5", "u").replace("\u2082", "2").replace("Âµ", "u").replace("â‚‚", "2")
    if "mmhg" in normalized:
        return value * 133.322387415, "Pa"
    if "sccm" in normalized:
        return None, None   # a volumetric flow at standard conditions; it contains "cm" but is not a length
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


_FUNCTION_WORDS = frozenset({"the", "of", "and", "in", "to", "a", "is", "for", "with", "on", "at", "by", "was", "that",
                             "are", "from", "as", "be", "this", "were"})
GARBLED_MIN_TOKENS = 40
GARBLED_MAX_FUNCTION_WORD_SHARE = 0.03


def text_layer_is_garbled(text: str) -> bool:
    """True for an English page whose extracted text is not language (e.g. a PDF font with a broken ToUnicode map).

    Real English prose has 15-30% function words; two FLEX papers in the corpus extract at 0-1%. Short pages
    (tables, captions) are never judged.
    """
    tokens = re.findall(r"[A-Za-z]+", text.lower())
    if len(tokens) < GARBLED_MIN_TOKENS:
        return False
    return sum(t in _FUNCTION_WORDS for t in tokens) / len(tokens) < GARBLED_MAX_FUNCTION_WORD_SHARE


def ocr_dpi(page) -> int:
    """OCR_DPI, lowered for large-format pages so the longest rendered side is at most OCR_MAX_SIDE_PX.
    A letter/A4 page keeps 300 DPI; a 34x44 in engineering drawing (ACME, SAME) renders at 150 DPI instead of a
    134-megapixel image that Tesseract needs tens of minutes for."""
    longest_in = max(page.rect.width, page.rect.height) / 72
    return max(72, min(OCR_DPI, int(OCR_MAX_SIDE_PX / longest_in))) if longest_in else OCR_DPI


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
        pixmap = page.get_pixmap(dpi=ocr_dpi(page))
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, timeout=OCR_TIMEOUT_S)
    except Exception:  # tesseract binary missing, failed, or timed out on this page
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


def _store_passage(session, *, source, file_record, document_id, label, locator, text, method, confidence, parser, now, flags=None,
                   index_text=None):
    """One evidence row plus its chunk. IDs depend only on the file hash and the locator.

    `text` is the evidence excerpt, exactly as extracted. `index_text` (default: the same) is what the search index sees."""
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
    existing = session.get(EvidenceRecord, evidence_id)
    if existing is None or existing.excerpt == text:
        # An administrator's review applies to the text they reviewed; changed text (e.g. OCR replacing a garbled
        # layer) goes back to machine_extracted.
        _keep_review(session, evidence_id, evidence_payload)
    session.merge(EvidenceRecord(
        evidence_id=evidence_id, source_id=source.source_id, file_id=file_record.file_id, document_id=document_id,
        experiment_id=None, analysis_id=None, kind="document_passage", origin="source_evidence", excerpt=text,
        locator=locator, payload=evidence_payload, created_at=now,
    ))
    session.merge(DocumentChunk(
        chunk_id=chunk_id, document_id=document_id, source_id=source.source_id, file_id=file_record.file_id,
        evidence_id=evidence_id, page=locator.get("page"), section=locator.get("label") if locator["type"] == "section" else None,
        text=text if index_text is None else index_text, ingested_at=now,
    ))


def _drop_stale_page_chunks(session: Session, document_id: str, new_text: dict[int, str]) -> None:
    """Re-ingest hygiene: remove chunks for pages that no longer yield text, and the embeddings of chunks whose
    text changed (e.g. a garbled text layer replaced by OCR), so `vector_index build` re-embeds them."""
    stale: list[str] = []
    for chunk in session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id):
        if chunk.page not in new_text:
            stale.append(chunk.chunk_id)
            evidence = session.get(EvidenceRecord, chunk.evidence_id)
            session.delete(chunk)
            if evidence is not None:
                session.delete(evidence)   # the page no longer yields text, so its old excerpt must not stay citable
        elif chunk.text != new_text[chunk.page]:
            stale.append(chunk.chunk_id)
    if stale and session.bind.dialect.name == "postgresql":
        from sqlalchemy import text as sql

        if session.execute(sql("select to_regclass('chunk_embedding') is not null")).scalar_one():
            session.execute(sql("delete from chunk_embedding where chunk_id = any(:ids)"), {"ids": stale})
    session.flush()


def _document_identity(source: SourceRecord, path: Path) -> tuple[str, str, str | None]:
    """(title, document_type, identifier). NTRS sources are single reports named by their registry row."""
    if source.repository == "NASA NTRS":
        return source.title, "technical_report", source.short_name
    return path.stem.replace("_", " "), _document_type(path), None


def _index_texts(passages: list[tuple[int, str, str, float | None, bool]]) -> dict[int, str]:
    """Page number -> the text to index. Text-layer pages are normalised together (running headers are a property of the
    whole document); OCR pages are indexed as read."""
    verbatim = [(page, text) for page, text, method, *_ in passages if method == "verbatim_text"]
    normalised = dict(zip((page for page, _ in verbatim), normalize_document([text for _, text in verbatim])))
    return {page: normalised.get(page, text) for page, text, *_ in passages}


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
    garbled_pages: list[int] = []
    for index, page in enumerate(document, start=1):
        text = page.get_text("text").replace("\x00", "").strip()
        if len(text) >= MIN_PAGE_CHARS and not text_layer_is_garbled(text):
            passages.append((index, text, "verbatim_text", None, False))
            continue
        if len(text) >= MIN_PAGE_CHARS:
            garbled_pages.append(index)   # unreadable text layer: never index it; OCR the rendered page instead
        else:
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
        text_layer="none" if len(blank_pages) + len(garbled_pages) == page_count
        else "full" if not blank_pages and not garbled_pages else "partial",
        pages_without_text=sorted(blank_pages + garbled_pages),
        parser_version=PARSER_VERSION,
        ingested_at=now,
        payload={"garbled_text_pages": garbled_pages, "text_normalization": NORMALIZER_VERSION, "ocr": {
            "status": ocr_status if blank_pages or garbled_pages else "not_needed",
            "engine": ocr_engine,
            "dpi": OCR_DPI if ocr_pages else None,
            "max_render_side_px": OCR_MAX_SIDE_PX if ocr_pages else None,
            "page_confidence": ocr_pages,
            "low_confidence_pages": sorted(int(p) for p, c in ocr_pages.items() if c < OCR_MIN_CONFIDENCE),
            "min_confidence": OCR_MIN_CONFIDENCE,
        }},
    ))
    index_texts = _index_texts(passages)
    _drop_stale_page_chunks(session, document_id, index_texts)
    for page_number, page_text, method, confidence, low in passages:
        locator = {"type": "page", "page": page_number, "section": None, "row": None, "frame_index": None, "label": f"p. {page_number}"}
        _store_passage(session, source=source, file_record=file_record, document_id=document_id, label=f"p. {page_number}",
                       locator=locator, text=page_text, method=method, confidence=confidence, parser=PARSER_VERSION, now=now,
                       flags={"low_confidence": True} if low else None, index_text=index_texts[page_number])
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


# ISA-Tab investigation fields shown as citable sections, in display order (docs/data/COMBUSTION_DATASET_ANALYSIS.md §3.5).
ISATAB_SECTIONS = (
    ("Objective", "Comment[Objective]"),
    ("Hypothesis", "Comment[Hypothesis]"),
    ("Approach", "Comment[Approach]"),
    ("Research impacts", "Comment[Research Impacts]"),
    ("Experiment hardware", "Comment[Experiment Hardware]"),
    ("Flight platform", "Comment[Flight Platform]"),
    ("Research area", "Comment[SubResearch Area]"),
    ("Keywords", "Study Design Type"),
    ("Publications", "Comment[Study Publication Link]"),
)
ISATAB_FIELDS = {
    "title": "Study Title", "acronym": "Comment[Investigation Acronym]", "doi": "Comment[DOI]",
    "start_date": "Comment[Investigation Start Date]", "end_date": "Comment[Investigation End Date]",
    "release_date": "Study Public Release Date", "center": "Comment[Managing NASA Center]",
}
ISATAB_MAX_BYTES = 2_000_000


def parse_isatab(raw: bytes) -> tuple[dict, list[tuple[str, str]]]:
    """(fields, sections) from a PSI metadata zip holding an ISA-Tab i_Investigation.txt.

    NASA's own text, kept verbatim. It is untrusted input for any model (requirements SR-1),
    so it only ever reaches a prompt as quoted evidence.
    """
    import io

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        names = [n for n in archive.namelist() if Path(n).name.lower().startswith("i_") and n.lower().endswith(".txt")]
        if not names:
            raise QuarantineError("isatab_missing_investigation_file")
        info = archive.getinfo(names[0])
        if info.file_size > ISATAB_MAX_BYTES:
            raise QuarantineError("isatab_too_large")
        text = archive.read(info).decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError, EOFError, OSError) as exc:
        # corrupt, encrypted or unsupported-compression archives quarantine one file, never abort the ingest run
        raise QuarantineError("invalid_zip") from exc
    rows: dict[str, list[str]] = {}
    for line in text.splitlines():
        cells = [cell.strip().strip('"').strip() for cell in line.split("\t")]
        if cells and cells[0] and cells[0] not in rows:
            rows[cells[0]] = [c for c in cells[1:] if c]
    fields = {key: (rows.get(label) or [None])[0] for key, label in ISATAB_FIELDS.items()}
    fields["publications"] = rows.get("Comment[Study Publication Link]", [])
    fields["keywords"] = rows.get("Study Design Type", [])
    sections = []
    for heading, label in ISATAB_SECTIONS:
        values = rows.get(label) or []
        body = ("\n".join(values) if label in {"Comment[Study Publication Link]"} else "; ".join(values) if label == "Study Design Type" else " ".join(values)).strip()
        if len(body) >= MIN_PAGE_CHARS:
            sections.append((heading, body[:20000]))
    return fields, sections


def _create_isatab_document(session: Session, file_record: FileRecord) -> dict[str, int]:
    """PSI investigation metadata: one document, one citable section per ISA-Tab field."""
    path = Path(file_record.local_path or "")
    source = session.get(SourceRecord, file_record.source_id)
    if not path.is_file() or not source:
        return {"pages": 0, "chunks": 0, "skipped": 1}
    fields, sections = parse_isatab(path.read_bytes())
    if not sections:
        raise QuarantineError("no_text_in_isatab")
    now = _utc_now()
    document_id = stable_ulid(f"document:{file_record.file_id}")
    title = f"{fields.get('title') or source.title}: investigation metadata"
    session.merge(DocumentRecord(
        document_id=document_id, source_id=source.source_id, file_id=file_record.file_id, title=title,
        document_type="dataset_documentation", identifier=fields.get("acronym") or source.short_name,
        persistent_identifier=source.persistent_identifier, page_count=None, text_layer="full", pages_without_text=[],
        parser_version=ISATAB_PARSER_VERSION, ingested_at=now,
        payload={"sections": len(sections), "isatab": fields},
    ))
    for number, (heading, body) in enumerate(sections, start=1):
        locator = {"type": "section", "page": None, "section": number, "row": None, "frame_index": None, "label": heading}
        _store_passage(session, source=source, file_record=file_record, document_id=document_id, label=f"§ {heading}",
                       locator=locator, text=f"{source.short_name or source.title} {heading.lower()}: {body}", method="verbatim_text",
                       confidence=None, parser=ISATAB_PARSER_VERSION, now=now)
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


# Per investigation: which column names a test, and which names its fuel or material (first non-empty wins).
# Headers are matched after stripping, so "Sample Number " is "Sample Number". Docs: docs/data/PSI_COMBUSTION_DATASETS.md.
TEST_ID_COLUMNS = {
    "FF-PSI-10": ("Test",),                          # ACME Flame Design (normal + inverse tables)
    "FF-PSI-20": (),                                 # ACME BRE: one row per test day, no ID column
    "FF-PSI-21": ("Test Day",),                      # ACME CLD Flame (YYDDD)
    "FF-PSI-22": ("Test Day",),                      # ACME E-FIELD
    "FF-PSI-23": ("Test Day*",),                     # ACME s-Flame
    "FF-PSI-25": ("Test #",),
    "FF-PSI-26": ("Test #", "As Run Test #"),        # BASS
    "FF-PSI-39": ("Flex Number", "CIR"),             # CFI
    "FF-PSI-47": ("Session Name",),                  # DAFT
    "FF-PSI-68": ("Sample (Fuel Type)",),            # FLEX-2 test matrix
    "FF-PSI-69": ("FLEX Identifier", "FLEX Test #"),
    "FF-PSI-98": ("Sample Number",),
    "FF-PSI-99": ("Sample Number",),                 # SAFFIRE-II
    "FF-PSI-100": ("Sample Number",),                # SAFFIRE-III
    "FF-PSI-101": ("SAME Test #",),                  # SAME-R
    "FF-PSI-102": ("Sample #",),                     # SAME
    "FF-PSI-106": ("Test Date",),                    # SLICE
    "FF-PSI-107": ("Test ID", "Test #"),
    "FF-PSI-142": ("Data ID",),
    "FF-PSI-159": ("Test",),                         # ACME CFI-G (normal + inverse tables)
}
FUEL_COLUMNS = {
    "FF-PSI-10": ("Fuel",),                          # the inverse-flame table has no fuel column (ethylene, XC2H4)
    "FF-PSI-20": ("Fuel Bottle",),
    "FF-PSI-21": ("Fuel Bottle",),
    "FF-PSI-22": ("Fuel Bottle",),
    "FF-PSI-23": ("Fuel Bottle",),
    "FF-PSI-25": ("Fuel Sample Material",),
    "FF-PSI-26": ("Fuel Sample Material",),
    "FF-PSI-39": ("Fuel",),
    "FF-PSI-47": ("Sample Material",),
    "FF-PSI-68": ("Sample (Fuel Type)",),
    "FF-PSI-69": ("Fuel",),
    "FF-PSI-98": ("Material",),
    "FF-PSI-99": ("Material",),
    "FF-PSI-100": ("Material",),
    "FF-PSI-101": ("Sample Type",),
    "FF-PSI-102": ("Sample Material",),
    "FF-PSI-106": ("Fuel Type",),
    "FF-PSI-107": ("Fuel",),
    "FF-PSI-159": ("Fuel",),
}
# SAFFIRE tables end with camera-legend and note rows ("F1C1/F1C2", "Note 1"); real samples look like these.
SAFFIRE_SAMPLE = {"FF-PSI-98": r"[A-Za-z]\d+", "FF-PSI-99": r"\d+-\d+", "FF-PSI-100": r"[A-Za-z]\d+"}


def _test_id(source_id: str, row: dict[str, str], row_number: int) -> str:
    for key in TEST_ID_COLUMNS.get(source_id, ()):
        if row.get(key, "").strip():
            return row[key].strip()
    return f"row-{row_number:05d}"


def _fuel(source_id: str, row: dict[str, str]) -> str | None:
    for key in FUEL_COLUMNS.get(source_id, ()):
        if row.get(key, "").strip():
            return row[key].strip()
    return None


def _unit(header: str) -> str | None:
    match = re.search(r"[;(]\s*([^;)]+)\s*[)]?$", header)
    if match:
        return match.group(1).strip()
    if ";" in header:
        return header.rsplit(";", 1)[1].strip()
    normalized = header.lower().replace("\u2082", "2").replace("â‚‚", "2")
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
    pattern = SAFFIRE_SAMPLE.get(source_id)
    if pattern is None:
        return False
    return not re.fullmatch(pattern, row.get(test_column, "").strip())


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
        test_column = (TEST_ID_COLUMNS.get(source.source_id) or ("",))[0]
        seen_rows: set[tuple[str, ...]] = set()
        now = _utc_now()
        experiments = evidence_count = duplicates = valid_rows = 0
        for row_number, raw_row in enumerate(reader, start=1):
            row = {key.strip(): (value or "").strip() for key, value in raw_row.items() if key}
            if not any(row.values()):          # spreadsheet padding (861 blank rows in the CFI-G inverse table)
                continue
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
            fuel = _fuel(source.source_id, row)
            condition_ids = []
            searchable_values = [test_id, source.short_name or "", fuel or ""]
            # Evidence and conditions reference the experiment, so it must exist before they are inserted.
            session.merge(ExperimentRecord(
                experiment_id=experiment_id, source_id=source.source_id, test_id=test_id,
                investigation=source.short_name, gravity_regime="microgravity", fuel_or_material=fuel,
                table_file_id=file_record.file_id, searchable_text="", ingested_at=now,
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
                ingested_at=now,
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
    """Parse one file. Returns (outcome, counts); outcome is ingested | skipped | quarantined | failed.

    `quarantined` is a verdict on the file (unreadable, wrong checksum, no text). `failed` is any other parser exception:
    the file's partial rows are rolled back, the error is logged with its traceback and the run goes on with the next
    file. A failed file is not quarantined and records no run, because the fault may be the parser's, so the next
    ingest retries it. Database errors are not the file's fault either; they propagate and end the run.

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
    is_isatab = suffix == ".zip" and path.parent.name.lower() == "metadata"
    if suffix not in {".pdf", ".html", ".htm", ".json"} and not is_table and not is_isatab:
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
            elif is_isatab:
                counts, transformation = _create_isatab_document(session, file_record), ISATAB_PARSER_VERSION
            else:
                counts, transformation = _create_table_experiments(session, file_record), TABLE_PARSER_VERSION
    except QuarantineError as exc:
        quarantine(session, file_record, exc.reason)
        _record_run(session, file_record, "quarantine", {"reason": exc.reason})
        return "quarantined", {"reason": exc.reason}
    except SQLAlchemyError:
        raise
    except Exception as exc:
        reason = f"parser_error:{type(exc).__name__}"
        logger.exception("ingest_file_failed file_id=%s path=%s reason=%s", file_record.file_id, file_record.local_path, reason)
        return "failed", {"reason": reason}
    _record_run(session, file_record, transformation, counts)
    return "ingested", counts


def _transformation_for(file_record: FileRecord) -> str | None:
    """The parser version ingest_file would apply to this file now (None: no parser)."""
    path = Path(file_record.local_path or "")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PARSER_VERSION
    if suffix in {".html", ".htm"}:
        return HTML_PARSER_VERSION
    if suffix == ".json":
        return JSON_PARSER_VERSION
    if suffix == ".csv" and "experimental table" in str(path).lower():
        return TABLE_PARSER_VERSION
    if suffix == ".zip" and path.parent.name.lower() == "metadata":
        return ISATAB_PARSER_VERSION
    return None


def _already_ingested(session: Session) -> set[tuple[str, str, str]]:
    """(file_id, input sha256, transformation) of every completed parse. Output IDs depend only on these, so
    parsing the same bytes with the same parser version again reproduces exactly the same rows."""
    return set(session.execute(
        select(IngestionRun.file_id, IngestionRun.input_sha256, IngestionRun.transformation_id)
        .where(IngestionRun.transformation_id != "quarantine")
    ).all())


def ingest(force: bool = False) -> dict[str, int]:
    """Parse every registered file. A file already parsed from the same bytes by the same parser version is skipped
    (counted as `unchanged`), so a container restart does not re-OCR the whole corpus; `force` re-parses everything.
    A new parser version or a changed file is always parsed again."""
    seed()
    session = SessionLocal()
    totals = {"pdf_documents": 0, "pdf_pages": 0, "pdf_chunks": 0, "ocr_pages": 0, "ocr_low_confidence": 0,
              "text_documents": 0, "text_chunks": 0, "experiments": 0, "table_evidence": 0, "spice_duplicates": 0,
              "skipped": 0, "quarantined": 0, "failed": 0, "not_cleared": 0, "unchanged": 0}
    try:
        files = (
            session.query(FileRecord)
            .filter(FileRecord.source_id.notin_(NOT_INGESTED_SOURCES))
            .order_by(FileRecord.source_id, FileRecord.file_id)
            .all()
        )
        done = set() if force else _already_ingested(session)
        # A source that is not verified and licensed in the registry stays metadata only (KB audit 2026-11-13).
        blocked = uncleared_sources()
        for source_id in sorted({f.source_id for f in files} & blocked.keys()):
            logger.warning("ingest_source_not_cleared source_id=%s reason=%s", source_id, blocked[source_id])
        for file_record in files:
            if file_record.source_id in blocked:
                totals["not_cleared"] += 1
                continue
            transformation = _transformation_for(file_record)
            if transformation and file_record.status != "quarantined" \
                    and (file_record.file_id, file_record.sha256, transformation) in done:
                totals["unchanged"] += 1
                continue
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
            elif suffix in {".html", ".htm", ".json", ".zip"}:
                totals["text_documents"] += 1
                totals["text_chunks"] += counts["chunks"]
            else:
                totals["experiments"] += counts["experiments"]
                totals["table_evidence"] += counts["evidence"]
                totals["spice_duplicates"] += counts["duplicates"]
        session.commit()
        _publish_corpus_version(session, totals)
        _build_knowledge_graph(session, totals)
        _extract_nlp(session, totals)
        return totals
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _build_knowledge_graph(session: Session, totals: dict[str, int]) -> None:
    """Rebuild the table-derived knowledge graph (ADR-007). Derived data: a failure is logged and counted,
    and never undoes the ingestion it follows (`python -m flame_api.knowledge_graph build` retries it)."""
    from flame_api.knowledge_graph import build_graph

    try:
        counts = build_graph(session)
    except Exception:
        session.rollback()
        logger.exception("knowledge_graph_build_failed")
        totals["graph_build_failed"] = 1
        return
    totals["graph_entities"] = counts["entities"]
    totals["graph_relations"] = counts["relations"]


def _extract_nlp(session: Session, totals: dict[str, int]) -> None:
    """Run the source-linked NLP extractors over the ingested chunks, then add their graph edges (D1).

    Derived data, like the graph: a failure is logged and counted and never undoes the ingestion it follows
    (`python -m flame_api.nlp_extract run` and `python -m flame_api.nlp_graph build` retry it)."""
    from flame_api import nlp_extract, nlp_graph

    try:
        counts = nlp_extract.run(session)
        graph_counts = nlp_graph.build_nlp_edges(session)
    except Exception:
        session.rollback()
        logger.exception("nlp_extract_failed")
        totals["nlp_extract_failed"] = 1
        return
    totals["nlp_records_created"] = counts.get("created", 0)
    totals["nlp_records_superseded"] = counts.get("superseded", 0)
    totals["nlp_graph_relations_created"] = graph_counts.get("relations_created", 0)


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


def main(argv: list[str]) -> int:
    """Run ingest and print its totals. Exit status 1 when any file failed to parse (it is retried on the next run)."""
    import os

    force = "--force" in argv or os.environ.get("FLAME_INGEST_FORCE") == "1"
    totals = ingest(force=force)
    print(json.dumps(totals, sort_keys=True))
    return 1 if totals.get("failed") else 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))