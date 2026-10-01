# Torob adapter

The adapter uses public HTML surfaces only:

1. Search page: `GET /search/?query=...`
2. Selected product pages: `GET /p/<product-id>/...`

Extraction order is JSON-LD first and bounded DOM parsing second. Search returns lightweight product candidates. Product pages are fetched only for candidates selected by the application pipeline.

The adapter does not use Gemini, browser automation, or undocumented authenticated endpoints. Enable it explicitly with `PRICE_ANALYST_TOROB_ENABLED=true` after reviewing the source policy and network access requirements.
