"""Install the project's NASA datasets into datasets/raw/ and verify them.

Raw data is git-ignored, so a fresh clone has none. This script rebuilds it:

  DSI (solidification)   public s3://nasa-psi bucket, fetched over anonymous HTTPS
  Combustion pilot       BASS-II / FLEX / SAFFIRE-I / SPICE via the psi.nasa.gov API
                         (reuses psi_download.py and datasets/manifests/psi_pilot_selection.csv)

Every file is then checked against datasets/checksums/sha256.txt. Re-running skips
complete files and resumes partial ones, so it is safe to interrupt.

Usage:
    python knowledge/ingestion/install_datasets.py                  # everything (~6 GB)
    python knowledge/ingestion/install_datasets.py --skip-large     # skip files > 1 GB (DSI "S1 activity 4.zip")
    python knowledge/ingestion/install_datasets.py --only dsi       # or: --only combustion
    python knowledge/ingestion/install_datasets.py --only tables    # just the PSI experimental tables + metadata (~140 KB)

The experimental tables and investigation metadata are also committed (CC0, ~140 KB), so a fresh
clone can ingest every flight test without downloading anything; --only tables re-fetches them.
    python knowledge/ingestion/install_datasets.py --verify-only    # no downloads, just check hashes
"""
import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import psi_download  # noqa: E402

DATA_DIR = HERE.parents[1] / "datasets"
METADATA = DATA_DIR / "metadata" / "files.jsonl"
CHECKSUMS = DATA_DIR / "checksums" / "sha256.txt"
PILOT = DATA_DIR / "manifests" / "psi_pilot_selection.csv"
S3_URL = "https://nasa-psi.s3.amazonaws.com/{key}"
LARGE = 1_000_000_000
CHUNK = 4 * 1024 * 1024
RETRIES = 4


def dsi_records():
    with METADATA.open(encoding="utf-8") as fh:
        records = [json.loads(line) for line in fh if line.strip()]
    return [r for r in records if r["local_path"].startswith("raw/nasa_psi/") and r["is_original"]]


def fetch_s3(rec):
    dest = DATA_DIR / rec["local_path"]
    want = int(rec["size_bytes"])
    if dest.exists() and dest.stat().st_size == want:
        return "SKIP", rec, want
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    url = S3_URL.format(key=quote(rec["remote_object_key"]))
    for attempt in range(1, RETRIES + 1):
        try:
            have = part.stat().st_size if part.exists() else 0
            if have > want:
                part.unlink()
                have = 0
            if have < want:
                req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
                with urllib.request.urlopen(req, timeout=120) as resp, part.open("ab" if have else "wb") as out:
                    if have and resp.status != 206:
                        raise IOError("server ignored Range request")
                    for chunk in iter(lambda: resp.read(CHUNK), b""):
                        out.write(chunk)
            got = part.stat().st_size
            if got != want:
                raise IOError(f"size {got} != expected {want}")
            part.replace(dest)
            return "OK", rec, want
        except Exception as exc:  # network errors, truncated bodies
            if attempt == RETRIES:
                return f"FAIL ({exc})", rec, 0
            time.sleep(5 * attempt)


def run_pool(label, items, fn, name_of, workers):
    done, failures = 0, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fn, i) for i in items]
        for n, fut in enumerate(as_completed(futures), 1):
            status, item, size = fut.result()
            done += size
            if status.startswith("FAIL"):
                failures.append(name_of(item))
            print(f"[{label} {n}/{len(items)}] {status:<6} {done / 1e9:6.2f} GB  {name_of(item)}", flush=True)
    return failures


def install_dsi(skip_large, workers):
    recs = dsi_records()
    if skip_large:
        recs = [r for r in recs if int(r["size_bytes"]) < LARGE]
    print(f"DSI: {len(recs)} files, {sum(int(r['size_bytes']) for r in recs) / 1e9:.2f} GB", flush=True)
    return run_pool("dsi", recs, fetch_s3, lambda r: r["remote_object_key"], workers)


def is_table_or_metadata(row):
    """The small, committed PSI files: experimental tables (CSV) and ISA-Tab metadata zips."""
    key = row["object_key"]
    return "/Experimental table/" in key or "/metadata/" in key


def install_combustion(skip_large, workers, tables_only=False):
    with PILOT.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if tables_only:
        rows = [r for r in rows if is_table_or_metadata(r)]
    if skip_large:
        rows = [r for r in rows if int(r["size_bytes"]) < LARGE]
    print(f"Combustion: {len(rows)} files, {sum(int(r['size_bytes']) for r in rows) / 1e9:.2f} GB", flush=True)
    return run_pool("psi", rows, psi_download.download, lambda r: r["object_key"], workers)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def verify():
    """Compare files on disk with sha256.txt. Missing files are reported, not fatal."""
    ok = bad = missing = 0
    for line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(None, 1)
        path = DATA_DIR / rel.strip().lstrip("*")
        if not path.exists():
            missing += 1
        elif sha256(path) == digest:
            ok += 1
        else:
            bad += 1
            print(f"  HASH MISMATCH {rel}")
    print(f"Verify: {ok} ok, {bad} mismatched, {missing} not installed", flush=True)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", choices=["dsi", "combustion", "tables"], help="install just one dataset group")
    ap.add_argument("--skip-large", action="store_true", help="skip files over 1 GB")
    ap.add_argument("--verify-only", action="store_true", help="check hashes, download nothing")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    failures = []
    if not args.verify_only:
        if args.only in (None, "dsi"):
            failures += install_dsi(args.skip_large, args.workers)
        if args.only in (None, "combustion"):
            failures += install_combustion(args.skip_large, args.workers)
        if args.only == "tables":
            failures += install_combustion(args.skip_large, args.workers, tables_only=True)
    bad = verify()

    if failures:
        print(f"\n{len(failures)} download(s) failed:")
        for f in failures:
            print(f"  {f}")
        print("(Known: 3 combustion docs 404 on NASA's side for every version; see docs/data/CV_IMAGE_SOURCES.md)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
