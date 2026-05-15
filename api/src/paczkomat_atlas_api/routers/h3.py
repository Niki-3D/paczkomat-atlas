"""H3 hex aggregations — JSON form. Tile form lives in Phase 6 (Martin)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.db import get_session
from paczkomat_atlas_api.repositories import H3Repo
from paczkomat_atlas_api.schemas import ApiResponse, H3Cell

router = APIRouter(prefix="/h3", tags=["h3"])


@router.get(
    "/cells",
    response_model=ApiResponse[list[H3Cell]],
    operation_id="listH3Cells",
)
async def list_h3_cells(
    session: Annotated[AsyncSession, Depends(get_session)],
    country: Annotated[str | None, Query(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")] = None,
    min_count: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=10_000)] = 5_000,
) -> ApiResponse[list[H3Cell]]:
    """H3 cells at resolution 8 with locker/PUDO counts. For tabular use."""
    data = await H3Repo(session).list_cells(country=country, min_count=min_count, limit=limit)
    return ApiResponse(data=data, meta={"count": len(data), "resolution": 8})
