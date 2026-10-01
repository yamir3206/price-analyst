"""In-memory source health and temporary circuit breaking."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from price_analyst.domain.enums import Marketplace, SourceState
from price_analyst.domain.source_health import SourceStatus


@dataclass(slots=True)
class _HealthRecord:
    last_success: datetime | None = None
    last_failure: datetime | None = None
    average_response_time_ms: float | None = None
    response_samples: int = 0
    failure_count: int = 0
    temporary_disabled_until: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


class SourceHealthTracker:
    """Track consecutive failures and stop repeatedly failing sources."""

    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        cooldown_seconds: float = 300.0,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least one")
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = max(0.0, cooldown_seconds)
        self._records: dict[Marketplace, _HealthRecord] = {}
        self._locks: dict[Marketplace, asyncio.Lock] = {}

    def _lock(self, source: Marketplace) -> asyncio.Lock:
        if source not in self._locks:
            self._locks[source] = asyncio.Lock()
        return self._locks[source]

    def _record(self, source: Marketplace) -> _HealthRecord:
        if source not in self._records:
            self._records[source] = _HealthRecord()
        return self._records[source]

    async def can_request(self, source: Marketplace, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        async with self._lock(source):
            record = self._record(source)
            if record.temporary_disabled_until and record.temporary_disabled_until <= current:
                record.temporary_disabled_until = None
                record.failure_count = 0
            return not (
                record.temporary_disabled_until
                and record.temporary_disabled_until > current
            )

    async def record_success(self, source: Marketplace, response_time_ms: float) -> None:
        now = datetime.now(UTC)
        async with self._lock(source):
            record = self._record(source)
            record.last_success = now
            record.failure_count = 0
            record.temporary_disabled_until = None
            record.error_code = None
            record.error_message = None
            record.response_samples += 1
            if record.average_response_time_ms is None:
                record.average_response_time_ms = response_time_ms
            else:
                record.average_response_time_ms += (
                    response_time_ms - record.average_response_time_ms
                ) / record.response_samples

    async def record_failure(
        self,
        source: Marketplace,
        *,
        error_code: str,
        error_message: str,
        response_time_ms: float,
    ) -> None:
        now = datetime.now(UTC)
        async with self._lock(source):
            record = self._record(source)
            record.last_failure = now
            record.failure_count += 1
            record.error_code = error_code
            record.error_message = error_message
            record.response_samples += 1
            if record.average_response_time_ms is None:
                record.average_response_time_ms = response_time_ms
            else:
                record.average_response_time_ms += (
                    response_time_ms - record.average_response_time_ms
                ) / record.response_samples
            if record.failure_count >= self._failure_threshold:
                record.temporary_disabled_until = now + timedelta(
                    seconds=self._cooldown_seconds
                )

    async def status(
        self,
        source: Marketplace,
        *,
        state: SourceState = SourceState.READY,
        candidate_count: int = 0,
        offer_count: int = 0,
        stale_data_available: bool = False,
        stale_data_timestamp: datetime | None = None,
    ) -> SourceStatus:
        now = datetime.now(UTC)
        async with self._lock(source):
            record = self._record(source)
            effective_state = state
            if record.temporary_disabled_until and record.temporary_disabled_until > now:
                effective_state = SourceState.RATE_LIMITED
            return SourceStatus(
                source=source,
                state=effective_state,
                adapter_configured=True,
                last_success=record.last_success,
                last_failure=record.last_failure,
                average_response_time_ms=record.average_response_time_ms,
                candidate_count=candidate_count,
                offer_count=offer_count,
                failure_count=record.failure_count,
                temporary_disabled_until=record.temporary_disabled_until,
                stale_data_available=stale_data_available,
                stale_data_timestamp=stale_data_timestamp,
                error_code=record.error_code,
                error_message=record.error_message,
            )
