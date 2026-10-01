from pathlib import Path

import httpx
import pytest

from price_analyst.collectors.interfaces import SearchContext
from price_analyst.collectors.sources.torob.adapter import TorobAdapter
from price_analyst.domain.queries import NormalizedQuery

FIXTURES = Path(__file__).parents[1] / "fixtures" / "torob"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_adapter_uses_bounded_search_and_detail_requests() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/search/":
            return httpx.Response(200, text=fixture("search.html"), request=request)
        return httpx.Response(200, text=fixture("product.html"), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = TorobAdapter(client, base_url="https://torob.com")
        query = NormalizedQuery(
            original="Samsung S24",
            normalized_text="samsung s24",
            variants=["samsung s24"],
        )
        candidates = await adapter.search(
            query,
            SearchContext(request_id="test", max_candidates=1),
        )
        offers = await adapter.fetch_details(
            candidates[0],
            SearchContext(request_id="test", timeout_seconds=2),
        )

    assert len(candidates) == 1
    assert len(offers) == 2
    assert requests[0].url.path == "/search/"
    assert requests[0].url.params["query"] == "samsung s24"
    assert requests[1].url.path.startswith("/p/")
