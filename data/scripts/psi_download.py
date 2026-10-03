"""Download selected NASA PSI files through the public psi.nasa.gov download API.

The API returns a short-lived signed S3 URL per file (no account needed). Files are
mirrored byte-for-byte to data/raw/psi_api/<PSI-ID>/<path inside psi-data/<PSI-ID>/>,
written to a .part file first and renamed only after the size matches the inventory.
Re-running skips complete files and resumes partial ones.

Afterwards record checksums/provenance with:
    python data/scripts/record_provenance.py <PSI-ID> <SOURCE_ID> psi_api

Usage:
    python data/scripts/psi_download.py data/manifests/psi_pilot_selection.csv [--workers 4]
"""
import argparse
import csv
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode

DATA_DIR = Path(__file__).resolve().parents[1]
RAW_ROOT = DATA_DIR / "raw" / "psi_api"
API = "https://psi.nasa.gov/geode-py/ws/studies/{psi_id}/download?"
CHUNK = 4 * 1024 * 1024
RETRIES = 4


def signed_url(row):
    query = urlencode({"file": row["file_name"], "version": row["file_version"], "redirect": "false"})
    with urllib.request.urlopen(API.format(psi_id=row["psi_id"]) + query, timeout=60) as resp:
        return resp.read().decode().strip().strip('"')


def local_path(row):
    prefix = f"psi-data/{row['psi_id']}/"
    if not row["object_key"].startswith(prefix):
        raise ValueError(f"unexpected key {row['object_key']}")
    return RAW_ROOT / row["psi_id"] / row["object_key"][len(prefix):]


def download(row):
    dest = local_path(row)
    want = int(row["size_bytes"])
    if dest.exists() and dest.stat().st_size == want:
        return "SKIP", row, want
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    for attempt in range(1, RETRIES + 1):
        try:
            have = part.stat().st_size if part.exists() else 0
            if have > want:
                part.unlink()
                have = 0
            if have < want:
                # Signed URLs expire, so fetch a fresh one on every attempt.
                req = urllib.request.Request(signed_url(row), headers={"Range": f"bytes={have}-"} if have else {})
                with urllib.request.urlopen(req, timeout=120) as resp, part.open("ab" if have else "wb") as out:
                    if have and resp.status != 206:
                        raise IOError("server ignored Range request")
                    for chunk in iter(lambda: resp.read(CHUNK), b""):
                        out.write(chunk)
            got = part.stat().st_size
            if got != want:
                raise IOError(f"size {got} != expected {want}")
            part.replace(dest)
            return "OK", row, want
        except Exception as exc:  # network errors, truncated bodies, expired URLs
            if attempt == RETRIES:
                return f"FAIL ({exc})", row, 0
            time.sleep(5 * attempt)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("selection", type=Path, help="CSV with psi_id, object_key, file_name, size_bytes, file_version")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    with args.selection.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    total = sum(int(r["size_bytes"]) for r in rows)
    print(f"{len(rows)} files, {total / 1e9:.2f} GB -> {RAW_ROOT}", flush=True)

    done_bytes, failures = 0, []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(download, r) for r in rows]
        for n, fut in enumerate(as_completed(futures), 1):
            status, row, size = fut.result()
            done_bytes += size
            if status.startswith("FAIL"):
                failures.append(row["object_key"])
            print(f"[{n}/{len(rows)}] {status:<6} {done_bytes / 1e9:6.2f} GB  {row['psi_id']}  {row['file_name']}", flush=True)

    print(f"\nDONE: {len(rows) - len(failures)}/{len(rows)} files present; {len(failures)} failed", flush=True)
    for key in failures:
        print(f"  FAILED {key}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
