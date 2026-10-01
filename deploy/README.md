# Easy deployment

The Compose bundle runs the Flutter web client, FastAPI API, and migration job together. Marketplace adapters, wholesale feeds, and Gemini remain disabled unless explicitly configured in the root `.env` file.

## Local or single-host deployment

Requirements: Docker Engine with Compose v2.

```bash
./deploy/quick-start.sh
```

The script checks for Docker, creates `.env` from `.env.example` if needed, and starts the stack. Keep public sources and Gemini disabled unless they have been reviewed.

Open <http://localhost:8080>. The `migrate` service applies all Alembic migrations before the API starts. SQLite data is kept in the `app-data` named volume. Useful commands:

```bash
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs -f api web
./deploy/backup-sqlite.sh
docker compose -f deploy/docker-compose.yml down
```

The browser uses `/api` and Nginx proxies that path to the internal API service; no browser code calls `localhost` to reach the backend.

## External PostgreSQL

The image includes the PostgreSQL driver. Set `DEPLOY_DATABASE_URL` in the shell or root `.env` to a reachable URL before starting the stack:

```dotenv
DEPLOY_DATABASE_URL=postgresql+psycopg://price_analyst:replace-me@db.example.com:5432/price_analyst
```

The migration and API services use the same value. Keep PostgreSQL credentials outside source control, restrict database network access, and use TLS parameters required by the provider. Use the provider's `pg_dump`/backup facility for PostgreSQL; `deploy/backup-sqlite.sh` is only for the default SQLite volume.

## Backups and readiness

The API exposes `GET /api/v1/ready` for the Compose healthcheck. It verifies the configured SQL database when durable caching is enabled and does not require marketplace or Gemini availability.

For the default SQLite deployment, create a consistent online backup with:

```bash
./deploy/backup-sqlite.sh
# or: make deploy-backup
```

Backups are written to `backups/`, which is intentionally not a source-controlled directory. Copy them to durable external storage and periodically test restoration with a separate Compose volume.

## HTTPS on a public host

The default profile is HTTP for local/single-host testing. For a DNS name pointing at the host, the optional Caddy profile obtains and renews certificates automatically:

```bash
DEPLOY_DOMAIN=prices.example.com \
  docker compose --profile tls -f deploy/docker-compose.yml up --build -d
```

Allow inbound TCP ports 80 and 443. Caddy stores certificates in named volumes. Do not expose the API port directly; it is only on the internal Compose network.

## Configuration and secrets

- `PRICE_ANALYST_GEMINI_API_KEY` belongs only in the deployment secret store or uncommitted `.env`.
- `PRICE_ANALYST_CORS_ORIGINS` must list the public origin when a separate frontend origin is used. Same-origin Compose deployment normally needs no additional origin.
- Durable caching is enabled by the Compose deployment and is bounded by the configured TTL and maximum entries.
- All marketplace and wholesale adapters are disabled by default.
- Change the generated application and deployment passwords before production use; never commit `.env`, signing keys, or database credentials.

This is a small single-host deployment baseline. Production operators still own backups, monitoring, firewall policy, TLS/DNS, vulnerability scanning, and authentication if the API is exposed to multiple users.
