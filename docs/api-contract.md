# API Contract

This document describes the stable HTTP contract for the current `v1` API. The machine-readable schema is [`openapi.json`](openapi.json), generated from the FastAPI application by [`backend/scripts/export_openapi.py`](../backend/scripts/export_openapi.py).

- **Contract snapshot:** repository version `0.4.0`
- **Base path:** `/api/v1`
- **Content type:** `application/json`
- **Authentication:** none is implemented in this baseline; do not expose it to untrusted multi-user traffic without an authentication/authorization design.

## Contract rules

- Request bodies use `snake_case` JSON keys.
- Request models reject unknown fields.
- `query` is required and has length `1..200`.
- `refresh` is optional and defaults to `false`.
- Response objects may contain nullable fields; clients must handle `null`, empty lists, partial collection, stale data, and future enum values gracefully.
- The API returns a deterministic snapshot even when no source or Gemini is configured.
- Ordinary search does not invoke Gemini. AI is requested only through `/searches/analysis`.
- Retail and wholesale responses are separate contracts and must not be merged by clients.
- Every API response receives `X-Request-ID` plus the baseline security headers. The request ID may be supplied by a client only when it satisfies the server's safe-character/length rules.

## Endpoints

### `GET /api/v1/health`

Liveness/configuration information. It does not check marketplace availability or database readiness.

Example `200` response:

```json
{
  "status": "ok",
  "service": "Price Analyst API",
  "version": "0.4.0",
  "environment": "development",
  "gemini_configured": false
}
```

Semantics:

- `status` is currently `ok` when the application can answer.
- `gemini_configured` only reports whether a non-empty server-side Gemini key is configured. It does not mean a Gemini request will succeed.

### `GET /api/v1/ready`

Readiness for local configured dependencies. With the default in-memory cache it returns `200` without external marketplace calls. When durable caching is enabled, it checks the configured SQL database.

Example `200` response:

```json
{"status":"ready"}
```

A configured database failure returns `503` with a generic detail message. Readiness must not depend on marketplace or Gemini health.

### `POST /api/v1/searches`

Runs the deterministic retail flow. It normalizes the query, collects only enabled retail adapters, performs local matching/statistics/classification/opportunity analysis, and returns an `ai_analysis.status` of `not_requested`.

Request:

```json
{
  "query": "Samsung S24 Ultra 256 GB",
  "refresh": false
}
```

A successful response is a `SearchSnapshot`. With all sources disabled, the response is still `200` but must contain:

- `offers: []`;
- `collection_status: "no_sources_configured"`;
- one `SourceStatus` per built-in retail source (`torob`, `basalam`, `digikala`, `divar`), normally `state: "not_configured"`;
- empty local analysis lists;
- `ai_analysis.status: "not_requested"`.

This is a truthful no-source result, not evidence that marketplaces returned no products.

### `POST /api/v1/searches/analysis`

Runs the same deterministic retail flow and explicitly requests optional Gemini interpretation. The full local result is always retained. Without a server key, the endpoint returns `200` with `ai_analysis.status: "disabled"` and deterministic data.

Request:

```json
{
  "query": "laptop",
  "refresh": false
}
```

Possible AI statuses:

| Status | Meaning |
|---|---|
| `not_requested` | Ordinary search did not request AI |
| `disabled` | No usable server-side Gemini key/configuration |
| `cached` | A successful compatible result was reused |
| `completed` | A new validated AI result was accepted |
| `invalid_response` | Provider output did not satisfy the strict contract |
| `failed` | Provider/network/timeout/retry failure |

AI failure must not discard deterministic offers/statistics.

### `POST /api/v1/wholesale/searches`

Runs the separate wholesale flow. It never invokes the retail pipeline, never adds listings to retail offers, and normally returns `collection_status: "no_sources_configured"` unless an explicitly reviewed public HTTPS JSON feed is enabled.

Request:

```json
{
  "query": "laptop",
  "refresh": false
}
```

A successful response is a `WholesaleSnapshot` with `listings`, `source_statuses`, `collection_status`, `collected_at`, and `stale`.

## Request schemas

All three request bodies have the same shape but intentionally use separate Pydantic types:

| Field | Type | Required | Constraints |
|---|---|---:|---|
| `query` | string | yes | length 1 to 200 |
| `refresh` | boolean | no | default `false`; bypasses the applicable snapshot cache |

Unknown fields are rejected. Do not add an untyped `dict` escape hatch to accept raw HTML, URLs, provider payloads, or AI prompts.

## Retail response schemas

### `SearchSnapshot`

| Field | Type | Meaning |
|---|---|---|
| `search_id` | UUID | snapshot identifier |
| `query` | `NormalizedQuery` | deterministic query representation |
| `offers` | `Offer[]` | full normalized retail offers retained locally |
| `statistics` | `PriceStatistics` or `null` | optional summary statistics |
| `source_statuses` | `SourceStatus[]` | per-retail-source state and counts |
| `collection_status` | enum | `complete`, `partial`, `no_sources_configured`, or `failed` |
| `collected_at` | RFC 3339 datetime | snapshot observation time |
| `stale` | boolean | whether stale cached data participates |
| `local_analysis` | `LocalAnalysis` | deterministic matches, groups, classifications, charts, opportunities |
| `ai_analysis` | `AIAnalysisEnvelope` | explicit AI state/result metadata |

### `NormalizedQuery`

