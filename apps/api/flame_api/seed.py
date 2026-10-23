import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from flame_api.database import SessionLocal
from flame_api.ids import stable_ulid
from flame_api.models import FileRecord, ImageAsset, ModelRecord, SourceRecord
from flame_api.registry import read_registry

ROOT = Path(__file__).resolve().parents[3]
DATASETS = ROOT / "datasets"


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seed_sources(session: Session) -> int:
    path = DATASETS / "registry" / "source_registry.csv"
    if not path.exists():
        return 0
    count = 0
    # The shared decoder turns the CSV's literal "null" into None (it used to be stored as text).
    for row in read_registry(path):
        session.merge(SourceRecord(
            source_id=row["source_id"],
            title=row["title"],
            short_name=row.get("short_name"),
            repository=row.get("repository") or "Other",
            persistent_identifier=row.get("persistent_identifier"),
            license=row.get("license"),
            access_url=row.get("access_url") or row.get("data_access_url") or "https://psi.nasa.gov/",
            domain="non_combustion" if row["source_id"] == "FF-PSI-DSI" else "combustion",
        ))
        count += 1
    return count


def seed_files(session: Session) -> tuple[int, int]:
    path = DATASETS / "metadata" / "files.jsonl"
    if not path.exists():
        return 0, 0
    known_sources = {row[0] for row in session.query(SourceRecord.source_id).all()}
    count = skipped = 0
    with path.open(encoding="utf-8") as records:
        for line in records:
            if not line.strip():
                continue
            row = json.loads(line)
            source_id = row["source_id"]
            if source_id not in known_sources:
                skipped += 1
                continue
            dataset_relative_path = row.get("local_path")
            local_path = str(DATASETS / dataset_relative_path) if dataset_relative_path else None
            session.merge(FileRecord(
                file_id=row["file_id"],
                source_id=source_id,
                sha256=row["sha256"],
                original_filename=row["original_filename"],
                media_type=row.get("content_type") or "application/octet-stream",
                size_bytes=int(row.get("size_bytes") or 0),
                retrieved_at=_date(row["retrieval_timestamp_utc"]),
                canonical_source_url=row.get("canonical_source_url") or None,
                is_original=bool(row.get("is_original", True)),
                parent_file_id=row.get("parent_file_id") or None,
                local_path=local_path,
            ))
            count += 1
    return count, skipped


_IMAGE_SUFFIXES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def seed_image_assets(session: Session) -> int:
    """Derived CV samples (incl. DSI frames) with lineage to their raw parent file (M9, E2-4)."""
    path = DATASETS / "samples" / "cv" / "manifest.jsonl"
    if not path.exists():
        return 0
    known_files = {row[0] for row in session.query(FileRecord.file_id).all()}
    count = 0
    with path.open(encoding="utf-8") as records:
        for line in records:
            if not line.strip():
                continue
            row = json.loads(line)
            media_type = _IMAGE_SUFFIXES.get(Path(row["sample_path"]).suffix.lower())
            if media_type is None:
                continue          # videos are Workstream A assets, not images
            parent = row.get("parent_file_id")
            session.merge(ImageAsset(
                image_id=stable_ulid(f"image-asset:{row['sha256']}"),
                file_id=None,
                parent_file_id=parent if parent in known_files else None,
                source_id=row.get("source_id"),
                analysis_id=None,
                sha256=row["sha256"],
                media_type=media_type,
                width=row.get("width"),
                height=row.get("height"),
                frame_index=row.get("frame_index"),
                derivation=row.get("conversion"),
                payload={
                    "sample_path": f"samples/cv/{row['sample_path']}",
                    "member": row.get("member"),
                    "parent_local_path": row.get("parent_local_path"),
                    "sequence_length": row.get("sequence_length"),
                    "original_format": row.get("original_format"),
                    "parent_file_id_declared": parent,
                },
                created_at=_date(row["created_at"]),
            ))
            count += 1
    return count


def seed_models(session: Session) -> int:
    """The H-3 model manifest into the `model` table (C1 registry, 2H Task 4)."""
    from ai.routing.registry import load_manifest

    now = datetime.now(UTC)
    entries = load_manifest()
    for entry in entries:
        existing = session.get(ModelRecord, entry["model_id"])
        session.merge(ModelRecord(
            model_id=entry["model_id"],
            capability=entry["capability"],
            provider=entry["provider"],
            runtime=entry["runtime"],
            name=entry["name"],
            version=entry.get("version"),
            quantization=entry.get("quantization"),
            license=entry.get("license"),
            source_url=entry.get("source_url"),
            sha256=entry.get("sha256"),
            size_bytes=entry.get("size_bytes"),
            locality=entry["locality"],
            context_window=entry.get("context_window"),
            status=entry["status"],
            model_card=entry.get("model_card"),
            payload={k: entry.get(k) for k in ("ram_mb", "vram_mb", "cpu_only", "notes")},
            registered_at=existing.registered_at if existing else now,
        ))
    return len(entries)


def seed() -> dict[str, int]:
    session = SessionLocal()
    try:
        sources = seed_sources(session)
        session.flush()   # SessionLocal has autoflush=False: files look their sources up by query
        files, skipped = seed_files(session)
        session.flush()
        images = seed_image_assets(session)
        models = seed_models(session)
        session.commit()
        return {"sources": sources, "files": files, "files_skipped_unknown_source": skipped,
                "image_assets": images, "models": models}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print(json.dumps(seed(), sort_keys=True))
