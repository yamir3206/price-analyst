from datetime import UTC, datetime
from pathlib import Path

import pytest

from price_analyst.collectors.sources.basalam.parser import BasalamParser
from price_analyst.collectors.sources.digikala.parser import DigikalaParser
from price_analyst.collectors.sources.divar.parser import DivarParser
from price_analyst.domain.enums import Currency, Marketplace, OfferCondition

FIXTURES = Path(__file__).parents[1] / "fixtures"
OBSERVED_AT = datetime(2026, 9, 19, tzinfo=UTC)


@pytest.mark.parametrize(
    ("parser", "source", "slug", "expected_id", "expected_currency"),
    [
        (BasalamParser(), Marketplace.BASALAM, "basalam", "123456", Currency.IRT),
        (DigikalaParser(), Marketplace.DIGIKALA, "digikala", "987654", Currency.IRT),
        (DivarParser(), Marketplace.DIVAR, "divar", "abc123xyz", Currency.IRT),
    ],
)
def test_public_search_and_detail_parsers_extract_deterministic_fields(
    parser,
    source: Marketplace,
    slug: str,
    expected_id: str,
    expected_currency: Currency,
) -> None:
    search_html = (FIXTURES / slug / "search.html").read_text(encoding="utf-8")
    product_html = (FIXTURES / slug / "product.html").read_text(encoding="utf-8")

    candidates = parser.parse_search_html(search_html, observed_at=OBSERVED_AT)
    assert len(candidates) == 1
    assert candidates[0].source is source
    assert candidates[0].source_offer_id == expected_id
    assert candidates[0].price is not None
    assert candidates[0].price.currency is expected_currency

    offers = parser.parse_product_html(
        product_html,
        product_url=candidates[0].url,
        observed_at=OBSERVED_AT,
    )
    assert len(offers) == 1
    assert offers[0].source is source
    assert offers[0].source_offer_id == expected_id
    assert offers[0].price is not None
    assert offers[0].price.currency is expected_currency
    assert offers[0].details_fetched is True
    assert offers[0].image_url is not None


def test_divar_parser_preserves_used_condition_without_inference() -> None:
    parser = DivarParser()
    html = (FIXTURES / "divar" / "product.html").read_text(encoding="utf-8")

    offers = parser.parse_product_html(
        html,
        product_url="https://divar.ir/v/galaxy-s24/abc123xyz",
        observed_at=OBSERVED_AT,
    )

    assert offers[0].condition is OfferCondition.USED
