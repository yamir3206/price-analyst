#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-deploy/docker-compose.yml}"
backup_dir="${BACKUP_DIR:-backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_path="${backup_dir}/price_analyst-${timestamp}.db"
container="$(docker compose -f "$compose_file" ps -q api)"

if [[ -z "$container" ]]; then
    echo "The API container is not running. Start the deployment before backing up." >&2
    exit 1
fi

mkdir -p "$backup_dir"
temporary_path="/tmp/price_analyst-${timestamp}.db"
cleanup() {
    docker compose -f "$compose_file" exec -T api rm -f "$temporary_path" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker compose -f "$compose_file" exec -T api python - "$temporary_path" <<'PY'
import sqlite3
import sys

source_path = "/data/price_analyst.db"
target_path = sys.argv[1]
with sqlite3.connect(source_path) as source, sqlite3.connect(target_path) as target:
    source.backup(target)
PY

docker cp "${container}:${temporary_path}" "$backup_path"
echo "SQLite backup written to $backup_path"
