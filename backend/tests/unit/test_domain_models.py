from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from price_analyst.domain.ai_analysis import AIAnalysis, CompactAnalysisDataset
from price_analyst.domain.enums import Currency, Marketplace, OfferCondition
from price_analyst.domain.money import Money
from price_analyst.domain.offers import Offer
from price_analyst.domain.queries import NormalizedQuery


def make_offer(offer_id: str, amount: int) -> Offer:
    return Offer(
        offer_id=offer_id,
        source=Marketplace.TOROB,
        source_offer_id=offer_id,
        title="Samsung S24",
        normalized_title="samsung s24",
        price=Money(amount=amount, currency=Currency.IRT),
        seller="seller",
        product_url="https://example.com/product",
        condition=OfferCondition.NEW,
        observed_at=datetime.now(UTC),
    )


def test_money_is_explicit_and_exact() -> None:
    money = Money(amount=48_900_000, currency=Currency.IRT)
    assert money.amount == 48_900_000
    assert money.currency is Currency.IRT


def test_money_rejects_negative_amount() -> None:
    with pytest.raises(ValidationError):
        Money(amount=-1, currency=Currency.IRT)


def test_ai_output_is_strictly_typed() -> None:
    result = AIAnalysis(summary="Observed prices vary.", confidence=0.7)
    assert result.confidence == 0.7
    assert result.facts == []


def test_compact_dataset_does_not_need_full_offer_fields() -> None:
    query = NormalizedQuery(
        original="Samsung S24",
        normalized_text="samsung s24",
        variants=["samsung s24"],
    )
    compact = CompactAnalysisDataset(
        product=query.normalized_text,
        offers=[
            {
                "offer_id": "torob:1",
                "source": "torob",
                "price": 48_900_000,
                "condition": "new",
            }
        ],
    )
    assert "product_url" not in compact.model_dump()
    assert compact.offers[0].price == 48_900_000


def test_offer_requires_a_source_url() -> None:
    payload = make_offer("torob:1", 1).model_dump()
    payload["product_url"] = ""
    with pytest.raises(ValidationError):
        Offer.model_validate(payload)
