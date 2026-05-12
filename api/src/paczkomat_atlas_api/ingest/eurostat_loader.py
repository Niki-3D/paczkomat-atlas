"""Load Eurostat NUTS-2 boundaries and population.

Sources:
- data/raw/eurostat/nuts2_2024.geojson (NUTS_RG_01M_2024_4326_LEVL_2.geojson)
- data/raw/eurostat/population_nuts2_2024.tsv.gz (demo_r_pjangrp3)
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from sqlalchemy import text

from paczkomat_atlas_api.db import SessionLocal
from paczkomat_atlas_api.logging import get_logger

log = get_logger("ingest.eurostat")

NUTS_FILE = Path("data/raw/eurostat/nuts2_2024.geojson")
POP_FILE = Path("data/raw/eurostat/population_nuts2_2024.tsv.gz")


async def load_nuts2_boundaries() -> int:
    """Load NUTS-2 polygons from GeoJSON. SRID 4326 native."""
    if not NUTS_FILE.exists():
        raise FileNotFoundError(f"NUTS-2 file not found at {NUTS_FILE}.")

    with NUTS_FILE.open(encoding="utf-8") as f:
        fc = json.load(f)

    rows = []
    for feat in fc.get("features", []):
        props = feat.get("properties", {})
        code = props.get("NUTS_ID")
        if not code or len(code) != 4:  # NUTS-2 codes are 4 chars (e.g. PL92)
            continue
        rows.append({
            "code": code,
            "name_latn": props.get("NAME_LATN") or props.get("NUTS_NAME") or code,
            "country": props.get("CNTR_CODE", code[:2]),
            "geom_geojson": json.dumps(feat["geometry"]),
        })

    if not rows:
        log.warning("eurostat.no_nuts2_parsed")
        return 0

    sql = text("""
        INSERT INTO nuts2 (code, name_latn, country, geom)
        VALUES (
            :code, :name_latn, :country,
            ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom_geojson), 4326))
        )
        ON CONFLICT (code) DO UPDATE SET
            name_latn = EXCLUDED.name_latn,
            country = EXCLUDED.country,
            geom = EXCLUDED.geom
    """)
    async with SessionLocal() as session:
        for i in range(0, len(rows), 100):
            chunk = rows[i:i + 100]
            await session.execute(sql, chunk)
        await session.commit()

    log.info("eurostat.nuts2_loaded", rows=len(rows))
    return len(rows)


async def load_nuts2_population() -> int:
    """Parse Eurostat TSV population file. demo_r_pjangrp3 format.

    Composite key column header: 'freq,sex,unit,age,geo\\TIME_PERIOD'.
    The URL's age=TOTAL&sex=T&time=2024 filters are silently ignored by
    the bulk-download endpoint, so the file contains every sex/age combo
    for all years 2014–2025. We filter in-process.
    """
    if not POP_FILE.exists():
        raise FileNotFoundError(f"Eurostat population file not found at {POP_FILE}.")

    # Restrict inserts to NUTS-2 codes we actually loaded (avoid FK violations
    # from EFTA / candidate-country regions that Eurostat publishes but we
    # don't have boundaries for).
    async with SessionLocal() as session:
        known_codes_result = await session.execute(text("SELECT code FROM nuts2"))
        known_codes: set[str] = {row[0] for row in known_codes_result.all()}
    log.info("eurostat.known_nuts2_codes", count=len(known_codes))

    rows = []
    with gzip.open(POP_FILE, mode="rt", encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        try:
            year_idx = next(
                i for i, h in enumerate(header) if h.strip() == "2024"
            )
        except StopIteration:
            log.warning("eurostat.no_2024_column", header=header[:5])
            return 0

        # Locate dimension positions in the composite key.
        # Header format: 'freq,sex,unit,age,geo\TIME_PERIOD'
        key_header = header[0].split("\\")[0]
        dims = key_header.split(",")
        try:
            sex_pos = dims.index("sex")
            age_pos = dims.index("age")
            geo_pos = dims.index("geo")
        except ValueError:
            log.error("eurostat.unexpected_dims", dims=dims)
            return 0

        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < year_idx + 1:
                continue
            key_parts = parts[0].split(",")
            if len(key_parts) <= max(sex_pos, age_pos, geo_pos):
                continue
            sex = key_parts[sex_pos].strip()
            age = key_parts[age_pos].strip()
            geo = key_parts[geo_pos].strip()
            if sex != "T" or age != "TOTAL":
                continue
            if len(geo) != 4 or geo not in known_codes:
                continue
            raw_val = parts[year_idx].strip().rstrip(":").strip()
            if not raw_val or raw_val == ":":
                continue
            val_clean = "".join(c for c in raw_val.split(" ")[0] if c.isdigit())
            if not val_clean or val_clean == "0":
                continue
            rows.append({"code": geo, "year": 2024, "value": int(val_clean)})

    if not rows:
        log.warning("eurostat.no_population_parsed")
        return 0

    sql = text("""
        INSERT INTO population_nuts2 (code, year, value)
        VALUES (:code, :year, :value)
        ON CONFLICT (code, year) DO UPDATE SET value = EXCLUDED.value
    """)
    async with SessionLocal() as session:
        for i in range(0, len(rows), 500):
            chunk = rows[i:i + 500]
            await session.execute(sql, chunk)
        await session.commit()

    log.info("eurostat.population_loaded", rows=len(rows))
    return len(rows)
