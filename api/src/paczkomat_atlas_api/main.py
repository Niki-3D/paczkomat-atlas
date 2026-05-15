"""FastAPI entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from paczkomat_atlas_api.config import settings
from paczkomat_atlas_api.logging import configure_logging, get_logger
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


_error_log = get_logger("http")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for un-handled exceptions.

    FastAPI's default 500 response is already minimal (`{"detail":"Internal
    Server Error"}`), but it doesn't echo the request_id and doesn't go
    through our structlog pipeline. This handler logs the full traceback
    server-side and returns a sanitized JSON body with the request_id so
    operators can correlate user-reported failures to a log line.
    """
    request_id = request.headers.get("x-request-id", "unknown")
    _error_log.exception(
        "http.unhandled_error",
        method=request.method,
        path=request.url.path,
        error_type=exc.__class__.__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "errors": [{"code": "internal_server_error", "message": "Internal server error"}],
            "request_id": request_id,
        },
    )


@app.get("/", operation_id="root")
async def root() -> dict[str, str]:
    return {"service": "paczkomat-atlas-api", "version": app.version, "docs": "/docs"}
