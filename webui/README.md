# Persian Web UI (`webui/`)

A lightweight, right-to-left Persian interface for the FastAPI backend that needs **no Flutter, Node.js, Docker, or build step**. It is plain HTML/CSS/JavaScript plus a launcher written only with the Python standard library.

```text
browser ──► webui/serve.py (127.0.0.1:8080)
              ├── static files: index.html, app.js, style.css
              └── /api/v1/*  ──proxy──►  FastAPI backend (127.0.0.1:8000)
```

The browser only calls relative `/api/v1/...` URLs on the same origin, so the backend CORS policy does not need to change.

## Windows: one click

1. Install Python 3.11+ from <https://www.python.org/downloads/> and tick **Add python.exe to PATH**.
2. Double-click **`run-windows.bat`** in the repository root.

The first run creates `.venv`, installs the backend with `pip`, and copies `.env.example` to `.env`. It then starts the backend and opens `http://127.0.0.1:8080` in your browser. Later runs start immediately. To reinstall from scratch, delete `.venv` and run it again.

## Manual (any OS)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: . .venv/bin/activate)
python -m pip install -e backend
python webui/serve.py --start-backend --open
```

If the backend is already running elsewhere, start only the UI:

```bash
python webui/serve.py --backend http://127.0.0.1:8000
```

Options: `--host` (default `127.0.0.1`), `--port` (default `8080`), `--backend-port` (default `8000`), `--backend URL`, `--start-backend`, `--open`.

## Troubleshooting

- **`[WinError 10013] ... forbidden by its access permissions` or "port in use":** Windows reserves some port ranges (Hyper-V, WSL, Docker), or another program is using the port. The launcher checks ports 8000 (backend) and 8080 (UI) before using them and automatically switches to a free port, printing the address it chose. The browser opens the right address. To choose ports yourself, pass e.g. `run-windows.bat --port 8090 --backend-port 8010`. To see the reserved ranges, run `netsh interface ipv4 show excludedportrange protocol=tcp`.

## Features

- Retail search (`POST /api/v1/searches`) with offers, match score, price classification, source status, and partial/stale/no-sources banners
- Per-currency statistics and an SVG price chart with p25/median/p75 lines
- Locally calculated opportunities
- Explicit optional AI analysis (`POST /api/v1/searches/analysis`) showing facts, inferences, and uncertainties separately
- Separate wholesale search (`POST /api/v1/wholesale/searches`)
- Service health/readiness (`/api/v1/health`, `/api/v1/ready`)

## Safety notes

- All marketplace sources stay **disabled** by default. Enable them in `.env` only after reviewing the source policy (`docs/scraping-policy.md`), then restart.
- IRR and IRT are displayed with their own units and are never converted. Price sorting groups by currency first.
- The Gemini key stays in the backend `.env`; the UI never receives it.
- The UI binds to `127.0.0.1` by default because the API has no authentication. Do not use `--host 0.0.0.0` on an untrusted network.
- Marketplace text is HTML-escaped, only `http(s)` links/images are rendered, and static pages are served with a strict Content-Security-Policy. The proxy forwards only `GET`/`POST` under `/api/v1/` and limits request (64 KB) and response (32 MB) sizes.

## Tests

```bash
python -m unittest discover -s webui/tests -v
```
