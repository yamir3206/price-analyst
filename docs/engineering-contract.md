# Engineering Contract

This document records the design rules that future agents and developers must preserve. It describes the current implementation at the repository baseline and the acceptance criteria for extensions.

## 1. System boundaries

```text
Flutter presentation/state
        │ JSON over HTTP
        ▼
api/ (validation, HTTP translation)
        ▼
application/ (use-case orchestration)
   ┌────┼───────────────┬──────────────┐
   ▼    ▼               ▼              ▼
collectors  normalization/matching/analysis  ai/  persistence/
   │                    │              │       │
source adapters     deterministic truth  optional  bounded cache/migrations
```

Dependency direction:

- `api/` may depend on application services, domain contracts, and API schemas.
- `application/` may depend on domain contracts and application ports; it should not know HTTP or Flutter details.
- `collectors/` owns the generic source protocols, bounded HTTP behavior, registries, and independent source adapters.
- `normalization/`, `matching/`, and `analysis/` are deterministic and should remain usable without network access or Gemini.
- `ai/` owns compact projection, token/character budgets, the server-side client, strict output validation, cache, and in-flight deduplication.
- `persistence/` owns SQLAlchemy models, database engines, cache implementations, and migration compatibility.
- `frontend/` owns presentation, client state, and JSON decoding; it does not collect sources or hold server secrets.

A source selector, marketplace URL, HTML parser, provider credential, or HTTP retry policy must not leak into the domain model or generic business analysis.

## 2. Data and truth rules

### 2.1 Full deterministic dataset

A retail `SearchSnapshot` retains the full normalized `Offer` records returned by enabled sources. Full offers may contain product URLs, image URLs, source metadata, seller, shipping, and observed time for UI and local traceability. Local analysis must not delete full offers merely because they are duplicates or non-matches; it represents grouping and matching separately.

A `WholesaleSnapshot` is a different contract. `WholesaleListing` records, statuses, cache keys, and service behavior never enter a retail snapshot or retail statistics.

### 2.2 Currency

`Money.amount` is an integer in the source unit and always has an explicit `Currency`. `IRR`, `IRT`, and `UNKNOWN` are distinct. Never convert rial/toman implicitly, compare different currencies in one statistic, or display a conversion as if it were source data. A future conversion feature requires an explicit policy, timestamp/rate provenance, tests, and a contract review.

### 2.3 Missing and uncertain data

Unknown values remain `null` or an explicit enum value such as `unknown`. Adapters must not infer a price, currency, availability, condition, supplier, or contact field from an unsupported assumption. A partial result must expose its source statuses and stale state.

### 2.4 AI projection

The complete local dataset and compact AI dataset are separate representations:

- Compact records are bounded and deterministic.
- Raw HTML, product URLs, images, public contacts, credentials, and unreviewed adapter metadata are excluded.
- The compact dataset retains explicit currency and relevant deterministic match/classification information.
- The dataset is canonically serialized/hashed for cache lookup and request coalescing.
- A successful AI result must reference only valid compact offer IDs when references are used.
- Facts, inferences, and uncertainties remain separate fields.

AI failure, invalid output, quota exhaustion, timeout, or absent key must return deterministic data with an explicit AI status, not fail the ordinary search.

## 3. Source collection contract

All retail adapters implement the existing retail port and are registered independently. All wholesale adapters implement the separate wholesale port and registry. A new source is disabled by default until:

1. public/official access and authorization are reviewed;
2. terms of service, robots directives, rate policy, authentication requirements, and applicable law are documented;
3. URL and network behavior are bounded;
4. parser/adapter code is isolated under its source package;
5. fixture-based tests cover valid, missing, changed, and malformed source data;
6. partial failure, stale fallback, rate limiting, retry, and source status behavior are tested;
7. the configuration flag and operator documentation are added.

Collection must preserve:

- explicit timeouts;
- bounded retries with backoff;
- per-source pacing and concurrency limits;
- candidate and detail-page limits;
- circuit breaking after repeated failures;
- bounded response/body sizes;
- no fabricated fields;
- no raw HTML sent to Gemini.

