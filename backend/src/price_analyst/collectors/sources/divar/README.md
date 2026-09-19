# Divar adapter

The adapter uses a configured public Divar city/category search path and listing pages. It extracts listing titles, prices, condition, images, and stable listing identifiers without requiring user accounts or hidden APIs. A currency is retained only when the public page declares it; otherwise it remains `UNKNOWN`.

Configure the city/category with `PRICE_ANALYST_DIVAR_CITY` and `PRICE_ANALYST_DIVAR_CATEGORY`. The adapter is disabled by default and is enabled with `PRICE_ANALYST_DIVAR_ENABLED=true`.
