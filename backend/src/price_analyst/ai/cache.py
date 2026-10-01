"""Bounded in-memory cache for validated AI results."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from price_analyst.domain.ai_analysis import AIAnalysis


@dataclass(slots=True)
class _Entry:
    value: AIAnalysis
    expires_at: datetime


class InMemoryAIAnalysisCache:
    """Bounded TTL cache keyed by dataset, prompt version, and model."""

    def __init__(self, *, max_entries: int = 256) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least one")
        self._max_entries = max_entries
        self._entries: OrderedDict[str, _Entry] = OrderedDict()

    async def get(self, key: str) -> AIAnalysis | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(UTC):
            self._entries.pop(key, None)
            return None
        self._entries.move_to_end(key)
        return entry.value

    async def put(self, key: str, value: AIAnalysis, ttl_seconds: int) -> None:
        self._entries[key] = _Entry(
            value=value,
            expires_at=datetime.now(UTC) + timedelta(seconds=max(0, ttl_seconds)),
        )
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()
