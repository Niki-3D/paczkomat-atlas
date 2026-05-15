"""add app role with least privilege

Revision ID: 72d896bb1f4e
Revises: 801d68ba0f8e
Create Date: 2026-05-15 11:27:37.342627

Creates `paczkomat_app` — the role the production FastAPI process connects as.

Privileges (strictly less than the admin role used in dev):
- USAGE on schema public
- SELECT on all existing and future tables (including materialized views)
- SELECT on all sequences (counters used by ORM defaults)
- INSERT / UPDATE / DELETE on the seven ingest target tables only
- EXECUTE on the three Martin tile-source functions

Explicitly NOT granted:
- Superuser, CREATEDB, CREATEROLE, REPLICATION
- DDL on schema public
- pg_cron job management
- Access to extensions / system catalogs beyond the standard PUBLIC grants

Password handling:
- Migration creates the role with a placeholder password `change_me_at_deploy`.
- On first prod deploy, rotate via `ALTER ROLE paczkomat_app PASSWORD '<rand>'`
  and put the value in POSTGRES_APP_PASSWORD. See docs/DEPLOY.md.

Dev environments keep using the admin role (DATABASE_URL points there) and
this migration adds capability without changing behaviour. Switching the dev
app to the restricted role would block schema-modifying tests.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '72d896bb1f4e'
down_revision: Union[str, Sequence[str], None] = '801d68ba0f8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WRITE_TABLES = (
    "lockers",
    "ingest_snapshots",
    "population_gmina",
    "population_nuts2",
    "gminy",
    "nuts2",
)

TILE_FUNCTIONS = (
    "lockers_tiles(integer, integer, integer, json)",
    "nuts2_density_tiles(integer, integer, integer, json)",
    "gminy_density_tiles(integer, integer, integer, json)",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'paczkomat_app') THEN
                CREATE ROLE paczkomat_app WITH LOGIN PASSWORD 'change_me_at_deploy';
            END IF;
        END
        $$;
        """
    )

    op.execute("GRANT USAGE ON SCHEMA public TO paczkomat_app")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO paczkomat_app")
    op.execute("GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO paczkomat_app")

    write_grants = ", ".join(WRITE_TABLES)
    op.execute(
        f"GRANT INSERT, UPDATE, DELETE ON {write_grants} TO paczkomat_app"
    )

    # Future-proof: tables created after this migration get SELECT automatically.
    # Write privileges are intentionally NOT in default privileges — new write
    # targets must be added explicitly in a follow-up migration so the blast
    # radius is reviewed each time the schema grows.
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT ON TABLES TO paczkomat_app
        """
    )
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT ON SEQUENCES TO paczkomat_app
        """
    )

    for fn in TILE_FUNCTIONS:
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO paczkomat_app")


def downgrade() -> None:
    """Downgrade schema."""
    # DROP OWNED revokes every grant the role holds across the database, then
    # DROP ROLE removes the role itself. Safe because the role only ever has
    # grants from this migration — it never owns objects.
    op.execute("DROP OWNED BY paczkomat_app CASCADE")
    op.execute("DROP ROLE IF EXISTS paczkomat_app")
