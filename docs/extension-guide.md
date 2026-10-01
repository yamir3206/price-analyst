# Extension Guide for Future Development

Use this guide before implementing a new source, endpoint, response field, persistence feature, Gemini capability, or Flutter screen. The goal is to extend the existing contracts without accidentally changing the truth model or operational safety.

## 1. Start every change

Before coding:

1. Read `AGENTS.md`, `docs/engineering-contract.md`, and the relevant section of `docs/api-contract.md`.
2. Inspect `git status`, the current implementation, nearby tests, `.env.example`, and deployment configuration.
3. Write down the existing behavior that must remain unchanged.
4. Decide whether the work is a domain, collector, application, API, persistence, AI, frontend, or deployment change.
5. Define the smallest additive contract and its failure/rollback behavior.
6. Confirm that an external source is permitted before writing any adapter code.

Do not start by changing the broad pipeline or by adding a generic `dict[str, Any]` escape hatch.

## 2. Add a retail marketplace source

A new retail source must be independently replaceable and disabled by default.

### Required steps

1. **Authorization review**
   - Record the public/official access method, terms, robots directives, authentication requirements, rate expectations, allowed geography, and legal/security review.
   - Do not use browser automation, private/authenticated endpoints, undocumented APIs, or social-network access without explicit authorization.
2. **Configuration**
   - Add a typed `*_enabled` flag and base URL/settings to `Settings` and `.env.example`.
   - Default the flag to `false`.
   - Document the variables and operational bounds.
3. **Package isolation**
   - Add `backend/src/price_analyst/collectors/sources/<source>/`.
   - Keep selectors, source URL construction, parsing, normalization quirks, and source error mapping in that package.
   - Add a short source README with the reviewed access method and known limitations.
4. **Adapter contract**
   - Implement the existing retail adapter protocol and register it only when its flag is enabled.
   - Return typed `SearchCandidate`/`Offer` records; leave unknown fields empty.
   - Reuse shared bounded HTTP, retry, pacing, timeout, source-health, and candidate-ranking utilities.
5. **Fixtures and tests**
   - Add saved HTML/structured-data fixtures with no secrets or unnecessary live URLs.
   - Test JSON-LD/structured extraction, bounded DOM fallback, Persian digits/currency/availability/condition, missing/malformed fields, candidate ranking, detail limits, and source-specific failures.
   - Test that a failure produces partial/stale truthful status and does not prevent another source from returning offers.
6. **Review**
   - Check response-size and URL safeguards, no raw HTML crossing the AI boundary, no unbounded loops, and no live network dependency in normal CI.

Do not modify the core pipeline to accommodate a single marketplace. If a capability is genuinely generic, add it to a typed shared port with tests for existing sources.

## 3. Add a wholesale source

Wholesale is not another retail adapter. Use `collectors/wholesale.py`, `wholesale_registry.py`, `application/wholesale_service.py`, the wholesale cache port, and `domain/wholesale.py`.

Required properties:

- The source is explicitly authorized and separately configured.
- The adapter returns strict `WholesaleListing` objects.
- The source is never registered in the retail `AdapterRegistry`.
- `POST /api/v1/wholesale/searches` remains the only wholesale flow unless a new endpoint is deliberately designed.
- Public contact and supplier data stay in wholesale and are not sent to Gemini.
- HTTPS, no credentials in URLs, private-address/SSRF protections, response-size limits, listing limits, timeout, retry, pacing, concurrency, and stale fallback remain active.
- A social or messaging source is not implied by the generic feed adapter; it requires a separate permission and security review.

## 4. Add or change an API endpoint

1. Define a typed request/response model in the appropriate API/domain module.
2. Use `ConfigDict(extra="forbid")` for important external boundaries.
3. Bound string lengths, list sizes, integer ranges, URLs, and nested payloads.
4. Put business behavior in an application service/use-case, not directly in a route.
5. Keep the route thin: parse, call the service, translate expected `ValueError`/domain failures to stable HTTP behavior.
6. Add `TestClient` integration tests for:
   - valid request;
   - missing/wrong/oversized/unknown fields;
   - empty/no-source result;
   - partial and stale result;
   - dependency or provider failure;
   - backward compatibility with existing fields.
7. Update the Flutter API client/models/state/UI if the endpoint is user-facing.
8. Regenerate `docs/openapi.json`:

   ```bash
   python backend/scripts/export_openapi.py
   ```

9. Update `docs/api-contract.md`, README/deployment docs, and any threat-model assumptions.

Do not change a v1 field from nullable to required, rename it, reinterpret an enum, or alter success semantics without a versioning/deprecation plan.

## 5. Add a response field or domain concept

