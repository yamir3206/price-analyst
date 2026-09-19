"""Search API route."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from price_analyst.api.dependencies import get_search_pipeline
from price_analyst.api.schemas import AnalysisRequest, SearchRequest
from price_analyst.application.search_pipeline import SearchPipeline
from price_analyst.domain.snapshots import SearchSnapshot

router = APIRouter(prefix="/searches", tags=["searches"])


@router.post("", response_model=SearchSnapshot, status_code=status.HTTP_200_OK)
async def create_search(
    payload: SearchRequest,
    pipeline: Annotated[SearchPipeline, Depends(get_search_pipeline)],
) -> SearchSnapshot:
    try:
        return await pipeline.run(payload.query, refresh=payload.refresh)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/analysis", response_model=SearchSnapshot, status_code=status.HTTP_200_OK)
async def analyze_search(
    payload: AnalysisRequest,
    pipeline: Annotated[SearchPipeline, Depends(get_search_pipeline)],
) -> SearchSnapshot:
    """Explicitly request optional AI interpretation of a deterministic snapshot."""

    try:
        return await pipeline.run(payload.query, refresh=payload.refresh, analyze=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
