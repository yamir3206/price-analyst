"""FastAPI dependency boundaries."""

from typing import cast

from fastapi import Request

from price_analyst.application.search_pipeline import SearchPipeline
from price_analyst.application.wholesale_service import WholesaleService


def get_search_pipeline(request: Request) -> SearchPipeline:
    return cast(SearchPipeline, request.app.state.search_pipeline)


def get_wholesale_service(request: Request) -> WholesaleService:
    return cast(WholesaleService, request.app.state.wholesale_service)
