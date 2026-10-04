"""Build the small, git-tracked CV sample set from the mirrored raw data.

Raw archives stay untouched in datasets/raw/ (git-ignored, several > 100 MB). This picks
evenly spaced frames from each image sequence so the CV team has real frames in Git for
the image-intake spec and pipeline development. It is NOT a training set.

  - FLEX BMP (RGB) and TIFF (16-bit mono) frames -> lossless PNG (bit depth preserved)
  - SAFFIRE-I / SPICE JPEG and PNG frames         -> byte-for-byte copies
  - DSI 8-bit BMP frames (nested zips)             -> lossless PNG
  - the smallest BASS-II test videos               -> byte-for-byte copies

Every sample is recorded in datasets/samples/cv/manifest.jsonl with its sha256 and the
file_id of the raw parent from datasets/metadata/files.jsonl (DAY1_DATA_ACQUISITION.md section 3).

Usage:
    python knowledge/ingestion/make_cv_samples.py
"""
import hashlib
import io
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from PIL import Image

DATA_DIR = Path(__file__).resolve().parents[2] / "datasets"
RAW = DATA_DIR / "raw"
OUT = DATA_DIR / "samples" / "cv"
FILES_JSONL = DATA_DIR / "metadata" / "files.jsonl"
IMAGE_EXT = (".bmp", ".tif", ".tiff", ".jpg", ".jpeg", ".png")
COPY_EXT = (".jpg", ".jpeg", ".png")   # already compact; keep the original bytes

# (source_id, archive path relative to datasets/raw, frames to take)
SEQUENCES = [
    *[("FF-PSI-69", f"psi_api/PSI-69/Raw Data/PSI-69_Raw Data_{name}.zip", 15)
      for name in ("176F001D", "195F002D", "C021H03C", "C024M06C",
                   "H08M101D", "H14H101C", "X168M03D", "X177H10D")],
    ("FF-PSI-98", "psi_api/PSI-98/Raw Data/PSI-98_Raw Data_SAFFIRE_I_F2C2_jpeg.zip", 15),
    ("FF-PSI-98", "psi_api/PSI-98/Raw Data/PSI-98_Raw Data_SAFFIRE_I_F2C2_Mapped_jpeg.zip", 15),
    ("FF-PSI-107", "psi_api/PSI-107/Raw Data/PSI-107_Raw Data_Downlink Frame Grabs 36f.zip", 10),
    ("FF-PSI-107", "psi_api/PSI-107/Raw Data/PSI-107_Raw Data_SPICE GMT045 2009 jpegs.zip", 10),
]
# DSI: frames live in inner zips inside the stored outer zip.
DSI_OUTER = "nasa_psi/DSI/Data/S1 activity 4.zip"
DSI_INNER = ["S1 activity 4/DA_TC_DSI_SEQ2_ACTIVITE04_HR1.zip",
             "S1 activity 4/DA_TC_DSI_SEQ2_ACTIVITE04_HR2_1.zip"]
DSI_FRAMES = 6
VIDEOS = [
    ("FF-PSI-25", "psi_api/PSI-25/Raw Data/PSI-25_Raw Data_BASS_GMT50_SAMPLE_147_TEST_B1.mp4"),
    ("FF-PSI-25", "psi_api/PSI-25/Raw Data/PSI-25_Raw Data_BASS_GMT210_SAMPLE_199_TEST_P12_LOS_Portion_1132-1133.mp4"),
    ("FF-PSI-25", "psi_api/PSI-25/Raw Data/PSI-25_Raw Data_BASS_GMT216_SAMPLE_138_TEST_T25_2ND_VIEW.mp4"),
]


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def evenly_spaced(items, k):
    """Deterministic pick of k items spread from first to last."""
    if len(items) <= k:
        return list(enumerate(items))
    idx = sorted({round(i * (len(items) - 1) / (k - 1)) for i in range(k)})
    return [(i, items[i]) for i in idx]


