"""Inventory every file of NASA PSI combustion investigations through the public psi.nasa.gov API.

The Space Apps "Flame in Freefall" resources page points at the PSI repository search for
"combustion". This script lists those investigations (or the IDs you pass), finds each study's latest
version, and writes one CSV row per file in the same columns as
datasets/manifests/psi_combustion_file_inventory.csv, so the rows feed straight into psi_download.py.

No account is needed. Nothing is downloaded except the JSON file listings.

Usage:
    python knowledge/ingestion/psi_inventory.py
    python knowledge/ingestion/psi_inventory.py --ids PSI-26 PSI-102 --out some.csv
    python knowledge/ingestion/psi_inventory.py --select datasets/manifests/psi_docs_tables_selection.csv
        (offline: experimental tables + ISA-Tab metadata + document PDFs, the input for psi_download.py)
"""
import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

BASE = "https://psi.nasa.gov/geode-py/ws"
FIELDS = ["source_id", "psi_id", "object_key", "file_name", "size_bytes", "category", "subcategory",
          "file_version", "updated", "restricted"]
INVESTIGATION_FIELDS = ["psi_id", "source_id", "acronym", "title", "project_type", "sub_research_area",
                        "flight_platform", "related_investigations", "public_release_epoch", "study_version",
                        "doi", "license", "experimental_tables", "file_count", "total_bytes"]
MAX_STUDY_VERSION = 20
RETRIES = 4
SEARCH_SIZE = 500


def _open(req, timeout: int):
    """urlopen with retries for network errors (DNS blips, resets); HTTP errors are raised at once."""
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == RETRIES:
                raise
            time.sleep(5 * attempt)


def _get(url: str):
    return _open(url, 60)


def _post(url: str, body: dict):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return _open(req, 180)


def search(term: str = "combustion") -> dict[str, dict]:
    """Every PSI investigation the repository search returns for `term`, keyed by accession (PSI-nn)."""
    # The endpoint ignores `page` (it returns the first 25 again) but honours `size`.
    query = urlencode({"term": term, "source": "psi", "type": "investigation", "size": SEARCH_SIZE})
    hits = _get(f"{BASE}/repo/search?{query}")["hits"]
    found = {hit["_source"]["Accession"]: hit["_source"] for hit in hits["hits"]}
    total = hits["total"]["value"] if isinstance(hits["total"], dict) else hits["total"]
    if len(found) < total:
        raise RuntimeError(f"search returned {len(found)} of {total} investigations; raise SEARCH_SIZE")
    return found


def file_tree(psi_id: str, version: int) -> dict | None:
    body = {"folder": f"psi-data/{psi_id}/", "fileType": "study", "studyId": psi_id, "version": version,
            "obfuscationcode": ""}
    try:
        data = _post(f"{BASE}/files/v2", body)
    except urllib.error.HTTPError as exc:   # "Study Version not found" comes back as 404
        if exc.code == 404:
            return None
        raise
    return data if "files" in data else None


def landing(psi_id: str) -> dict:
    """The investigation's landing-page record: current `version`, `doi`, `totalFileSize`, license, tables."""
    return _get(f"{BASE}/repo/investigations/{psi_id}")


def latest_tree(psi_id: str, version: int | None = None) -> tuple[int, dict]:
    """The file tree of the current study version (from the landing record, else the highest that exists)."""
    if version:
        tree = file_tree(psi_id, version)
        if tree is not None:
            return version, tree
    best: tuple[int, dict] | None = None
    for candidate in range(1, MAX_STUDY_VERSION + 1):
        tree = file_tree(psi_id, candidate)
        if tree is None:
            if best:
                return best
            continue
        best = (candidate, tree)
    if best is None:
        raise LookupError(f"{psi_id}: no study version found")
    return best


def leaves(node: dict, folder: str = ""):
    """(leaf, folder key) pairs. File names can contain '/', so the name is the key minus its folder, not its last part."""
    for child in node["files"]:
        if child.get("directory") or child["files"]:
            yield from leaves(child, child.get("key") or folder)
        else:
            yield child, folder


