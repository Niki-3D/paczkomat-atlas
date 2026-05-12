"""Time-series snapshots of locker state for expansion-velocity analytics.

Hypertable created via alembic op.execute, not declarative — TimescaleDB
hypertable creation requires the table to exist first, then create_hypertable().
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from paczkomat_atlas_api.db import SRID_WGS84, Base


class IngestSnapshotModel(Base):
    """One row = one locker state at one snapshot time. Hypertable on snapshot_at."""

    __tablename__ = "ingest_snapshots"

    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    locker_name: Mapped[str] = mapped_column(String(64))
    country: Mapped[str] = mapped_column(String(2))
    is_locker: Mapped[bool] = mapped_column()
    status: Mapped[str] = mapped_column(String(16))

    geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=SRID_WGS84),
    )

    __table_args__ = (
        PrimaryKeyConstraint("snapshot_at", "locker_name", name="pk_ingest_snapshots"),
    )
