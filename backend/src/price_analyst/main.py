"""FastAPI application factory and adapter wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from price_analyst.ai.client import DisabledGeminiClient
from price_analyst.api.router import api_router
from price_analyst.application.search_pipeline import SearchPipeline
from price_analyst.application.source_health import SourceHealthTracker
from price_analyst.cache.in_memory import InMemorySnapshotCache
from price_analyst.collectors.rate_limit import SourceRateLimiter
from price_analyst.collectors.registry import AdapterRegistry
from price_analyst.collectors.retry import RetryPolicy
from price_analyst.collectors.sources.basalam import BasalamAdapter
from price_analyst.collectors.sources.digikala import DigikalaAdapter
from price_analyst.collectors.sources.divar import DivarAdapter
from price_analyst.collectors.sources.torob import TorobAdapter
from price_analyst.infrastructure.config import Settings
from price_analyst.infrastructure.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        retry_policy = RetryPolicy(
            max_attempts=app_settings.retry_max_attempts,
            base_delay_seconds=app_settings.retry_base_delay_seconds,
            max_delay_seconds=app_settings.retry_max_delay_seconds,
        )
        health = SourceHealthTracker(
            failure_threshold=app_settings.source_failure_threshold,
            cooldown_seconds=app_settings.source_cooldown_seconds,
        )
        rate_limiter = SourceRateLimiter(app_settings.source_min_interval_seconds)
        async with httpx.AsyncClient(
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "fa,en;q=0.8",
                "User-Agent": "PriceAnalyst/0.3 (+deterministic-public-collector)",
            },
        ) as http_client:
            registry = AdapterRegistry()
            if app_settings.torob_enabled:
                registry.register(
                    TorobAdapter(
                        http_client,
                        base_url=app_settings.torob_base_url,
                        retry_policy=retry_policy,
                    )
                )
            if app_settings.basalam_enabled:
                registry.register(
                    BasalamAdapter(
                        http_client,
                        base_url=app_settings.basalam_base_url,
                        retry_policy=retry_policy,
                    )
                )
            if app_settings.digikala_enabled:
                registry.register(
                    DigikalaAdapter(
                        http_client,
                        base_url=app_settings.digikala_base_url,
                        retry_policy=retry_policy,
                    )
                )
            if app_settings.divar_enabled:
                registry.register(
                    DivarAdapter(
                        http_client,
                        base_url=app_settings.divar_base_url,
                        city=app_settings.divar_city,
                        category=app_settings.divar_category,
                        retry_policy=retry_policy,
                    )
                )
            application.state.adapter_registry = registry
            application.state.snapshot_cache = InMemorySnapshotCache()
            application.state.source_health = health
            application.state.rate_limiter = rate_limiter
            application.state.gemini_client = DisabledGeminiClient()
            application.state.search_pipeline = SearchPipeline(
                registry,
                cache=application.state.snapshot_cache,
                health=health,
                rate_limiter=rate_limiter,
                cache_ttl_seconds=app_settings.snapshot_cache_ttl_seconds,
                source_timeout_seconds=app_settings.source_timeout_seconds,
                max_search_candidates=app_settings.max_search_candidates,
                max_detail_candidates=app_settings.max_detail_candidates,
                source_concurrency=app_settings.source_concurrency,
            )
            yield

    application = FastAPI(
        title=app_settings.app_name,
        version="0.3.0",
        description=(
            "Deterministic price intelligence API. Marketplace collection and "
            "AI analysis are deliberately separate layers."
        ),
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(api_router)
    return application


app = create_app()
