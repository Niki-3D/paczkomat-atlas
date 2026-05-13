"""Smoke tests against every endpoint. Requires running DB with data."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["locker_count"] > 100_000  # we have ~150k


@pytest.mark.asyncio
async def test_network_summary(client: AsyncClient) -> None:
    r = await client.get("/api/v1/kpi/summary")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["n_network_total"] > 100_000
    assert data["n_countries_active"] >= 10


@pytest.mark.asyncio
async def test_country_list(client: AsyncClient) -> None:
    r = await client.get("/api/v1/kpi/countries")
    assert r.status_code == 200
    countries = {c["country"] for c in r.json()["data"]}
    assert "PL" in countries
    assert "FR" in countries


@pytest.mark.asyncio
async def test_country_404(client: AsyncClient) -> None:
    r = await client.get("/api/v1/kpi/countries/ZZ")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_top_gminy(client: AsyncClient) -> None:
    r = await client.get("/api/v1/density/gminy/top?limit=5")
    assert r.status_code == 200
    rows = r.json()["data"]
    assert len(rows) == 5
    # Top gmina should be in dense locker country
    assert rows[0]["lockers_per_10k"] > 5


@pytest.mark.asyncio
async def test_top_nuts2_pl_dominates(client: AsyncClient) -> None:
    """All top NUTS-2 should be Polish — the headline insight."""
    r = await client.get("/api/v1/density/nuts2/top?limit=15")
    assert r.status_code == 200
    rows = r.json()["data"]
    pl_count = sum(1 for x in rows if x["country"] == "PL")
    # At least 10 of top 15 should be PL
    assert pl_count >= 10


@pytest.mark.asyncio
async def test_locker_filter_country(client: AsyncClient) -> None:
    r = await client.get("/api/v1/lockers?country=NL&limit=10")
    assert r.status_code == 200
    body = r.json()
    assert all(row["country"] == "NL" for row in body["data"])
    assert body["meta"]["total"] >= 1000  # NL has ~1400


@pytest.mark.asyncio
async def test_h3_pl(client: AsyncClient) -> None:
    r = await client.get("/api/v1/h3/cells?country=PL&limit=10")
    assert r.status_code == 200
    rows = r.json()["data"]
    assert len(rows) == 10
    assert all(c["country"] == "PL" for c in rows)


@pytest.mark.asyncio
async def test_velocity_pl(client: AsyncClient) -> None:
    r = await client.get("/api/v1/velocity?country=PL")
    assert r.status_code == 200
    rows = r.json()["data"]
    assert len(rows) >= 5  # at least 5 historical points
    assert all(p["country"] == "PL" for p in rows)


@pytest.mark.asyncio
async def test_cache_headers_on_data_endpoints(client: AsyncClient) -> None:
    r = await client.get("/api/v1/kpi/countries")
    assert "public" in r.headers.get("cache-control", "")


@pytest.mark.asyncio
async def test_no_cache_on_health(client: AsyncClient) -> None:
    r = await client.get("/api/v1/health")
    assert r.headers.get("cache-control") == "no-store"


@pytest.mark.asyncio
async def test_request_id_header(client: AsyncClient) -> None:
    r = await client.get("/api/v1/health")
    assert "x-request-id" in r.headers
