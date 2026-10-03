"""Record provenance + SHA-256 checksums for files mirrored from s3://nasa-psi.

Implements DAY1_DATA_ACQUISITION.md section 3 (per-object provenance) and the
section 8 checksum criterion. Original files are only read, never modified.

Usage:
    python data/scripts/record_provenance.py [INVESTIGATION] [SOURCE_ID]
    python data/scripts/record_provenance.py DSI FF-PSI-DSI
"""
import hashlib
import json
import mimetypes
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1]
RAW_ROOT = DATA_DIR / "raw" / "nasa_psi"
LISTING = DATA_DIR / "manifests" / "nasa_psi_full_listing.txt"
CHECKSUMS = DATA_DIR / "checksums" / "sha256.txt"
METADATA = DATA_DIR / "metadata" / "files.jsonl"
BUCKET = "nasa-psi"
LISTING_LINE = re.compile(r"^\S+ \S+\s+(\d+)\s+(.+)$")


def load_listing_sizes(prefix):
    """Map remote object key -> size_bytes from the `aws s3 ls --recursive` dump."""
    if not LISTING.exists():
        return {}
    raw = LISTING.read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    sizes = {}
    for line in text.splitlines():
        m = LISTING_LINE.match(line.strip())
        if m and m.group(2).startswith(prefix + "/"):
            sizes[m.group(2)] = int(m.group(1))
    return sizes


def sha256_of(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    investigation = sys.argv[1] if len(sys.argv) > 1 else "DSI"
    source_id = sys.argv[2] if len(sys.argv) > 2 else f"FF-PSI-{investigation}"
    local_root = RAW_ROOT / investigation
    if not local_root.is_dir():
        sys.exit(f"No mirrored files at {local_root}")

    expected = load_listing_sizes(investigation)
    files = sorted(p for p in local_root.rglob("*") if p.is_file())

    # Keep records for other investigations; replace this one's.
    keep_sums, keep_meta = [], []
    if CHECKSUMS.exists():
        keep_sums = [l for l in CHECKSUMS.read_text(encoding="utf-8").splitlines()
                     if l and f"raw/nasa_psi/{investigation}/" not in l]
    if METADATA.exists():
        keep_meta = [l for l in METADATA.read_text(encoding="utf-8").splitlines()
                     if l and json.loads(l)["source_id"] != source_id]

    recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sums, meta, mismatches, unlisted = [], [], [], []
    for path in files:
        key = f"{investigation}/{path.relative_to(local_root).as_posix()}"
        size = path.stat().st_size
        if key not in expected:
            unlisted.append(key)
        elif expected[key] != size:
            mismatches.append((key, expected[key], size))
        digest = sha256_of(path)
        rel = path.relative_to(DATA_DIR).as_posix()
        sums.append(f"{digest}  {rel}")
        meta.append(json.dumps({
            "file_id": f"sha256:{digest[:16]}",
            "source_id": source_id,
            "original_filename": path.name,
            "remote_object_key": key,
            "canonical_source_url": f"s3://{BUCKET}/{key}",
            "local_path": rel,
            "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "size_bytes": size,
            "listing_size_bytes": expected.get(key),
            "sha256": digest,
            "retrieval_timestamp_utc": recorded_at,
            # aws s3 cp sets mtime to the object's S3 LastModified, not the download time.
            "remote_last_modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
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
