"""Load PRG (Polish gmina boundaries) into Postgres via ogr2ogr.

PRG ships in EPSG:2180 (PUWG 1992). We keep that SRID in the gminy table for
metric-accurate area/distance ops within Poland.

The shapefile attribute we care about is JPT_KOD_JE — the 7-char TERYT code.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sqlalchemy import text

from paczkomat_atlas_api.db import SessionLocal
from paczkomat_atlas_api.logging import get_logger

log = get_logger("ingest.prg")

PRG_SHAPEFILE = Path("data/raw/prg/A03_Granice_gmin.shp")
GDAL_IMAGE = "ghcr.io/osgeo/gdal:ubuntu-small-3.10.0"
DOCKER_NETWORK = "paczkomat-atlas_default"


def run_ogr2ogr_to_staging(
    db_host: str, db_port: int, db_user: str, db_pass: str, db_name: str
) -> None:
    """Load PRG shapefile into staging.gminy_prg via ogr2ogr.

    Uses the GDAL container wrapper (scripts/ogr.sh). Caller must ensure
    the DB schema 'staging' exists.
    """
    if not PRG_SHAPEFILE.exists():
        raise FileNotFoundError(
            f"PRG shapefile not found at {PRG_SHAPEFILE}. "
            "Run scripts/download_static_data.sh first."
        )

    # Invoke `docker run` directly rather than the scripts/ogr.sh wrapper.
    # Python's subprocess on Windows can't execute .sh shebangs reliably
    # (WinError 193) and falling back to `bash` picks up WSL's bash, which
    # mis-resolves the project paths. Calling docker straight avoids both.
    # `os.getcwd()` is fine here because the loader is always invoked from
    # repo root (cli.py / CLI usage requires it for data/raw/* paths).
    cwd = os.getcwd().replace("\\", "/")
    # On Git Bash, MSYS_NO_PATHCONV stops Bash from rewriting /work into a
    # Windows path on the way to docker.exe.
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{cwd}:/work",
        "-w", "/work",
        "--network", DOCKER_NETWORK,
        GDAL_IMAGE,
        "ogr2ogr",
        "-f", "PostgreSQL",
        f"PG:host={db_host} port={db_port} user={db_user} password={db_pass} dbname={db_name}",
        PRG_SHAPEFILE.as_posix(),  # forward slashes for the Linux container
        "-nln", "staging.gminy_prg",
        "-overwrite",
        "-lco", "GEOMETRY_NAME=geom",
        "-lco", "FID=gid",
        "-lco", "SCHEMA=staging",
        "-t_srs", "EPSG:2180",
        "-nlt", "PROMOTE_TO_MULTI",
        "--config", "PG_USE_COPY", "YES",
    ]
    log.info("prg.ogr2ogr_start", file=str(PRG_SHAPEFILE))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if result.returncode != 0:
        log.error("prg.ogr2ogr_failed", stderr=result.stderr[:1000])
        raise RuntimeError(f"ogr2ogr failed: {result.stderr[:200]}")
    log.info("prg.ogr2ogr_done")


async def merge_staging_to_gminy() -> int:
    """Move staging.gminy_prg into canonical gminy table. Idempotent."""
    sql = text("""
        INSERT INTO gminy (teryt, name, voivodeship, powiat, geom)
        SELECT
            jpt_kod_je AS teryt,
            jpt_nazwa_ AS name,
            -- TERYT code structure: WWPPGG_T — first 2 chars = voivodeship code
            CASE LEFT(jpt_kod_je, 2)
                WHEN '02' THEN 'dolnośląskie'
                WHEN '04' THEN 'kujawsko-pomorskie'
                WHEN '06' THEN 'lubelskie'
                WHEN '08' THEN 'lubuskie'
                WHEN '10' THEN 'łódzkie'
                WHEN '12' THEN 'małopolskie'
                WHEN '14' THEN 'mazowieckie'
                WHEN '16' THEN 'opolskie'
                WHEN '18' THEN 'podkarpackie'
                WHEN '20' THEN 'podlaskie'
                WHEN '22' THEN 'pomorskie'
                WHEN '24' THEN 'śląskie'
                WHEN '26' THEN 'świętokrzyskie'
                WHEN '28' THEN 'warmińsko-mazurskie'
                WHEN '30' THEN 'wielkopolskie'
                WHEN '32' THEN 'zachodniopomorskie'
            END AS voivodeship,
            NULL AS powiat,
            geom
        FROM staging.gminy_prg
        WHERE jpt_kod_je IS NOT NULL
          AND length(jpt_kod_je) = 7
        ON CONFLICT (teryt) DO UPDATE SET
            name = EXCLUDED.name,
            voivodeship = EXCLUDED.voivodeship,
            geom = EXCLUDED.geom
    """)
    async with SessionLocal() as session:
        result = await session.execute(sql)
        await session.commit()
        rowcount = result.rowcount or 0
    log.info("prg.merge_done", rows=rowcount)
    return rowcount


async def compute_areas() -> int:
    """Populate gminy.area_km2 using EPSG:2180 (metric)."""
    sql = text("""
        UPDATE gminy
        SET area_km2 = ROUND((ST_Area(geom) / 1e6)::numeric, 2)
        WHERE area_km2 IS NULL
    """)
    async with SessionLocal() as session:
        result = await session.execute(sql)
        await session.commit()
        rowcount = result.rowcount or 0
    log.info("prg.areas_computed", rows=rowcount)
    return rowcount
