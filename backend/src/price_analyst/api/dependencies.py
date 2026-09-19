"""FastAPI dependency boundaries."""

from fastapi import Request

from price_analyst.application.search_pipeline import SearchPipeline


def get_search_pipeline(request: Request) -> SearchPipeline:
    return request.app.state.search_pipeline
