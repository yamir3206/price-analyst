"""Optional AI orchestration after deterministic local analysis."""

from __future__ import annotations

import asyncio
from time import monotonic
from typing import Protocol

from price_analyst.ai.cache import InMemoryAIAnalysisCache
from price_analyst.ai.client import GeminiResponseError, GeminiUnavailableError
from price_analyst.ai.compact_dataset import build_compact_dataset, rehash_dataset
from price_analyst.ai.prompts import (
    ANALYSIS_PROMPT_VERSION,
    SYSTEM_INSTRUCTION,
    render_user_prompt,
)
from price_analyst.ai.token_budget import within_input_budget
from price_analyst.application.ports import AIAnalysisCache
from price_analyst.domain.ai_analysis import AIAnalysis, AIAnalysisEnvelope, CompactAnalysisDataset
from price_analyst.domain.enums import AIAnalysisStatus
from price_analyst.domain.snapshots import SearchSnapshot


class AIClient(Protocol):
    enabled: bool

    async def analyze(self, dataset: CompactAnalysisDataset) -> AIAnalysis:
        ...


class AIAnalysisService:
    """Build bounded input, cache results, and coalesce identical requests."""

    def __init__(
        self,
        client: AIClient,
        *,
        cache: AIAnalysisCache | None = None,
        cache_ttl_seconds: int = 3600,
        max_offers: int = 30,
        max_input_tokens: int = 4000,
        prompt_version: str = ANALYSIS_PROMPT_VERSION,
        model: str | None = None,
        max_concurrency: int = 2,
        min_interval_seconds: float = 0.0,
    ) -> None:
        if max_offers < 1:
            raise ValueError("max_offers must be at least one")
        if max_input_tokens < 1:
            raise ValueError("max_input_tokens must be at least one")
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least one")
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must not be negative")
        self._client = client
        self._cache = cache if cache is not None else InMemoryAIAnalysisCache()
        self._cache_ttl_seconds = cache_ttl_seconds
        self._max_offers = max_offers
        self._max_input_tokens = max_input_tokens
        self._prompt_version = prompt_version
        self._model = model
        self._request_gate = asyncio.Semaphore(max_concurrency)
        self._min_interval_seconds = min_interval_seconds
        self._last_request_at = 0.0
        self._rate_lock = asyncio.Lock()
        self._inflight: dict[str, asyncio.Task[AIAnalysis]] = {}
        self._inflight_lock = asyncio.Lock()

    async def analyze_snapshot(self, snapshot: SearchSnapshot) -> AIAnalysisEnvelope:
        dataset = self._build_budgeted_dataset(snapshot)
        if not getattr(self._client, "enabled", True):
            return self._envelope(
                AIAnalysisStatus.DISABLED,
                dataset,
                error_code="gemini_disabled",
                error_message="Gemini analysis is disabled by configuration.",
            )

        cache_key = self._cache_key(dataset.dataset_hash)
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return self._envelope(AIAnalysisStatus.CACHED, dataset, result=cached)

        try:
            result = await self._coalesced_analysis(cache_key, dataset)
            return self._envelope(AIAnalysisStatus.COMPLETED, dataset, result=result)
        except GeminiResponseError:
            return self._envelope(
                AIAnalysisStatus.INVALID_RESPONSE,
                dataset,
                error_code="invalid_gemini_response",
                error_message="Gemini returned an invalid structured response.",
            )
        except GeminiUnavailableError:
            return self._envelope(
                AIAnalysisStatus.FAILED,
                dataset,
                error_code="gemini_unavailable",
                error_message="Gemini could not be reached or rejected the request.",
            )
        except Exception:
            return self._envelope(
                AIAnalysisStatus.FAILED,
                dataset,
                error_code="gemini_analysis_failed",
                error_message="Gemini analysis failed unexpectedly.",
            )

    def _envelope(
        self,
        status: AIAnalysisStatus,
        dataset: CompactAnalysisDataset,
        *,
        result: AIAnalysis | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> AIAnalysisEnvelope:
        return AIAnalysisEnvelope(
            status=status,
            result=result,
            dataset_hash=dataset.dataset_hash,
            prompt_version=self._prompt_version,
            model=self._model,
            error_code=error_code,
            error_message=error_message,
        )

    def _build_budgeted_dataset(self, snapshot: SearchSnapshot) -> CompactAnalysisDataset:
        limit = min(self._max_offers, len(snapshot.offers))
        limit = max(1, limit) if snapshot.offers else 1
        while limit >= 1:
            dataset = build_compact_dataset(
                snapshot.query,
                snapshot.offers,
                snapshot.statistics,
                max_offers=limit,
                local_analysis=snapshot.local_analysis,
                statistics_by_currency=snapshot.local_analysis.statistics_by_currency,
                stale=snapshot.stale,
            )
            request_text = f"{SYSTEM_INSTRUCTION}\n{render_user_prompt(dataset)}"
            if within_input_budget(request_text, self._max_input_tokens):
                return dataset
            if not snapshot.offers:
                return dataset
            limit -= 1
        minimal_offers = [
            offer.model_copy(
                update={
                    "title": None,
                    "seller": None,
                    "condition": None,
                    "availability": None,
                    "classification": None,
                    "match_score": None,
                }
            )
            for offer in dataset.offers[:1]
        ]
        minimal = rehash_dataset(
            dataset.model_copy(
                update={
                    "offers": minimal_offers,
                    "statistics": None,
                    "statistics_by_currency": [],
                    "dataset_hash": None,
                }
            )
        )
        while not within_input_budget(
            f"{SYSTEM_INSTRUCTION}\n{render_user_prompt(minimal)}",
            self._max_input_tokens,
        ) and len(minimal.product) > 1:
            minimal = rehash_dataset(
                minimal.model_copy(
                    update={"product": minimal.product[: max(1, len(minimal.product) // 2)]}
                )
            )
        return minimal

    async def _coalesced_analysis(
        self,
        cache_key: str,
        dataset: CompactAnalysisDataset,
    ) -> AIAnalysis:
        async with self._inflight_lock:
            task = self._inflight.get(cache_key)
            if task is None:
                task = asyncio.create_task(self._run_and_cache(cache_key, dataset))
                self._inflight[cache_key] = task
                task.add_done_callback(
                    lambda completed: self._inflight.pop(cache_key, None)
                    if self._inflight.get(cache_key) is completed
                    else None
                )
        try:
            return await asyncio.shield(task)
        finally:
            async with self._inflight_lock:
                if self._inflight.get(cache_key) is task and task.done():
                    self._inflight.pop(cache_key, None)

    async def _run_and_cache(
        self,
        cache_key: str,
        dataset: CompactAnalysisDataset,
    ) -> AIAnalysis:
        async with self._request_gate:
            await self._wait_for_ai_interval()
            result = await self._client.analyze(dataset)
        allowed_ids = {offer.offer_id for offer in dataset.offers}
        self._validate_references(result, allowed_ids)
        await self._cache.put(cache_key, result, self._cache_ttl_seconds)
        return result

    async def _wait_for_ai_interval(self) -> None:
        async with self._rate_lock:
            now = monotonic()
            delay = self._min_interval_seconds - (now - self._last_request_at)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request_at = monotonic()

    @staticmethod
    def _validate_references(result: AIAnalysis, allowed_ids: set[str]) -> None:
        for field in ("cheap_offers", "expensive_offers", "potential_opportunities"):
            references = getattr(result, field)
            if any(reference not in allowed_ids for reference in references):
                raise GeminiResponseError("Gemini referenced an offer outside the compact dataset.")

    def _cache_key(self, dataset_hash: str | None) -> str:
        return ":".join(
            (
                "ai-v1",
                self._prompt_version,
                self._model or "unknown-model",
                dataset_hash or "no-dataset-hash",
            )
        )
