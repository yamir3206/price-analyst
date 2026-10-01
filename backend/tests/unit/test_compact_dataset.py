from datetime import UTC, datetime

from price_analyst.ai.compact_dataset import build_compact_dataset
from price_analyst.domain.enums import Currency, Marketplace
from price_analyst.domain.money import Money
from price_analyst.domain.offers import Offer
from price_analyst.domain.queries import NormalizedQuery


def offer(identifier: str, price: int) -> Offer:
    return Offer(
        offer_id=identifier,
        source=Marketplace.TOROB,
        source_offer_id=identifier,
        title="Verbose title that must not enter the compact payload",
        normalized_title="verbose title",
        price=Money(amount=price, currency=Currency.IRT),
        seller="seller",
        product_url="https://example.com/with/tracking?utm_source=test",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_compact_dataset_is_bounded_and_hash_is_stable() -> None:
    query = NormalizedQuery(
        original="Samsung S24",
        normalized_text="samsung s24",
        variants=["samsung s24"],
    )
    offers = [offer(f"torob:{index:03d}", 40_000_000 + index) for index in range(5)]

    first = build_compact_dataset(query, offers, None, max_offers=2)
    second = build_compact_dataset(query, list(reversed(offers)), None, max_offers=2)

    assert len(first.offers) == 2
    assert first.dataset_hash == second.dataset_hash
    assert all("product_url" not in item.model_dump() for item in first.offers)
    assert [item.offer_id for item in first.offers] == ["torob:000", "torob:001"]
