# Architecture

## Principle

Deterministic collection and analysis are the source of truth. Gemini is an optional final interpretation layer.

```text
query → normalize → source search → deterministic extraction
      → normalize → deduplicate → match → local statistics
      → compact AI dataset → optional Gemini analysis → UI
```

## Boundaries

- `api/` translates HTTP requests and responses.
- `application/` orchestrates use cases.
- `collectors/` defines the marketplace port and owns source-specific adapters. The Torob adapter currently implements bounded search and product-page collection.
- `normalization/`, `matching/`, and `analysis/` contain deterministic logic.
- `ai/` creates bounded structured Gemini requests and validates responses.
- `persistence/` owns SQLAlchemy models, repositories, and migrations.
- `frontend/` contains presentation and client state only.

No marketplace selector, endpoint, or parser belongs in the core pipeline.

## Dataset separation

The full dataset is retained for the UI and local analysis. A separate compact dataset contains only fields needed by Gemini. The compact dataset is canonically serialized and hashed for cache lookup and request deduplication.

## Failure behavior

Source failures are represented per source and never abort a search for other sources. Gemini failures return deterministic data with an explicit AI status.