def short_name(archive_rel):
    stem = PurePosixPath(archive_rel).stem
    for prefix in ("PSI-69_Raw Data_", "PSI-98_Raw Data_", "PSI-107_Raw Data_", "PSI-25_Raw Data_",
                   "DA_TC_DSI_SEQ2_"):
        stem = stem.replace(prefix, "")
    return stem.replace(" ", "_")


def save_frame(data, member, dest_dir):
    """Write one frame; returns (stored_path, conversion, image info)."""
    im = Image.open(io.BytesIO(data))
    info = {"original_format": im.format, "original_mode": im.mode, "width": im.width, "height": im.height}
    name = PurePosixPath(member).name
    if name.lower().endswith(COPY_EXT):
        dest = dest_dir / name
        dest.write_bytes(data)
        return dest, "byte-copy", info
    dest = dest_dir / (PurePosixPath(name).stem + ".png")
    im.save(dest, format="PNG", optimize=True)   # PNG keeps RGB and 16-bit greyscale losslessly
    return dest, "lossless-png", info


def main():
    parents = {}
    for line in FILES_JSONL.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        parents[rec["local_path"]] = rec["file_id"]

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records = []

    def record(source_id, parent_rel, member, frame_index, seq_len, dest, conversion, info):
        records.append({
            "sample_path": dest.relative_to(OUT).as_posix(),
            "sha256": sha256_bytes(dest.read_bytes()),
            "size_bytes": dest.stat().st_size,
            "source_id": source_id,
            "parent_file_id": parents.get(f"raw/{parent_rel}"),
            "parent_local_path": f"raw/{parent_rel}",
            "member": member,
            "frame_index": frame_index,
            "sequence_length": seq_len,
            **info,
            "conversion": conversion,
            "created_at": created,
        })

    for source_id, rel, k in SEQUENCES:
        with zipfile.ZipFile(RAW / rel) as zf:
            frames = sorted(n for n in zf.namelist() if n.lower().endswith(IMAGE_EXT))
            dest_dir = OUT / source_id / short_name(rel)
            dest_dir.mkdir(parents=True, exist_ok=True)
            for i, member in evenly_spaced(frames, k):
                dest, conv, info = save_frame(zf.read(member), member, dest_dir)
                record(source_id, rel, member, i, len(frames), dest, conv, info)

    with zipfile.ZipFile(RAW / DSI_OUTER) as outer:
        for inner_name in DSI_INNER:
            with zipfile.ZipFile(outer.open(inner_name)) as inner:
                frames = sorted(n for n in inner.namelist() if n.lower().endswith(IMAGE_EXT))
                dest_dir = OUT / "FF-PSI-DSI" / short_name(inner_name)
                dest_dir.mkdir(parents=True, exist_ok=True)
                for i, member in evenly_spaced(frames, DSI_FRAMES):
                    dest, conv, info = save_frame(inner.read(member), member, dest_dir)
                    record("FF-PSI-DSI", DSI_OUTER, f"{inner_name}!/{member}", i, len(frames), dest, conv, info)

    for source_id, rel in VIDEOS:
        src = RAW / rel
        dest_dir = OUT / source_id / "videos"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        shutil.copyfile(src, dest)
        record(source_id, rel, None, None, None, dest, "byte-copy",
               {"original_format": "MP4", "original_mode": None, "width": None, "height": None})

    with (OUT / "manifest.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")

    total = sum(r["size_bytes"] for r in records)
    missing = sum(1 for r in records if r["parent_file_id"] is None)
    biggest = max(records, key=lambda r: r["size_bytes"])
    print(f"{len(records)} samples, {total / 1e6:.1f} MB -> {OUT}")
    print(f"largest file: {biggest['size_bytes'] / 1e6:.1f} MB ({biggest['sample_path']})")
    print(f"samples without a parent_file_id: {missing}")


if __name__ == "__main__":
    main()
