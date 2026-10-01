"""Deterministic chart data construction for the client."""

from __future__ import annotations

from collections.abc import Iterable

from price_analyst.domain.enums import Availability, Currency, PriceClassification
from price_analyst.domain.local_analysis import (
    DeduplicationGroup,
    OfferClassification,
    OfferMatch,
    PriceChart,
    PriceChartPoint,
)
from price_analyst.domain.offers import Offer
from price_analyst.domain.statistics import PriceStatistics


def build_price_charts(
    offers: Iterable[Offer],
    matches: Iterable[OfferMatch],
    classifications: Iterable[OfferClassification],
    groups: Iterable[DeduplicationGroup],
    statistics: Iterable[PriceStatistics],
) -> list[PriceChart]:
    """Build stable per-currency points without comparing unlike currencies."""

    offer_by_id = {offer.offer_id: offer for offer in offers}
    match_by_id = {match.offer_id: match for match in matches}
    class_by_id = {item.offer_id: item for item in classifications}
    group_by_offer_id = {
        offer_id: group.group_id for group in groups for offer_id in group.offer_ids
    }
    stats_by_currency = {
        report.currency: report for report in statistics if report.currency is not None
    }
    points_by_currency: dict[Currency, list[PriceChartPoint]] = {}
    for offer in offer_by_id.values():
        if not match_by_id.get(offer.offer_id, None) or not match_by_id[offer.offer_id].is_match:
            continue
        if (
            offer.availability is Availability.OUT_OF_STOCK
            or not offer.price
            or offer.price.currency not in stats_by_currency
        ):
            continue
        classification = class_by_id.get(offer.offer_id)
        points_by_currency.setdefault(offer.price.currency, []).append(
            PriceChartPoint(
                offer_id=offer.offer_id,
                source=offer.source,
                label=offer.seller or offer.source.value,
                amount=offer.price.amount,
                currency=offer.price.currency,
                classification=(
                    classification.classification
                    if classification
                    else PriceClassification.UNKNOWN
                ),
                group_id=group_by_offer_id.get(offer.offer_id),
            )
        )

    charts: list[PriceChart] = []
    for currency in sorted(points_by_currency, key=lambda item: item.value):
        report = stats_by_currency[currency]
        points = sorted(
            points_by_currency[currency],
            key=lambda point: (point.amount, point.source.value, point.offer_id),
        )
        charts.append(
            PriceChart(
                currency=currency,
                points=points,
                p25=report.p25,
                median=report.median,
                p75=report.p75,
            )
        )
    return charts
