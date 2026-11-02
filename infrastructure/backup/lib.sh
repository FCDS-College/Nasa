# Shared by backup.sh and restore.sh (P2-11). Sourced, not executed. No secrets live here: every
# credential comes from the environment by name.

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# Export PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE from a SQLAlchemy or libpq URL
# (postgresql+psycopg://user:pass@host:port/db). Using libpq's env vars keeps the password out of `ps`.
pg_env_from_url() {
  local url="$1"
  [ -n "$url" ] || die "database URL is empty"
  eval "$(python3 - "$url" <<'PY'
import shlex, sys
from urllib.parse import unquote, urlsplit
u = urlsplit(sys.argv[1])
if not u.scheme.startswith("postgres"):
    sys.exit("not a PostgreSQL URL")
values = {"PGHOST": u.hostname or "localhost", "PGPORT": str(u.port or 5432), "PGUSER": unquote(u.username or ""),
          "PGPASSWORD": unquote(u.password or ""), "PGDATABASE": unquote(u.path.lstrip("/"))}
for key, value in values.items():
    if value:
        print(f"export {key}={shlex.quote(value)}")
PY
)" || die "could not parse the database URL"
}

# Map Flame's S3 settings onto what aws/mc read, without ever printing them.
s3_env() {
  export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${FLAME_S3_ACCESS_KEY:-}}"
  export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${FLAME_S3_SECRET_KEY:-}}"
  export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${FLAME_S3_REGION:-us-east-1}}"
  S3_ENDPOINT="${FLAME_S3_ENDPOINT_URL:-}"
}

# s3_copy SRC DST: one of them is s3://bucket[/prefix], the other a local directory.
s3_copy() {
  local src="$1" dst="$2"
  if command -v aws >/dev/null 2>&1; then
    aws s3 sync --only-show-errors ${S3_ENDPOINT:+--endpoint-url "$S3_ENDPOINT"} "$src" "$dst"
  elif command -v mc >/dev/null 2>&1; then
    [ -n "$S3_ENDPOINT" ] || die "mc needs FLAME_S3_ENDPOINT_URL"
    local scheme="${S3_ENDPOINT%%://*}" host="${S3_ENDPOINT#*://}"
    export MC_HOST_flamebackup="${scheme}://${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}@${host}"
    mc mirror --quiet --overwrite "${src/#s3:\/\//flamebackup/}" "${dst/#s3:\/\//flamebackup/}"
  else
    die "neither aws nor mc is installed (or set BACKUP_SKIP_S3=1 / RESTORE_SKIP_S3=1)"
  fi
}

# Exact row count of every table in the public schema, one "table<TAB>count" line each, sorted.
row_counts() {
  local table
  psql -X -At -v ON_ERROR_STOP=1 -c \
    "select tablename from pg_tables where schemaname = 'public' order by tablename" |
    while read -r table; do
      printf '%s\t%s\n' "$table" "$(psql -X -At -v ON_ERROR_STOP=1 -c "select count(*) from public.\"$table\"")"
    done
}
