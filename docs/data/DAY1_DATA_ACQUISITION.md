# Flame in Freefall — Day 1 Dataset Acquisition Specification

## 1. Canonical data source

Use NASA Physical Sciences Informatics (PSI) as the canonical source registry backbone.

- PSI repository: https://psi.nasa.gov/physci/repo
- Public AWS bucket: `s3://nasa-psi/`
- AWS region: `us-west-2`
- Anonymous CLI access is documented by NASA/AWS: `aws s3 ls --no-sign-request s3://nasa-psi/`
- PSI registry/license note: NASA's AWS Open Data listing states the PSI data are public and unrestricted for use. citeturn595254search1

## 2. Datasets selected for Day 1

| source_id | NASA source | Canonical ID | Evidence | Day-1 role |
|---|---|---|---|---|
| FF-PSI-25 | Burning and Suppression of Solids-II | PSI-25 / DOI 10.60555/4qc4-de67 | NASA PSI landing page | Primary vertical slice: solid flame spread/extinction |
| FF-PSI-69 | Flame Extinguishment Experiment | PSI-69 / DOI 10.60555/mbq8-0451 | NASA PSI landing page | Primary vertical slice: liquid droplets/extinction |
| FF-PSI-98 | Spacecraft Fire Safety Experiment-I | PSI-98 / DOI 10.60555/0t15-1z43 | NASA PSI landing page | Large-scale fire/sensor evidence |
| FF-PSI-107 | Smoke Point in Co-flow Experiment | PSI-107 / DOI 10.60555/9kbh-e962 | NASA PSI landing page | Soot/smoke/flame-length evidence |

## 3. Acquisition policy

The team should **mirror source files rather than mutate them**.

For every downloaded object, persist:

```text
original_filename
source_id
canonical_source_url
PSI_D​​OI (when available)
remote_object_key
retrieval_timestamp_utc
content_type
size_bytes
sha256
```

Source data must remain immutable. Any normalization, OCR, frame extraction, CSV conversion, or unit normalization creates a new derived artifact with a parent `source_file_id`.

## 4. Suggested first-pass materialization

Do not mirror the full repository for the hackathon MVP. First materialize:

- metadata package for each P0 source;
- experimental tables, where present;
- 3–5 representative videos/images per source family;
- supporting experiment summary/report files;
- file manifests and checksums.

For BASS-II, NASA PSI currently reports 694 files added in Version 4, including raw MP4 data and an explicit metadata ZIP; this is too large for an uncontrolled Day-1 ingest, so the first pull should be manifest-first. citeturn311459search1

For SPICE, NASA PSI reports 6.47 GB for the investigation, again favoring manifest-first acquisition. citeturn373787search1

## 5. CLI bootstrap

```bash
mkdir -p datasets/raw/psi datasets/manifests datasets/derived

aws s3 ls --no-sign-request s3://nasa-psi/ > datasets/manifests/nasa_psi_root_listing.txt

# After discovering the canonical object prefix from the PSI manifest:
# aws s3 ls --no-sign-request s3://nasa-psi/<prefix>/ --recursive > datasets/manifests/<source_id>.listing.txt
# aws s3 cp --no-sign-request s3://nasa-psi/<object-key> datasets/raw/psi/<source_id>/
```

### Important

The current web pass verified the public bucket and the source landing pages, but it did **not** recover the exact S3 object prefixes for each PSI investigation. Therefore the repository should discover and record those keys from the bucket manifest rather than guessing URL paths.

## 6. File-class ingestion rules

### Metadata / ISA ZIP

Parse into:

- investigation metadata
- experiment metadata
- sample metadata
- variable dictionaries
- units
- controlled vocab candidates

### CSV / XLS / XLSX / TSV

Normalize to Parquet for analytics, but retain original file byte-for-byte.

Required columns where available:

```text
source_id
investigation_id
test_id
timestamp
sample_id
fuel_or_material
o2_fraction
pressure
flow_velocity
flow_direction
gravity_regime
initial_size
flame_state
outcome
unit_metadata
original_file
```

Unknown fields are preserved in a source-specific extension namespace; do not drop them merely because the canonical schema does not yet model them.

### Video / image

For Day 1, create metadata records first. Only extract frames for selected demonstration tests.

Store:

```text
media_id
source_file_id
test_id
frame_index or timecode
width
height
fps (for video)
extraction_method
sha256
```

Do not claim a flame metric from a frame until the measurement method is defined and validated against a small manually reviewed sample.

## 7. Provenance contract

Every downstream evidence row must be traceable:

```text
EvidenceRecord
  -> source_file_id
  -> source_id
  -> original_filename
  -> original_object_key
  -> location (row/cell/timecode/page/frame)
  -> transformation_version
  -> derived_by
```

This is the minimum needed for an evidence-first dashboard and prevents the AI layer from producing source-less claims.

## 8. Acquisition acceptance criteria

Day 1 acquisition is accepted when:

- every P0 source has a registry row;
- every verified PSI source has a persistent identifier;
- every mirrored file has a SHA-256 checksum;
- original files are immutable;
- metadata and source-file records can be joined;
- a human can move from one extracted fact back to the exact source file and location;
- no unverified S3 path has been hard-coded.
