"""Health endpoint — DB ping, lockers count, MV freshness, tile server reachable."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.config import settings
from paczkomat_atlas_api.db import get_session

router = APIRouter(tags=["health"])


@router.get("/health", operation_id="healthCheck")
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Confirm app + DB + tile server + data freshness.

    Returns granular booleans (`db_ok`, `martin_ok`) alongside the legacy
    string fields so the frontend nav badge can show "API healthy" even
    when only the tile server is having a moment.
    """
    db_ok = True
    martin_ok = True
    payload: dict[str, object] = {"db": "ok", "martin": "unknown"}

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
        payload.update({
            "locker_count": int(locker_count),
            "country_kpi_rows": int(mv_count),
            "snapshot_rows": int(snapshot_count),
        })
    except Exception as e:
        db_ok = False
        payload["db"] = f"error: {str(e)[:120]}"

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(settings.martin_health_url)
        if r.status_code == 200:
            payload["martin"] = "ok"
        else:
            payload["martin"] = f"http {r.status_code}"
            martin_ok = False
    except Exception as e:
        payload["martin"] = f"unreachable: {str(e)[:120]}"
        martin_ok = False

    payload["db_ok"] = db_ok
    payload["martin_ok"] = martin_ok
    # Legacy aggregate string for older clients.
    payload["status"] = "ok" if (db_ok and martin_ok) else "degraded"
    return payload
