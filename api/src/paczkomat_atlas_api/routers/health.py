"""Health endpoint — DB ping, lockers count, MV freshness."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.db import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Confirm app + DB + data freshness."""
    try:
        locker_count = (await session.execute(
            text("SELECT count(*) FROM lockers")
        )).scalar_one()
        mv_count = (await session.execute(
            text("SELECT count(*) FROM mv_country_kpi")
        )).scalar_one()
        snapshot_count = (await session.execute(
            text("SELECT count(*) FROM ingest_snapshots")
        )).scalar_one()
        return {
            "status": "ok",
            "db": "connected",
            "locker_count": int(locker_count),
            "country_kpi_rows": int(mv_count),
            "snapshot_rows": int(snapshot_count),
        }
    except Exception as e:
        # Health endpoint deliberately catches everything to keep returning JSON
        return {"status": "degraded", "db": "error", "error": str(e)[:200]}
