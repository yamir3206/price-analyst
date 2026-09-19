"""Process-local TTL cache for bounded wholesale snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from price_analyst.domain.wholesale import WholesaleSnapshot


@dataclass(slots=True)
class _Entry:
    value: WholesaleSnapshot
    expires_at: datetime


class InMemoryWholesaleSnapshotCache:
    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}

    async def get(self, key: str) -> WholesaleSnapshot | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(UTC):
            self._entries.pop(key, None)
            return None
        return entry.value

    async def put(self, key: str, value: WholesaleSnapshot, ttl_seconds: int) -> None:
        self._entries[key] = _Entry(
            value=value,
            expires_at=datetime.now(UTC) + timedelta(seconds=max(0, ttl_seconds)),
        )

    def clear(self) -> None:
        self._entries.clear()
