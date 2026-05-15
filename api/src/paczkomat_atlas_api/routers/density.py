"""Density endpoints — gminy and NUTS-2 choropleth data + top lists."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.db import get_session
from paczkomat_atlas_api.repositories import DensityRepo
from paczkomat_atlas_api.schemas import (
    ApiResponse,
    DensityGmina,
    DensityNuts2,
    GminaTopList,
    Nuts2TopList,
)

router = APIRouter(prefix="/density", tags=["density"])


@router.get(
    "/gminy",
    response_model=ApiResponse[list[DensityGmina]],
    operation_id="listGminy",
)
async def list_gminy(
    session: Annotated[AsyncSession, Depends(get_session)],
    voivodeship: Annotated[
        str | None,
        Query(description="Filter by voivodeship name", max_length=64),
    ] = None,
    min_population: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=2500)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApiResponse[list[DensityGmina]]:
    """Paginated list of gminy with density. Default returns up to 500 of ~2477."""
    rows, total = await DensityRepo(session).list_gminy(
        voivodeship=voivodeship,
        min_population=min_population,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=rows, meta={"total": total, "limit": limit, "offset": offset})


@router.get(
    "/gminy/top",
    response_model=ApiResponse[list[GminaTopList]],
    operation_id="topGminy",
)
async def top_gminy(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 15,
    min_population: Annotated[int, Query(ge=0)] = 5000,
    min_lockers: Annotated[int, Query(ge=0)] = 5,
) -> ApiResponse[list[GminaTopList]]:
    """Top N gminy by lockers per 10k. Filtered to avoid tiny outliers."""
    data = await DensityRepo(session).top_gminy(
        limit=limit, min_population=min_population, min_lockers=min_lockers,
    )
    return ApiResponse(data=data, meta={"count": len(data)})


@router.get(
    "/nuts2",
    response_model=ApiResponse[list[DensityNuts2]],
    operation_id="listNuts2",
)
async def list_nuts2(
    session: Annotated[AsyncSession, Depends(get_session)],
    country: Annotated[str | None, Query(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")] = None,
    min_population: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApiResponse[list[DensityNuts2]]:
    """Paginated list of NUTS-2 regions with density."""
    rows, total = await DensityRepo(session).list_nuts2(
        country=country, min_population=min_population, limit=limit, offset=offset,
    )
    return ApiResponse(data=rows, meta={"total": total, "limit": limit, "offset": offset})


@router.get(
    "/nuts2/top",
    response_model=ApiResponse[list[Nuts2TopList]],
    operation_id="topNuts2",
)
async def top_nuts2(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 15,
    min_population: Annotated[int, Query(ge=0)] = 100_000,
) -> ApiResponse[list[Nuts2TopList]]:
    """Top N NUTS-2 regions by lockers per 10k."""
    data = await DensityRepo(session).top_nuts2(limit=limit, min_population=min_population)
    return ApiResponse(data=data, meta={"count": len(data)})
