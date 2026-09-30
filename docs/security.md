# Security and deployment baseline

This document records the Phase 6 hardening boundary. It is an engineering baseline, not a substitute for a production penetration test or legal review.

## Request and response controls

- API request models reject unknown fields and bound query lengths.
- Responses include a generated or validated `X-Request-ID`.
- API responses set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, a restrictive `Permissions-Policy`, and `Cache-Control: no-store`.
- CORS is configuration-driven and credentials are disabled.
- Source requests use bounded timeouts, retries, exponential backoff, per-source pacing, and concurrency limits.

## Wholesale feed controls

- Wholesale collection is disabled unless a feed is explicitly enabled and configured.
- The generic feed adapter accepts HTTPS only and rejects credentials and literal private, loopback, link-local, and reserved IPs.
- Feed response bodies have a configurable byte limit. Listing objects are validated against a strict schema; unknown fields are rejected.
- DNS-based private-address resolution and a full egress allowlist remain deployment-level hardening work.
- No social or authenticated source is enabled by default. Each future source requires an explicit permission and terms review.

## Secrets and data boundaries

- Gemini credentials are backend-only `SecretStr` values and are never included in Flutter configuration or logs.
- Raw HTML, source metadata, and retail URLs do not cross the Gemini boundary.
- Wholesale public contact fields remain in the wholesale flow and are not sent to Gemini.
- Deterministic retail and wholesale snapshots are separate contracts.

## Durable cache operation

`PRICE_ANALYST_DURABLE_CACHE_ENABLED` is disabled by default. Before enabling it, apply Alembic migrations to the configured SQLite or PostgreSQL database:

```bash
alembic -c backend/alembic.ini upgrade head
```

The durable cache stores bounded JSON snapshots with TTLs and entry limits. It does not store API credentials. Database encryption, backup retention, access-control policy, and production connection-pool tuning remain deployment responsibilities.

## Compose deployment baseline

- The backend image runs as a non-root user and exposes port 8000 only to the Compose network.
- A one-shot migration service applies Alembic migrations before the API starts.
- Nginx serves the Flutter web bundle and proxies only `/api/` to the API container.
- The default deployment uses a named SQLite volume; an external PostgreSQL URL can be supplied through `DEPLOY_DATABASE_URL`.
- The optional Caddy profile terminates HTTPS and stores certificate state in named volumes. Do not expose the HTTP web port publicly when using a public hostname.
- The deployment smoke test starts the stack with all external adapters and Gemini disabled, then checks both the web shell and API health endpoint.

## Remaining deployment review items

- Deployment-specific authentication and authorization if the API becomes multi-user
- DNS rebinding protection or outbound host allowlisting for configured feeds
- Database backup/restore drills, encryption, monitoring, and alerting
- Android release signing, production device acceptance, and Play release review
- Independent penetration test and dependency/container vulnerability scanning
