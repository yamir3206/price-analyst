"""Source-neutral adapter for an explicitly permitted public wholesale JSON feed."""

from __future__ import annotations

import ipaddress
from collections.abc import Mapping
from typing import cast
from urllib.parse import urlparse

import httpx

from price_analyst.collectors.http import get_with_retry
from price_analyst.collectors.retry import RetryPolicy
from price_analyst.collectors.wholesale import WholesaleSearchContext
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.wholesale import WholesaleListing


class WholesaleFeedError(ValueError):
    """Raised when a configured feed is not a valid bounded wholesale feed."""


class PublicWholesaleJsonAdapter:
    """Read a configured HTTPS JSON feed without scraping or authentication.

    The feed must return either a JSON list or ``{"listings": [...]}``, where
    each item already follows the ``WholesaleListing`` field contract. This
    deliberately does not select a social network or marketplace on behalf of
    the operator; the URL must be reviewed and permitted before enabling it.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        source: str,
        feed_url: str,
        retry_policy: RetryPolicy,
        max_response_bytes: int = 1_000_000,
    ) -> None:
        self._validate_url(feed_url)
        if not source.strip():
            raise ValueError("source must not be empty")
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be at least one")
        self._client = client
        self.source = source.strip()
        self._feed_url = feed_url
        self._retry_policy = retry_policy
        self._max_response_bytes = max_response_bytes

    async def search(
        self,
        query: NormalizedQuery,
        context: WholesaleSearchContext,
    ) -> list[WholesaleListing]:
        response = await get_with_retry(
            self._client,
            self._feed_url,
            policy=self._retry_policy,
            timeout=context.timeout_seconds,
            params={"q": query.normalized_text},
        )
        if len(response.content) > self._max_response_bytes:
            raise WholesaleFeedError("Wholesale feed response exceeded the configured size limit.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise WholesaleFeedError("Wholesale feed did not return JSON.") from exc
        records = self._records(payload)
        if len(records) > context.max_listings:
            records = records[: context.max_listings]
        listings: list[WholesaleListing] = []
        for record in records:
            if not isinstance(record, Mapping):
                raise WholesaleFeedError("Wholesale feed contained a non-object listing.")
            normalized = dict(record)
            normalized["source"] = self.source
            try:
                listings.append(WholesaleListing.model_validate(normalized))
            except ValueError as exc:
                raise WholesaleFeedError("Wholesale feed contained an invalid listing.") from exc
        return listings

    @staticmethod
    def _records(payload: object) -> list[object]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("listings"), list):
            return cast(list[object], payload["listings"])
        raise WholesaleFeedError("Wholesale feed must be a listing array.")

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("wholesale feed URL must use HTTPS and include a host")
        if parsed.username or parsed.password:
            raise ValueError("wholesale feed URL must not contain credentials")
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            return
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
        ):
            raise ValueError("wholesale feed URL must not target a private address")
