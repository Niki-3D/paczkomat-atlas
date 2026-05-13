"""Pydantic schemas — request/response shapes. Mirror models/ but with API semantics."""

from paczkomat_atlas_api.schemas.density import (
    DensityGmina,
    DensityNuts2,
    GminaTopList,
    Nuts2TopList,
)
from paczkomat_atlas_api.schemas.envelope import ApiResponse, Pagination
from paczkomat_atlas_api.schemas.h3 import H3Cell
from paczkomat_atlas_api.schemas.kpi import CountryKpi, NetworkSummary
from paczkomat_atlas_api.schemas.locker import LockerDetail, LockerSummary
from paczkomat_atlas_api.schemas.velocity import VelocityPoint

__all__ = [
    "ApiResponse",
    "CountryKpi",
    "DensityGmina",
    "DensityNuts2",
    "GminaTopList",
    "H3Cell",
    "LockerDetail",
    "LockerSummary",
    "NetworkSummary",
    "Nuts2TopList",
    "Pagination",
    "VelocityPoint",
]
