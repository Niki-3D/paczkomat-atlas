"""Cache-Control headers — data updates once daily, cache aggressively."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Path prefixes that get long-cache headers. Everything else is no-cache.
CACHED_PREFIXES: tuple[str, ...] = (
    "/api/v1/density",
    "/api/v1/kpi",
    "/api/v1/h3",
    "/api/v1/velocity",
)

CACHE_HEADER = "public, max-age=3600, stale-while-revalidate=86400"


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Add Cache-Control headers based on path prefix.

    Data updates once daily (after the 04:15-04:45 pg_cron MV refresh window).
    1h max-age + 24h stale-while-revalidate gives near-instant CDN responses
    with reasonable freshness.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        if request.url.path.startswith(CACHED_PREFIXES) and request.method == "GET":
            response.headers["Cache-Control"] = CACHE_HEADER
        else:
            response.headers["Cache-Control"] = "no-store"
        return response
