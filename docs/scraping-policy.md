# Collection policy

Marketplace adapters must use permitted/public access methods and should prefer official APIs or structured public endpoints. The Phase 2 Torob adapter uses public search/product HTML, JSON-LD, and bounded DOM parsing; it does not use authenticated endpoints or browser automation. Source-specific code must be isolated under its adapter directory.

Collection is bounded:

- Search surfaces are preferred over full product pages.
- Detail pages are fetched only for relevant selected candidates.
- HTTP calls use explicit timeouts, retries, backoff, rate limits, and concurrency bounds.
- Raw HTML is never sent to Gemini.
- Missing fields stay `null`; adapters must not fabricate values.
- Terms of service, robots directives, authentication requirements, and local law must be reviewed before enabling a source.
