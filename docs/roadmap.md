# Roadmap and Future Work

This is a planning document, not automatic authorization to implement every item. A future task must state its scope, confirm source/legal permission where relevant, and preserve `AGENTS.md`/`docs/engineering-contract.md`.

## Current baseline

Phases 1 through 7 are implemented at the current repository baseline:

- typed FastAPI/domain foundation and Flutter shell;
- deterministic query normalization and local price analysis;
- independent Torob, Basalam, Digikala, and Divar adapter packages, disabled by default;
- bounded collection, retries, pacing, concurrency, circuit breaking, partial results, and stale fallback;
- optional explicit server-side Gemini interpretation with compact input, strict output, cache, and in-flight deduplication;
- separate wholesale contracts and public HTTPS JSON-feed adapter, disabled by default;
- SQLite/PostgreSQL-compatible bounded durable snapshot cache and Alembic migrations;
- API security/readiness baseline, non-root Compose deployment, backups, Caddy TLS profile, Android packaging baseline, and deployment threat model;
- Persian deployment guide, quick-start script, Colab in-process smoke-test notebook, and agent/API engineering context files.

The baseline is useful without marketplace credentials or Gemini. A no-source response is expected when all external adapters are disabled.

## Candidate next milestones

### M1 — Production access control and operational ownership

**Problem:** The current API has no authentication/authorization and is not a complete multi-user boundary.

Before implementation:

- define user/tenant ownership and retention requirements;
- choose an identity/token/session design;
- define endpoint-level authorization, inbound rate limits, quotas, audit events, abuse handling, and secret rotation;
- update the threat model and privacy/data-retention policy.

Acceptance criteria:

- unauthenticated access behavior is deliberate and tested;
- user data cannot cross tenants;
- secrets are stored outside Git and rotated;
- rate-limit/auth failure behavior is documented and covered by integration tests;
- existing controlled local/demo deployment remains usable or is explicitly versioned.

### M2 — Deployment operations

**Problem:** Backups, monitoring, restore drills, and outbound network controls are still operator responsibilities.

Candidate work:

- automated/verified SQLite and PostgreSQL restore procedure;
- health, latency, source failure, cache, and resource metrics;
- log redaction and retention;
- DNS rebinding/outbound egress allowlisting for configured feeds;
- dependency and container vulnerability scanning;
- documented update/rollback runbook.

Acceptance criteria:

- restore has been tested in an isolated environment;
- alerts distinguish API readiness, source failure, and Gemini failure;
- no credentials or raw source payloads appear in logs;
- security docs and deployment CI reflect the actual controls.

### M3 — Explicitly authorized additional sources

Only implement a source after the user/operator supplies or approves a permitted access method. Each source is a separate milestone, not a generic “scrape everything” task.

Acceptance criteria:

- permission/terms/robots/network review is recorded;
- source adapter is isolated and disabled by default;
- fixtures cover stable and changed/malformed pages or API payloads;
- bounds, retry, pacing, concurrency, source health, partial results, and stale fallback are tested;
- source data never bypasses deterministic normalization or the compact AI boundary.

Social, authenticated, private, or undocumented integrations remain out of scope until explicitly authorized and threat-modeled.

### M4 — Mobile release readiness

Candidate work:

- assign production signing-key ownership and secure storage;
- define Android/iOS application IDs, environments, API URL strategy, privacy disclosures, and release channels;
- device acceptance tests for API failures, stale data, RTL, offline/slow network, and release HTTPS;
- crash/error monitoring without sensitive payload capture.

Acceptance criteria:

- release builds do not use debug cleartext or local addresses;
- signing material is outside Git and recoverable by the owner;
- device matrix and rollback process are documented;
- API compatibility is tested against the released client.

### M5 — AI and analysis evolution

Possible future improvements include a durable AI result cache, richer deterministic analytics, user-supplied cost assumptions, and better explanations. These are only safe if:

- deterministic facts remain authoritative;
- the compact input stays bounded and privacy-reviewed;
- prompt/schema/model versions are part of cache identity;
- output remains strict and reference-validated;
- confidence and uncertainty are not presented as verified facts;
- cost, quota, latency, and provider outage behavior are measured.

Do not add automatic AI calls to ordinary search as a convenience change.

## Explicit non-goals unless re-authorized

- A permanent public server inside free Colab or a public tunnel workaround.
- Unbounded marketplace crawling, browser automation, credentialed scraping, or undocumented/private APIs.
- Mixing wholesale supplier data into retail price statistics.
- Silent IRR/IRT conversion or fabricated prices/availability/currency.
- Treating Render/Railway/other credit-based tiers as guaranteed free production infrastructure.
- Shipping authentication or multi-tenancy by adding a token field without a complete design.
- Replacing the deterministic local pipeline with Gemini.

## How to start a milestone

A future agent should create a small task plan containing:

1. the user-visible goal and the milestone/roadmap item;
2. current contracts/invariants that must not change;
3. affected files and a rollback plan;
4. external permissions/secrets/data-flow review;
5. targeted tests and unavailable toolchains;
6. documentation/OpenAPI/migration impact;
7. measurable acceptance criteria.

Then follow the `ANALYZE → PLAN → IMPLEMENT → TEST → REVIEW → FIX → REPORT` loop in `AGENTS.md`.
