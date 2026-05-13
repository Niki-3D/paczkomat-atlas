"""H3 hex cell schemas — for the heatmap layer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class H3Cell(BaseModel):
    """One H3 hex with aggregated locker counts."""

    h3: str = Field(..., description="H3 cell index as hex string")
    country: str
    n_lockers: int = Field(..., ge=0)
    n_pudo: int = Field(..., ge=0)
    n_total: int = Field(..., ge=0)
    # geom returned separately via vector tile endpoint, not JSON
