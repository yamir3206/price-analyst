"""Deterministic market-reference opportunity calculations."""

from __future__ import annotations

from collections.abc import Iterable

from price_analyst.domain.enums import Availability, Currency, PriceClassification
from price_analyst.domain.local_analysis import OfferClassification, OfferMatch
from price_analyst.domain.money import Money
from price_analyst.domain.offers import Offer
from price_analyst.domain.opportunities import OpportunityInputs, OpportunityResult
from price_analyst.domain.statistics import PriceStatistics


def _ensure_currency(value: Money | None, currency: Currency) -> None:
    if value is not None and value.currency is not currency:
        raise ValueError("opportunity costs must use the same currency as purchase price")


def calculate_opportunity(
    offer: Offer,
    expected_resale_price: Money,
    *,
    shipping: Money | None = None,
    platform_fee: Money | None = None,
    payment_fee: Money | None = None,
    other_costs: Money | None = None,
) -> OpportunityResult:
    """Calculate one opportunity using explicit, same-currency amounts."""

    if offer.price is None:
        raise ValueError("an opportunity requires a purchase price")
    currency = offer.price.currency
    if expected_resale_price.currency is not currency:
        raise ValueError("resale and purchase prices must use the same currency")
    for cost in (shipping, platform_fee, payment_fee, other_costs):
        _ensure_currency(cost, currency)

    total_cost = offer.price.amount + sum(
        cost.amount for cost in (shipping, platform_fee, payment_fee, other_costs) if cost
    )
    profit = expected_resale_price.amount - total_cost
    resale = expected_resale_price.amount
    return OpportunityResult(
        offer_id=offer.offer_id,
        currency=currency,
        total_cost=float(total_cost),
        profit=float(profit),
        profit_margin=round(profit / resale, 6) if resale else None,
        roi=round(profit / total_cost, 6) if total_cost else None,
        spread=float(expected_resale_price.amount - offer.price.amount),
        assumptions=OpportunityInputs(
            purchase_price=offer.price,
            expected_resale_price=expected_resale_price,
            shipping=shipping,
            platform_fee=platform_fee,
            payment_fee=payment_fee,
            other_costs=other_costs,
        ),
    )


def calculate_opportunities(
    offers: Iterable[Offer],
    matches: Iterable[OfferMatch],
    classifications: Iterable[OfferClassification],
    statistics: Iterable[PriceStatistics],
    *,
    max_results: int = 20,
) -> list[OpportunityResult]:
    """Return only positive, available below-market candidates.

    The expected resale reference is the comparable-market median. This is an
    explicit analytical assumption, not a promise of future resale value.
    """

    match_by_id = {item.offer_id: item for item in matches}
    class_by_id = {item.offer_id: item for item in classifications}
    stats_by_currency = {
        item.currency: item for item in statistics if item.currency is not None
    }
    opportunities: list[OpportunityResult] = []
    for offer in offers:
        if offer.availability is Availability.OUT_OF_STOCK:
            continue
        if not match_by_id.get(offer.offer_id, None) or not match_by_id[offer.offer_id].is_match:
            continue
        classification = class_by_id.get(offer.offer_id)
        if not classification or classification.classification not in {
            PriceClassification.BELOW_MARKET,
            PriceClassification.LOW_OUTLIER,
        }:
            continue
        if not offer.price:
            continue
        report = stats_by_currency.get(offer.price.currency)
        if not report or report.median is None or report.median <= offer.price.amount:
            continue
        expected_resale = Money(
            amount=round(report.median),
            currency=offer.price.currency,
        )
        try:
            result = calculate_opportunity(offer, expected_resale, shipping=offer.shipping)
        except ValueError:
            continue
        if result.profit > 0:
            result = result.model_copy(update={"classification": classification.classification})
            opportunities.append(result)

    opportunities.sort(
        key=lambda item: (
            -(item.profit_margin if item.profit_margin is not None else -1),
            -item.profit,
            item.offer_id,
        )
    )
    return opportunities[: max(0, max_results)]
