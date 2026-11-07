#!/usr/bin/env bash
# P2-11: timestamped backup of Flame's PostgreSQL database and object-storage bucket.
#
#   FLAME_DATABASE_URL=... FLAME_S3_BUCKET=flame-artifacts infrastructure/backup/backup.sh
#
# Environment (names only; never commit values):
#   FLAME_DATABASE_URL       required. SQLAlchemy or libpq URL of the database to dump.
#   FLAME_S3_BUCKET          bucket to mirror (required unless BACKUP_SKIP_S3=1).
#   FLAME_S3_ENDPOINT_URL    S3 endpoint (MinIO: http://minio:9000); empty for AWS.
#   FLAME_S3_ACCESS_KEY / FLAME_S3_SECRET_KEY, or AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY.
#   BACKUP_DIR               where backups go (default ./backups).
#   BACKUP_RETENTION_DAYS    delete backups older than this many days after a successful run (default 14).
#   BACKUP_SKIP_S3=1         database only.
#
# Output: $BACKUP_DIR/<UTC timestamp>/{postgres.dump, row_counts.tsv, s3/, MANIFEST}. The directory is
# only given its final name once everything succeeded, so a partial backup is never mistaken for one.
# Needs pg_dump/psql of the server's major version (16 for Compose), python3, and aws or mc.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "$here/lib.sh"

backup_dir="${BACKUP_DIR:-./backups}"
retention_days="${BACKUP_RETENTION_DAYS:-14}"
[[ "$retention_days" =~ ^[0-9]+$ ]] || die "BACKUP_RETENTION_DAYS must be a whole number"
pg_env_from_url "${FLAME_DATABASE_URL:?FLAME_DATABASE_URL is required}"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"
work="$backup_dir/.partial-$stamp"
final="$backup_dir/$stamp"
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT
started=$(date +%s)

log "pg_dump $PGDATABASE@$PGHOST:$PGPORT -> $final/postgres.dump"
pg_dump --format=custom --compress=6 --file="$work/postgres.dump"
row_counts > "$work/row_counts.tsv"
log "$(wc -l < "$work/row_counts.tsv") tables counted"

if [ "${BACKUP_SKIP_S3:-0}" = "1" ]; then
  log "BACKUP_SKIP_S3=1: object storage not mirrored"
  s3_line="skipped"
else
  s3_env
  bucket="${FLAME_S3_BUCKET:?FLAME_S3_BUCKET is required (or BACKUP_SKIP_S3=1)}"
  log "mirror s3://$bucket -> $final/s3/"
  mkdir -p "$work/s3"
  s3_copy "s3://$bucket" "$work/s3"
  s3_line="$bucket $(find "$work/s3" -type f | wc -l) objects"
fi

{
  echo "created_utc=$stamp"
  echo "database=$PGDATABASE host=$PGHOST port=$PGPORT"
  echo "server_version=$(psql -X -At -c 'show server_version')"
  echo "alembic_revision=$(psql -X -At -c 'select version_num from alembic_version' 2>/dev/null || echo none)"
  echo "s3=$s3_line"
  echo "duration_s=$(( $(date +%s) - started ))"
  (cd "$work" && sha256sum postgres.dump row_counts.tsv)
} > "$work/MANIFEST"

mv "$work" "$final"
trap - EXIT
log "backup complete: $final ($(du -sh "$final" | cut -f1))"

# Retention: only timestamped directories this script made, and only after a successful backup.
find "$backup_dir" -mindepth 1 -maxdepth 1 -type d -name '20[0-9][0-9][01][0-9][0-3][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z' \
  -mtime +"$retention_days" -print -exec rm -rf {} + | sed 's/^/pruned /' >&2 || true
echo "$final"
