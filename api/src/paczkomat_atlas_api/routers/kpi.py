"""KPI endpoints — network summary and per-country totals."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.db import get_session
from paczkomat_atlas_api.repositories import KpiRepo
from paczkomat_atlas_api.schemas import ApiResponse, CountryKpi, NetworkSummary

router = APIRouter(prefix="/kpi", tags=["kpi"])


@router.get(
    "/summary",
    response_model=ApiResponse[NetworkSummary],
    operation_id="getNetworkSummary",
)
async def get_network_summary(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[NetworkSummary]:
    """Top-line headline numbers for the landing page hero."""
    data = await KpiRepo(session).network_summary()
    return ApiResponse(data=data, meta={"source": "mv_country_kpi"})


@router.get(
    "/countries",
    response_model=ApiResponse[list[CountryKpi]],
    operation_id="listCountryKpis",
)
async def list_country_kpis(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[list[CountryKpi]]:
    """All 14 active countries with operating counts."""
    data = await KpiRepo(session).list_countries()
    return ApiResponse(data=data, meta={"count": len(data)})


@router.get(
    "/countries/{country}",
    response_model=ApiResponse[CountryKpi],
    operation_id="getCountryKpi",
)
async def get_country_kpi(
    country: Annotated[str, Path(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse[CountryKpi]:
    """Single country detail."""
    data = await KpiRepo(session).get_country(country)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Country {country!r} not found")
    return ApiResponse(data=data)
