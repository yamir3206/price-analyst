"""Deterministic search orchestration with bounded source/detail collection."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

import httpx

from price_analyst.application.ports import SnapshotCache
from price_analyst.collectors.interfaces import MarketplaceAdapter, SearchContext
from price_analyst.collectors.registry import AdapterRegistry
from price_analyst.collectors.relevance import rank_candidates
from price_analyst.domain.enums import CollectionStatus, Marketplace, SourceState
from price_analyst.domain.offers import Offer, SearchCandidate
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.snapshots import SearchSnapshot
from price_analyst.domain.source_health import SourceStatus
from price_analyst.normalization.query_normalizer import normalize_query, normalize_text

_INITIAL_MARKETPLACES = (
    Marketplace.TOROB,
    Marketplace.BASALAM,
    Marketplace.DIGIKALA,
    Marketplace.DIVAR,
)


@dataclass(frozen=True, slots=True)
class _SourceCollection:
    source: Marketplace
    offers: list[Offer]
    status: SourceStatus
    search_succeeded: bool


class SearchPipeline:
    """Coordinate independent adapters without putting source logic here."""

    def __init__(
        self,
        registry: AdapterRegistry,
        *,
        cache: SnapshotCache | None = None,
        cache_ttl_seconds: int = 300,
        source_timeout_seconds: float = 10.0,
        max_search_candidates: int = 100,
        max_detail_candidates: int = 8,
        source_concurrency: int = 2,
    ) -> None:
        self._registry = registry
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._source_timeout_seconds = source_timeout_seconds
        self._max_search_candidates = max_search_candidates
        self._max_detail_candidates = max_detail_candidates
        self._source_concurrency = max(1, source_concurrency)

    async def run(self, query_text: str, *, refresh: bool = False) -> SearchSnapshot:
        query = normalize_query(query_text)
        cache_key = self._cache_key(query)
        if self._cache is not None and not refresh:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached

        search_id = uuid4()
        request_id = str(search_id)
        now = datetime.now(UTC)
        configured = [
            (source, self._registry.get(source))
            for source in self._source_order()
            if self._registry.get(source) is not None
        ]
        if not configured:
            snapshot = SearchSnapshot(
                search_id=search_id,
                query=query,
                source_statuses=[
                    self._not_configured_status(source) for source in _INITIAL_MARKETPLACES
                ],
                collection_status=CollectionStatus.NO_SOURCES_CONFIGURED,
                collected_at=now,
            )
            await self._cache_snapshot(cache_key, snapshot)
            return snapshot

        source_gate = asyncio.Semaphore(self._source_concurrency)

        async def collect_one(
            source: Marketplace,
            adapter: MarketplaceAdapter | None,
        ) -> _SourceCollection:
            if adapter is None:
                return _SourceCollection(
                    source=source,
                    offers=[],
                    status=self._not_configured_status(source),
                    search_succeeded=False,
                )
            async with source_gate:
                return await self._collect_source(adapter, query, request_id)

        results = await asyncio.gather(
            *(collect_one(source, adapter) for source, adapter in configured)
        )
        successful = [result for result in results if result.search_succeeded]
        all_offers = self._deduplicate_offers(
            [offer for result in results for offer in result.offers]
        )
        statuses = self._merge_statuses(results)
        successful_count = len(successful)
        has_detail_failures = any(result.status.last_failure is not None for result in successful)
        if successful_count == len(configured) and not has_detail_failures:
            collection_status = CollectionStatus.COMPLETE
        elif successful_count > 0:
            collection_status = CollectionStatus.PARTIAL
        else:
            collection_status = CollectionStatus.FAILED

        snapshot = SearchSnapshot(
            search_id=search_id,
            query=query,
            offers=all_offers,
            source_statuses=statuses,
            collection_status=collection_status,
            collected_at=now,
        )
        if successful_count > 0:
            await self._cache_snapshot(cache_key, snapshot)
        return snapshot

    async def _collect_source(
        self,
        adapter: MarketplaceAdapter,
        query: NormalizedQuery,
        request_id: str,
    ) -> _SourceCollection:
        started = perf_counter()
        now = datetime.now(UTC)
        context = SearchContext(
            request_id=request_id,
            timeout_seconds=self._source_timeout_seconds,
            max_candidates=self._max_search_candidates,
        )
        try:
            raw_candidates = await asyncio.wait_for(
                adapter.search(query, context),
                timeout=self._source_timeout_seconds,
            )
        except Exception as exc:  # source failures must be isolated
            return _SourceCollection(
                source=adapter.source,
                offers=[],
                status=SourceStatus(
                    source=adapter.source,
                    state=SourceState.UNAVAILABLE,
                    adapter_configured=True,
                    last_failure=now,
                    failure_count=1,
                    average_response_time_ms=self._elapsed_ms(started),
                    error_code=self._error_code(exc),
                    error_message="The source search request failed.",
                ),
                search_succeeded=False,
            )

        candidates = self._deduplicate_candidates(raw_candidates[: self._max_search_candidates])
        selected = rank_candidates(
            query,
            candidates,
            limit=min(self._max_detail_candidates, len(candidates)),
        )
        selected_ids = {candidate.source_offer_id for candidate in selected}
        detail_results = await asyncio.gather(
            *(self._fetch_details(adapter, candidate, context) for candidate in selected)
        )

        offers: list[Offer] = []
        detail_failures = 0
        for candidate in candidates:
            if candidate.source_offer_id not in selected_ids:
                offers.append(self._candidate_to_offer(candidate, now))
        for candidate, details, error in detail_results:
            if error is not None or not details:
                detail_failures += 1 if error is not None else 0
                offers.append(self._candidate_to_offer(candidate, now))
            else:
                offers.extend(details)

        error_message = None
        error_code = None
        last_failure = None
        if detail_failures:
            last_failure = now
            error_code = "detail_fetch_failed"
            error_message = f"{detail_failures} selected product detail request(s) failed."
        status = SourceStatus(
            source=adapter.source,
            state=SourceState.READY,
            adapter_configured=True,
            last_success=now,
            last_failure=last_failure,
            average_response_time_ms=self._elapsed_ms(started),
            candidate_count=len(candidates),
            offer_count=len(offers),
            failure_count=detail_failures,
            error_code=error_code,
            error_message=error_message,
        )
        return _SourceCollection(
            source=adapter.source,
            offers=offers,
            status=status,
            search_succeeded=True,
        )

    async def _fetch_details(
        self,
        adapter: MarketplaceAdapter,
        candidate: SearchCandidate,
        context: SearchContext,
    ) -> tuple[SearchCandidate, list[Offer], Exception | None]:
        try:
            details = await asyncio.wait_for(
                adapter.fetch_details(candidate, context),
                timeout=self._source_timeout_seconds,
            )
            return candidate, details, None
        except Exception as exc:  # one product page must not fail the source
            return candidate, [], exc

    def _candidate_to_offer(self, candidate: SearchCandidate, observed_at: datetime) -> Offer:
        metadata = dict(candidate.metadata)
        metadata["collection_stage"] = "search"
        return Offer(
            offer_id=f"{candidate.source.value}:search:{candidate.source_offer_id}",
            source=candidate.source,
            source_offer_id=candidate.source_offer_id,
            title=candidate.title,
            normalized_title=normalize_text(candidate.title),
            price=candidate.price,
            seller=candidate.seller,
            product_url=candidate.url,
            availability=candidate.availability,
            condition=candidate.condition,
            brand=candidate.brand,
            model=candidate.model,
            capacity=candidate.capacity,
            observed_at=observed_at,
            details_fetched=False,
            metadata=metadata,
        )

    def _source_order(self) -> tuple[Marketplace, ...]:
        registered = self._registry.sources()
        return tuple(dict.fromkeys((*_INITIAL_MARKETPLACES, *registered)))

    def _merge_statuses(self, results: list[_SourceCollection]) -> list[SourceStatus]:
        statuses = {result.source: result.status for result in results}
        return [
            statuses.get(source, self._not_configured_status(source))
            for source in self._source_order()
        ]

    @staticmethod
    def _deduplicate_candidates(candidates: list[SearchCandidate]) -> list[SearchCandidate]:
        seen: set[tuple[Marketplace, str]] = set()
        result: list[SearchCandidate] = []
        for candidate in candidates:
            key = (candidate.source, candidate.source_offer_id)
            if key in seen:
                continue
            seen.add(key)
            result.append(candidate)
        return result

    @staticmethod
    def _deduplicate_offers(offers: list[Offer]) -> list[Offer]:
        seen: set[str] = set()
        result: list[Offer] = []
        for offer in offers:
            if offer.offer_id in seen:
                continue
            seen.add(offer.offer_id)
            result.append(offer)
        return result

    @staticmethod
    def _not_configured_status(source: Marketplace) -> SourceStatus:
        return SourceStatus(
            source=source,
            state=SourceState.NOT_CONFIGURED,
            adapter_configured=False,
            error_code="adapter_not_configured",
            error_message="This marketplace adapter is not enabled yet.",
        )

    async def _cache_snapshot(self, key: str, snapshot: SearchSnapshot) -> None:
        if self._cache is not None:
            await self._cache.put(key, snapshot, self._cache_ttl_seconds)

    @staticmethod
    def _cache_key(query: NormalizedQuery) -> str:
        payload = json.dumps(
            query.model_dump(mode="json", exclude={"original", "variants"}),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"search:v1:{hashlib.sha256(payload).hexdigest()}"

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return round((perf_counter() - started) * 1000, 2)

    @staticmethod
    def _error_code(error: Exception) -> str:
        if isinstance(error, (asyncio.TimeoutError, httpx.TimeoutException)):
            return "timeout"
        if isinstance(error, httpx.HTTPStatusError):
            return f"http_{error.response.status_code}"
        return "collection_error"
