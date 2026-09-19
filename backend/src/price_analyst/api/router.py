"""Versioned API router."""

from fastapi import APIRouter

from price_analyst.api.routes.health import router as health_router
from price_analyst.api.routes.searches import router as searches_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(searches_router)
