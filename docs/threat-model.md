# Deployment threat model

This is the bounded Phase 7 threat-model baseline for the single-host Compose topology. It records the assumptions that must be revisited before exposing the service to multiple users or enabling new external sources.

## System and trust boundaries

```text
Browser/device
    │ HTTPS or local HTTP
    ▼
Caddy (optional TLS) → Nginx web container
                            │ /api/ only
                            ▼
                       FastAPI API
                       │         │
              named DB volume   public source hosts
                       │
                SQLite/PostgreSQL
```

Gemini is a separate outbound dependency used only by the explicit analysis endpoint. It is disabled by default. Wholesale feeds and retail marketplace adapters are independent outbound dependencies and are disabled by default.

## Protected assets

- Gemini API key, database credentials, Android signing material, and deployment environment files
- Stored deterministic retail and wholesale snapshots
- Public supplier contact fields and source metadata
- API availability and bounded outbound network access
- Integrity of deterministic statistics and source-status claims

## Threats and controls

| Threat | Control | Residual risk / owner |
| --- | --- | --- |
| Public client reaches an internal API or bypasses the proxy | API is Compose-internal; Nginx proxies only `/api/`; browser uses relative API paths | Host firewall and reverse-proxy policy remain operator responsibilities |
| Database credential or Gemini key leaks into the client | Keys are backend settings; Flutter receives no secrets; `.env` and key files are ignored | Secret-store, rotation, and access policy are deployment responsibilities |
| Source/feed URL causes SSRF or excessive egress | HTTPS-only feed, private literal-IP rejection, response limits, timeout/retry/concurrency bounds | DNS rebinding and outbound allowlists require deployment/network controls |
| Malicious source content influences AI | Raw HTML, URLs, and unbounded source fields stay outside the Gemini compact dataset; AI output is strict and validated | Prompt injection in allowed compact text remains a residual risk; keep AI optional |
| Cache/database corruption changes returned facts | Typed snapshot re-validation, Alembic migrations, TTL/entry bounds, deterministic local analysis | Backups, restore drills, encryption, and database ACLs remain operator duties |
| API abuse exhausts resources | Bounded request models, source pacing, concurrency, timeouts, retry caps, and container-internal API | Multi-user authentication, inbound rate limiting, WAF, and quotas are not enabled |
| Container compromise gains host access | Backend runs non-root; containers have no host filesystem bind mount by default | Image scanning, runtime policy, patching, and host hardening remain required |
| TLS or DNS misconfiguration exposes traffic | Optional Caddy profile, HTTPS release configuration, security headers, no API port publication | Verify DNS, certificate renewal, firewall, and HSTS policy before production |
| Unsafe migration or backup operation loses data | Migration is a separate startup job; SQLite online backup script; PostgreSQL provider tooling | Test restore in an isolated volume and retain versioned backups |

## Accepted deployment assumptions

- The initial Compose deployment is single-host and not a complete multi-tenant security boundary.
- No user authentication is assumed; do not expose the service to untrusted multi-user traffic without adding an auth design.
- Public source authorization, terms, robots directives, and permitted access methods must be reviewed before enabling an adapter.
- Production secrets, signing keys, database backups, and logs must be managed outside Git.

## Review triggers

Revisit this model when adding authentication, a social/API source, a new outbound integration, multi-user data ownership, public API exposure, background jobs, or a production mobile release.
