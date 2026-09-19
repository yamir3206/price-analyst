# Backend

The backend is a FastAPI application under `src/price_analyst`.

```bash
python3 -m pip install -e '.[dev]'
PYTHONPATH=src pytest tests
uvicorn price_analyst.main:app --host 0.0.0.0 --port 8000
```

Phase 2 includes a deterministic Torob adapter. Enable it explicitly with `PRICE_ANALYST_TOROB_ENABLED=true` in `.env`; otherwise `POST /api/v1/searches` exercises query normalization and returns `no_sources_configured` without making external requests.

The Torob adapter uses JSON-LD first, then bounded DOM parsing, and fetches product pages only for the top-ranked search candidates. Tests use saved HTML fixtures and `httpx.MockTransport`; they do not depend on the live Torob website.
