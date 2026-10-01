"""Exact-currency deterministic price statistics."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal

from price_analyst.domain.enums import Currency
from price_analyst.domain.money import Money
from price_analyst.domain.offers import Offer
from price_analyst.domain.statistics import PriceStatistics


def _rounded(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("quantile requires at least one value")
    if len(values) == 1:
        return values[0]
    position = fraction * (len(values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] + (values[upper] - values[lower]) * weight


def calculate_price_statistics(
    prices: Iterable[Money],
    *,
    currency: Currency | None = None,
) -> PriceStatistics:
    """Calculate statistics without converting or mixing explicit currencies."""

    values = list(prices)
    currencies = {price.currency for price in values}
    if currency is not None:
        unexpected = currencies - {currency}
        if unexpected:
            raise ValueError("price statistics cannot mix currencies")
    if len(currencies) > 1:
        raise ValueError("price statistics cannot mix currencies")
    selected_currency = next(iter(currencies), currency)
    amounts = sorted(float(price.amount) for price in values)
    if not amounts:
        return PriceStatistics(count=0, currency=selected_currency)

    mean = sum(amounts) / len(amounts)
    variance = sum((amount - mean) ** 2 for amount in amounts) / len(amounts)
    standard_deviation = math.sqrt(variance)
    p25 = _quantile(amounts, 0.25)
    median = _quantile(amounts, 0.50)
    p75 = _quantile(amounts, 0.75)
    p10 = _quantile(amounts, 0.10)
    p90 = _quantile(amounts, 0.90)
    return PriceStatistics(
        count=len(amounts),
        currency=selected_currency,
        minimum=_rounded(amounts[0]),
        p10=_rounded(p10),
        p25=_rounded(p25),
        median=_rounded(median),
        p50=_rounded(median),
        p75=_rounded(p75),
        p90=_rounded(p90),
        mean=_rounded(mean),
        maximum=_rounded(amounts[-1]),
        standard_deviation=_rounded(standard_deviation),
        price_range=_rounded(amounts[-1] - amounts[0]),
        coefficient_of_variation=_rounded(standard_deviation / mean if mean else None),
    )


def statistics_by_currency(
    offers: Iterable[Offer],
    *,
    include_unknown: bool = False,
) -> list[PriceStatistics]:
    """Return independent reports; unknown currency is excluded by default."""

    grouped: defaultdict[Currency, list[Money]] = defaultdict(list)
    for offer in offers:
        if offer.price is None:
            continue
        if offer.price.currency is Currency.UNKNOWN and not include_unknown:
            continue
        grouped[offer.price.currency].append(offer.price)
    return [
        calculate_price_statistics(grouped[currency], currency=currency)
        for currency in sorted(grouped, key=lambda item: item.value)
    ]


def primary_statistics(statistics: Iterable[PriceStatistics]) -> PriceStatistics | None:
    """Select a stable primary report for legacy single-report API fields."""

    reports = list(statistics)
    if not reports:
        return None
    largest_count = max(report.count for report in reports)
    largest = [report for report in reports if report.count == largest_count]
    return largest[0] if len(largest) == 1 else None


def decimal_amount(statistics: PriceStatistics | None, field: str) -> Decimal | None:
    """Expose a Decimal helper for callers that need exact downstream arithmetic."""

    value = getattr(statistics, field, None) if statistics else None
    return Decimal(str(value)) if value is not None else None
