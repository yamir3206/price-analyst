from datetime import UTC, datetime
from pathlib import Path

from price_analyst.collectors.sources.torob.normalizer import parse_money
from price_analyst.collectors.sources.torob.parser import TorobParser
from price_analyst.domain.enums import Availability, Currency, OfferCondition

FIXTURES = Path(__file__).parents[1] / "fixtures" / "torob"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_search_parser_prefers_json_ld_and_deduplicates_dom_cards() -> None:
    parser = TorobParser()
    candidates = parser.parse_search_html(
        fixture("search.html"),
        observed_at=datetime(2026, 9, 19, tzinfo=UTC),
    )

    assert [candidate.source_offer_id for candidate in candidates] == [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    ]
    assert candidates[0].price is not None
    assert candidates[0].price.amount == 467_000_000
    assert candidates[0].price.currency is Currency.IRR
    assert candidates[0].metadata["parser"] == "json_ld"


def test_search_parser_supports_dom_fallback_and_scaled_prices() -> None:
    parser = TorobParser()
    candidates = parser.parse_search_html(
        fixture("search_dom_only.html"),
        observed_at=datetime(2026, 9, 19, tzinfo=UTC),
    )

    assert len(candidates) == 1
    assert candidates[0].title == "گوشی تستی"
    assert candidates[0].price is not None
    assert candidates[0].price.amount == 1_200_000
    assert candidates[0].price.currency is Currency.IRT


def test_product_parser_extracts_seller_offers_and_preserves_condition() -> None:
    parser = TorobParser()
    offers = parser.parse_product_html(
        fixture("product.html"),
        product_url="https://torob.com/p/11111111-1111-1111-1111-111111111111/s24-fe/",
        observed_at=datetime(2026, 9, 19, tzinfo=UTC),
    )

    assert len(offers) == 2
    assert offers[0].source_offer_id == "offer-one"
    assert offers[0].seller == "فروشگاه آفتاب"
    assert offers[0].price is not None
    assert offers[0].price.amount == 467_000_000
    assert offers[0].price.currency is Currency.IRR
    assert offers[0].availability is Availability.IN_STOCK
    assert offers[1].condition is OfferCondition.USED
    assert offers[1].price is not None
    assert offers[1].price.amount == 184_400_000
    assert offers[1].price.currency is Currency.IRT
    assert offers[0].product_url.endswith("/s24-fe/")


def test_price_parser_does_not_invent_currency() -> None:
    assert parse_money("۴۶۷٫۰۰۰٫۰۰۰ ریال").currency is Currency.IRR
    assert parse_money("۴۶٫۷۰۰٫۰۰۰ تومان").currency is Currency.IRT
    assert parse_money("ناموجود") is None
