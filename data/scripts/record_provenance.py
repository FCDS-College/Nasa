"""Record provenance + SHA-256 checksums for mirrored NASA PSI files.

Implements DAY1_DATA_ACQUISITION.md section 3 (per-object provenance) and the
section 8 checksum criterion. Original files are only read, never modified.

Two mirror layouts are supported:
  s3       data/raw/nasa_psi/<INVESTIGATION>/...   from the public s3://nasa-psi bucket,
           sizes checked against manifests/nasa_psi_full_listing.txt
  psi_api  data/raw/psi_api/<PSI-ID>/...           from the psi.nasa.gov download API
           (data/scripts/psi_download.py), sizes checked against
           manifests/psi_combustion_file_inventory.csv

Usage:
    python data/scripts/record_provenance.py INVESTIGATION SOURCE_ID [s3|psi_api]
    python data/scripts/record_provenance.py DSI FF-PSI-DSI
    python data/scripts/record_provenance.py PSI-25 FF-PSI-25 psi_api
"""
import csv
import hashlib
import json
import mimetypes
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode

DATA_DIR = Path(__file__).resolve().parents[1]
RAW_DIRS = {"s3": DATA_DIR / "raw" / "nasa_psi", "psi_api": DATA_DIR / "raw" / "psi_api"}
LISTING = DATA_DIR / "manifests" / "nasa_psi_full_listing.txt"
INVENTORY = DATA_DIR / "manifests" / "psi_combustion_file_inventory.csv"
CHECKSUMS = DATA_DIR / "checksums" / "sha256.txt"
METADATA = DATA_DIR / "metadata" / "files.jsonl"
BUCKET = "nasa-psi"
PSI_DOWNLOAD_API = "https://psi.nasa.gov/geode-py/ws/studies/{psi_id}/download?"
LISTING_LINE = re.compile(r"^\S+ \S+\s+(\d+)\s+(.+)$")


def load_listing(prefix):
    """s3 layout: map 'DSI/...' object key -> {size}, from the `aws s3 ls --recursive` dump."""
    if not LISTING.exists():
        return {}
    raw = LISTING.read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    objects = {}
    for line in text.splitlines():
        m = LISTING_LINE.match(line.strip())
        if m and m.group(2).startswith(prefix + "/"):
            objects[m.group(2)] = {"size": int(m.group(1))}
    return objects


def load_inventory(psi_id):
    """psi_api layout: map 'psi-data/PSI-25/...' object key -> {size, version, updated}."""
    if not INVENTORY.exists():
        return {}
    objects = {}
    with INVENTORY.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["psi_id"] == psi_id:
                objects[row["object_key"]] = {"size": int(row["size_bytes"]),
                                              "version": row["file_version"],
                                              "updated": row["updated"]}
    return objects


def sha256_of(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iso_utc(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    investigation = sys.argv[1] if len(sys.argv) > 1 else "DSI"
    source_id = sys.argv[2] if len(sys.argv) > 2 else f"FF-PSI-{investigation}"
    layout = sys.argv[3] if len(sys.argv) > 3 else "s3"
    if layout not in RAW_DIRS:
        sys.exit(f"Unknown layout {layout!r}; use one of {sorted(RAW_DIRS)}")
    local_root = RAW_DIRS[layout] / investigation
    if not local_root.is_dir():
        sys.exit(f"No mirrored files at {local_root}")

    if layout == "s3":
        expected = load_listing(investigation)
        key_prefix = f"{investigation}/"
    else:
        expected = load_inventory(investigation)
        key_prefix = f"psi-data/{investigation}/"
    # Skip in-progress downloads written by psi_download.py.
    files = sorted(p for p in local_root.rglob("*") if p.is_file() and not p.name.endswith(".part"))

    # Keep records for other investigations; replace this one's.
    local_prefix = f"{RAW_DIRS[layout].relative_to(DATA_DIR).as_posix()}/{investigation}/"
    keep_sums, keep_meta = [], []
    if CHECKSUMS.exists():
        keep_sums = [l for l in CHECKSUMS.read_text(encoding="utf-8").splitlines()
                     if l and local_prefix not in l]
    if METADATA.exists():
        keep_meta = [l for l in METADATA.read_text(encoding="utf-8").splitlines()
                     if l and json.loads(l)["source_id"] != source_id]

    recorded_at = iso_utc(datetime.now(timezone.utc))
    sums, meta, mismatches, unlisted = [], [], [], []
    for path in files:
        key = key_prefix + path.relative_to(local_root).as_posix()
        obj = expected.get(key)
        size = path.stat().st_size
        if obj is None:
            unlisted.append(key)
        elif obj["size"] != size:
            mismatches.append((key, obj["size"], size))
        if layout == "s3":
            source_url = f"s3://{BUCKET}/{key}"
            # aws s3 cp sets mtime to the object's S3 LastModified, not the download time.
            remote_modified = iso_utc(datetime.fromtimestamp(path.stat().st_mtime, timezone.utc))
        else:
            version = obj["version"] if obj else ""
            source_url = PSI_DOWNLOAD_API.format(psi_id=investigation) + urlencode(
                {"file": path.name, "version": version})
            remote_modified = iso_utc(parsedate_to_datetime(obj["updated"])) if obj and obj["updated"] else None
        digest = sha256_of(path)
        rel = path.relative_to(DATA_DIR).as_posix()
        sums.append(f"{digest}  {rel}")
        meta.append(json.dumps({
            "file_id": f"sha256:{digest[:16]}",
            "source_id": source_id,
            "original_filename": path.name,
            "remote_object_key": key,
            "canonical_source_url": source_url,
            "local_path": rel,
            "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "size_bytes": size,
            "listing_size_bytes": obj["size"] if obj else None,
            "sha256": digest,
            "retrieval_timestamp_utc": recorded_at,
            "remote_last_modified_utc": remote_modified,
            "is_original": True,
            "parent_file_id": None,
        }))
        print(f"{digest[:12]}  {size:>14,}  {key}")

    CHECKSUMS.parent.mkdir(parents=True, exist_ok=True)
    METADATA.parent.mkdir(parents=True, exist_ok=True)
    # LF endings: on Windows, CRLF makes `sha256sum -c` read "\r" as part of the path.
    CHECKSUMS.write_text("\n".join(keep_sums + sums) + "\n", encoding="utf-8", newline="\n")
    METADATA.write_text("\n".join(keep_meta + meta) + "\n", encoding="utf-8", newline="\n")

    print(f"\n{len(files)} files recorded for {source_id}; "
          f"{len(unlisted)} not in listing; {len(mismatches)} size mismatches")
    for key in unlisted:
        print(f"  UNLISTED {key}")
    for key, want, got in mismatches:
        print(f"  MISMATCH {key}: listing={want} local={got}")
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
