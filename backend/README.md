# Backend

The backend is a FastAPI application under `src/price_analyst`.

```bash
python3 -m pip install -e '.[dev]'
PYTHONPATH=src pytest tests
uvicorn price_analyst.main:app --host 0.0.0.0 --port 8000
```

Phase 3 includes independent deterministic adapters for Torob, Basalam, Digikala, and Divar. Enable each source explicitly with its `PRICE_ANALYST_<SOURCE>_ENABLED=true` setting; all are disabled by default. Divar also requires a configured city and category path. If no source is enabled, `POST /api/v1/searches` returns `no_sources_configured` without making external requests.

Adapters use public search/product or listing HTML only. They prefer JSON-LD and structured price fields, then bounded DOM parsing, and fetch detail pages only for the top-ranked candidates. Shared orchestration applies timeouts, bounded retries, per-source pacing, temporary circuit breaking, partial-result reporting, and stale-cache fallback on refresh. Successful snapshots include deterministic matching, per-currency statistics, classifications, chart points, and conservative opportunity references; currencies are never silently converted.

Ordinary `POST /api/v1/searches` requests stop after deterministic analysis. The explicit `POST /api/v1/searches/analysis` endpoint optionally sends a bounded compact projection to Gemini. The projection excludes URLs, raw HTML, images, and adapter metadata; the full offers remain local. Gemini is disabled without `PRICE_ANALYST_GEMINI_API_KEY`, and the key is never sent to Flutter. Validated successful interpretations are cached in process by dataset hash, prompt version, and model, while identical concurrent requests are coalesced.

Wholesale collection is intentionally separate at `POST /api/v1/wholesale/searches`. It is no-source-by-default and can use only an explicitly configured public HTTPS JSON feed. The feed adapter enforces response-size bounds, rejects private literal IPs, and validates every listing against the typed wholesale contract. The Flutter wholesale page displays truthful no-source and partial/stale states. API responses include request IDs and baseline security headers. An optional SQLAlchemy-backed durable cache is available for SQLite or PostgreSQL after applying migrations; it remains disabled by default. Tests use saved HTML fixtures, mocked HTTP, and do not depend on live marketplaces.
