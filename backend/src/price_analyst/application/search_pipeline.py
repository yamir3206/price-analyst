"""Deterministic search orchestration with bounded, refreshable source collection."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID, uuid4

import httpx

from price_analyst.analysis.service import analyze_offers
from price_analyst.application.ports import SnapshotCache
from price_analyst.application.source_health import SourceHealthTracker
from price_analyst.cache.in_memory import InMemorySnapshotCache
from price_analyst.collectors.interfaces import MarketplaceAdapter, SearchContext
from price_analyst.collectors.rate_limit import SourceRateLimiter
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
    partial_failure: bool = False


class SearchPipeline:
    """Coordinate independent adapters without putting source logic here."""

    def __init__(
        self,
        registry: AdapterRegistry,
        *,
        cache: SnapshotCache | None = None,
        health: SourceHealthTracker | None = None,
        rate_limiter: SourceRateLimiter | None = None,
        cache_ttl_seconds: int = 300,
        source_timeout_seconds: float = 10.0,
        max_search_candidates: int = 100,
        max_detail_candidates: int = 8,
        source_concurrency: int = 2,
        analysis_match_threshold: float = 0.55,
        analysis_max_opportunities: int = 20,
    ) -> None:
        if not 0 <= analysis_match_threshold <= 1:
            raise ValueError("analysis_match_threshold must be between zero and one")
        self._registry = registry
        self._cache = cache if cache is not None else InMemorySnapshotCache()
        self._health = health if health is not None else SourceHealthTracker()
        self._rate_limiter = rate_limiter if rate_limiter is not None else SourceRateLimiter(0.0)
        self._cache_ttl_seconds = cache_ttl_seconds
        self._source_timeout_seconds = source_timeout_seconds
        self._max_search_candidates = max_search_candidates
        self._max_detail_candidates = max_detail_candidates
        self._source_concurrency = max(1, source_concurrency)
        self._analysis_match_threshold = analysis_match_threshold
        self._analysis_max_opportunities = max(0, analysis_max_opportunities)

    async def run(self, query_text: str, *, refresh: bool = False) -> SearchSnapshot:
        query = normalize_query(query_text)
        cache_key = self._cache_key(query)
        previous = await self._cache.get(cache_key)
        if previous is not None and not refresh:
            return previous

        search_id = uuid4()
        request_id = str(search_id)
        now = datetime.now(UTC)
        configured = [
            (source, self._registry.get(source))
            for source in self._source_order()
            if self._registry.get(source) is not None
        ]
        if not configured:
            snapshot = self._snapshot_without_adapters(search_id, query, now, previous)
            await self._cache.put(cache_key, snapshot, self._cache_ttl_seconds)
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
        all_offers: list[Offer] = []
        statuses: dict[Marketplace, SourceStatus] = {}
        fresh_success_count = 0
        stale_source_count = 0
        has_partial_failure = False
        for result in results:
            statuses[result.source] = result.status
            has_partial_failure = has_partial_failure or result.partial_failure
            if result.search_succeeded:
                fresh_success_count += 1
                all_offers.extend(result.offers)
                continue
            old_offers = self._offers_for_source(previous, result.source)
            if old_offers:
                stale_source_count += 1
                all_offers.extend(old_offers)
                statuses[result.source] = self._stale_status(result.status, previous)

        for source in self._source_order():
            if source in statuses:
                continue
            old_offers = self._offers_for_source(previous, source)
            status = self._not_configured_status(source)
            if old_offers:
                stale_source_count += 1
                all_offers.extend(old_offers)
                status = self._stale_status(status, previous)
            statuses[source] = status

        if (
            fresh_success_count == len(configured)
            and stale_source_count == 0
            and not has_partial_failure
        ):
            collection_status = CollectionStatus.COMPLETE
        elif fresh_success_count > 0 or stale_source_count > 0:
            collection_status = CollectionStatus.PARTIAL
        else:
            collection_status = CollectionStatus.FAILED

        snapshot_offers = self._deduplicate_offers(all_offers)
        local_analysis = analyze_offers(
            query,
            snapshot_offers,
            match_threshold=self._analysis_match_threshold,
            max_opportunities=self._analysis_max_opportunities,
        )
        snapshot = SearchSnapshot(
            search_id=search_id,
            query=query,
            offers=snapshot_offers,
            statistics=local_analysis.primary_statistics,
            local_analysis=local_analysis.analysis,
            source_statuses=[statuses[source] for source in self._source_order()],
            collection_status=collection_status,
            collected_at=now,
            stale=stale_source_count > 0,
        )
        if fresh_success_count > 0 or stale_source_count > 0:
            await self._cache.put(cache_key, snapshot, self._cache_ttl_seconds)
        return snapshot

    async def _collect_source(
        self,
        adapter: MarketplaceAdapter,
        query: NormalizedQuery,
        request_id: str,
    ) -> _SourceCollection:
        if not await self._health.can_request(adapter.source):
            status = await self._health.status(adapter.source, state=SourceState.RATE_LIMITED)
            return _SourceCollection(
                source=adapter.source,
                offers=[],
                status=status,
                search_succeeded=False,
            )

        started = perf_counter()
        now = datetime.now(UTC)
        context = SearchContext(
            request_id=request_id,
            timeout_seconds=self._source_timeout_seconds,
            max_candidates=self._max_search_candidates,
        )
        try:
            await self._rate_limiter.acquire(adapter.source)
            raw_candidates = await asyncio.wait_for(
                adapter.search(query, context),
                timeout=self._source_timeout_seconds,
            )
        except Exception as exc:  # source failures must be isolated
            elapsed = self._elapsed_ms(started)
            await self._health.record_failure(
                adapter.source,
                error_code=self._error_code(exc),
                error_message="The source search request failed.",
                response_time_ms=elapsed,
            )
            status = await self._health.status(adapter.source, state=SourceState.UNAVAILABLE)
            return _SourceCollection(
                source=adapter.source,
                offers=[],
                status=status,
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

        elapsed = self._elapsed_ms(started)
        if detail_failures:
            await self._health.record_failure(
                adapter.source,
                error_code="detail_fetch_failed",
                error_message=f"{detail_failures} selected detail request(s) failed.",
                response_time_ms=elapsed,
            )
        else:
            await self._health.record_success(adapter.source, elapsed)
        status = await self._health.status(
            adapter.source,
            state=SourceState.READY,
            candidate_count=len(candidates),
            offer_count=len(offers),
        )
        return _SourceCollection(
            source=adapter.source,
            offers=offers,
            status=status,
            search_succeeded=True,
            partial_failure=detail_failures > 0,
        )

    async def _fetch_details(
        self,
        adapter: MarketplaceAdapter,
        candidate: SearchCandidate,
        context: SearchContext,
    ) -> tuple[SearchCandidate, list[Offer], Exception | None]:
        try:
            await self._rate_limiter.acquire(adapter.source)
            details = await asyncio.wait_for(
                adapter.fetch_details(candidate, context),
                timeout=self._source_timeout_seconds,
            )
            return candidate, details, None
        except Exception as exc:  # one product page must not fail the source
            return candidate, [], exc

    def _snapshot_without_adapters(
        self,
        search_id: UUID,
        query: NormalizedQuery,
        now: datetime,
        previous: SearchSnapshot | None,
    ) -> SearchSnapshot:
        offers: list[Offer] = []
        statuses: list[SourceStatus] = []
        stale = False
        for source in _INITIAL_MARKETPLACES:
            old_offers = self._offers_for_source(previous, source)
            status = self._not_configured_status(source)
            if old_offers:
                stale = True
                offers.extend(old_offers)
                status = self._stale_status(status, previous)
            statuses.append(status)
        snapshot_offers = self._deduplicate_offers(offers)
        local_analysis = analyze_offers(
            query,
            snapshot_offers,
            match_threshold=self._analysis_match_threshold,
            max_opportunities=self._analysis_max_opportunities,
        )
        return SearchSnapshot(
            search_id=search_id,
            query=query,
            offers=snapshot_offers,
            statistics=local_analysis.primary_statistics,
            local_analysis=local_analysis.analysis,
            source_statuses=statuses,
            collection_status=CollectionStatus.NO_SOURCES_CONFIGURED,
            collected_at=now,
            stale=stale,
        )

    @staticmethod
    def _offers_for_source(
        snapshot: SearchSnapshot | None,
        source: Marketplace,
    ) -> list[Offer]:
        if snapshot is None:
            return []
        return [offer for offer in snapshot.offers if offer.source is source]

    @staticmethod
    def _stale_status(status: SourceStatus, previous: SearchSnapshot | None) -> SourceStatus:
        timestamp = previous.collected_at if previous else None
        old_offers = SearchPipeline._offers_for_source(previous, status.source)
        return status.model_copy(
            update={
                "state": SourceState.STALE,
                "offer_count": len(old_offers),
                "stale_data_available": True,
                "stale_data_timestamp": timestamp,
                "error_message": status.error_message
                or "Using the most recent cached data for this source.",
            }
        )

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
