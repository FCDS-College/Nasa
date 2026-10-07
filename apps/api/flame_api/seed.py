import csv
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from flame_api.database import SessionLocal
from flame_api.models import FileRecord, SourceRecord

ROOT = Path(__file__).resolve().parents[3]
DATASETS = ROOT / "datasets"


def _date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def seed_sources(session: Session) -> int:
    path = DATASETS / "registry" / "source_registry.csv"
    if not path.exists():
        return 0
    count = 0
    with path.open(encoding="utf-8-sig", newline="") as source_file:
        for row in csv.DictReader(source_file):
            session.merge(SourceRecord(
                source_id=row["source_id"],
                title=row["title"],
                short_name=row.get("short_name") or None,
                repository=row.get("repository") or "Other",
                persistent_identifier=row.get("persistent_identifier") or None,
                license=row.get("license") or None,
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


def seed() -> dict[str, int]:
    session = SessionLocal()
    try:
        sources = seed_sources(session)
        files, skipped = seed_files(session)
        session.commit()
        return {"sources": sources, "files": files, "files_skipped_unknown_source": skipped}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print(json.dumps(seed(), sort_keys=True))