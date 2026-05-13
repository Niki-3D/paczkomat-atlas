"""KPI schemas — network-wide and per-country summaries."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CountryKpi(BaseModel):
    """Per-country headline metrics from mv_country_kpi."""

    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    n_lockers: int = Field(..., ge=0, description="Operating parcel_locker machines")
    n_pudo: int = Field(..., ge=0, description="Operating PUDO points")
    n_total: int = Field(..., ge=0, description="Sum of lockers + PUDO, operating only")
    n_247: int = Field(..., ge=0, description="24/7 accessible (operating only)")
    pct_247: float | None = Field(None, description="Percentage 24/7 of operating total")


class NetworkSummary(BaseModel):
    """Top-line numbers for the whole network."""

    n_lockers_total: int
    n_pudo_total: int
    n_network_total: int
    n_countries_active: int
    pl_lockers: int
    pl_pct_247: float | None
