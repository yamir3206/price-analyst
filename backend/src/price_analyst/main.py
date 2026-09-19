"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from price_analyst.api.router import api_router
from price_analyst.application.search_pipeline import SearchPipeline
from price_analyst.collectors.registry import AdapterRegistry
from price_analyst.infrastructure.config import Settings
from price_analyst.infrastructure.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    configure_logging()
    application = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        description=(
            "Deterministic price intelligence API. Marketplace collection and "
            "AI analysis are deliberately separate layers."
        ),
    )
    application.state.settings = app_settings
    application.state.adapter_registry = AdapterRegistry()
    application.state.search_pipeline = SearchPipeline(application.state.adapter_registry)
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
