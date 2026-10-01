# Price Analyst — Agent Development Context

This file is the first repository-level instruction for coding agents. Read it before changing code. It is intentionally short; the linked documents contain the detailed contracts.

## Required reading order

1. `AGENTS.md` (this file)
2. `docs/engineering-contract.md` for non-negotiable architecture and safety rules
3. `docs/api-contract.md` for HTTP behavior and compatibility rules when changing backend/frontend contracts
4. `docs/extension-guide.md` for the correct way to add adapters, endpoints, fields, migrations, or UI
5. The relevant source-specific README, test fixtures, deployment document, and existing tests
6. `docs/roadmap.md` before starting a new milestone or broad feature

`docs/openapi.json` is a generated API snapshot. Regenerate it with `python backend/scripts/export_openapi.py`; do not hand-edit it.

## Repository purpose

Price Analyst is a Flutter client plus a typed FastAPI backend for deterministic price intelligence. The authoritative data flow is:

```text
request → query normalization → independent source collection
        → deterministic extraction/normalization → deduplication/matching
        → local statistics/classification/opportunities → optional AI interpretation
```

The deterministic local result is the source of truth. Gemini is an optional, explicit, server-side interpretation layer and is never a prerequisite for ordinary search.

## Non-negotiable invariants

- **Do not break existing contracts.** Keep `/api/v1/health`, `/api/v1/ready`, `/api/v1/searches`, `/api/v1/searches/analysis`, and `/api/v1/wholesale/searches` backward-compatible. Prefer additive changes. A breaking change requires a new versioned contract and an explicit migration plan.
- **Retail and wholesale stay separate.** Wholesale listings must never enter retail offers, retail statistics, retail matching, or the retail `SearchSnapshot`.
- **Source-specific logic stays in an adapter.** Do not put selectors, source URLs, or marketplace assumptions in the core pipeline, domain models, or generic orchestration.
- **Use only permitted access methods.** Do not add scraping, authenticated endpoints, social APIs, browser automation, or a new source without an explicit permission/terms/robots/network review. The default for every source is disabled.
- **Deterministic first.** Normalize, match, deduplicate, calculate statistics, classify, and produce opportunities locally before any AI call. Preserve the full local dataset.
- **Protect the Gemini boundary.** Gemini receives only a bounded compact projection. Never send raw HTML, product URLs, images, public contacts, credentials, or unrestricted adapter metadata. AI remains disabled gracefully without a server-side key and is triggered only through the explicit analysis flow.
- **Never silently convert currencies or invent missing values.** `IRR`, `IRT`, and `UNKNOWN` remain distinct. Unknown fields stay `null` or an explicit unknown enum.
- **Keep failure partial and truthful.** A source failure must not erase other sources or turn an incomplete result into a success claim. Preserve source status, stale state, bounded retries, timeouts, pacing, concurrency limits, and cache behavior.
- **Keep secrets server-side.** Never place Gemini keys, database passwords, signing keys, or `.env` contents in Flutter, notebooks, fixtures, logs, commits, or generated public assets.
- **Treat persistence changes as migrations.** Do not rely on `create_all()` or destructive startup changes for a deployed database. Keep SQLite and PostgreSQL compatibility and test upgrade/rollback behavior where relevant.
- **Do not weaken security controls for convenience.** Preserve strict Pydantic boundaries, request IDs, response security headers, CORS policy, SSRF/response-size safeguards, no-store responses, and non-root deployment behavior.

## Source-of-truth hierarchy

When documents disagree, use this order and update the lower-level documentation after the code change:

1. Current typed implementation and tests for behavior
2. `docs/openapi.json` generated from the FastAPI app for HTTP schemas
3. `docs/api-contract.md` for compatibility and semantic intent
4. `docs/engineering-contract.md` and `docs/extension-guide.md` for architecture rules
5. `README.md`, `README.fa.md`, and component READMEs for user/operator instructions
6. Historical phase notes and roadmap items

If implementation and a contract document disagree, do not silently choose one: determine whether the implementation or the contract is intended, add/update tests, then update all affected documents in the same change.

## Standard development loop

Follow this order and report it in the final response:

1. **ANALYZE** — inspect the relevant code, tests, configuration, contracts, and current git status; identify compatibility and security impact.
2. **PLAN** — state the smallest additive design and the files/tests it affects.
3. **IMPLEMENT** — make focused changes; do not refactor unrelated code.
4. **TEST** — run targeted tests first, then the relevant regression/lint/type checks.
5. **REVIEW** — inspect the diff, generated contract, migration, logs, secrets, and failure behavior.
6. **FIX** — address every discovered issue before reporting completion.
7. **REPORT** — list files, behavior, tests, limitations, security/performance implications, and follow-up work.

## Standard validation commands

From the repository root, with the project virtualenv active:

```bash
python -m pytest backend/tests
python -m ruff check backend/src backend/tests backend/scripts
python -m mypy backend/src
python backend/scripts/export_openapi.py
```

When Flutter is installed:

```bash
make frontend-analyze
make frontend-test
```

For deployment changes:

```bash
bash -n deploy/quick-start.sh
docker compose -f deploy/docker-compose.yml config
docker compose -f deploy/docker-compose.yml up --build -d
curl --fail http://localhost:8080/api/v1/ready
```

If a tool is unavailable in the environment, say so explicitly; do not claim that check passed. Never enable live marketplace collection merely to make a smoke test appear populated.

## Change hygiene

- Work only on the session branch specified by the environment. In Arena sessions this is `arena/01a0b551-price-analyst`; do not switch branches.
- Keep changes additive and reviewable. Avoid unrelated formatting or generated cache files.
- Update tests and documentation when a contract changes.
- Update the relevant `docs/*` file and regenerate `docs/openapi.json` for API changes.
- Use a clear commit message and push only to the session branch when the user asks for commit/push.
