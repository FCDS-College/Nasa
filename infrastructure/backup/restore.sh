#!/usr/bin/env bash
# P2-11: restore a backup made by backup.sh, then verify per-table row counts against it.
#
#   RESTORE_DATABASE_URL=... infrastructure/backup/restore.sh backups/20261102T120000Z
#
# Environment (names only; never commit values):
#   RESTORE_DATABASE_URL     required. Target database; create it empty first (createdb -O flame <name>).
#                            It must not be FLAME_DATABASE_URL unless RESTORE_ALLOW_SAME=1.
#   RESTORE_CLEAN=1          drop existing objects in the target first (pg_restore --clean --if-exists).
#   RESTORE_S3_BUCKET        bucket to sync the mirrored objects into (default FLAME_S3_BUCKET).
#   FLAME_S3_ENDPOINT_URL, FLAME_S3_ACCESS_KEY / FLAME_S3_SECRET_KEY (or AWS_*), as for backup.sh.
#   RESTORE_SKIP_S3=1        database only.
#
# Exit status is non-zero if pg_restore fails or any table's row count differs from row_counts.tsv.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
. "$here/lib.sh"

src="${1:?usage: restore.sh <backup directory>}"
[ -f "$src/postgres.dump" ] || die "$src/postgres.dump not found"
target="${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL is required}"
if [ "$target" = "${FLAME_DATABASE_URL:-}" ] && [ "${RESTORE_ALLOW_SAME:-0}" != "1" ]; then
  die "RESTORE_DATABASE_URL equals FLAME_DATABASE_URL; set RESTORE_ALLOW_SAME=1 to restore over it"
fi
(cd "$src" && sha256sum --check --quiet <(grep -E '^[0-9a-f]{64}  ' MANIFEST)) || die "checksum mismatch in $src"
pg_env_from_url "$target"
started=$(date +%s)

clean=()
[ "${RESTORE_CLEAN:-0}" = "1" ] && clean=(--clean --if-exists)
log "pg_restore $src/postgres.dump -> $PGDATABASE@$PGHOST:$PGPORT"
pg_restore --exit-on-error --no-owner --no-privileges "${clean[@]}" --dbname="$PGDATABASE" "$src/postgres.dump"
psql -X -q -v ON_ERROR_STOP=1 -c "analyze" >/dev/null

if diff <(row_counts) "$src/row_counts.tsv" >&2; then
  log "row counts match for $(wc -l < "$src/row_counts.tsv") tables"
else
  die "row counts differ from the backup (diff above: < restored, > backup)"
fi

if [ "${RESTORE_SKIP_S3:-0}" = "1" ] || [ ! -d "$src/s3" ]; then
  log "object storage not restored (RESTORE_SKIP_S3=1 or no s3/ in the backup)"
else
  s3_env
  bucket="${RESTORE_S3_BUCKET:-${FLAME_S3_BUCKET:?RESTORE_S3_BUCKET or FLAME_S3_BUCKET is required}}"
  log "sync $src/s3/ -> s3://$bucket"
  s3_copy "$src/s3" "s3://$bucket"
  log "$(find "$src/s3" -type f | wc -l) objects synced"
fi
log "restore complete in $(( $(date +%s) - started )) s"
