# Development phases

## Phase 1 — foundation

Implemented:

- FastAPI application and typed domain contracts
- Adapter registry and application pipeline boundary
- Deterministic query normalization
- SQLite/PostgreSQL-compatible persistence foundation and migration
- Flutter shell and feature navigation
- API, model, normalization, and compact dataset tests

## Phase 2 — one deterministic source

Implemented for Torob:

- Public search and product-page adapter
- JSON-LD-first extraction with deterministic DOM fallback
- Persian digit/currency/availability/condition parsing
- Search candidate and seller-offer mapping
- Bounded detail-page collection
- Deterministic candidate ranking
- In-memory snapshot cache and refresh bypass
- Fixture-driven parser and adapter tests

The adapter is disabled by default and must be explicitly enabled through configuration.


## Phase 3 — remaining marketplaces

Implemented:

- Independent public-HTML adapters for Basalam, Digikala, and Divar
- Shared bounded retries with exponential backoff and per-source request pacing
- In-memory source health tracking and temporary circuit breaking
- Partial result responses and stale cached-offer fallback during refresh
- Fixture-driven parser, adapter, retry, health, and refresh tests

All marketplace adapters remain disabled by default and must be explicitly enabled through configuration.

## Phase 4 — local analysis

Implemented:

- Deterministic query-to-offer matching with explicit evidence and mismatch reporting
- Exact-repeat removal plus cross-marketplace product-equivalence groups without deleting full offers
- Per-currency percentile, mean, spread, standard deviation, and variation statistics
- Below-market, typical, above-market, and outlier classifications
- Per-currency chart points with median and quartile reference lines
- Conservative opportunity calculations using market median as an explicit resale-reference assumption
- Snapshot/API integration with configurable match threshold and opportunity limit

Currencies are never silently converted. Unknown-currency prices are retained in the full offer set but excluded from comparable statistics by default.

## Phase 5 — AI layer

Implement compact offer selection, token budgeting, Gemini client, structured validation, cache, request coalescing, and AI UI.

## Phase 6 — wholesale and hardening

Add wholesale adapters, permitted social sources, performance work, Android packaging, security review, and integration testing.
