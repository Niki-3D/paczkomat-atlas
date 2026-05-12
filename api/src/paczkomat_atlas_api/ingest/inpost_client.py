"""InPost public points API client.

Endpoint: https://api-global-points.easypack24.net/v1/points
Verified by recon (docs/recon/01-inpost-api.md, 04-cross-country.md):
- 14 country codes, ~154k total records
- No incremental sync — full re-crawl strategy
- Max per_page=5000 verified working
- Unknown params silently ignored — assert count to detect filter bugs
- Per-country test-data and null-island patterns vary; see data-quality-rules.md
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import Any, Final

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from paczkomat_atlas_api.config import settings
from paczkomat_atlas_api.logging import get_logger

log = get_logger("ingest.inpost")

DEFAULT_PER_PAGE: Final = 1000
MAX_PER_PAGE: Final = 5000
DEFAULT_TIMEOUT: Final = 30.0

COUNTRIES_ACTIVE: Final[tuple[str, ...]] = (
    "PL", "FR", "GB", "DE", "ES", "IT",
    "AT", "SE", "PT", "HU", "DK", "FI", "BE", "NL",
)

VALID_STATUSES: Final[frozenset[str]] = frozenset({
    "Operating", "Created", "Disabled", "Overloaded",
})

# Country-specific test markers (data-quality-rules.md)
IT_TEST_NAME_RE: Final = re.compile(r"^DGM.*TEST", re.IGNORECASE)
TEST_PROVINCES: Final[frozenset[str]] = frozenset({"test", "TEST"})


class InPostAPIError(Exception):
    """Non-recoverable API error."""


class InPostClient:
    """Async client for the InPost public points API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = (base_url or settings.inpost_api_url).rstrip("/")
        self._timeout = timeout
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> InPostClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        wait=wait_exponential(multiplier=1.5, min=1, max=15),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        assert self._client is not None
        url = f"{self._base_url}/{path.lstrip('/')}"
        resp = await self._client.get(url, params=params)

        if resp.status_code in (429, 500, 502, 503, 504):
            log.warning("inpost.retry_status", status=resp.status_code, url=str(resp.url))
            resp.raise_for_status()  # triggers tenacity retry

        if resp.status_code >= 400:
            raise InPostAPIError(f"http {resp.status_code}: {resp.text[:200]}")

        return resp.json()

    async def fetch_page(
        self,
        country: str,
        page: int = 1,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> dict[str, Any]:
        if per_page > MAX_PER_PAGE:
            raise ValueError(f"per_page {per_page} exceeds max {MAX_PER_PAGE}")
        return await self._get("points", {
            "country": country, "page": page, "per_page": per_page,
        })

    async def iter_country(
        self,
        country: str,
        per_page: int = DEFAULT_PER_PAGE,
    ) -> AsyncIterator[dict[str, Any]]:
        """Paginate through every record for one country."""
        page = 1
        seen = 0
        total: int | None = None

        while True:
            body = await self.fetch_page(country, page=page, per_page=per_page)
            items = body.get("items", [])
            if total is None:
                total = body.get("count", 0)
                log.info(
                    "inpost.country_start",
                    country=country, total=total, per_page=per_page,
                )

            if not items:
                break

            for item in items:
                yield item
                seen += 1

            if total is not None and seen >= total:
                break
            page += 1

        log.info("inpost.country_done", country=country, yielded=seen)


def is_valid_point(item: dict[str, Any]) -> bool:
    """Apply data-quality-rules.md filters.

    Returns False for:
    - PL/PL-style test data (province in {'test', 'TEST'})
    - IT test data (name matches DGM*TEST)
    - Null island (lat/lon both zero)
    - Unknown status enum values
    """
    province = (item.get("address_details") or {}).get("province")
    if province in TEST_PROVINCES:
        return False

    name = item.get("name", "")
    if IT_TEST_NAME_RE.match(name):
        return False

    loc = item.get("location") or {}
    if loc.get("latitude") in (0, 0.0) and loc.get("longitude") in (0, 0.0):
        return False

    if item.get("status") not in VALID_STATUSES:
        return False

    return True


def is_locker_type(item: dict[str, Any]) -> bool:
    """True = parcel_locker (Paczkomat machine), False = PUDO/other.

    Verified cross-country in docs/recon/04-cross-country.md.
    """
    types = item.get("type") or []
    return "parcel_locker" in types