- `original`: original user query.
- `normalized_text`: normalized searchable text.
- `brand`, `model`, `capacity`, `color`: nullable extracted intent fields.
- `attributes`: string-to-string normalized attributes.
- `variants`: bounded list of deterministic query variants, maximum five.

### `Money`

```json
{"amount": 125000000, "currency": "IRR"}
```

`amount` is a non-negative integer. `currency` is exactly `IRR`, `IRT`, or `UNKNOWN`; no implicit conversion is allowed.

### `Offer`

An offer has the following fields:

- identity: `offer_id`, `source`, `source_offer_id`;
- product: `title`, `normalized_title`, optional `brand`, `model`, `capacity`, `specifications`;
- money: nullable `price`, `original_price`, and `shipping`, each a `Money` object;
- provenance: `product_url`, optional `image_url`, `observed_at`, `details_fetched`, `metadata`;
- state: `seller`, `availability`, `condition`, and optional `shipping_information`.

`Offer` URLs remain local in the full deterministic dataset. They are not sent to Gemini's compact projection.

### `SourceStatus`

| Field | Meaning |
|---|---|
| `source` | `torob`, `basalam`, `digikala`, `divar`, or a future enum value |
| `state` | `ready`, `not_configured`, `unavailable`, `rate_limited`, or `stale` |
| `adapter_configured` | whether the adapter is enabled/configured |
| `last_success`, `last_failure` | nullable timestamps |
| `average_response_time_ms` | nullable non-negative response-time estimate |
| `candidate_count`, `offer_count`, `failure_count` | bounded collection counters |
| `temporary_disabled_until` | nullable circuit-breaker timestamp |
| `stale_data_available`, `stale_data_timestamp` | stale fallback information |
| `error_code`, `error_message` | nullable operational detail; do not treat an error message as a stable code |

### `LocalAnalysis`

- `matches`: `OfferMatch[]`, each with `offer_id`, score, match boolean, matched/mismatched/missing fields.
- `deduplication_groups`: equivalent product groups; grouping does not delete offers.
- `classifications`: per-offer price classification and distance/relative values.
- `statistics_by_currency`: separate statistics for each explicit currency.
- `price_charts`: per-currency points plus `p25`, `median`, and `p75` reference lines.
- `opportunities`: conservative results with explicit assumptions, costs, spread, profit, ROI/margin where available.

Unknown-currency prices may remain in `offers` but are excluded from comparable currency statistics by default.

### `AIAnalysisEnvelope`

| Field | Meaning |
|---|---|
| `status` | one of the AI statuses listed above |
| `result` | nullable strict `AIAnalysis` object |
| `dataset_hash` | compact deterministic dataset identity |
| `prompt_version` | prompt/schema version used for cache compatibility |
| `model` | configured model identifier |
| `error_code`, `error_message` | nullable operational result; never expose secrets |

`AIAnalysis` separates `facts`, `inferences`, `uncertainties`, and bounded lists of summary/assessment/risks/opportunities, with `confidence` in `[0, 1]`. Its string items are not a substitute for verified local facts.

## Wholesale response schemas

### `WholesaleSnapshot`

| Field | Type | Meaning |
|---|---|---|
| `search_id` | UUID | wholesale snapshot identifier |
| `query` | `NormalizedQuery` | shared query representation |
| `listings` | `WholesaleListing[]` | maximum 100 bounded listings |
| `source_statuses` | `WholesaleSourceStatus[]` | independent wholesale source state |
| `collection_status` | `CollectionStatus` | same collection status enum, interpreted in wholesale flow |
| `collected_at` | datetime | observation time |
| `stale` | boolean | stale wholesale fallback marker |

### `WholesaleListing`

- required: `listing_id`, `source`, `title`;
- optional: `supplier_name`, `minimum_order_quantity`, `unit_price`, `product_url`, `shipping_information`, `location`, `public_contact`;
- state: `availability`, `condition`, `observed_at`;
- `product_url`, when present, must be an HTTP(S) URL without credentials;
- maximums: listing ID 200 chars, source 100, title 500, product URL 2000, shipping/location/contact bounded by the generated schema.

Public contact information remains within the wholesale flow and is not sent to Gemini.

## Error behavior

### Validation errors (`422`)

Malformed JSON, missing `query`, query length violations, wrong types, or unknown request fields are rejected by FastAPI/Pydantic. The standard body has a `detail` list with locations/messages, for example:

```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

Application-level invalid query errors are also translated to `422` with a string `detail`. Clients should show a safe generic message and use status code/structured fields, not parse English error text as a protocol.

### Readiness error (`503`)

A configured durable database that cannot answer `SELECT 1` makes `/ready` return `503`. This must not be retried indefinitely by the client; deployment health checks should use bounded retries.

### Partial collection (`200`)

A source timeout, rate limit, circuit breaker, or parser failure can still produce a `200` snapshot from other sources. Inspect `collection_status`, `source_statuses`, `stale`, and per-offer provenance before presenting the result as complete.

## Compatibility procedure for API changes

1. Change the typed backend schema/service intentionally.
2. Add or update backend integration tests for the old and new behavior.
3. Update Flutter models/client/state/UI for every new field or enum value.
4. Regenerate the machine-readable contract:

   ```bash
   python backend/scripts/export_openapi.py
   ```

5. Update this document and relevant README/deployment docs.
6. Run backend tests, ruff, mypy, and Flutter checks when available.
7. Do not remove/rename a v1 field or change its meaning without a new versioned path and migration/deprecation plan.
