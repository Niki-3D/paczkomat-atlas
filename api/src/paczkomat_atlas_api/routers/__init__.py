"""FastAPI routers — one per domain. Mounted under /api/v1."""

from paczkomat_atlas_api.routers.health import router as health_router
from paczkomat_atlas_api.routers.kpi import router as kpi_router

__all__ = ["health_router", "kpi_router"]
