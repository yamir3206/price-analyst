import asyncio
from time import perf_counter

import httpx
import pytest

from price_analyst.application.search_pipeline import SearchPipeline
from price_analyst.application.source_health import SourceHealthTracker
from price_analyst.cache.in_memory import InMemorySnapshotCache
from price_analyst.collectors.http import get_with_retry
from price_analyst.collectors.interfaces import SearchContext
from price_analyst.collectors.rate_limit import SourceRateLimiter
from price_analyst.collectors.registry import AdapterRegistry
from price_analyst.collectors.retry import RetryPolicy
from price_analyst.domain.enums import Currency, Marketplace, SourceState
from price_analyst.domain.money import Money
from price_analyst.domain.offers import Offer, SearchCandidate
from price_analyst.domain.queries import NormalizedQuery


@pytest.mark.asyncio
async def test_http_get_retries_transient_5xx_with_bounded_attempts() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, text="ok", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await get_with_retry(
            client,
            "https://source.test/search",
            policy=RetryPolicy(max_attempts=2, base_delay_seconds=0, max_delay_seconds=0),
            timeout=1,
        )

    assert response.text == "ok"
    assert calls == 2


@pytest.mark.asyncio
async def test_health_tracker_temporarily_disables_after_consecutive_failures() -> None:
    tracker = SourceHealthTracker(failure_threshold=2, cooldown_seconds=60)

    await tracker.record_failure(
        Marketplace.BASALAM,
        error_code="timeout",
        error_message="timed out",
        response_time_ms=10,
    )
    await tracker.record_failure(
        Marketplace.BASALAM,
        error_code="timeout",
        error_message="timed out",
        response_time_ms=11,
    )

    assert await tracker.can_request(Marketplace.BASALAM) is False
    status = await tracker.status(Marketplace.BASALAM)
    assert status.state is SourceState.RATE_LIMITED
    assert status.failure_count == 2
    assert status.temporary_disabled_until is not None

    await tracker.record_success(Marketplace.BASALAM, 5)
    assert await tracker.can_request(Marketplace.BASALAM) is True
    assert (await tracker.status(Marketplace.BASALAM)).failure_count == 0


@pytest.mark.asyncio
async def test_rate_limiter_tracks_each_marketplace_independently() -> None:
    limiter = SourceRateLimiter(0.02)

    await limiter.acquire(Marketplace.BASALAM)
    started = perf_counter()
    await asyncio.gather(
        limiter.acquire(Marketplace.BASALAM),
        limiter.acquire(Marketplace.DIVAR),
    )
    elapsed = perf_counter() - started

    assert elapsed >= 0.015


class FlakyAdapter:
    source = Marketplace.TOROB

    def __init__(self) -> None:
        self.search_calls = 0

    async def search(
        self,
        query: NormalizedQuery,
        context: SearchContext,
    ) -> list[SearchCandidate]:
        del query, context
        self.search_calls += 1
        if self.search_calls > 1:
            raise TimeoutError("source unavailable")
        return [
            SearchCandidate(
                source=self.source,
                source_offer_id="cached-1",
                title="Samsung S24 256GB",
                url="https://torob.com/p/cached-1",
                price=Money(amount=100, currency=Currency.IRT),
            )
        ]

    async def fetch_details(
        self,
        candidate: SearchCandidate,
        context: SearchContext,
    ) -> list[Offer]:
        del candidate, context
        return []


class DetailFailingAdapter(FlakyAdapter):
    async def fetch_details(
        self,
        candidate: SearchCandidate,
        context: SearchContext,
    ) -> list[Offer]:
        del candidate, context
        raise ConnectionError("detail unavailable")


@pytest.mark.asyncio
async def test_detail_failure_returns_partial_search_candidate() -> None:
    pipeline = SearchPipeline(
        AdapterRegistry([DetailFailingAdapter()]),
        cache=InMemorySnapshotCache(),
        max_detail_candidates=1,
    )

    snapshot = await pipeline.run("Samsung S24 256GB")

    assert snapshot.collection_status.value == "partial"
    assert len(snapshot.offers) == 1
    assert snapshot.offers[0].details_fetched is False


@pytest.mark.asyncio
async def test_refresh_uses_stale_offers_when_a_source_fails() -> None:
    adapter = FlakyAdapter()
    pipeline = SearchPipeline(
        AdapterRegistry([adapter]),
        cache=InMemorySnapshotCache(),
        health=SourceHealthTracker(failure_threshold=3, cooldown_seconds=60),
        max_detail_candidates=1,
    )

    first = await pipeline.run("Samsung S24 256GB")
    refreshed = await pipeline.run("Samsung S24 256GB", refresh=True)

    assert first.collection_status.value == "complete"
    assert refreshed.collection_status.value == "partial"
    assert refreshed.stale is True
    assert len(refreshed.offers) == 1
    torob_status = next(
        status for status in refreshed.source_statuses if status.source is Marketplace.TOROB
    )
    assert torob_status.state is SourceState.STALE
    assert torob_status.stale_data_available is True
    assert adapter.search_calls == 2
