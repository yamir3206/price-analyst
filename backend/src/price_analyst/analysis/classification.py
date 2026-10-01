"""Deterministic relative-price classifications."""

from __future__ import annotations

from collections.abc import Iterable

from price_analyst.domain.enums import Availability, PriceClassification
from price_analyst.domain.local_analysis import OfferClassification, OfferMatch
from price_analyst.domain.offers import Offer
from price_analyst.domain.statistics import PriceStatistics


def classify_price(amount: int, statistics: PriceStatistics) -> PriceClassification:
    """Classify a price using quartiles and a deterministic 1.5 IQR fence."""

    if statistics.median is None or statistics.p25 is None or statistics.p75 is None:
        return PriceClassification.UNKNOWN
    iqr = statistics.p75 - statistics.p25
    if iqr > 0:
        if amount < statistics.p25 - 1.5 * iqr:
            return PriceClassification.LOW_OUTLIER
        if amount > statistics.p75 + 1.5 * iqr:
            return PriceClassification.HIGH_OUTLIER
    if amount < statistics.p25:
        return PriceClassification.BELOW_MARKET
    if amount > statistics.p75:
        return PriceClassification.ABOVE_MARKET
    return PriceClassification.TYPICAL


def classify_offers(
    offers: Iterable[Offer],
    matches: Iterable[OfferMatch],
    statistics: Iterable[PriceStatistics],
) -> list[OfferClassification]:
    """Classify every offer; unmatched or incomparable offers remain unknown."""

    match_by_id = {match.offer_id: match for match in matches}
    statistics_by_currency = {
        report.currency: report for report in statistics if report.currency is not None
    }
    result: list[OfferClassification] = []
    for offer in offers:
        match = match_by_id.get(offer.offer_id)
        price = offer.price
        report = statistics_by_currency.get(price.currency) if price else None
        if (
            not match
            or not match.is_match
            or offer.availability is Availability.OUT_OF_STOCK
            or not price
            or not report
        ):
            result.append(
                OfferClassification(
                    offer_id=offer.offer_id,
                    classification=PriceClassification.UNKNOWN,
                    price=price.amount if price else None,
                    currency=price.currency if price else None,
                )
            )
            continue
        median = report.median
        result.append(
            OfferClassification(
                offer_id=offer.offer_id,
                classification=classify_price(price.amount, report),
                price=price.amount,
                currency=price.currency,
                distance_from_median=(
                    round(price.amount - median, 6) if median is not None else None
                ),
                relative_to_median=(
                    round(price.amount / median - 1, 6) if median else None
                ),
            )
        )
    return result
