"""Lockers — current snapshot of all InPost pickup points."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from paczkomat_atlas_api.db import SRID_WGS84, Base


class LockerModel(Base):
    """A single InPost pickup point (parcel_locker machine or PUDO)."""

    __tablename__ = "lockers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    country: Mapped[str] = mapped_column(String(2), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    physical_type: Mapped[str | None] = mapped_column(String(32))
    location_247: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locker: Mapped[bool] = mapped_column(Boolean, index=True)

    geom: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=SRID_WGS84, spatial_index=True),
    )

    # Spatial join results — populated after ingest by post-processing
    gmina_teryt: Mapped[str | None] = mapped_column(
        String(7), ForeignKey("gminy.teryt", ondelete="SET NULL"), index=True,
    )
    nuts2_id: Mapped[str | None] = mapped_column(
        String(5), ForeignKey("nuts2.code", ondelete="SET NULL"), index=True,
    )

    raw: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_lockers_country_is_locker", "country", "is_locker"),
        Index("ix_lockers_country_status", "country", "status"),
    )
