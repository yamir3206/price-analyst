# Basalam adapter

The adapter reads the public Basalam search surface at `/s?q=...` and selected product pages. It prefers JSON-LD and uses bounded DOM parsing for product cards. Search results are lightweight candidates; detail pages are fetched only for the candidates selected by the shared pipeline.

The adapter is disabled by default and is enabled with `PRICE_ANALYST_BASALAM_ENABLED=true`.
