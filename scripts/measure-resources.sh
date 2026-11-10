#!/usr/bin/env bash
# Resource usage of the MusicStudio stack on the server that runs it (after a Coolify deploy).
#
# Usage:  scripts/measure-resources.sh [name-filter]
#   name-filter: a substring of the container names (Coolify appends the resource id, e.g.
#   "backend-abc123"); default: every running container.
# Read-only: it only runs docker stats/inspect/df and a SELECT on the database size.
set -euo pipefail

FILTER="${1:-}"
mapfile -t NAMES < <(docker ps --format '{{.Names}}' | grep -- "$FILTER" || true)
if [ "${#NAMES[@]}" -eq 0 ]; then
  echo "No running containers match '$FILTER'." >&2
  exit 1
fi

echo "== Host"
echo "CPU cores: $(nproc)"
free -h | sed -n '1,2p'
df -h / | tail -1 | awk '{print "Disk /: " $3 " used of " $2 " (" $5 ")"}'

echo
echo "== Containers (one snapshot; run again under load to compare)"
docker stats --no-stream \
  --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.PIDs}}' "${NAMES[@]}"

echo
echo "== Images"
for name in "${NAMES[@]}"; do
  image="$(docker inspect -f '{{.Config.Image}}' "$name")"
  bytes="$(docker image inspect -f '{{.Size}}' "$image")"
  printf '%-40s %-45s %6d MB\n' "$name" "$image" $((bytes / 1024 / 1024))
done

echo
echo "== Volumes (database, backups, redis)"
docker system df -v --format '{{range .Volumes}}{{.Name}}\t{{.Size}}{{"\n"}}{{end}}' | grep -- "$FILTER" || true

db="$(printf '%s\n' "${NAMES[@]}" | grep '^db' | head -1 || true)"
if [ -n "$db" ]; then
  echo
  echo "== Database"
  docker exec "$db" sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc \
    "select '"'"'size: '"'"' || pg_size_pretty(pg_database_size(current_database())) \
     || '"'"', lessons: '"'"' || (select count(*) from lessons_lesson)"'
fi
