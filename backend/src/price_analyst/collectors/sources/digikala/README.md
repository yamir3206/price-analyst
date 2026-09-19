# Digikala adapter

The adapter uses the public Digikala search/product HTML surfaces. It prefers JSON-LD and structured price attributes, then uses bounded product-card parsing. Currency remains `UNKNOWN` when the public field does not declare rial or toman; no silent conversion is performed.

The adapter is disabled by default and is enabled with `PRICE_ANALYST_DIGIKALA_ENABLED=true`.
