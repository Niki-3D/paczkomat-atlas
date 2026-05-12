"""Integration test for paginated fetch using respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from paczkomat_atlas_api.ingest.inpost_client import InPostClient


@pytest.mark.asyncio
@respx.mock
async def test_iter_country_paginates_to_completion() -> None:
    base = "https://api-global-points.easypack24.net/v1"

    respx.get(f"{base}/points").mock(
        side_effect=[
            httpx.Response(200, json={
                "count": 3,
                "items": [
                    {"name": "A001", "country": "PL", "status": "Operating", "type": ["parcel_locker"]},
                    {"name": "A002", "country": "PL", "status": "Operating", "type": ["parcel_locker"]},
                ],
            }),
            httpx.Response(200, json={
                "count": 3,
                "items": [
                    {"name": "A003", "country": "PL", "status": "Operating", "type": ["parcel_locker"]},
                ],
            }),
            httpx.Response(200, json={"count": 3, "items": []}),
        ]
    )

    async with InPostClient() as client:
        names = [item["name"] async for item in client.iter_country("PL", per_page=2)]

    assert names == ["A001", "A002", "A003"]


@pytest.mark.asyncio
@respx.mock
async def test_iter_country_retries_on_500() -> None:
    base = "https://api-global-points.easypack24.net/v1"

    respx.get(f"{base}/points").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json={
                "count": 1,
                "items": [
                    {"name": "B001", "country": "FR", "status": "Operating", "type": ["pop"]},
                ],
            }),
            httpx.Response(200, json={"count": 1, "items": []}),
        ]
    )

    async with InPostClient() as client:
        names = [item["name"] async for item in client.iter_country("FR")]

    assert names == ["B001"]
