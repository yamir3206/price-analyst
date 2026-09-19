# Backend

The backend is a FastAPI application under `src/price_analyst`.

```bash
python3 -m pip install -e '.[dev]'
PYTHONPATH=src pytest tests
uvicorn price_analyst.main:app --host 0.0.0.0 --port 8000
```

Phase 1 has no live marketplace adapters. `POST /api/v1/searches` exercises the query normalization and response contract while truthfully returning `no_sources_configured`.
