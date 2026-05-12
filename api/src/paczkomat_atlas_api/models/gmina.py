"""Polish gminas (LAU2) from PRG. Native EPSG:2180."""

from __future__ import annotations

from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from paczkomat_atlas_api.db import SRID_PL_PUWG, Base


class GminaModel(Base):
    """Polish gmina (administrative commune) with PRG geometry."""

    __tablename__ = "gminy"

    teryt: Mapped[str] = mapped_column(String(7), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    voivodeship: Mapped[str | None] = mapped_column(String(64))
    powiat: Mapped[str | None] = mapped_column(String(128))

    geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=SRID_PL_PUWG, spatial_index=True),
    )

    area_km2: Mapped[float | None] = mapped_column(Numeric(10, 2))
