"""Population data — keyed by gmina TERYT or NUTS-2 code, with year."""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, PrimaryKeyConstraint, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from paczkomat_atlas_api.db import Base


class PopulationGminaModel(Base):
    """Population per gmina per year, from GUS BDL."""

    __tablename__ = "population_gmina"

    teryt: Mapped[str] = mapped_column(
        String(7), ForeignKey("gminy.teryt", ondelete="CASCADE"),
    )
    year: Mapped[int] = mapped_column(SmallInteger)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("teryt", "year", name="pk_population_gmina"),
    )


class PopulationNuts2Model(Base):
    """Population per NUTS-2 region per year, from Eurostat."""

    __tablename__ = "population_nuts2"

    code: Mapped[str] = mapped_column(
        String(5), ForeignKey("nuts2.code", ondelete="CASCADE"),
    )
    year: Mapped[int] = mapped_column(SmallInteger)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("code", "year", name="pk_population_nuts2"),
    )
