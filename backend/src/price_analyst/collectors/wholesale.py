"""Ports for independently replaceable wholesale sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.wholesale import WholesaleListing


@dataclass(frozen=True, slots=True)
class WholesaleSearchContext:
    """Bounded request context passed to a wholesale adapter."""

    request_id: str
    timeout_seconds: float = 10.0
    max_listings: int = 100


class WholesaleAdapter(Protocol):
    """A source-specific wholesale boundary; no selectors belong in the service."""

    source: str

    async def search(
        self,
        query: NormalizedQuery,
        context: WholesaleSearchContext,
    ) -> list[WholesaleListing]:
        """Return normalized public listings for a bounded query."""