The generic public wholesale JSON adapter additionally requires an explicitly configured public HTTPS URL, rejects credentials/private literal addresses, validates strict listing objects, and enforces response-size/listing limits. This is not permission to add a social or authenticated source.

## 4. API and client compatibility

The API is currently an unauthenticated v1 contract intended for controlled deployment. Its complete generated schema is `docs/openapi.json`, and its semantic rules are in `docs/api-contract.md`.

- Existing paths, request fields, response fields, enum values, and success meanings are compatibility-sensitive.
- Do not remove or rename a response field used by the Flutter client.
- Add optional response fields before considering a version change.
- Unknown request fields remain rejected unless a deliberate compatibility design changes this rule.
- Adding an enum value requires frontend fallback behavior and tests; clients must not assume that an enum list is permanently closed.
- A breaking change needs a new versioned path/contract, migration notes, fixture updates, and a deprecation plan.
- Any API change requires backend integration tests, frontend model/client updates, OpenAPI regeneration, and documentation updates.

## 5. Persistence and migrations

The durable cache is optional but must remain compatible with both SQLite and PostgreSQL. It stores bounded snapshots/cache data, not credentials. Before enabling it in a new environment:

```bash
(cd backend && alembic upgrade head)
```

Migration rules:

- Add a new Alembic revision for schema changes; do not mutate an applied revision.
- Make upgrades explicit and as reversible as the database permits.
- Do not drop/rename data without a migration and backup/rollback plan.
- Test the upgrade from the repository's current head and exercise both SQLite and PostgreSQL-sensitive SQL where relevant.
- Keep runtime startup safe when migrations have not run: readiness should fail truthfully rather than silently create/alter production tables.
- Update persistence models, payload serialization, migration, tests, deployment docs, and backup guidance together.

## 6. Security contract

Preserve the existing baseline:

- Pydantic request and source contracts reject unknown fields at important boundaries.
- Request IDs are generated/validated and returned in `X-Request-ID`.
- Security headers and `Cache-Control: no-store` remain on API responses.
- CORS is configuration-driven with credentials disabled.
- Source/feed URL validation, timeouts, response limits, and private-address safeguards remain active.
- Gemini and database secrets are backend-only and never logged or bundled into Flutter.
- The backend container remains non-root; API is internal to the default Compose topology.
- No public multi-user authentication is assumed. Adding public exposure requires an explicit auth, authorization, rate-limit, and threat-model design.

## 7. Performance and reliability contract

Bounded behavior is a correctness requirement, not an optional optimization. New work must state its impact on:

- source and AI concurrency;
- timeout and retry budgets;
- request/body/response sizes;
- cache TTL and maximum entries;
- database query count and payload size;
- frontend rendering/state growth;
- cold start and container memory.

Never trade away source pacing or retry bounds to make a demo faster. Use deterministic fixture/mocked tests and the existing benchmark tooling rather than live marketplace calls for repeatable performance claims.

## 8. Required test layers

Choose the smallest complete set for the change:

- Pure domain/normalization/matching/analysis change: unit tests, including edge cases and currency behavior.
- Adapter/parser change: saved fixtures, malformed/missing fields, mocked HTTP, bounds, and source-status tests; no live website dependency.
- Application/persistence change: service tests, cache/migration/expiry tests, partial failure and stale fallback tests.
- API change: `TestClient` integration tests for success, validation, status semantics, and backward compatibility.
- Flutter API/model/state change: Dart model/client/controller/widget tests and explicit loading/error/partial/stale/disabled states.
- Deployment/config change: shell/config validation, Compose config, readiness, backup/restore or a documented environment limitation.
- Any change touching Gemini: compact dataset boundary, strict output, disabled/no-key path, cache/deduplication, and secret handling tests.

## 9. Definition of done

A change is not complete until:

- the smallest additive design is implemented;
- affected contracts and docs are updated;
- tests and static checks pass or unavailable checks are explicitly reported;
- generated OpenAPI is refreshed for API changes;
- migration and rollback implications are documented;
- security, source authorization, privacy, performance, and partial-failure behavior are reviewed;
- `git diff` contains no secrets, generated caches, unrelated rewrites, or untracked required artifacts;
- the final report lists files, tests, limitations, and follow-up risks.
