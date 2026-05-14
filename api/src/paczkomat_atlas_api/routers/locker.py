"""Locker endpoints — filtered list + detail by name."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.db import get_session
from paczkomat_atlas_api.repositories import LockerRepo
from paczkomat_atlas_api.schemas import ApiResponse, LockerDetail, LockerSummary

router = APIRouter(prefix="/lockers", tags=["lockers"])


@router.get(
    "",
    response_model=ApiResponse[list[LockerSummary]],
    operation_id="listLockers",
)
async def list_lockers(
    session: Annotated[AsyncSession, Depends(get_session)],
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    is_locker: Annotated[bool | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    location_247: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApiResponse[list[LockerSummary]]:
    """Filtered locker list. Most callers should hit the tile endpoint instead."""
    rows, total = await LockerRepo(session).list_lockers(
        country=country, is_locker=is_locker, status=status,
        location_247=location_247, limit=limit, offset=offset,
    )
    return ApiResponse(data=rows, meta={"total": total, "limit": limit, "offset": offset})


@router.get(
    "/{name}",
    response_model=ApiResponse[LockerDetail],
    operation_id="getLocker",
)
async def get_locker(
    name: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[LockerDetail]:
    """Single locker detail by name (e.g. WAW01N)."""
    data = await LockerRepo(session).get_by_name(name)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Locker {name!r} not found")
    return ApiResponse(data=data)
