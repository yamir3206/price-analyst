from datetime import UTC, datetime

import pytest

from price_analyst.analysis.opportunities import calculate_opportunity
from price_analyst.analysis.service import analyze_offers
from price_analyst.analysis.statistics import calculate_price_statistics
from price_analyst.domain.enums import Currency, Marketplace, PriceClassification
from price_analyst.domain.money import Money
from price_analyst.domain.offers import Offer
from price_analyst.matching.deduplicator import deduplicate_offers
from price_analyst.matching.matcher import match_offer
from price_analyst.normalization.query_normalizer import normalize_query


def make_offer(
    identifier: str,
    amount: int,
    *,
    source: Marketplace = Marketplace.TOROB,
    source_offer_id: str | None = None,
    product_url: str | None = None,
    seller: str = "seller",
    currency: Currency = Currency.IRT,
    details_fetched: bool = True,
) -> Offer:
    return Offer(
        offer_id=identifier,
        source=source,
        source_offer_id=source_offer_id or identifier,
        title="گوشی Samsung S24 256GB",
        normalized_title="گوشی samsung s24 256gb",
        price=Money(amount=amount, currency=currency),
        seller=seller,
        product_url=product_url or f"https://example.test/products/{identifier}",
        brand="Samsung",
        model="S24",
        capacity="256GB",
        observed_at=datetime(2026, 9, 19, tzinfo=UTC),
        details_fetched=details_fetched,
    )


def test_price_statistics_use_interpolated_percentiles_and_explicit_currency() -> None:
    report = calculate_price_statistics(
        [
            Money(amount=100, currency=Currency.IRT),
            Money(amount=200, currency=Currency.IRT),
            Money(amount=300, currency=Currency.IRT),
            Money(amount=400, currency=Currency.IRT),
        ]
    )

    assert report.count == 4
    assert report.currency is Currency.IRT
    assert report.minimum == 100
    assert report.p10 == 130
    assert report.p25 == 175
    assert report.median == 250
    assert report.p75 == 325
    assert report.maximum == 400
    assert report.price_range == 300


def test_price_statistics_reject_mixed_currencies_without_conversion() -> None:
    with pytest.raises(ValueError, match="cannot mix currencies"):
        calculate_price_statistics(
            [
                Money(amount=100, currency=Currency.IRT),
                Money(amount=1000, currency=Currency.IRR),
            ]
        )


def test_matcher_marks_explicit_capacity_mismatch_as_not_matching() -> None:
    query = normalize_query("Samsung S24 256GB")
    offer = make_offer("wrong", 100, source_offer_id="wrong")
    offer = offer.model_copy(update={"capacity": "128GB", "title": "Samsung S24 128GB"})

    result = match_offer(query, offer)

    assert result.is_match is False
    assert result.score < 0.55
    assert "capacity" in result.mismatched_fields


def test_deduplication_removes_exact_repeats_but_preserves_marketplace_prices() -> None:
    first = make_offer(
        "search-record",
        100,
        source_offer_id="same-listing",
        product_url="https://example.test/product/1?tracking=old",
        details_fetched=False,
    )
    detail = make_offer(
        "detail-record",
        100,
        source_offer_id="same-listing",
        product_url="https://example.test/product/1?tracking=new",
        details_fetched=True,
    )
    other_marketplace = make_offer(
        "other-marketplace",
        120,
        source=Marketplace.DIGIKALA,
        source_offer_id="different-listing",
        product_url="https://other.test/product/2",
    )

    result = deduplicate_offers([first, detail, other_marketplace])

    assert len(result.unique_offers) == 2
    assert result.unique_offers[0].offer_id == "detail-record"
    assert len(result.groups) == 1
    assert set(result.groups[0].offer_ids) == {
        "search-record",
        "detail-record",
        "other-marketplace",
    }
    assert result.group_by_offer_id["other-marketplace"] == result.groups[0].group_id


def test_local_analysis_builds_classifications_chart_and_opportunity() -> None:
    query = normalize_query("Samsung S24 256GB")
    offers = [make_offer("cheap", 80), make_offer("typical", 100), make_offer("high", 120)]

    result = analyze_offers(query, offers)

    assert result.primary_statistics is not None
    assert result.primary_statistics.median == 100
    classifications = {
        item.offer_id: item.classification for item in result.analysis.classifications
    }
    assert classifications["cheap"] is PriceClassification.BELOW_MARKET
    assert classifications["typical"] is PriceClassification.TYPICAL
    assert classifications["high"] is PriceClassification.ABOVE_MARKET
    assert len(result.analysis.price_charts) == 1
    assert [point.offer_id for point in result.analysis.price_charts[0].points] == [
        "cheap",
        "typical",
        "high",
    ]
    assert [item.offer_id for item in result.analysis.opportunities] == ["cheap"]
    assert result.analysis.opportunities[0].profit == 20


def test_opportunity_costs_must_match_purchase_currency() -> None:
    offer = make_offer("offer", 100)

    with pytest.raises(ValueError, match="same currency"):
        calculate_opportunity(
            offer,
            Money(amount=150, currency=Currency.IRT),
            shipping=Money(amount=10, currency=Currency.IRR),
        )
