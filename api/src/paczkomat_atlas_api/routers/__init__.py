"""FastAPI routers — one per domain. Mounted under /api/v1."""

from paczkomat_atlas_api.routers.density import router as density_router
from paczkomat_atlas_api.routers.health import router as health_router
from paczkomat_atlas_api.routers.kpi import router as kpi_router
from paczkomat_atlas_api.routers.locker import router as locker_router

__all__ = ["density_router", "health_router", "kpi_router", "locker_router"]
