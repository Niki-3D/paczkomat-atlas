"""SQLAlchemy models — re-export for alembic autodiscovery."""

from paczkomat_atlas_api.models.gmina import GminaModel
from paczkomat_atlas_api.models.locker import LockerModel
from paczkomat_atlas_api.models.nuts2 import Nuts2Model
from paczkomat_atlas_api.models.population import (
    PopulationGminaModel,
    PopulationNuts2Model,
)
from paczkomat_atlas_api.models.snapshot import IngestSnapshotModel

__all__ = [
    "GminaModel",
    "IngestSnapshotModel",
    "LockerModel",
    "Nuts2Model",
    "PopulationGminaModel",
    "PopulationNuts2Model",
]
