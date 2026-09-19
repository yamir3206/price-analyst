# Backend

The backend is a FastAPI application under `src/price_analyst`.

```bash
python3 -m pip install -e '.[dev]'
PYTHONPATH=src pytest tests
uvicorn price_analyst.main:app --host 0.0.0.0 --port 8000
```

Phase 3 includes independent deterministic adapters for Torob, Basalam, Digikala, and Divar. Enable each source explicitly with its `PRICE_ANALYST_<SOURCE>_ENABLED=true` setting; all are disabled by default. Divar also requires a configured city and category path. If no source is enabled, `POST /api/v1/searches` returns `no_sources_configured` without making external requests.

Adapters use public search/product or listing HTML only. They prefer JSON-LD and structured price fields, then bounded DOM parsing, and fetch detail pages only for the top-ranked candidates. Shared orchestration applies timeouts, bounded retries, per-source pacing, temporary circuit breaking, partial-result reporting, and stale-cache fallback on refresh. Tests use saved HTML fixtures and `httpx.MockTransport`; they do not depend on live marketplaces.
