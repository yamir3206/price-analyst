"""Shared HTTP request helper for source adapters."""

from __future__ import annotations

from collections.abc import Mapping

import httpx

from price_analyst.collectors.retry import RetryPolicy, with_retry


async def get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    policy: RetryPolicy,
    timeout: float,
    params: Mapping[str, str] | None = None,
) -> httpx.Response:
    async def request() -> httpx.Response:
        response = await client.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response

    return await with_retry(request, policy=policy)
