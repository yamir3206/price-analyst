"""Service health and readiness endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from price_analyst import __version__
from price_analyst.api.schemas import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=__version__,
        environment=settings.environment,
        gemini_configured=settings.gemini_configured,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(request: Request) -> ReadinessResponse:
    """Report whether configured local dependencies can accept traffic."""
    engine = getattr(request.app.state, "database_engine", None)
    if engine is not None:
        try:
            await asyncio.to_thread(_check_database, engine)
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=503,
                detail="A configured service dependency is not ready.",
            ) from exc
    return ReadinessResponse(status="ready")


def _check_database(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
