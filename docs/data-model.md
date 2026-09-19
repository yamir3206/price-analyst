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
- `CompactAnalysisDataset`
- `AIAnalysisEnvelope`

Missing source fields are represented as `null`. Models reject unknown fields at important boundaries to prevent accidental propagation of raw or unreviewed data.
