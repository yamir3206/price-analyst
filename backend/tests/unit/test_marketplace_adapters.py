from pathlib import Path

import httpx
import pytest

from price_analyst.collectors.interfaces import SearchContext
from price_analyst.collectors.retry import RetryPolicy
from price_analyst.collectors.sources.basalam.adapter import BasalamAdapter
from price_analyst.collectors.sources.digikala.adapter import DigikalaAdapter
from price_analyst.collectors.sources.divar.adapter import DivarAdapter
from price_analyst.domain.enums import Marketplace
from price_analyst.domain.queries import NormalizedQuery

FIXTURES = Path(__file__).parents[1] / "fixtures"
QUERY = NormalizedQuery(
    original="Samsung S24",
    normalized_text="samsung s24",
    variants=["samsung s24"],
)


@pytest.mark.parametrize(
    ("source", "adapter_factory", "search_path", "detail_path", "fixture_dir"),
    [
        (
            Marketplace.BASALAM,
            lambda client: BasalamAdapter(
                client,
                base_url="https://basalam.test",
                retry_policy=RetryPolicy(max_attempts=1),
            ),
            "/s",
            "/seller/product/123456",
            "basalam",
        ),
        (
            Marketplace.DIGIKALA,
            lambda client: DigikalaAdapter(
                client,
                base_url="https://digikala.test",
                retry_policy=RetryPolicy(max_attempts=1),
            ),
            "/search/",
            "/product/dkp-987654/galaxy-s24",
            "digikala",
        ),
        (
            Marketplace.DIVAR,
            lambda client: DivarAdapter(
                client,
                base_url="https://divar.test",
                city="tehran",
                category="electronic-devices",
                retry_policy=RetryPolicy(max_attempts=1),
            ),
            "/s/tehran/electronic-devices",
            "/v/galaxy-s24/abc123xyz",
            "divar",
        ),
    ],
)
@pytest.mark.asyncio
async def test_adapters_use_public_search_then_same_host_detail_html(
    source: Marketplace,
    adapter_factory,
    search_path: str,
    detail_path: str,
    fixture_dir: str,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        name = "search.html" if request.url.path == search_path else "product.html"
        return httpx.Response(
            200,
            text=(FIXTURES / fixture_dir / name).read_text(encoding="utf-8"),
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = adapter_factory(client)
        candidates = await adapter.search(
            QUERY,
            SearchContext(request_id="test", max_candidates=2),
        )
        offers = await adapter.fetch_details(
            candidates[0],
            SearchContext(request_id="test"),
        )

    assert adapter.source is source
    assert len(candidates) == 1
    assert len(offers) == 1
    assert requests[0].url.path == search_path
    assert requests[0].url.params["q"] == "samsung s24"
    assert requests[1].url.path == detail_path
