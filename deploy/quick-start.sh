#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker Engine is required. Install Docker Desktop or Docker Engine with Compose v2." >&2
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose v2 is required. Install or enable the Compose plugin." >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "Created .env from .env.example. Review secrets and public-source flags before production use."
fi

docker compose -f deploy/docker-compose.yml up --build -d

echo "Price Analyst is starting at http://localhost:8080"
echo "Check readiness with: curl --fail http://localhost:8080/api/v1/ready"
