# CV sample set (git-tracked)

A small, real-data sample of the microgravity imagery, so Engineer 3 (Princess) can write the **image intake spec** and develop the CV pipeline (`cv/`) without downloading GBs first. It is **for development only, not for training or evaluation**: 185 files (64.5 MB), with evenly spaced frames from each sequence.

Built by `python knowledge/ingestion/make_cv_samples.py` from the raw mirror in `datasets/raw/` (git-ignored). Every file is listed in `manifest.jsonl`.

## Contents

| Folder | Source | Frames | Original format → stored as |
|---|---|---|---|
| `FF-PSI-69/<test>/` | **FLEX** droplet combustion, 8 tests (one per fuel × diluent class) | 15 per test, 120 in total | 5 tests: BMP 640×480 RGB → lossless PNG · 3 tests (`C021H03C`, `C024M06C`, `H14H101C`): **TIFF 512×512 16-bit greyscale** → 16-bit lossless PNG |
| `FF-PSI-98/SAFFIRE_I_F2C2_jpeg/` and `…_Mapped_jpeg/` | **SAFFIRE-I** camera F2C2, raw vs distortion-mapped | 15 + 15 | JPEG, byte-for-byte copy |
| `FF-PSI-107/` | **SPICE** downlink frame grabs + flight JPEGs | 10 + 10 | PNG / JPEG, byte-for-byte copy |
| `FF-PSI-25/videos/` | **BASS-II** test videos B1, P12 (LOS portion), T25 (2nd view) | 3 videos | MP4, byte-for-byte copy |
| `FF-PSI-DSI/ACTIVITE04_HR1/`, `…_HR2_1/` | **DSI** solidification (non-combustion; plumbing tests only) | 6 + 6 | BMP 1024×1024 8-bit greyscale → lossless PNG |

All PNG conversions were checked to be **pixel-identical** to the originals (132/132, 16-bit included).

## `manifest.jsonl` fields

`sample_path`, `sha256`, `size_bytes`, `source_id`, `parent_file_id` (the raw archive's id in `datasets/metadata/files.jsonl`), `parent_local_path`, `member` (path inside the archive; nested zips are joined with `!/`), `frame_index`, `sequence_length`, `original_format`, `original_mode`, `width`, `height`, `conversion` (`byte-copy` | `lossless-png`), `created_at`.

## Things the intake spec must handle (seen in these samples)

- **Mixed bit depth:** 8-bit RGB (FLEX colour, SAFFIRE, SPICE), **16-bit greyscale** with a ~12-bit range (FLEX TIFF, max ≈ 7,600), and 8-bit greyscale (DSI). Don't assume RGB uint8.
- **Distortion-mapped vs raw** frames for the same SAFFIRE camera.
- **Video** input (BASS-II MP4); frame extraction needs ffmpeg or OpenCV.
- Frame order is the sorted member name. `frame_index`/`sequence_length` give each frame's position in the original sequence.

## Getting the full data

The full pilot (3.1 GB) and the DSI run are not in Git. Rebuild them with the commands in the root `README.md` (`knowledge/ingestion/psi_download.py` + `record_provenance.py`). The file list is in `datasets/manifests/psi_pilot_selection.csv`.

**Rules:** split by **test**, never by frame (MVP plan §18). Never infer temperature from pixel values without calibration (MVP plan §10).
