"""Full sync pipeline: fetch → filter → upsert → spatial-join post-process.

Plain async functions, no Procrastinate. Invoke via CLI or pg_cron.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.db import SessionLocal
from paczkomat_atlas_api.ingest.inpost_client import (
    COUNTRIES_ACTIVE,
    InPostClient,
    is_locker_type,
    is_valid_point,
)
from paczkomat_atlas_api.logging import get_logger
from paczkomat_atlas_api.models import LockerModel

log = get_logger("ingest.sync")

DEFAULT_BATCH_SIZE = 500


def compute_content_hash(item: dict[str, Any]) -> str:
    """Stable SHA-256 over canonical JSON. Used to detect changed records."""
    canon = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def item_to_row(item: dict[str, Any]) -> dict[str, Any]:
    """Map API payload to lockers row dict."""
    loc = item["location"]
    return {
        "name": item["name"],
        "country": item["country"],
        "status": item["status"],
        "physical_type": item.get("physical_type"),
        "location_247": bool(item.get("location_247", False)),
        "is_locker": is_locker_type(item),
        "geom": f"SRID=4326;POINT({loc['longitude']} {loc['latitude']})",
        "raw": item,
        "content_hash": compute_content_hash(item),
    }


async def upsert_batch(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    """Upsert by name. Skips rows whose content_hash is unchanged."""
    if not rows:
        return 0
    stmt = pg_insert(LockerModel).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["name"],
        set_={
            "country": stmt.excluded.country,
            "status": stmt.excluded.status,
            "physical_type": stmt.excluded.physical_type,
            "location_247": stmt.excluded.location_247,
            "is_locker": stmt.excluded.is_locker,
            "geom": stmt.excluded.geom,
            "raw": stmt.excluded.raw,
            "content_hash": stmt.excluded.content_hash,
        },
        where=(LockerModel.content_hash != stmt.excluded.content_hash),
    )
    await session.execute(stmt)
    return len(rows)


async def sync_country(country: str, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, int]:
    """Fetch + filter + upsert one country. Returns summary stats."""
    stats = {"fetched": 0, "filtered_out": 0, "upserted": 0}
    batch: list[dict[str, Any]] = []

    async with InPostClient() as client, SessionLocal() as session:
        async for item in client.iter_country(country):
            stats["fetched"] += 1
            if not is_valid_point(item):
                stats["filtered_out"] += 1
                continue
            batch.append(item_to_row(item))

            if len(batch) >= batch_size:
                stats["upserted"] += await upsert_batch(session, batch)
                await session.commit()
                batch.clear()
                log.info("ingest.batch_committed", country=country, total=stats["upserted"])

        if batch:
            stats["upserted"] += await upsert_batch(session, batch)
            await session.commit()

    log.info("ingest.country_complete", country=country, **stats)
    return stats


async def sync_all() -> dict[str, dict[str, int]]:
    """Sync every active country, sequentially."""
    results: dict[str, dict[str, int]] = {}
    for country in COUNTRIES_ACTIVE:
        log.info("ingest.country_start", country=country)
        results[country] = await sync_country(country)
    return results


async def assign_gminy() -> int:
    """Populate lockers.gmina_teryt via spatial join. Returns rows updated."""
    sql = text("""
        UPDATE lockers l
        SET gmina_teryt = g.teryt
        FROM gminy g
        WHERE l.country = 'PL'
          AND l.gmina_teryt IS NULL
          AND ST_Within(
            ST_Transform(l.geom::geometry, 2180),
            g.geom
          )
    """)
    async with SessionLocal() as session:
        result = await session.execute(sql)
        await session.commit()
        rowcount = result.rowcount or 0
    log.info("ingest.assign_gminy", updated=rowcount)
    return rowcount


async def assign_nuts2() -> int:
    """Populate lockers.nuts2_id via spatial join. Returns rows updated."""
    sql = text("""
        UPDATE lockers l
        SET nuts2_id = n.code
        FROM nuts2 n
        WHERE l.nuts2_id IS NULL
          AND ST_Within(l.geom::geometry, n.geom)
    """)
    async with SessionLocal() as session:
        result = await session.execute(sql)
        await session.commit()
        rowcount = result.rowcount or 0
    log.info("ingest.assign_nuts2", updated=rowcount)
    return rowcount


async def refresh_materialized_views() -> None:
    """Trigger CONCURRENT refresh of all dashboard MVs."""
    mvs = [
        "mv_country_kpi",
        "mv_density_gmina",
        "mv_density_nuts2",
        "mv_h3_density_r8",
    ]
    async with SessionLocal() as session:
        for mv in mvs:
            log.info("ingest.mv_refresh_start", mv=mv)
            await session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}"))
            await session.commit()
            log.info("ingest.mv_refresh_done", mv=mv)


async def snapshot_to_hypertable() -> int:
    """Insert current lockers state into ingest_snapshots hypertable."""
    sql = text("""
        INSERT INTO ingest_snapshots (snapshot_at, locker_name, country, is_locker, status, geom)
        SELECT now(), name, country, is_locker, status, geom::geometry
        FROM lockers
    """)
    async with SessionLocal() as session:
        result = await session.execute(sql)
        await session.commit()
        rowcount = result.rowcount or 0
    log.info("ingest.snapshot", rows=rowcount)
    return rowcount


async def full_pipeline(country: str | None = None) -> dict[str, Any]:
    """End-to-end: fetch → upsert → spatial-join → snapshot → refresh."""
    summary: dict[str, Any] = {}

    if country is None:
        summary["sync"] = await sync_all()
    else:
        summary["sync"] = {country: await sync_country(country)}

    summary["assign_gminy"] = await assign_gminy()
    summary["assign_nuts2"] = await assign_nuts2()
    summary["snapshot_rows"] = await snapshot_to_hypertable()
    await refresh_materialized_views()
    summary["mvs_refreshed"] = True

    return summary
