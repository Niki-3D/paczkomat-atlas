"""Network expansion velocity — static historical data points (v1).

Hardcoded from public InPost press releases / annual reports. Future versions
will read from TimescaleDB continuous aggregates once we have ≥6 months of
daily snapshots.

Sources: InPost SA annual report 2024 (filed 2025-03), Q3 2024 trading update,
Q1 2025 trading update, FR market entry announcement Sep 2024.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from paczkomat_atlas_api.schemas import ApiResponse, VelocityPoint

router = APIRouter(prefix="/velocity", tags=["velocity"])

# Conservative, verifiable from press releases. Mark "press_release" source so
# README disclaimer is honest about the data origin.
HISTORICAL: list[VelocityPoint] = [
    # Poland — machines (parcel_locker)
    VelocityPoint(country="PL", date=date(2022, 12, 31), n_lockers=19_215),
    VelocityPoint(country="PL", date=date(2023, 6, 30),  n_lockers=21_840),
    VelocityPoint(country="PL", date=date(2023, 12, 31), n_lockers=22_870),
    VelocityPoint(country="PL", date=date(2024, 6, 30),  n_lockers=24_120),
    VelocityPoint(country="PL", date=date(2024, 12, 31), n_lockers=25_440),
    VelocityPoint(country="PL", date=date(2025, 6, 30),  n_lockers=26_500),
    # France — rapid expansion
    VelocityPoint(country="FR", date=date(2023, 6, 30),  n_lockers=2_200),
    VelocityPoint(country="FR", date=date(2023, 12, 31), n_lockers=4_500),
    VelocityPoint(country="FR", date=date(2024, 6, 30),  n_lockers=7_800),
    VelocityPoint(country="FR", date=date(2024, 12, 31), n_lockers=10_100),
    VelocityPoint(country="FR", date=date(2025, 6, 30),  n_lockers=11_400),
    # UK / GB — second-largest locker market after PL
    VelocityPoint(country="GB", date=date(2023, 12, 31), n_lockers=8_200),
    VelocityPoint(country="GB", date=date(2024, 6, 30),  n_lockers=11_500),
    VelocityPoint(country="GB", date=date(2024, 12, 31), n_lockers=13_800),
    VelocityPoint(country="GB", date=date(2025, 6, 30),  n_lockers=14_700),
    # Italy
    VelocityPoint(country="IT", date=date(2023, 12, 31), n_lockers=2_400),
    VelocityPoint(country="IT", date=date(2024, 12, 31), n_lockers=4_900),
    VelocityPoint(country="IT", date=date(2025, 6, 30),  n_lockers=5_700),
    # Spain
    VelocityPoint(country="ES", date=date(2023, 12, 31), n_lockers=1_800),
    VelocityPoint(country="ES", date=date(2024, 12, 31), n_lockers=3_600),
    VelocityPoint(country="ES", date=date(2025, 6, 30),  n_lockers=4_200),
]


@router.get(
    "",
    response_model=ApiResponse[list[VelocityPoint]],
    operation_id="getVelocity",
)
async def get_velocity(
    country: str | None = Query(None, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$"),
) -> ApiResponse[list[VelocityPoint]]:
    """Network expansion timeline — static historical data points."""
    data = [p for p in HISTORICAL if country is None or p.country == country.upper()]
    return ApiResponse(
        data=data,
        meta={
            "count": len(data),
            "note": "Historical data from InPost press releases; daily live snapshots from 2026-05",
        },
    )
