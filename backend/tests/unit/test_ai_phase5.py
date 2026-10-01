import asyncio
import json
from datetime import UTC, datetime

import httpx
import pytest

from price_analyst.ai.client import GeminiHttpClient, GeminiResponseError
from price_analyst.ai.compact_dataset import build_compact_dataset
from price_analyst.ai.prompts import SYSTEM_INSTRUCTION, render_user_prompt
from price_analyst.ai.service import AIAnalysisService
from price_analyst.ai.token_budget import within_input_budget
from price_analyst.collectors.retry import RetryPolicy
from price_analyst.domain.ai_analysis import AIAnalysis
from price_analyst.domain.enums import CollectionStatus, Currency, Marketplace, PriceClassification
from price_analyst.domain.local_analysis import LocalAnalysis, OfferClassification, OfferMatch
from price_analyst.domain.money import Money
from price_analyst.domain.offers import Offer
from price_analyst.domain.queries import NormalizedQuery
from price_analyst.domain.snapshots import SearchSnapshot


def make_offer(
    offer_id: str,
    source: Marketplace,
    amount: int,
    *,
    title: str = "Samsung S24",
    seller: str = "seller",
) -> Offer:
    return Offer(
        offer_id=offer_id,
        source=source,
        source_offer_id=offer_id,
        title=title,
        normalized_title=title.lower(),
        price=Money(amount=amount, currency=Currency.IRT),
        seller=seller,
        product_url=f"https://{source.value}.example/{offer_id}",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def make_snapshot(offers: list[Offer]) -> SearchSnapshot:
    query = NormalizedQuery(
        original="Samsung S24",
        normalized_text="samsung s24",
        variants=["samsung s24"],
    )
    return SearchSnapshot(
        query=query,
        offers=offers,
        collection_status=CollectionStatus.COMPLETE,
    )


def valid_result(offer_id: str | None = None) -> AIAnalysis:
    return AIAnalysis(
        summary="Observed variation.",
        market_assessment="The deterministic sample is limited.",
        cheap_offers=[offer_id] if offer_id else [],
        facts=["Prices were supplied by the collector."],
        inferences=["The sample may not represent the entire market."],
        uncertainties=["The analysis does not verify seller claims."],
        confidence=0.6,
    )


def test_compact_selection_prioritizes_opportunities_and_source_diversity() -> None:
    offers = [
        make_offer("torob:ordinary", Marketplace.TOROB, 100),
        make_offer("torob:opportunity", Marketplace.TOROB, 80),
        make_offer("basalam:ordinary", Marketplace.BASALAM, 110),
    ]
    analysis = LocalAnalysis(
        matches=[
            OfferMatch(offer_id=offer.offer_id, score=0.9, is_match=True)
            for offer in offers
        ],
        classifications=[
            OfferClassification(
                offer_id="torob:opportunity",
                classification=PriceClassification.LOW_OUTLIER,
                price=80,
                currency=Currency.IRT,
            )
        ],
        opportunities=[],
    )
    dataset = build_compact_dataset(
        NormalizedQuery(
            original="Samsung S24",
            normalized_text="samsung s24",
            variants=["samsung s24"],
        ),
        offers,
        None,
        max_offers=2,
        local_analysis=analysis,
    )

    assert [offer.offer_id for offer in dataset.offers] == [
        "torob:opportunity",
        "basalam:ordinary",
    ]
    assert all("product_url" not in offer.model_dump() for offer in dataset.offers)
    assert dataset.offers[0].classification == "low_outlier"


class RecordingAIClient:
    enabled = True

    def __init__(self, result: AIAnalysis) -> None:
        self.result = result
        self.calls = 0
        self.datasets = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def analyze(self, dataset):
        self.calls += 1
        self.datasets.append(dataset)
        self.started.set()
        await self.release.wait()
        return self.result


@pytest.mark.asyncio
async def test_ai_service_coalesces_inflight_requests_and_caches_success() -> None:
    offer = make_offer("torob:1", Marketplace.TOROB, 100)
    client = RecordingAIClient(valid_result("torob:1"))
    service = AIAnalysisService(client, max_offers=5)
    snapshot = make_snapshot([offer])

    first_task = asyncio.create_task(service.analyze_snapshot(snapshot))
    await client.started.wait()
    second_task = asyncio.create_task(service.analyze_snapshot(snapshot))
    await asyncio.sleep(0)
    client.release.set()
    first, second = await asyncio.gather(first_task, second_task)

    assert client.calls == 1
    assert first.status.value == "completed"
    assert second.status.value == "completed"

    cached = await service.analyze_snapshot(snapshot)
    assert cached.status.value == "cached"
    assert cached.result == first.result
    assert client.calls == 1


@pytest.mark.asyncio
async def test_ai_service_enforces_budget_with_deterministic_reduction() -> None:
    offer = make_offer(
        "torob:long",
        Marketplace.TOROB,
        100,
        title="very long title " * 40,
        seller="very long seller " * 30,
    )
    client = RecordingAIClient(valid_result())
    client.release.set()
    service = AIAnalysisService(client, max_offers=10, max_input_tokens=256)

    result = await service.analyze_snapshot(make_snapshot([offer]))

    assert result.status.value == "completed"
    dataset = client.datasets[0]
    assert len(dataset.offers) == 1
    assert dataset.offers[0].title is None
    assert within_input_budget(
        f"{SYSTEM_INSTRUCTION}\n{render_user_prompt(dataset)}",
        256,
    )


@pytest.mark.asyncio
async def test_gemini_client_validates_structured_json_and_keeps_key_out_of_url() -> None:
    seen_url = ""

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_url
        seen_url = str(request.url)
        body = json.dumps(valid_result().model_dump(mode="json"))
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": body}]}}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GeminiHttpClient(
            http_client,
            api_key="secret-that-must-not-be-a-url-part",
            model="gemini-test",
            timeout_seconds=2,
            max_output_tokens=200,
            retry_policy=RetryPolicy(max_attempts=1),
        )
        result = await client.analyze(
            build_compact_dataset(
                NormalizedQuery(
                    original="phone",
                    normalized_text="phone",
                    variants=["phone"],
                ),
                [],
                None,
                max_offers=1,
            )
        )

    assert result.confidence == 0.6
    assert "secret-that-must-not-be-a-url-part" not in seen_url


@pytest.mark.asyncio
async def test_gemini_client_rejects_extra_output_fields() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {"confidence": 0.5, "unexpected": "field"}
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = GeminiHttpClient(
            http_client,
            api_key="secret",
            model="gemini-test",
            timeout_seconds=2,
            max_output_tokens=200,
            retry_policy=RetryPolicy(max_attempts=1),
        )
        with pytest.raises(GeminiResponseError):
            await client.analyze(
                build_compact_dataset(
                    NormalizedQuery(
                        original="phone",
                        normalized_text="phone",
                        variants=["phone"],
                    ),
                    [],
                    None,
                    max_offers=1,
                )
            )