def rows_for(psi_id: str, source_id: str, tree: dict) -> list[dict]:
    rows, seen = [], set()
    for leaf, folder in leaves(tree):
        key = leaf["key"]
        if leaf.get("status", "active") != "active" or key in seen:   # PSI lists some files twice
            continue
        seen.add(key)
        name = key[len(folder):] if folder and key.startswith(folder) else key.rsplit("/", 1)[-1]
        rows.append({
            "source_id": source_id,
            "psi_id": psi_id,
            "object_key": key,
            "file_name": name,
            "size_bytes": int(leaf["bytes_size"]),
            "category": leaf.get("sortingCategory") or "",
            "subcategory": leaf.get("subcategory") or "",
            "file_version": leaf["version"],
            "updated": leaf.get("updated") or "",
            "restricted": bool(leaf.get("restricted") or leaf.get("restrictedAccess")),
        })
    return rows


DOCUMENT_CATEGORIES = {"engineering documents", "presentations", "reports", "science documents", "reference data"}


def selection_reason(row: dict) -> str | None:
    """What the ingestion pipeline can parse, without the media: experimental tables, ISA-Tab metadata, document PDFs.

    'Raw Data' PDFs are per-test data sheets (hundreds per investigation), not documents, so they are left out."""
    category = (row["category"] or "").strip().lower()
    suffix = row["file_name"].rsplit(".", 1)[-1].lower()
    if category == "experimental table" and suffix == "csv":
        return "experimental table"
    if category == "investigation metadata files" and suffix == "zip":
        return "ISA-Tab metadata"
    if category in DOCUMENT_CATEGORIES and suffix == "pdf":
        return "document pdf"
    return None


def select(inventory: Path, out: Path, ids: list[str] | None = None) -> None:
    with inventory.open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if not ids or r["psi_id"] in ids]
    chosen = []
    for row in rows:
        reason = selection_reason(row)
        if reason and row["restricted"] != "True":
            chosen.append({**row, "reason": reason})
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS + ["reason"])
        writer.writeheader()
        writer.writerows(chosen)
    size = sum(int(r["size_bytes"]) for r in chosen)
    print(f"{len(chosen)} of {len(rows)} files selected, {size / 1e9:.2f} GB -> {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--select", type=Path, metavar="SELECTION_CSV",
                    help="don't query PSI; write the tables+metadata+document-PDF selection from --out's inventory")
    ap.add_argument("--ids", nargs="*", help="PSI accessions (default: everything the 'combustion' search returns)")
    ap.add_argument("--term", default="combustion")
    ap.add_argument("--out", type=Path, default=Path("datasets/manifests/psi_all_combustion_inventory.csv"))
    ap.add_argument("--investigations", type=Path, default=Path("datasets/manifests/psi_combustion_investigations.csv"),
                    help="also write one summary row per investigation here")
    args = ap.parse_args()
    if args.select:
        select(args.out, args.select, args.ids)
        return 0

    found = search(args.term)
    ids = args.ids or sorted(found, key=lambda a: int(a.split("-")[1]))
    all_rows, summaries = [], []
    for psi_id in ids:
        meta = found.get(psi_id, {})
        source_id = f"FF-{psi_id}"
        page = landing(psi_id)
        version, tree = latest_tree(psi_id, page.get("version"))
        rows = rows_for(psi_id, source_id, tree)
        all_rows.extend(rows)
        total = sum(r["size_bytes"] for r in rows)
        summaries.append({
            "psi_id": psi_id, "source_id": source_id,
            "acronym": meta.get("Acronym") or page.get("investigationAcronym") or "",
            "title": meta.get("Title") or page.get("title") or "", "project_type": meta.get("Project Type", ""),
            "sub_research_area": meta.get("SubResearch Area", ""), "flight_platform": meta.get("Flight Platform", ""),
            "related_investigations": " ".join((meta.get("Related Investigations") or "").split()),
            "public_release_epoch": meta.get("Public Release Date", ""), "study_version": version,
            "doi": f"doi:{page['doi']}" if page.get("doi") else "", "license": page.get("licenseIdentifier") or "",
            "experimental_tables": len(page.get("experimentalTable") or []),
            "file_count": len(rows), "total_bytes": total,
        })
        print(f"{psi_id:<8} v{version:<2} {len(rows):>6} files {total / 1e9:9.2f} GB  {meta.get('Acronym', '')}", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)
    with args.investigations.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=INVESTIGATION_FIELDS)
        writer.writeheader()
        writer.writerows(summaries)
    grand = sum(r["size_bytes"] for r in all_rows)
    print(f"\n{len(ids)} investigations, {len(all_rows)} files, {grand / 1e9:.1f} GB -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
