from datetime import UTC, datetime

import pytest

from price_analyst.application.search_pipeline import SearchPipeline
from price_analyst.cache.in_memory import InMemorySnapshotCache
from price_analyst.collectors.interfaces import SearchContext
from price_analyst.collectors.registry import AdapterRegistry
from price_analyst.domain.enums import Currency, Marketplace
from price_analyst.domain.money import Money
from price_analyst.domain.offers import Offer, SearchCandidate
from price_analyst.domain.queries import NormalizedQuery


class FakeTorobAdapter:
    source = Marketplace.TOROB

    def __init__(self) -> None:
        self.search_calls = 0
        self.detail_calls = 0

    async def search(
        self,
        query: NormalizedQuery,
        context: SearchContext,
    ) -> list[SearchCandidate]:
        del query, context
        self.search_calls += 1
        return [
            SearchCandidate(
                source=Marketplace.TOROB,
                source_offer_id="product-1",
                title="Samsung S24 256GB",
                url="https://torob.com/p/product-1/",
                price=Money(amount=100, currency=Currency.IRT),
            ),
            SearchCandidate(
                source=Marketplace.TOROB,
                source_offer_id="product-2",
                title="Unrelated laptop",
                url="https://torob.com/p/product-2/",
                price=Money(amount=200, currency=Currency.IRT),
            ),
        ]

    async def fetch_details(
        self,
        candidate: SearchCandidate,
        context: SearchContext,
    ) -> list[Offer]:
        del context
        self.detail_calls += 1
        return [
            Offer(
                offer_id=f"torob:{candidate.source_offer_id}:seller",
                source=Marketplace.TOROB,
                source_offer_id=f"{candidate.source_offer_id}:seller",
                title=candidate.title,
                normalized_title=candidate.title.lower(),
                price=candidate.price,
                seller="Test seller",
                product_url=candidate.url,
                observed_at=datetime.now(UTC),
                details_fetched=True,
            )
        ]


@pytest.mark.asyncio
async def test_pipeline_fetches_details_for_only_top_candidates_and_caches_snapshot() -> None:
    adapter = FakeTorobAdapter()
    pipeline = SearchPipeline(
        AdapterRegistry([adapter]),
        cache=InMemorySnapshotCache(),
        max_detail_candidates=1,
    )

    first = await pipeline.run("Samsung S24 256GB")
    second = await pipeline.run("Samsung S24 256GB")

    assert first.collection_status.value == "complete"
    assert len(first.offers) == 2
    assert any(offer.details_fetched for offer in first.offers)
    assert adapter.search_calls == 1
    assert adapter.detail_calls == 1
    assert second.search_id == first.search_id


@pytest.mark.asyncio
async def test_pipeline_refresh_bypasses_snapshot_cache() -> None:
    adapter = FakeTorobAdapter()
    pipeline = SearchPipeline(
        AdapterRegistry([adapter]),
        cache=InMemorySnapshotCache(),
        max_detail_candidates=1,
    )

    await pipeline.run("Samsung S24")
    await pipeline.run("Samsung S24", refresh=True)

    assert adapter.search_calls == 2
    assert adapter.detail_calls == 2
