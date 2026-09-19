"""Per-source async request pacing."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict

from price_analyst.domain.enums import Marketplace


class SourceRateLimiter:
    """Ensure a minimum interval between requests to each source."""

    def __init__(self, minimum_interval_seconds: float = 0.25) -> None:
        if minimum_interval_seconds < 0:
            raise ValueError("minimum_interval_seconds must not be negative")
        self._interval = minimum_interval_seconds
        self._next_allowed: dict[Marketplace, float] = defaultdict(float)
        self._locks: dict[Marketplace, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def acquire(self, source: Marketplace) -> None:
        if self._interval == 0:
            return
        async with self._locks[source]:
            now = time.monotonic()
            wait_for = max(0.0, self._next_allowed[source] - now)
            if wait_for:
                await asyncio.sleep(wait_for)
            self._next_allowed[source] = time.monotonic() + self._interval
