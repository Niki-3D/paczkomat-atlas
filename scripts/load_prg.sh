#!/bin/sh
# One-shot loader: ingests PRG gmina shapefile into staging.gminy_prg.
#
# Designed to run inside the `prg-loader` compose service (alpine + gdal +
# psql). NOT meant to be run on the host directly — the host doesn't have
# ogr2ogr or psql installed.
#
# Idempotent: ogr2ogr -overwrite replaces the staging table on every run.
# After this finishes the canonical-merge step lives in the api container —
# call paczkomat_atlas_api.ingest.prg_loader.merge_staging_to_gminy().
#
# Schema target: staging.gminy_prg with SRID 2180 (PUWG 1992) — matches what
# merge_staging_to_gminy expects (it joins on jpt_kod_je, copies geom in 2180).
set -eu

SHAPEFILE="${SHAPEFILE:-/data/prg/A03_Granice_gmin.shp}"
STAGING_TABLE="staging.gminy_prg"

if [ ! -f "$SHAPEFILE" ]; then
    echo "ERROR: $SHAPEFILE not found in container."
    echo "Expected the host path /home/doppler/paczkomat-atlas/data/raw/prg/"
    echo "to contain A03_Granice_gmin.{shp,shx,dbf,prj}."
    exit 1
fi

echo "Loading $SHAPEFILE into $STAGING_TABLE on ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}..."

# The staging schema is created by Alembic migration e7db2eafbd0e. We don't
# create it here so this loader can never accidentally outrun the migration
# tree and create a schema that diverges later.
ogr2ogr \
    -f PostgreSQL \
    "PG:host=${POSTGRES_HOST} port=${POSTGRES_PORT} dbname=${POSTGRES_DB} user=${POSTGRES_USER} password=${POSTGRES_PASSWORD}" \
    "$SHAPEFILE" \
    -nln "$STAGING_TABLE" \
    -overwrite \
    -lco GEOMETRY_NAME=geom \
    -lco FID=gid \
    -lco SPATIAL_INDEX=GIST \
    -lco SCHEMA=staging \
    -t_srs EPSG:2180 \
    -nlt PROMOTE_TO_MULTI \
    --config PG_USE_COPY YES \
    -progress

echo "ogr2ogr done."
# Row-count verification happens OUTSIDE this script — gdal:ubuntu-small
# does not bundle psql, and adding apt-get install to a one-shot loader
# would be wasteful. Verify with:
#   docker exec paczkomat-db psql -U $POSTGRES_USER -d $POSTGRES_DB \
#     -c "SELECT count(*) FROM staging.gminy_prg"
echo "Staging load complete. Next step: merge_staging_to_gminy in the api container."
