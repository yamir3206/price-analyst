"""Explicit wholesale search API; it never invokes the retail pipeline."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from price_analyst.api.dependencies import get_wholesale_service
from price_analyst.api.schemas import WholesaleSearchRequest
from price_analyst.application.wholesale_service import WholesaleService
from price_analyst.domain.wholesale import WholesaleSnapshot

router = APIRouter(prefix="/wholesale/searches", tags=["wholesale"])


@router.post("", response_model=WholesaleSnapshot, status_code=status.HTTP_200_OK)
async def create_wholesale_search(
    payload: WholesaleSearchRequest,
    service: Annotated[WholesaleService, Depends(get_wholesale_service)],
) -> WholesaleSnapshot:
    try:
        return await service.run(payload.query, refresh=payload.refresh)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
