"""Async DB engine, session factory, declarative base, SRID constants."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Final

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from paczkomat_atlas_api.config import settings

# SRID constants — never hardcode in queries
SRID_WGS84: Final[int] = 4326          # storage default (geography)
SRID_PL_PUWG: Final[int] = 2180        # PUWG 1992 — metric ops within Poland
SRID_EU_LAEA: Final[int] = 3035        # LAEA Europe — metric ops pan-EU
SRID_WEB_MERCATOR: Final[int] = 3857   # tile generation only

# pgbouncer transaction pooling requires prepared_statement_cache_size=0
# to avoid "prepared statement does not exist" errors.
_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "pool_size": 5,
    "max_overflow": 10,
}
if "pgbouncer" in settings.database_url or ":6432" in settings.database_url:
    _engine_kwargs["connect_args"] = {"prepared_statement_cache_size": 0}


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""


engine = create_async_engine(settings.database_url, **_engine_kwargs)

SessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a transactional async session."""
    async with SessionLocal() as session:
        yield session
