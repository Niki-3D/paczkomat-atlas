"""Test fixtures — async httpx client against the running app."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from paczkomat_atlas_api.main import app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """ASGI-transport async client; hits the real DB through the real engine."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
