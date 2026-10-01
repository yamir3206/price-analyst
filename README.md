# Price Analyst

Price Analyst is a cross-platform price-intelligence application for Android, Windows, Web, and later iOS. It collects marketplace data deterministically, performs local normalization and analysis, and uses Gemini only as an optional final interpretation layer.

## Repository status

Phases 1–5 and Phase 6 wholesale/hardening milestones are implemented. The repository currently contains:

- A typed FastAPI backend foundation
- Domain models for queries, offers, source health, snapshots, opportunities, and AI analysis
- Independent deterministic public-HTML adapters for Torob, Basalam, Digikala, and Divar
- JSON-LD-first parsing with bounded DOM fallback and fixture tests
- Two-stage search/detail collection with candidate ranking and cache support
- Bounded retries with exponential backoff, per-source pacing, and temporary source circuit breaking
- Partial-result responses with stale cached offers during refresh failures
- Deterministic local matching, per-currency statistics, classifications, chart data, and opportunity references
- Optional server-side Gemini interpretation with bounded input, strict output validation, cache, coalescing, and an explicit analysis endpoint
- Separate wholesale contracts, bounded public HTTPS JSON-feed adapter, API flow, and Flutter UI
- Baseline API security headers, request IDs, response-size/URL safeguards, and integration tests
- Optional bounded SQLite/PostgreSQL durable snapshot caching with migrations
- Security and deployment baseline documentation
- A Flutter application shell with RTL support and local statistics, chart, and opportunity views
- Backend tests and frontend test scaffolding

All four marketplace adapters are disabled by default. Enable them individually in `.env` only after reviewing the source policy and network access.

## Architecture

```text
Flutter frontend
       │ REST/JSON
       ▼
FastAPI API
       │
       ├── Query normalization
       ├── Marketplace adapter orchestration
       ├── Deterministic extraction and matching
       ├── Local price statistics
       ├── Compact AI dataset generation
       └── Optional Gemini analysis
```

The full deterministic dataset and the compact Gemini dataset are separate representations. Gemini never receives raw HTML, product URLs, or unnecessary adapter fields, and the application remains useful when Gemini or a marketplace is unavailable. Ordinary searches do not call Gemini; use `POST /api/v1/searches/analysis` for the explicit optional interpretation step.

## Development contracts for future agents

- [`AGENTS.md`](AGENTS.md) is the repository-level agent context and change workflow.
- [`docs/engineering-contract.md`](docs/engineering-contract.md) records architecture, data, security, reliability, and compatibility invariants.
- [`docs/api-contract.md`](docs/api-contract.md) documents the v1 HTTP behavior; [`docs/openapi.json`](docs/openapi.json) is its generated machine-readable snapshot.
- [`docs/extension-guide.md`](docs/extension-guide.md) explains how to add sources, endpoints, migrations, AI behavior, or Flutter features safely.
- [`docs/roadmap.md`](docs/roadmap.md) lists future candidates without treating them as automatic authorization.

## Backend development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e 'backend[dev]'
pytest backend/tests
uvicorn price_analyst.main:app --app-dir backend/src --host 0.0.0.0 --port 8000 --reload
```

The health endpoint is available at `GET /api/v1/health`. With no adapters enabled, a normal search request normalizes the query and returns an explicit no-adapters-configured response; it does not claim to have collected marketplace data. The optional AI layer is requested separately through `POST /api/v1/searches/analysis`.

Copy `.env.example` to `.env` for local configuration. Gemini credentials belong only on the backend and must never be placed in the Flutter application.

## Easy deployment

With Docker Engine and Compose v2 installed:

```bash
./deploy/quick-start.sh
```

The script creates `.env` from `.env.example` when needed and starts the full stack. Open `http://localhost:8080`. The migration job runs before the API, SQLite data is kept in a named volume, and Nginx serves the Flutter web client while proxying `/api/` internally. Readiness is available at `/api/v1/ready`; SQLite backups use `make deploy-backup`. See [`deploy/README.md`](deploy/README.md) for external PostgreSQL and the optional Caddy HTTPS profile, [`README.fa.md`](README.fa.md) for the complete Persian deployment guide, and [`docs/threat-model.md`](docs/threat-model.md) for deployment assumptions.

## Flutter development

Flutter/Dart must be installed before running the frontend. From `frontend/`:

```bash
flutter pub get
flutter analyze
flutter test
flutter run -d chrome --dart-define=API_BASE_URL=/api
```

For an Android emulator, use a backend URL reachable from the emulator, commonly `http://10.0.2.2:8000`, passed through `API_BASE_URL`. Debug Android builds permit this cleartext address for local development only; release builds require HTTPS. Browser builds should use a relative `/api` URL and a development-server proxy rather than calling `localhost` from browser code. The checked-in Android runner has a reproducible debug-APK workflow; release signing uses private `frontend/android/key.properties` material and is not committed.

## License

This project is distributed under the GNU General Public License, version 3. See [LICENSE](LICENSE).
