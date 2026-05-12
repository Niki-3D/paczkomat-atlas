"""EU NUTS-2 regions from Eurostat GISCO. Native EPSG:4326."""

from __future__ import annotations

from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from paczkomat_atlas_api.db import SRID_WGS84, Base


class Nuts2Model(Base):
    """A NUTS-2 region (sub-country level, e.g. Île-de-France, Bayern)."""

    __tablename__ = "nuts2"

    code: Mapped[str] = mapped_column(String(5), primary_key=True)  # e.g. "PL92"
    name_latn: Mapped[str] = mapped_column(String(256), nullable=False)
    country: Mapped[str] = mapped_column(String(2), index=True)

    geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=SRID_WGS84, spatial_index=True),
    )
