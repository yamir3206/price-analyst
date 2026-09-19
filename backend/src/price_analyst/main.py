"""FastAPI application factory and adapter wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from price_analyst import __version__
from price_analyst.ai.cache import InMemoryAIAnalysisCache
from price_analyst.ai.client import DisabledGeminiClient, GeminiHttpClient
from price_analyst.ai.service import AIAnalysisService, AIClient
from price_analyst.api.router import api_router
from price_analyst.application.search_pipeline import SearchPipeline
from price_analyst.application.source_health import SourceHealthTracker
from price_analyst.application.wholesale_service import WholesaleService
from price_analyst.cache.in_memory import InMemorySnapshotCache
from price_analyst.collectors.rate_limit import SourceRateLimiter
from price_analyst.collectors.registry import AdapterRegistry
from price_analyst.collectors.retry import RetryPolicy
from price_analyst.collectors.sources.basalam import BasalamAdapter
from price_analyst.collectors.sources.digikala import DigikalaAdapter
from price_analyst.collectors.sources.divar import DivarAdapter
from price_analyst.collectors.sources.public_wholesale_json import PublicWholesaleJsonAdapter
from price_analyst.collectors.sources.torob import TorobAdapter
from price_analyst.collectors.wholesale_registry import WholesaleAdapterRegistry
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
            wholesale_registry = WholesaleAdapterRegistry()
            if app_settings.wholesale_feed_enabled and app_settings.wholesale_feed_url:
                wholesale_registry.register(
                    PublicWholesaleJsonAdapter(
                        http_client,
                        source=app_settings.wholesale_feed_source,
                        feed_url=app_settings.wholesale_feed_url,
                        retry_policy=retry_policy,
                        max_response_bytes=app_settings.wholesale_response_max_bytes,
                    )
                )
            application.state.adapter_registry = registry
            application.state.wholesale_adapter_registry = wholesale_registry
            application.state.snapshot_cache = InMemorySnapshotCache()
            application.state.source_health = health
            application.state.rate_limiter = rate_limiter
            wholesale_rate_limiter = SourceRateLimiter(
                app_settings.wholesale_min_interval_seconds,
            )
            application.state.wholesale_rate_limiter = wholesale_rate_limiter
            application.state.wholesale_service = WholesaleService(
                wholesale_registry,
                rate_limiter=wholesale_rate_limiter,
                cache_ttl_seconds=app_settings.snapshot_cache_ttl_seconds,
                source_timeout_seconds=app_settings.wholesale_timeout_seconds,
                source_concurrency=app_settings.wholesale_concurrency,
                max_listings=app_settings.max_wholesale_listings,
            )
            gemini_client: AIClient
            if app_settings.gemini_configured:
                api_key = app_settings.gemini_api_key
                assert api_key is not None
                gemini_client = GeminiHttpClient(
                    http_client,
                    api_key=api_key.get_secret_value(),
                    model=app_settings.gemini_model,
                    timeout_seconds=app_settings.gemini_timeout_seconds,
                    max_output_tokens=app_settings.max_gemini_output_tokens,
                    retry_policy=retry_policy,
                )
            else:
                gemini_client = DisabledGeminiClient()
            application.state.gemini_client = gemini_client
            application.state.ai_analysis_service = AIAnalysisService(
                gemini_client,
                cache=InMemoryAIAnalysisCache(
                    max_entries=app_settings.gemini_cache_max_entries,
                ),
                cache_ttl_seconds=app_settings.gemini_cache_ttl_seconds,
                max_offers=app_settings.max_offers_to_analyze,
                max_input_tokens=app_settings.max_gemini_input_tokens,
                prompt_version=f"price-analysis-v{app_settings.analysis_version}",
                model=app_settings.gemini_model,
                max_concurrency=app_settings.gemini_concurrency,
                min_interval_seconds=app_settings.gemini_min_interval_seconds,
            )
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
                analysis_match_threshold=app_settings.analysis_match_threshold,
                analysis_max_opportunities=app_settings.analysis_max_opportunities,
                ai_service=application.state.ai_analysis_service,
            )
            yield

    application = FastAPI(
        title=app_settings.app_name,
        version=__version__,
        description=(
            "Deterministic price intelligence API. Marketplace collection and "
            "AI analysis are deliberately separate layers."
        ),
        lifespan=lifespan,
    )
    @application.middleware("http")
    async def security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", "")
        if (
            not request_id
            or len(request_id) > 128
            or not request_id.isascii()
            or not all(char.isalnum() or char in "-_.:" for char in request_id)
        ):
            request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        return response

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
