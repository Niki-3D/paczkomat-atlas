"""Ingest CLI entry point.

Usage:
    uv run python -m paczkomat_atlas_api.ingest.cli --country PL
    uv run python -m paczkomat_atlas_api.ingest.cli --all
    uv run python -m paczkomat_atlas_api.ingest.cli --refresh-only
    uv run python -m paczkomat_atlas_api.ingest.cli --snapshot-only
"""

from __future__ import annotations

import argparse
import asyncio

from paczkomat_atlas_api.ingest.sync import (
    assign_gminy,
    assign_nuts2,
    full_pipeline,
    refresh_materialized_views,
    snapshot_to_hypertable,
    sync_country,
)
from paczkomat_atlas_api.logging import configure_logging, get_logger


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Paczkomat Atlas ingest")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--country", type=str, help="ISO-3166 alpha-2, e.g. PL")
    g.add_argument("--all", action="store_true", help="All 14 active countries")
    g.add_argument("--refresh-only", action="store_true", help="Just REFRESH the MVs")
    g.add_argument("--snapshot-only", action="store_true", help="Just snapshot to hypertable")
    g.add_argument("--assign-only", action="store_true", help="Just spatial joins")
    g.add_argument("--load-prg", action="store_true", help="Load PRG gminy from data/raw/prg/")
    g.add_argument("--load-nuts2", action="store_true", help="Load Eurostat NUTS-2 from data/raw/eurostat/")
    g.add_argument("--load-population", action="store_true", help="Load GUS + Eurostat population data")
    p.add_argument("--batch-size", type=int, default=500)
    return p.parse_args()


async def _main() -> None:
    configure_logging()
    log = get_logger("ingest.cli")
    args = _parse_args()

    if args.load_prg:
        from urllib.parse import urlparse

        from paczkomat_atlas_api.config import settings as _s
        from paczkomat_atlas_api.ingest.prg_loader import (
            compute_areas,
            merge_staging_to_gminy,
            run_ogr2ogr_to_staging,
        )
        url = urlparse(_s.database_url.replace("postgresql+asyncpg", "postgresql"))
        run_ogr2ogr_to_staging(
            db_host="db",  # docker network alias inside paczkomat-atlas_default
            db_port=5432,
            db_user=url.username or "",
            db_pass=url.password or "",
            db_name=(url.path or "/").lstrip("/"),
        )
        merged = await merge_staging_to_gminy()
        areas = await compute_areas()
        log.info("cli.prg_done", merged=merged, areas=areas)
        return

    if args.refresh_only:
        await refresh_materialized_views()
    elif args.snapshot_only:
        rows = await snapshot_to_hypertable()
        log.info("cli.snapshot_done", rows=rows)
    elif args.assign_only:
        g = await assign_gminy()
        n = await assign_nuts2()
        log.info("cli.assign_done", gminy=g, nuts2=n)
    elif args.all:
        summary = await full_pipeline()
        log.info("cli.full_pipeline_done", **summary)
    else:
        await sync_country(args.country, batch_size=args.batch_size)
        # Don't run full pipeline for single-country — keeps the CLI predictable
        log.info("cli.single_country_done", country=args.country,
                 hint="run --refresh-only and --snapshot-only separately if needed")


if __name__ == "__main__":
    asyncio.run(_main())
