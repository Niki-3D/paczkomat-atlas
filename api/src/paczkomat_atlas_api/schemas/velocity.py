"""Network expansion velocity — time-series of locker counts.

NOTE: v1 uses static historical points from InPost press releases (documented
in README). Phase 6+ will switch to TimescaleDB continuous aggregates once
we have a year of daily snapshots.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class VelocityPoint(BaseModel):
    """One (country, date, count) data point for the expansion timeline."""

    country: str
    date: date
    n_lockers: int
    source: str = "press_release"  # or "ingest_snapshot" once we have data
