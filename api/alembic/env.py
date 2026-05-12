"""Alembic env — async migrations driven by app settings."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Register all models so autogenerate sees them
from paczkomat_atlas_api.db import Base  # noqa: F401
from paczkomat_atlas_api.models import *  # noqa: F401, F403
from paczkomat_atlas_api.config import settings

# Optional: PostgreSQL enum support for autogenerate
try:
    import alembic_postgresql_enum  # noqa: F401
except ImportError:
    pass

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Force database URL from settings, not alembic.ini
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """Exclude PostGIS/TimescaleDB internal tables from autogenerate."""
    if type_ == "table" and name.startswith(("spatial_ref_sys", "_timescaledb_", "topology")):
        return False
    if type_ == "schema" and name in ("tiger", "topology", "_timescaledb_internal", "_timescaledb_catalog"):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
