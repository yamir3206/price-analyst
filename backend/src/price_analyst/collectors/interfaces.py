"""Ports for independently replaceable marketplace adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from price_analyst.domain.enums import Marketplace
from price_analyst.domain.offers import Offer, SearchCandidate
from price_analyst.domain.queries import NormalizedQuery


@dataclass(frozen=True, slots=True)
class SearchContext:
    """Request-scoped limits passed to adapters without exposing API concerns."""

    request_id: str
    timeout_seconds: float = 10.0
    max_candidates: int = 100


class MarketplaceAdapter(Protocol):
    """Source boundary; no source-specific logic belongs in the pipeline."""

    source: Marketplace

    async def search(
        self,
        query: NormalizedQuery,
        context: SearchContext,
    ) -> list[SearchCandidate]:
        """
        Return lightweight candidates from the source's search surface.

        Implementations should not fetch detail pages here unless the source
        has no separate search endpoint and the request is still bounded.
        """

    async def fetch_details(
        self,
        candidate: SearchCandidate,
        context: SearchContext,
    ) -> list[Offer]:
        """Fetch all normalized offers for one selected product candidate."""
