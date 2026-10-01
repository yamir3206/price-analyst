"""Bounded wholesale collection kept outside the retail search pipeline."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from price_analyst.application.ports import WholesaleSnapshotCache
from price_analyst.cache.wholesale import InMemoryWholesaleSnapshotCache
from price_analyst.collectors.rate_limit import SourceRateLimiter
from price_analyst.collectors.wholesale import WholesaleAdapter, WholesaleSearchContext
from price_analyst.collectors.wholesale_registry import WholesaleAdapterRegistry
from price_analyst.domain.enums import CollectionStatus, SourceState
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.wholesale import (
    WholesaleListing,
    WholesaleSnapshot,
    WholesaleSourceStatus,
)
from price_analyst.normalization.query_normalizer import normalize_query


@dataclass(frozen=True, slots=True)
class _WholesaleCollection:
    source: str
    listings: list[WholesaleListing]
    status: WholesaleSourceStatus
    succeeded: bool


class WholesaleService:
    """Collect public wholesale listings with the same bounded-failure rules."""

    def __init__(
        self,
        registry: WholesaleAdapterRegistry,
        *,
        cache: WholesaleSnapshotCache | None = None,
        rate_limiter: SourceRateLimiter | None = None,
        cache_ttl_seconds: int = 300,
        source_timeout_seconds: float = 10.0,
        source_concurrency: int = 2,
        max_listings: int = 100,
    ) -> None:
        if cache_ttl_seconds < 0:
            raise ValueError("cache_ttl_seconds must not be negative")
        if source_timeout_seconds <= 0:
            raise ValueError("source_timeout_seconds must be positive")
        if source_concurrency < 1:
            raise ValueError("source_concurrency must be at least one")
        if max_listings < 1:
            raise ValueError("max_listings must be at least one")
        self._registry = registry
        self._cache = cache if cache is not None else InMemoryWholesaleSnapshotCache()
        self._rate_limiter = rate_limiter or SourceRateLimiter(0.0)
        self._cache_ttl_seconds = cache_ttl_seconds
        self._source_timeout_seconds = source_timeout_seconds
        self._source_concurrency = source_concurrency
        self._max_listings = max_listings

    async def run(self, query_text: str, *, refresh: bool = False) -> WholesaleSnapshot:
        query = normalize_query(query_text)
        cache_key = self._cache_key(query)
        previous = await self._cache.get(cache_key)
        if previous is not None and not refresh:
            return previous

        adapters = self._registry.all()
        now = datetime.now(UTC)
        search_id = uuid4()
        if not adapters:
            snapshot = WholesaleSnapshot(
                search_id=search_id,
                query=query,
                collection_status=CollectionStatus.NO_SOURCES_CONFIGURED,
                collected_at=now,
            )
            await self._cache.put(cache_key, snapshot, self._cache_ttl_seconds)
            return snapshot

        gate = asyncio.Semaphore(self._source_concurrency)
        request_id = str(search_id)

        async def collect(adapter: WholesaleAdapter) -> _WholesaleCollection:
            async with gate:
                return await self._collect_source(adapter, query, request_id)

        results = await asyncio.gather(*(collect(adapter) for adapter in adapters))
        listings: list[WholesaleListing] = []
        statuses: list[WholesaleSourceStatus] = []
        fresh_count = 0
        stale_count = 0
        for result in results:
            status = result.status
            statuses.append(status)
            if result.succeeded:
                fresh_count += 1
                listings.extend(result.listings)
                continue
            old = self._listings_for_source(previous, result.source)
            if old:
                stale_count += 1
                listings.extend(old)
                statuses[-1] = status.model_copy(
                    update={
                        "state": SourceState.STALE,
                        "listing_count": len(old),
                        "stale_data_available": True,
                        "stale_data_timestamp": previous.collected_at if previous else None,
                    }
                )

        if fresh_count == len(adapters) and stale_count == 0:
            collection_status = CollectionStatus.COMPLETE
        elif fresh_count or stale_count:
            collection_status = CollectionStatus.PARTIAL
        else:
            collection_status = CollectionStatus.FAILED

        snapshot = WholesaleSnapshot(
            search_id=search_id,
            query=query,
            listings=self._deduplicate_listings(listings)[: self._max_listings],
            source_statuses=statuses,
            collection_status=collection_status,
            collected_at=now,
            stale=stale_count > 0,
        )
        if fresh_count or stale_count:
            await self._cache.put(cache_key, snapshot, self._cache_ttl_seconds)
        return snapshot

    async def _collect_source(
        self,
        adapter: WholesaleAdapter,
        query: NormalizedQuery,
        request_id: str,
    ) -> _WholesaleCollection:
        context = WholesaleSearchContext(
            request_id=request_id,
            timeout_seconds=self._source_timeout_seconds,
            max_listings=self._max_listings,
        )
        try:
            await self._rate_limiter.acquire(adapter.source)
            raw = await asyncio.wait_for(
                adapter.search(query, context),
                timeout=self._source_timeout_seconds,
            )
            listings = self._deduplicate_listings(raw)[: self._max_listings]
        except (Exception, asyncio.CancelledError) as exc:
            if isinstance(exc, asyncio.CancelledError):
                raise
            return _WholesaleCollection(
                source=adapter.source,
                listings=[],
                succeeded=False,
                status=WholesaleSourceStatus(
                    source=adapter.source,
                    state=SourceState.UNAVAILABLE,
                    adapter_configured=True,
                    error_code=self._error_code(exc),
                    error_message="The wholesale source request failed.",
                ),
            )
        return _WholesaleCollection(
            source=adapter.source,
            listings=listings,
            succeeded=True,
            status=WholesaleSourceStatus(
                source=adapter.source,
                state=SourceState.READY,
                adapter_configured=True,
                listing_count=len(listings),
            ),
        )

    @staticmethod
    def _listings_for_source(
        snapshot: WholesaleSnapshot | None,
        source: str,
    ) -> list[WholesaleListing]:
        if snapshot is None:
            return []
        return [listing for listing in snapshot.listings if listing.source == source]

    @staticmethod
    def _deduplicate_listings(listings: list[WholesaleListing]) -> list[WholesaleListing]:
        unique: dict[str, WholesaleListing] = {}
        for listing in listings:
            unique.setdefault(listing.listing_id, listing)
        return [unique[key] for key in sorted(unique)]

    @staticmethod
    def _cache_key(query: NormalizedQuery) -> str:
        payload = json.dumps(
            query.model_dump(mode="json", exclude={"original", "variants"}),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"wholesale:v1:{hashlib.sha256(payload).hexdigest()}"

    @staticmethod
    def _error_code(error: Exception) -> str:
        if isinstance(error, (asyncio.TimeoutError, httpx.TimeoutException)):
            return "timeout"
        if isinstance(error, httpx.HTTPStatusError):
            return f"http_{error.response.status_code}"
        return "collection_error"
