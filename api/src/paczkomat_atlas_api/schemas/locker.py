"""Locker schemas — list and detail views."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LockerSummary(BaseModel):
    """Compact locker row for list views."""

    name: str
    country: str = Field(..., min_length=2, max_length=2)
    status: str
    is_locker: bool = Field(..., description="True = Paczkomat machine, False = PUDO")
    physical_type: str | None
    location_247: bool
    latitude: float
    longitude: float


class LockerDetail(LockerSummary):
    """Full locker record including admin assignment + timestamps."""

    gmina_teryt: str | None
    nuts2_id: str | None
    updated_at: datetime
