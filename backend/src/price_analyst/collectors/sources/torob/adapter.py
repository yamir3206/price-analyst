"""Async Torob adapter using only public HTML surfaces."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

from price_analyst.collectors.http import get_with_retry
from price_analyst.collectors.interfaces import SearchContext
from price_analyst.collectors.retry import RetryPolicy
from price_analyst.collectors.sources.torob.parser import TorobParser
from price_analyst.domain.enums import Marketplace
from price_analyst.domain.offers import Offer, SearchCandidate
from price_analyst.domain.queries import NormalizedQuery


class TorobAdapter:
    """Collect Torob search candidates and selected product-page offers."""

    source = Marketplace.TOROB

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str = "https://torob.com",
        parser: TorobParser | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._parser = parser or TorobParser(base_url=self._base_url)
        self._retry_policy = retry_policy or RetryPolicy()

    async def search(
        self,
        query: NormalizedQuery,
        context: SearchContext,
    ) -> list[SearchCandidate]:
        response = await get_with_retry(
            self._client,
            f"{self._base_url}/search/",
            params={"query": query.normalized_text},
            timeout=context.timeout_seconds,
            policy=self._retry_policy,
        )
        return self._parser.parse_search_html(
            response.text,
            observed_at=datetime.now(UTC),
        )[: context.max_candidates]

    async def fetch_details(
        self,
        candidate: SearchCandidate,
        context: SearchContext,
    ) -> list[Offer]:
        candidate_host = urlsplit(candidate.url).netloc.lower()
        base_host = urlsplit(self._base_url).netloc.lower()
        if candidate_host and candidate_host != base_host:
            raise ValueError("refusing to fetch a product URL outside the configured Torob host")

        response = await get_with_retry(
            self._client,
            candidate.url,
            timeout=context.timeout_seconds,
            policy=self._retry_policy,
        )
        return self._parser.parse_product_html(
            response.text,
            product_url=candidate.url,
            observed_at=datetime.now(UTC),
        )
