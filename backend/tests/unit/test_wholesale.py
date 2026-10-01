from datetime import UTC, datetime

import httpx
import pytest

from price_analyst.application.wholesale_service import WholesaleService
from price_analyst.collectors.retry import RetryPolicy
from price_analyst.collectors.sources.public_wholesale_json import PublicWholesaleJsonAdapter
from price_analyst.collectors.wholesale import WholesaleSearchContext
from price_analyst.collectors.wholesale_registry import WholesaleAdapterRegistry
from price_analyst.domain.enums import CollectionStatus, Currency, SourceState
from price_analyst.domain.money import Money
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.wholesale import WholesaleListing


def query() -> NormalizedQuery:
    return NormalizedQuery(
        original="Samsung S24",
        normalized_text="samsung s24",
        variants=["samsung s24"],
    )


def listing(identifier: str, source: str = "test-feed") -> WholesaleListing:
    return WholesaleListing(
        listing_id=identifier,
        source=source,
        title="Samsung S24 wholesale",
        supplier_name="Public supplier",
        minimum_order_quantity=10,
        unit_price=Money(amount=90, currency=Currency.IRT),
        product_url="https://supplier.example/listing/1",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


class FakeWholesaleAdapter:
    source = "test-feed"

    def __init__(self) -> None:
        self.calls = 0
        self.fail = False

    async def search(self, query: NormalizedQuery, context: WholesaleSearchContext):
        del query, context
        self.calls += 1
        if self.fail:
            raise TimeoutError("feed unavailable")
        return [listing("test-feed:1")]


@pytest.mark.asyncio
async def test_wholesale_service_keeps_results_separate_and_reuses_stale_data() -> None:
    adapter = FakeWholesaleAdapter()
    service = WholesaleService(
        WholesaleAdapterRegistry([adapter]),
        source_timeout_seconds=1,
        max_listings=10,
    )

    first = await service.run("Samsung S24")
    adapter.fail = True
    refreshed = await service.run("Samsung S24", refresh=True)

    assert first.collection_status is CollectionStatus.COMPLETE
    assert refreshed.collection_status is CollectionStatus.PARTIAL
    assert refreshed.stale is True
    assert len(refreshed.listings) == 1
    assert refreshed.source_statuses[0].state is SourceState.STALE
    assert refreshed.source_statuses[0].stale_data_available is True
    assert adapter.calls == 2


@pytest.mark.asyncio
async def test_public_wholesale_json_adapter_is_bounded_and_maps_source() -> None:
    seen_query = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_query
        seen_query = request.url.params["q"]
        return httpx.Response(
            200,
            request=request,
            json={
                "listings": [
                    {
                        "listing_id": "feed:1",
                        "title": "Samsung S24 wholesale",
                        "minimum_order_quantity": 5,
                        "unit_price": {"amount": 90, "currency": "IRT"},
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = PublicWholesaleJsonAdapter(
            client,
            source="reviewed-feed",
            feed_url="https://wholesale.example/feed.json",
            retry_policy=RetryPolicy(max_attempts=1),
            max_response_bytes=10_000,
        )
        results = await adapter.search(
            query(),
            WholesaleSearchContext(request_id="test", max_listings=1),
        )

    assert seen_query == "samsung s24"
    assert len(results) == 1
    assert results[0].source == "reviewed-feed"
    assert results[0].unit_price == Money(amount=90, currency=Currency.IRT)


def test_public_wholesale_json_adapter_rejects_private_urls() -> None:
    with pytest.raises(ValueError, match="private address"):
        PublicWholesaleJsonAdapter(
            httpx.AsyncClient(),
            source="unsafe",
            feed_url="https://127.0.0.1/feed.json",
            retry_policy=RetryPolicy(max_attempts=1),
        )
