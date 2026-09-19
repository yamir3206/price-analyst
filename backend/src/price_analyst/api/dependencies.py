"""FastAPI dependency boundaries."""

from typing import cast

from fastapi import Request

from price_analyst.application.search_pipeline import SearchPipeline


def get_search_pipeline(request: Request) -> SearchPipeline:
    return cast(SearchPipeline, request.app.state.search_pipeline)
