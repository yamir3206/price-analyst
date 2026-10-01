# Collection policy

Marketplace adapters must use permitted/public access methods and should prefer official APIs or structured public endpoints. The Phase 3 Torob, Basalam, Digikala, and Divar adapters use public search/product or listing HTML, JSON-LD, structured data, and bounded DOM parsing; they do not use authenticated endpoints, undocumented APIs, or browser automation. Source-specific code must be isolated under its adapter directory.

Collection is bounded:

- Search surfaces are preferred over full product pages.
- Detail pages are fetched only for relevant selected candidates.
- HTTP calls use explicit timeouts, retries, backoff, rate limits, and concurrency bounds.
- Raw HTML is never sent to Gemini.
- Missing fields stay `null`; adapters must not fabricate values.
- Terms of service, robots directives, authentication requirements, and local law must be reviewed before enabling a source.

Wholesale-specific safeguards:

- Wholesale sources are separate from retail adapters and must return the typed `WholesaleListing` contract.
- The built-in feed adapter accepts only an explicitly configured public HTTPS JSON URL; it does not use browser automation, authenticated endpoints, or social-network APIs.
- Private, loopback, link-local, and reserved literal IP addresses are rejected to reduce SSRF risk. Feed responses have a strict byte limit and unknown listing fields are rejected.
- No social or messaging source is enabled by default. A future source requires explicit permission and a dedicated adapter review before implementation.
