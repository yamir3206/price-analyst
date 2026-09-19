"""Deterministic construction of the compact Gemini input boundary."""

from __future__ import annotations

import hashlib
import json

from price_analyst.domain.ai_analysis import CompactAnalysisDataset, CompactOffer
from price_analyst.domain.offers import Offer
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.statistics import PriceStatistics


def build_compact_dataset(
    query: NormalizedQuery,
    offers: list[Offer],
    statistics: PriceStatistics | None,
    *,
    max_offers: int,
) -> CompactAnalysisDataset:
    """Build a bounded representation without URLs, descriptions, or HTML.

    Phase 1 uses stable offer-id ordering. The percentile/diversity-aware
    selection strategy is intentionally isolated here for Phase 4/5.
    """

    selected = sorted(offers, key=lambda offer: offer.offer_id)[:max_offers]
    compact_offers = [
        CompactOffer(
            offer_id=offer.offer_id,
            source=offer.source,
            price=offer.price.amount if offer.price else None,
            seller=offer.seller,
            condition=offer.condition.value,
            availability=offer.availability.value,
        )
        for offer in selected
    ]
    without_hash = CompactAnalysisDataset(
        product=query.normalized_text,
        offers=compact_offers,
        statistics=statistics,
    )
    canonical = json.dumps(
        without_hash.model_dump(mode="json", exclude={"dataset_hash"}),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    dataset_hash = hashlib.sha256(canonical).hexdigest()
    return without_hash.model_copy(update={"dataset_hash": dataset_hash})