Follow this sequence:

1. Identify the source of truth and whether the field is deterministic, source-specific, AI-derived, or deployment-only.
2. Add a typed field with a safe default/nullable behavior where compatible.
3. Preserve `extra="forbid"` at boundaries.
4. Add domain/service tests for empty, unknown, stale, and malformed cases.
5. Update API schemas/OpenAPI and Flutter JSON decoding.
6. Update UI for loading, empty, partial, stale, disabled, and error states as applicable.
7. If persisted in a durable payload/table, add an Alembic migration or document why no schema migration is needed.
8. Update API and data-model documentation.

The Flutter client currently decodes JSON in `frontend/lib/core/models/`, calls the API through `frontend/lib/core/api/api_client.dart`, and manages requests through Riverpod controllers under `frontend/lib/core/state/`. Keep JSON keys in backend `snake_case`; do not silently change them to Dart naming.

## 6. Change persistence

For a database/schema change:

1. Update SQLAlchemy models and serialization contracts.
2. Create a new revision under `backend/migrations/versions/`; never edit an applied revision.
3. Run `alembic upgrade head` against a disposable SQLite database.
4. Check SQLAlchemy/PostgreSQL compatibility and test the relevant round trip/expiry behavior.
5. Test the previous schema upgrading to the new head and a safe downgrade where supported.
6. Update backup, readiness, deployment, and rollback instructions.
7. Keep cache TTL and maximum-entry bounds; this system stores bounded cache/snapshot data, not an unbounded event log.

A migration must not be hidden in application startup. Compose uses the one-shot `migrate` service; direct deployments must run the documented command.

## 7. Change Gemini or another AI provider

- Keep the provider server-side and optional.
- Extend the compact dataset only with bounded normalized fields that are necessary for the task.
- Explicitly exclude raw HTML, URLs, images, credentials, public contacts, and unrestricted adapter metadata.
- Version prompts/schema changes in the cache key (`analysis_version`/prompt version) so old results cannot be mistaken for new behavior.
- Preserve timeout, retry, concurrency, rate interval, output-size, JSON-only parsing, strict Pydantic validation, offer-reference validation, successful-result cache, and identical in-flight request coalescing.
- Test no-key/disabled behavior, provider failure, invalid output, cache hit, concurrent deduplication, and deterministic fallback.
- Never expose a provider key through Flutter or a notebook committed to the repository.

## 8. Change Flutter

For an API-backed feature:

1. Add/modify the typed model in `frontend/lib/core/models/`.
2. Add the API method in `frontend/lib/core/api/api_client.dart` with the existing status/error handling.
3. Add or update a Riverpod controller/state model.
4. Add a route/page only after the data and error states are defined.
5. Preserve RTL/localization and the existing relative `/api` deployment behavior.
6. Handle `no_sources_configured`, `partial`, `stale`, disabled AI, loading, empty, and failure states truthfully.
7. Add widget/model/controller tests where the toolchain is available.
8. Verify web, Android emulator, and release URL configuration; never put server secrets in `--dart-define`.

The browser must use a relative API path behind a same-origin proxy or an explicit HTTPS public API URL. Do not ship `localhost`, `127.0.0.1`, or `10.0.2.2` in a public build.

## 9. Change deployment/configuration

- Add all new settings to `Settings`, `.env.example`, relevant Docker environment, and docs.
- Choose safe defaults: external sources and Gemini off; bounded values; no credentials committed.
- Keep `GET /api/v1/ready` focused on configured local dependencies, not live marketplace availability.
- Preserve non-root container execution, internal API exposure, Nginx `/api/` proxying, Caddy TLS profile, and backup semantics.
- Validate `docker compose config`, shell syntax, readiness, logs, and upgrade/rollback instructions.
- Record any new exposed port, egress destination, secret, volume, resource limit, or health-check assumption in `docs/security.md`/`docs/threat-model.md`.

## 10. Definition-of-done checklist

```text
[ ] Existing behavior and compatibility risks identified
[ ] Permission/source review completed, if external access is involved
[ ] Typed contract and bounded inputs/outputs defined
[ ] Failure, stale, disabled, timeout, retry, and rollback behavior specified
[ ] Unit/integration/fixture/frontend tests added or updated
[ ] Persistence migration and backup impact reviewed
[ ] API OpenAPI snapshot regenerated when applicable
[ ] API/data/architecture/deployment docs updated
[ ] Secret and raw-source-data review completed
[ ] Backend tests + ruff + mypy pass
[ ] Flutter checks pass, or unavailable toolchain reported
[ ] Diff reviewed for unrelated/generated files
[ ] Final report includes files, tests, limitations, security/performance notes, and next step
```
