# Data model

Prices use an integer `amount` and explicit `currency`. Iranian rial (`IRR`) and toman (`IRT`) remain distinct until an explicit conversion policy exists.

The primary Phase 1 contracts are:

- `NormalizedQuery`
- `SearchCandidate`
- `Offer`
- `SourceStatus`
- `PriceStatistics`
- `OfferMatch`, `DeduplicationGroup`, `OfferClassification`, and `LocalAnalysis`
- `PriceChart` and `PriceChartPoint`
- `SearchSnapshot`
- `OpportunityInputs` and `OpportunityResult`
- `CompactAnalysisDataset` and its bounded `CompactOffer` records
- `AIAnalysis`, with separate facts, inferences, uncertainties, and validated offer-ID lists
- `AIAnalysisEnvelope`, carrying `not_requested`, `disabled`, `cached`, `completed`, `invalid_response`, or `failed` status
- `WholesaleListing`, `WholesaleSourceStatus`, and `WholesaleSnapshot`

`CompactAnalysisDataset` is an AI-only projection. The full `Offer` records remain in the `SearchSnapshot` and are never replaced by the compact selection. Compact records contain no URLs or raw HTML; prices retain their explicit `IRR`, `IRT`, or `UNKNOWN` currency. Missing source fields are represented as `null`. Models reject unknown fields at important boundaries to prevent accidental propagation of raw or unreviewed data.
