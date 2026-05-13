"""Density schemas — gminy and NUTS-2 choropleth data."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DensityGmina(BaseModel):
    """One gmina row from mv_density_gmina."""

    teryt: str = Field(..., min_length=7, max_length=7)
    name: str
    voivodeship: str | None
    population: int = Field(..., ge=0)
    n_lockers: int = Field(..., ge=0)
    n_pudo: int = Field(..., ge=0)
    lockers_per_10k: float | None = Field(None, description="NULL when population=0")


class DensityNuts2(BaseModel):
    """One NUTS-2 region row from mv_density_nuts2."""

    code: str = Field(..., min_length=4, max_length=5)
    name_latn: str
    country: str = Field(..., min_length=2, max_length=2)
    population: int = Field(..., ge=0)
    n_lockers: int = Field(..., ge=0)
    n_pudo: int = Field(..., ge=0)
    lockers_per_10k: float | None


class GminaTopList(BaseModel):
    """Compact form for ranked lists."""

    teryt: str
    name: str
    voivodeship: str | None
    lockers_per_10k: float
    n_lockers: int
    population: int


class Nuts2TopList(BaseModel):
    """Compact form for ranked lists."""

    code: str
    name_latn: str
    country: str
    lockers_per_10k: float
    n_lockers: int
    population: int
