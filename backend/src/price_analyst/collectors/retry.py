"""Bounded retry policy for transient external failures."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

import httpx

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("retry delays must not be negative")


def is_retryable(error: Exception) -> bool:
    if isinstance(error, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code == 429 or error.response.status_code >= 500
    return False


async def with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Run an async operation with bounded exponential backoff."""

    last_error: Exception | None = None
    for attempt in range(policy.max_attempts):
        try:
            return await operation()
        except Exception as error:
            last_error = error
            if attempt + 1 >= policy.max_attempts or not is_retryable(error):
                raise
            delay = min(
                policy.max_delay_seconds,
                policy.base_delay_seconds * (2**attempt),
            )
            if delay:
                await sleep(delay)
    assert last_error is not None
    raise last_error
