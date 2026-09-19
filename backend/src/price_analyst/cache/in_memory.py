"""Small async-safe-enough in-memory cache for the single-process MVP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from price_analyst.domain.snapshots import SearchSnapshot


@dataclass(slots=True)
class _Entry:
    value: SearchSnapshot
    expires_at: datetime


class InMemorySnapshotCache:
    """TTL cache abstraction that can later be backed by SQLite or Redis."""

    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}

    async def get(self, key: str) -> SearchSnapshot | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(UTC):
            self._entries.pop(key, None)
            return None
        return entry.value

    async def put(self, key: str, value: SearchSnapshot, ttl_seconds: int) -> None:
        expires_at = datetime.now(UTC) + timedelta(seconds=max(0, ttl_seconds))
        self._entries[key] = _Entry(value=value, expires_at=expires_at)

    def clear(self) -> None:
        self._entries.clear()
