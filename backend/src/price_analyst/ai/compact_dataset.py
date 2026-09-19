"""Deterministic construction of the bounded Gemini input boundary."""

from __future__ import annotations

import hashlib
import json
import re

from price_analyst.domain.ai_analysis import CompactAnalysisDataset, CompactOffer
from price_analyst.domain.local_analysis import LocalAnalysis
from price_analyst.domain.offers import Offer
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.statistics import PriceStatistics

_URL_PATTERN = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def _safe_text(value: str | None, *, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = _URL_PATTERN.sub("", value).strip()
    return cleaned[:max_length] or None


def _selected_offers(
    offers: list[Offer],
    *,
    max_offers: int,
    local_analysis: LocalAnalysis | None,
) -> list[Offer]:
    if max_offers < 1:
        raise ValueError("max_offers must be at least one")
    if local_analysis is None:
        return sorted(offers, key=lambda offer: offer.offer_id)[:max_offers]

    matches = {item.offer_id: item for item in local_analysis.matches}
    classifications = {
        item.offer_id: item for item in local_analysis.classifications
    }
    opportunity_ids = {
        item.offer_id
        for item in local_analysis.opportunities
        if item.offer_id is not None
    }

    def rank(offer: Offer) -> tuple[int, int, int, str, str]:
        match = matches.get(offer.offer_id)
        classification = classifications.get(offer.offer_id)
        return (
            0 if offer.offer_id in opportunity_ids else 1 if match and match.is_match else 2,
            0 if classification and classification.classification != "unknown" else 1,
            0 if offer.price is not None else 1,
            offer.source.value,
            offer.offer_id,
        )

    ranked = sorted(offers, key=rank)
    selected: list[Offer] = []
    selected_ids: set[str] = set()
    selected_sources: set[str] = set()
    # Keep at least one comparable offer from each source when the budget allows.
    for offer in ranked:
        if offer.source.value in selected_sources:
            continue
        selected.append(offer)
        selected_ids.add(offer.offer_id)
        selected_sources.add(offer.source.value)
        if len(selected) >= max_offers:
            return selected
    for offer in ranked:
        if offer.offer_id in selected_ids:
            continue
        selected.append(offer)
        if len(selected) >= max_offers:
            break
    return selected


def rehash_dataset(dataset: CompactAnalysisDataset) -> CompactAnalysisDataset:
    """Recompute the stable hash after a deterministic budget reduction."""

    without_hash = dataset.model_copy(update={"dataset_hash": None})
    canonical = json.dumps(
        without_hash.model_dump(mode="json", exclude={"dataset_hash"}),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    dataset_hash = hashlib.sha256(canonical).hexdigest()
    return without_hash.model_copy(update={"dataset_hash": dataset_hash})


def build_compact_dataset(
    query: NormalizedQuery,
    offers: list[Offer],
    statistics: PriceStatistics | None,
    *,
    max_offers: int,
    local_analysis: LocalAnalysis | None = None,
    statistics_by_currency: list[PriceStatistics] | None = None,
    stale: bool = False,
) -> CompactAnalysisDataset:
    """Build a bounded representation without URLs, descriptions, or HTML.

    Selection prioritizes deterministic opportunities and matched offers while
    retaining source diversity. The full offer list remains local and is never
    replaced by this compact representation.
    """

    selected = _selected_offers(
        offers,
        max_offers=max_offers,
        local_analysis=local_analysis,
    )
    matches = {item.offer_id: item for item in (local_analysis.matches if local_analysis else [])}
    classifications = {
        item.offer_id: item
        for item in (local_analysis.classifications if local_analysis else [])
    }
    compact_offers = [
        CompactOffer(
            offer_id=offer.offer_id,
            source=offer.source,
            title=_safe_text(offer.normalized_title, max_length=300),
            price=offer.price.amount if offer.price else None,
            currency=offer.price.currency if offer.price else None,
            seller=_safe_text(offer.seller, max_length=200),
            condition=offer.condition.value,
            availability=offer.availability.value,
            classification=(
                classifications[offer.offer_id].classification.value
                if offer.offer_id in classifications
                else None
            ),
            match_score=matches[offer.offer_id].score if offer.offer_id in matches else None,
        )
        for offer in selected
    ]
    reports = list(statistics_by_currency or [])
    if statistics is not None:
        reports = [report for report in reports if report != statistics]
    elif not reports:
        reports = []
    without_hash = CompactAnalysisDataset(
        product=query.normalized_text,
        offers=compact_offers,
        statistics=statistics,
        statistics_by_currency=reports,
        stale=stale,
    )
    return rehash_dataset(without_hash)
