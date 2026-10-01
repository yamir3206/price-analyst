"""Deterministic query matching and product-equivalence grouping."""

from price_analyst.matching.deduplicator import DeduplicationResult, deduplicate_offers
from price_analyst.matching.matcher import match_offer, match_offers

__all__ = [
    "DeduplicationResult",
    "deduplicate_offers",
    "match_offer",
    "match_offers",
]
