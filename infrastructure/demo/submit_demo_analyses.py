"""Submit the demo analyses (committed NASA media) to a running Flame API and wait for them.

    FLAME_API_ORIGIN=http://localhost:8000 FLAME_WRITE_API_TOKEN=... python infrastructure/demo/submit_demo_analyses.py

Uses only files already in the repository (CC0 NASA PSI samples, provenance in
datasets/samples/cv/manifest.jsonl): one BASS-II flight video and two SPICE ISS flame photographs.
Idempotent: the Idempotency-Key is derived from the file, so re-running returns the same analyses.
Stdlib only, so it runs anywhere Python does.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "datasets" / "samples" / "cv"
DEMO = [
    ("video", SAMPLES / "FF-PSI-25" / "videos" / "PSI-25_Raw Data_BASS_GMT50_SAMPLE_147_TEST_B1.mp4",
     {"sample_every_n_frames": "15", "max_frames": "120"}),
    ("image", SAMPLES / "FF-PSI-107" / "SPICE_GMT045_2009_jpegs" / "ISS018E030336.jpg", {}),
    ("image", SAMPLES / "FF-PSI-107" / "SPICE_GMT045_2009_jpegs" / "ISS018E030368.jpg", {}),
]


def _multipart(field: str, path: Path, extra: dict[str, str]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in extra.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{path.name}"\r\n'
                 f"Content-Type: {media}\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _request(url: str, token: str, data: bytes | None = None, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers={"Authorization": f"Bearer {token}", **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def main() -> int:
    origin = os.environ.get("FLAME_API_ORIGIN", "http://localhost:8000").rstrip("/")
    write = os.environ.get("FLAME_WRITE_API_TOKEN")
    read = os.environ.get("FLAME_READ_API_TOKEN", write)
    if not write:
        print("Set FLAME_WRITE_API_TOKEN (a write-scoped key).", file=sys.stderr)
        return 2
    ids = []
    for field, path, extra in DEMO:
        body, content_type = _multipart(field, path, extra)
        key = f"demo-{hashlib.sha256(path.read_bytes()).hexdigest()[:24]}"
        try:
            created = _request(f"{origin}/api/analyses", write, body, {"Content-Type": content_type, "Idempotency-Key": key})
        except urllib.error.HTTPError as exc:
            print(f"{path.name}: HTTP {exc.code} {exc.read()[:300]!r}", file=sys.stderr)
            return 1
        analysis_id = created["analysis"]["analysis_id"]
        ids.append((analysis_id, path.name))
        print(f"submitted {field} {path.name} -> {analysis_id}")
    deadline = time.time() + 900
    pending = dict(ids)
    while pending and time.time() < deadline:
        for analysis_id in list(pending):
            status = _request(f"{origin}/api/analyses/{analysis_id}", read)["analysis"]["status"]
            if status in {"completed", "failed"}:
                print(f"{status:9s} {pending.pop(analysis_id)} ({analysis_id})")
        time.sleep(3)
    if pending:
        print(f"still running after 15 min: {list(pending.values())}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
