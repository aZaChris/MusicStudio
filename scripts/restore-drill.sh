#!/usr/bin/env bash
# Restore drill (ADR-020): prove a backup can rebuild a working database.
#
# Usage:
#   scripts/restore-drill.sh <dump.sql.gz>                 # a local dump
#   scripts/restore-drill.sh --from-remote <path-in-remote> # e.g. daily/musicstudio-20261109.sql.gz
#   add --keep to keep the restored database afterwards (default: dropped)
#
# Connection to the PostgreSQL server where the drill database is created comes from the
# standard libpq variables (PGHOST, PGPORT, PGUSER, PGPASSWORD). --from-remote needs rclone
# with an `offsite:` remote configured (same RCLONE_CONFIG_* variables as the Compose
# service). The drill never touches the source database.
#
# Steps: fetch dump -> create a brand-new database -> restore with ON_ERROR_STOP ->
# compare the row count of every table with the rows inside the dump (COPY blocks: the
# dump *is* the snapshot) -> check migrations against the code -> print the elapsed time.
set -euo pipefail

keep=0
remote=""
dump=""
while [ $# -gt 0 ]; do
  case "$1" in
    --keep) keep=1 ;;
    --from-remote) remote="${2:?path in the remote}"; shift ;;
    *) dump="$1" ;;
  esac
  shift
done

repo="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)"
db="musicstudio_drill_$(date +%Y%m%d%H%M%S)"
started=$(date +%s)

cleanup() {
  rm -rf -- "$work"
  if [ "$keep" = 0 ]; then dropdb --if-exists "$db" 2>/dev/null || true; fi
}
trap cleanup EXIT

if [ -n "$remote" ]; then
  echo "== Downloading offsite:$remote"
  rclone copyto "offsite:$remote" "$work/dump.sql.gz"
  dump="$work/dump.sql.gz"
fi
[ -f "$dump" ] || { echo "Dump not found: $dump" >&2; exit 2; }

echo "== Dump:     $dump ($(du -h "$dump" | cut -f1))"
echo "== Server:   $(psql -d postgres -Atc 'show server_version')"
echo "== Database: $db (new)"
createdb "$db"

echo "== Restoring"
restore_start=$(date +%s)
gunzip -c "$dump" | psql -q -v ON_ERROR_STOP=1 -d "$db" >/dev/null
restore_secs=$(( $(date +%s) - restore_start ))

echo "== Row counts (expected = rows in the dump)"
# In a plain dump each table's data is "COPY schema.table (...) FROM stdin;" followed by
# one line per row and a final "\." line. Embedded newlines are escaped, so lines = rows.
gunzip -c "$dump" | awk '
  /^COPY / { table = $2; n = 0; inside = 1; next }
  inside && /^\\\.$/ { print table, n; inside = 0; next }
  inside { n++ }
' | sort > "$work/expected"

mismatches=0
tables=0
while read -r table expected; do
  actual=$(psql -d "$db" -Atc "select count(*) from $table")
  tables=$((tables + 1))
  if [ "$actual" != "$expected" ]; then
    echo "   MISMATCH $table: dump $expected, restored $actual"
    mismatches=$((mismatches + 1))
  fi
done < "$work/expected"
rows=$(awk '{ s += $2 } END { print s + 0 }' "$work/expected")
echo "   $tables tables, $rows rows, $mismatches mismatches"
for t in public.accounts_user public.studios_studio public.students_student \
         public.packages_package public.lessons_lesson public.payments_payment; do
  grep -E "^$t " "$work/expected" | sed 's/^/   /' || true
done

echo "== Migrations: restored schema vs code"
migrations="skipped (backend not found)"
if [ -d "$repo/backend" ]; then
  host="${PGHOST:-localhost}"
  case "$host" in /*) host="localhost" ;; esac
  url="postgres://${PGUSER:-$USER}${PGPASSWORD:+:$PGPASSWORD}@${host}:${PGPORT:-5432}/$db"
  if (cd "$repo/backend" && DATABASE_URL="$url" uv run python manage.py migrate --check \
        --settings=config.settings.test >/dev/null); then
    migrations="ok (no unapplied migrations)"
  else
    migrations="FAILED (schema behind the code)"
    mismatches=$((mismatches + 1))
  fi
fi
echo "   $migrations"

total=$(( $(date +%s) - started ))
echo "== Restore ${restore_secs}s, drill total ${total}s"
if [ "$mismatches" -eq 0 ]; then
  echo "RESULT: OK"
else
  echo "RESULT: FAILED"
  exit 1
fi
