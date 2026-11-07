"""Fetch and register the curated NASA NTRS technical reports (E2-9, corpus expansion 2026-11-07).

Every bibliographic field (title, authors, year, report number, download URL) is read from the
NTRS API record (https://ntrs.nasa.gov/api/citations/<id>); nothing is typed in by hand except the
curation fields in SELECTION (why a report was chosen, which experiment family it belongs to).

A report is accepted only if its NTRS record says
  distribution == "PUBLIC", copyright.determinationType in PERMITTED_DETERMINATIONS,
  copyright.containsThirdPartyMaterial is false, exportControl.isExportControl == "NO",
  a PDF download exists, the PDF is <= 6 MB and PyMuPDF extracts >= 3000 characters.
Accepted PDFs are saved to docs/research/<id>.pdf and appended (once) to
datasets/registry/source_registry.csv, datasets/metadata/files.jsonl and datasets/checksums/sha256.txt.
Re-running skips sources that are already registered.

    python knowledge/ingestion/fetch_ntrs.py --discover      # list candidates (PSI ISA-Tab links + searches)
    python knowledge/ingestion/fetch_ntrs.py --dry-run       # check SELECTION, download nothing to the repo
    python knowledge/ingestion/fetch_ntrs.py                 # download + register SELECTION

PDF content is treated as data: it is only opened with PyMuPDF to count pages and characters.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import tempfile
import time
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASETS = ROOT / "datasets"
RESEARCH = ROOT / "docs" / "research"
REGISTRY = DATASETS / "registry" / "source_registry.csv"
FILES = DATASETS / "metadata" / "files.jsonl"
CHECKSUMS = DATASETS / "checksums" / "sha256.txt"
NTRS = "https://ntrs.nasa.gov"

PERMITTED_DETERMINATIONS = {
    "GOV_PUBLIC_USE_PERMITTED": "work of the U.S. Government; public use permitted",
    "PUBLIC_USE_PERMITTED": "public use permitted",
}
MAX_BYTES = 6 * 1024 * 1024
MAX_TOTAL_BYTES = 60 * 1024 * 1024
MIN_CHARS = 3000

DISCOVERY_QUERIES = [
    "spacecraft fire safety microgravity", "Saffire large scale flame spread",
    "BASS burning and suppression of solids", "FLEX droplet extinction microgravity",
    "ACME coflow laminar diffusion flame", "smoke point microgravity SPICE",
    "material flammability exploration atmosphere oxygen", "NASA-STD-6001 flammability",
    "limiting oxygen index microgravity", "fire suppression spacecraft",
    "Advanced Combustion via Microgravity Experiments", "Flame Extinguishment Experiment droplet",
    "cool flame droplet International Space Station", "flammability of materials microgravity",
]

# id -> (selection basis, experiment_family or None, primary_fire_safety_use, why relevant)
SELECTION: dict[str, tuple[str, str | None, list[str], str]] = {
    # a. cited by the PSI investigations (Comment[Study Publication Link] in the ISA-Tab files)
    "20150019858": ("psi_link:PSI-25", "BASS-II", ["fire detection;combustion product sensing"],
                    "BASS-II on-board CSA-CP/CDM gas sensor readings during solid burning"),
    "20160012691": ("psi_link:PSI-25", "BASS-II", ["flammability limits;blowoff"],
                    "links normal-gravity mixed-convection blowoff limits to BASS microgravity limits"),
    "20130014061": ("psi_link:PSI-69", "FLEX", ["liquid-fuel droplet combustion;extinction"],
                    "FLEX methanol droplet burning and extinction in oxygen-inert atmospheres"),
    "20120016855": ("psi_link:PSI-69", "FLEX", ["droplet extinction;suppressant effects"],
                    "FLEX methanol droplet extinction with CO2 dilution (suppressant relevance)"),
    "20120015928": ("psi_link:PSI-69", "FLEX", ["droplet combustion;fire suppression"],
                    "FLEX programme overview: objectives, hardware and principal results"),
    "20170001636": ("psi_link:PSI-98", "SAFFIRE", ["large-scale flame spread;material flammability"],
                    "Saffire objectives, development and status"),
    "20170000230": ("psi_link:PSI-98", "SAFFIRE", ["large-scale flame spread;fire environment sensing"],
                    "Saffire flight operations and development status"),
    # a'. listed by title in the PSI ISA-Tab (link points elsewhere); found on NTRS by title
    "20150008961": ("psi_title:PSI-25", "BASS-II", ["solid-material flammability;concurrent flame spread"],
                    "BASS-II PMMA rod flammability in concurrent flow"),
    "20140006750": ("psi_title:PSI-69", "FLEX", ["droplet combustion;cool-flame extinction"],
                    "FLEX cool-flame extinction of n-alkane droplets"),
    # b. NTRS searches
    "20090014827": ("ntrs_search:smoke point microgravity SPICE", "SPICE", ["soot;smoke point"],
                    "SPICE experiment description (smoke points of coflow flames)"),
    "20130001713": ("ntrs_search:spacecraft fire safety microgravity", "SAFFIRE",
                    ["large-scale flame spread;spacecraft fire safety"],
                    "rationale and design of the large-scale spacecraft fire safety experiments"),
    "19990063738": ("ntrs_search:spacecraft fire safety microgravity", None,
                    ["spacecraft fire safety;detection;suppression"],
                    "review of fire safety in the low-gravity spacecraft environment"),
    "20140006580": ("ntrs_search:spacecraft fire safety microgravity", None,
                    ["fire scenarios;spacecraft fire safety"],
                    "realistic spacecraft fire scenarios for design and response"),
    "20140009169": ("ntrs_search:Advanced Combustion via Microgravity Experiments", "ACME",
                    ["gaseous diffusion flames;soot;extinction"],
                    "ACME gaseous non-premixed flame research plan for the ISS"),
    "20210021781": ("ntrs_search:Advanced Combustion via Microgravity Experiments", "ACME",
                    ["gaseous diffusion flames;soot;flame stability"],
                    "ACME results on gaseous-fuel flames aboard the ISS"),
    "20150004099": ("ntrs_search:NASA-STD-6001 flammability", None,
                    ["material flammability testing;exploration atmospheres"],
                    "flammability limit probabilities and normoxic upward limiting pressure (NASA-STD-6001 Test 1)"),
    "20080012607": ("ntrs_search:material flammability exploration atmosphere oxygen", None,
                    ["ignition;exploration atmospheres"],
                    "pressure effect on piloted ignition delay of PMMA"),
    "20110008636": ("ntrs_search:flammability of materials microgravity", None,
                    ["material flammability limits;exploration atmospheres"],
                    "parametric effects (pressure, oxygen, thickness) on material flammability limits"),
    "20150023467": ("ntrs_search:flammability of materials microgravity", None,
                    ["ignition;suppression;exploration atmospheres"],
                    "MIST summary: material ignition and suppression in exploration atmospheres"),
    "20070010766": ("ntrs_search:fire suppression spacecraft", None,
                    ["fire detection;suppression;exploration habitats"],
                    "fire safety technology development (detection, suppression, response) for exploration"),
    "20040161216": ("ntrs_search:fire suppression spacecraft", None, ["fire suppression"],
                    "testing and evaluation of spacecraft fire suppressants"),
}

REGISTRY_FIELDS = [
    "source_id", "title", "short_name", "provider", "repository", "psi_id", "persistent_identifier",
    "source_type", "experiment_family", "flight_platform", "data_modalities", "primary_fire_safety_use",
    "key_variables", "key_outputs", "license", "access_status", "access_url", "data_access_url",
    "aws_bucket", "version", "last_verified_utc", "source_date_range", "known_file_count", "known_size",
    "ingestion_strategy", "notes", "provenance_requirements", "priority", "p0_candidate_reason",
    "verification_state",
]


def _http(url: str, body: dict | None = None, timeout: int = 120, retries: int = 3) -> bytes:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json", "Content-Type": "application/json"} if body is not None else {}
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=timeout) as r:
                return r.read()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError("unreachable")


def record(ntrs_id: str) -> dict:
    return json.loads(_http(f"{NTRS}/api/citations/{ntrs_id}"))


def psi_cited_ids() -> dict[str, str]:
    """NTRS ids linked from Comment[Study Publication Link] in the PSI ISA-Tab investigation files."""
    pattern = re.compile(r"ntrs\.nasa\.gov/(?:citations/|search\.jsp\?R=|archive/nasa/casi\.ntrs\.nasa\.gov/|api/citations/)(\d{11})")
    found: dict[str, str] = {}
    csv.field_size_limit(10**8)
    for archive in sorted((DATASETS / "raw" / "psi_api").glob("PSI-*/metadata/*.zip")):
        text = zipfile.ZipFile(archive).read("i_Investigation.txt").decode("utf-8", "replace")
        for row in csv.reader(io.StringIO(text), delimiter="\t"):
            if row and row[0] == "Comment[Study Publication Link]":
                for cell in row[1:]:
                    for match in pattern.finditer(cell):
                        found.setdefault(match.group(1), archive.parts[-3])
    return found


def permission(rec: dict) -> tuple[bool, str]:
    cp = rec.get("copyright") or {}
    det = cp.get("determinationType")
    if rec.get("distribution") != "PUBLIC":
        return False, f"distribution={rec.get('distribution')}"
    if det not in PERMITTED_DETERMINATIONS:
        return False, f"determinationType={det}"
    if cp.get("containsThirdPartyMaterial"):
        return False, "containsThirdPartyMaterial=true"
    if (rec.get("exportControl") or {}).get("isExportControl") not in (None, "NO"):
        return False, "export controlled"
    return True, det


def pdf_link(rec: dict) -> tuple[str, str] | None:
    for d in rec.get("downloads") or []:
        link = (d.get("links") or {}).get("pdf")
        if link and d.get("mimetype") == "application/pdf":
            return d.get("name") or Path(link).name, link
    return None


def discover() -> int:
    candidates = {i: f"psi_link:{p}" for i, p in psi_cited_ids().items()}
    for q in DISCOVERY_QUERIES:
        hits = json.loads(_http(f"{NTRS}/api/citations/search", {"q": q, "page": {"size": 25}}))
        for hit in hits.get("results", []):
            candidates.setdefault(str(hit["id"]), f"ntrs_search:{q}")
    for i, basis in candidates.items():
        try:
            rec = record(i)
        except Exception as exc:  # noqa: BLE001
            print(f"{i}\tERROR {exc}")
            continue
        ok, why = permission(rec)
        print(f"{i}\t{'OK ' if ok else 'NO '}{why}\t{rec.get('stiType')}\t{'pdf' if pdf_link(rec) else 'no-pdf'}"
              f"\t{basis}\t{rec.get('title')}")
    return 0


def _year(rec: dict) -> str | None:
    for p in rec.get("publications") or []:
        if p.get("publicationDate"):
            return p["publicationDate"][:7]
    for m in rec.get("meetings") or []:
        if m.get("startDate"):
            return m["startDate"][:7]
    return None


def _short_name(rec: dict) -> str:
    for number in rec.get("otherReportNumbers") or []:
        if number.startswith("NASA/"):
            return number
    authors = sorted(rec.get("authorAffiliations") or [], key=lambda a: a.get("sequence", 0))
    first = authors[0]["meta"]["author"]["name"].strip() if authors else "NTRS"
    surname = first.split(",")[0].strip() if "," in first else first.split()[-1]   # "Olson, Sandra L." or "Dennis P Stocker"
    label = f"{surname} et al." if len(authors) > 1 else surname
    year = _year(rec)
    return f"{label} {year[:4]}" if year else label


def _authors(rec: dict) -> list[str]:
    ordered = sorted(rec.get("authorAffiliations") or [], key=lambda a: a.get("sequence", 0))
    return [a["meta"]["author"]["name"] for a in ordered if a.get("meta", {}).get("author")]


def _provider(rec: dict) -> str:
    orgs: list[str] = []
    for a in sorted(rec.get("authorAffiliations") or [], key=lambda a: a.get("sequence", 0)):
        name = ((a.get("meta") or {}).get("organization") or {}).get("name")
        if name and name not in orgs:
            orgs.append(name)
    if orgs:
        return "; ".join(orgs[:3])
    center = (rec.get("center") or {}).get("name")
    return f"NASA {center}" if center else "NASA"


def _pdf_stats(path: Path) -> tuple[int, int]:
    import pymupdf

    with pymupdf.open(path) as doc:
        return doc.page_count, sum(len(page.get_text()) for page in doc)


def registered_ids() -> set[str]:
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        return {row["source_id"] for row in csv.DictReader(handle)}


def run(dry_run: bool) -> int:
    already = registered_ids()
    total = 0
    accepted: list[dict] = []
    staging = Path(tempfile.mkdtemp(prefix="ntrs_"))
    for ntrs_id, (basis, family, uses, why) in SELECTION.items():
        source_id = f"FF-NTRS-{ntrs_id}"
        if source_id in already:
            print(f"{ntrs_id}: already registered, skipped")
            continue
        rec = record(ntrs_id)
        ok, determination = permission(rec)
        link = pdf_link(rec)
        if not ok or link is None:
            print(f"{ntrs_id}: SKIP ({determination if not ok else 'no PDF download'})")
            continue
        name, path = link
        url = NTRS + path
        retrieved = datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = _http(url, timeout=300)
        if len(data) > MAX_BYTES:
            print(f"{ntrs_id}: SKIP (PDF {len(data)} bytes > 6 MB)")
            continue
        staged = staging / f"{ntrs_id}.pdf"
        staged.write_bytes(data)
        pages, chars = _pdf_stats(staged)
        if chars < MIN_CHARS:
            print(f"{ntrs_id}: SKIP (only {chars} extracted characters)")
            continue
        if total + len(data) > MAX_TOTAL_BYTES:
            print(f"{ntrs_id}: SKIP (total size limit)")
            continue
        total += len(data)
        accepted.append({"id": ntrs_id, "rec": rec, "basis": basis, "family": family, "uses": uses, "why": why,
                         "determination": determination, "name": name, "url": url, "data": data,
                         "pages": pages, "chars": chars, "retrieved": retrieved})
        print(f"{ntrs_id}: OK {len(data):,} B, {pages} pp, {chars:,} chars, {determination} - {rec['title']}")
    print(f"{len(accepted)} accepted, {total / 1e6:.1f} MB")
    if dry_run or not accepted:
        return 0

    reg_rows, file_rows, sum_lines = [], [], []
    for item in accepted:
        rec, ntrs_id = item["rec"], item["id"]
        digest = hashlib.sha256(item["data"]).hexdigest()
        dest = RESEARCH / f"{ntrs_id}.pdf"
        part = dest.with_suffix(".pdf.part")
        part.write_bytes(item["data"])
        part.replace(dest)
        cp = rec.get("copyright") or {}
        basis = item["basis"]
        basis_text = {"psi_link": "linked from the ISA-Tab Comment[Study Publication Link] of",
                      "psi_title": "listed by title in the ISA-Tab Study Publication Title of",
                      "ntrs_search": "found by NTRS API search"}[basis.split(":")[0]]
        basis_value = basis.split(":", 1)[1]
        basis_note = (f"{basis_text} {basis_value}" if not basis.startswith("ntrs_search")
                      else f"{basis_text} '{basis_value}'")
        notes = (
            f"Single PDF committed at docs/research/{ntrs_id}.pdf, downloaded from the NTRS API on "
            f"{item['retrieved']} (NTRS file name '{item['name']}'). Metadata from the NTRS API record: "
            f"authors {', '.join(_authors(rec)) or 'not listed'}; STI type {rec.get('stiTypeDetails') or rec.get('stiType')}; "
            f"date {_year(rec) or 'not given'}; report numbers {', '.join(n for n in rec.get('otherReportNumbers') or [] if not n.startswith('Report Number:')) or 'none'}. "
            f"Permission: NTRS distribution={rec.get('distribution')}, copyright.determinationType={cp.get('determinationType')}, "
            f"containsThirdPartyMaterial={cp.get('containsThirdPartyMaterial')}, exportControl={(rec.get('exportControl') or {}).get('isExportControl')}. "
            f"Selection: {basis_note}; relevance: {item['why']}. {item['pages']} pages, {item['chars']:,} characters extracted by PyMuPDF."
        )
        reg_rows.append({
            "source_id": f"FF-NTRS-{ntrs_id}", "title": rec["title"].strip(), "short_name": _short_name(rec),
            "provider": _provider(rec), "repository": "NASA NTRS", "psi_id": "null",
            "persistent_identifier": "null", "source_type": "technical_report",
            "experiment_family": item["family"] or "null", "flight_platform": "null",
            "data_modalities": f"{(rec.get('stiTypeDetails') or 'technical report').lower()} (PDF)",
            "primary_fire_safety_use": ";".join(item["uses"]), "key_variables": "null", "key_outputs": "null",
            "license": f"NTRS {item['determination']} ({PERMITTED_DETERMINATIONS[item['determination']]})",
            "access_status": "confirmed_public", "access_url": f"{NTRS}/citations/{ntrs_id}",
            "data_access_url": item["url"], "aws_bucket": "null", "version": "null",
            "last_verified_utc": item["retrieved"], "source_date_range": _year(rec) or "null",
            "known_file_count": "1", "known_size": f"{item['pages']} pages", "ingestion_strategy": "document_first",
            "notes": notes, "provenance_requirements": "retain NTRS citation ID;hash the committed PDF;cite by page",
            "priority": "P1", "p0_candidate_reason": "null", "verification_state": "verified",
        })
        file_rows.append({
            "file_id": f"sha256:{digest[:16]}", "source_id": f"FF-NTRS-{ntrs_id}", "original_filename": item["name"],
            "remote_object_key": None, "canonical_source_url": item["url"],
            "local_path": f"../docs/research/{ntrs_id}.pdf", "content_type": "application/pdf",
            "size_bytes": len(item["data"]), "listing_size_bytes": None, "sha256": digest,
            "retrieval_timestamp_utc": item["retrieved"], "remote_last_modified_utc": None,
            "is_original": True, "parent_file_id": None,
        })
        sum_lines.append(f"{digest}  ../docs/research/{ntrs_id}.pdf\n")

    with REGISTRY.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_FIELDS, lineterminator="\n")
        writer.writerows(reg_rows)
    with FILES.open("a", encoding="utf-8") as handle:
        handle.writelines(json.dumps(row, ensure_ascii=False) + "\n" for row in file_rows)
    with CHECKSUMS.open("a", encoding="utf-8") as handle:
        handle.writelines(sum_lines)
    print(f"registered {len(reg_rows)} reports")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--discover", action="store_true", help="list candidates and their NTRS permission status")
    ap.add_argument("--dry-run", action="store_true", help="check SELECTION without writing to the repository")
    args = ap.parse_args()
    return discover() if args.discover else run(args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
