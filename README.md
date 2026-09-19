# Price Analyst

Price Analyst is a cross-platform price-intelligence application for Android, Windows, Web, and later iOS. It collects marketplace data deterministically, performs local normalization and analysis, and uses Gemini only as an optional final interpretation layer.

## Repository status

Phases 1–3 are implemented. The repository currently contains:

- A typed FastAPI backend foundation
- Domain models for queries, offers, source health, snapshots, opportunities, and AI analysis
- Independent deterministic public-HTML adapters for Torob, Basalam, Digikala, and Divar
- JSON-LD-first parsing with bounded DOM fallback and fixture tests
- Two-stage search/detail collection with candidate ranking and cache support
- Bounded retries with exponential backoff, per-source pacing, and temporary source circuit breaking
- Partial-result responses with stale cached offers during refresh failures
- SQLite/PostgreSQL-compatible persistence scaffolding
- A Flutter application shell with RTL support and placeholder feature screens
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

The full deterministic dataset and the compact Gemini dataset are separate representations. Gemini never receives raw HTML and the application remains useful when Gemini or a marketplace is unavailable.

## Backend development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e 'backend[dev]'
pytest backend/tests
uvicorn price_analyst.main:app --app-dir backend/src --host 0.0.0.0 --port 8000 --reload
```

The health endpoint is available at `GET /api/v1/health`. A Phase 1 search request normalizes the query and returns an explicit no-adapters-configured response; it does not claim to have collected marketplace data.

Copy `.env.example` to `.env` for local configuration. Gemini credentials belong only on the backend and must never be placed in the Flutter application.

## Flutter development

Flutter/Dart must be installed before running the frontend. From `frontend/`:

```bash
flutter pub get
flutter analyze
flutter test
flutter run -d chrome --dart-define=API_BASE_URL=/api
```

For an Android emulator, use a backend URL reachable from the emulator, commonly `http://10.0.2.2:8000`, passed through `API_BASE_URL`. Browser builds should use a relative `/api` URL and a development-server proxy rather than calling `localhost` from browser code.

## License

This project is distributed under the GNU General Public License, version 3. See [LICENSE](LICENSE).
