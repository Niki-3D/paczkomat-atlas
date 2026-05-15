"""FastAPI entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from paczkomat_atlas_api.config import settings
from paczkomat_atlas_api.logging import configure_logging
from paczkomat_atlas_api.middleware import CacheControlMiddleware, RequestLoggingMiddleware
from paczkomat_atlas_api.routers import (
    density_router,
    h3_router,
    health_router,
    kpi_router,
    locker_router,
    velocity_router,
)

configure_logging()

app = FastAPI(
    title="Paczkomat Atlas API",
    description="InPost parcel locker network analytics — coverage, density, expansion.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(health_router, prefix="/api/v1")
app.include_router(kpi_router, prefix="/api/v1")
app.include_router(density_router, prefix="/api/v1")
app.include_router(locker_router, prefix="/api/v1")
app.include_router(h3_router, prefix="/api/v1")
app.include_router(velocity_router, prefix="/api/v1")


@app.get("/", operation_id="root")
async def root() -> dict[str, str]:
    return {"service": "paczkomat-atlas-api", "version": app.version, "docs": "/docs"}
