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
- `collectors/` defines the marketplace port and owns source-specific adapters. Torob, Basalam, Digikala, and Divar each implement bounded public-HTML search and detail/listing collection in independent packages.
- `normalization/`, `matching/`, and `analysis/` contain deterministic logic. Matching reports evidence and mismatch fields; local analysis calculates per-currency statistics, classifications, chart data, and opportunity references without discarding full offers.
- `ai/` creates bounded structured Gemini requests and validates responses.
- `persistence/` owns SQLAlchemy models, repositories, and migrations.
- `frontend/` contains presentation and client state only.

No marketplace selector, endpoint, or parser belongs in the core pipeline.

## Dataset separation

The full dataset is retained for the UI and local analysis. A separate compact dataset contains only bounded normalized fields, explicit currency, deterministic classifications, match scores, and statistics. It never contains raw HTML, product URLs, images, or adapter metadata. Selection is deterministic: local opportunities and matches are preferred, then source diversity is preserved, and the input is reduced until the configured character/token estimate fits. The compact dataset is canonically serialized and hashed for cache lookup and request deduplication.

## Optional AI flow

`POST /api/v1/searches` performs ordinary deterministic collection only. `POST /api/v1/searches/analysis` first obtains or reuses that deterministic snapshot and then explicitly requests the optional Gemini interpretation. The server passes the compact dataset to Gemini; the API key is held in a `SecretStr` configuration value and sent only in a server-side request header. Gemini is disabled when no key is configured.

Gemini output is accepted only when it is a JSON object matching the strict `AIAnalysis` contract. Offer references are checked against the compact offer IDs, and facts, inferences, and uncertainties are separate fields. Successful results are cached by prompt version, model, and dataset hash; identical concurrent requests share one in-flight task. The current cache is process-local and can be replaced by a database-backed implementation later without changing the API boundary.

## Failure behavior

Source failures are represented per source and never abort a search for other sources. Requests use bounded exponential retries and a per-source minimum interval. Consecutive failures temporarily disable a source through an in-memory circuit breaker. On refresh, the pipeline reuses the last cached offers for a failed or disabled source and marks that source and snapshot as stale. Gemini failures return deterministic data with an explicit AI status.
