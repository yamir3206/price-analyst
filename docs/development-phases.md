# Development phases

## Phase 1 — foundation

Implemented in this change:

- FastAPI application and typed domain contracts
- Adapter registry and application pipeline boundary
- Deterministic query normalization
- SQLite/PostgreSQL-compatible persistence foundation and migration
- Flutter shell and feature navigation
- API, model, normalization, and compact dataset tests

Live marketplace adapters are intentionally not part of Phase 1.

## Phase 2 — one deterministic source

Implement one permitted marketplace adapter with fixture-driven parsing, search/detail staging, cache behavior, and parser tests.

## Phase 3 — remaining marketplaces

Add Torob, Basalam, Digikala, and Divar adapters, source health, rate limits, retries, partial failure handling, and incremental refresh.

## Phase 4 — local analysis

Implement matching, deduplication, price statistics, classifications, charts, and opportunity calculations.

## Phase 5 — AI layer

Implement compact offer selection, token budgeting, Gemini client, structured validation, cache, request coalescing, and AI UI.

## Phase 6 — wholesale and hardening

Add wholesale adapters, permitted social sources, performance work, Android packaging, security review, and integration testing.
