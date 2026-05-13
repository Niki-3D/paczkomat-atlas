"""FastAPI routers — one per domain. Mounted under /api/v1."""

from paczkomat_atlas_api.routers.health import router as health_router

__all__ = ["health_router"]
