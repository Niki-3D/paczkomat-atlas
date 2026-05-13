#!/usr/bin/env bash
# Download static boundary and population data sources.
# Idempotent — skips downloads if files already present.
set -euo pipefail

mkdir -p data/raw/prg data/raw/eurostat data/raw/gus

# === PRG: Polish gmina boundaries ===
# dane.gov.pl resource id 29515 — "jednostki administracyjne" (admin units),
# Shapefile format, refreshed in place by GUGiK. Source page at:
#   https://dane.gov.pl/pl/dataset/726
PRG_URL="https://api.dane.gov.pl/media/resources/20210420/00_jednostki_administracyjne.zip"
PRG_ZIP="data/raw/prg/00_jednostki_administracyjne.zip"
if [ ! -f "$PRG_ZIP" ]; then
  echo "Downloading PRG (~375 MB)..."
  curl -fL --retry 3 -o "$PRG_ZIP" "$PRG_URL"
else
  echo "PRG zip already present, skipping download."
fi

if [ ! -f data/raw/prg/A03_Granice_gmin.shp ]; then
  # Selective extract: pull only the 4 gmina-boundary files from the ~600MB
  # archive (shp, shx, dbf, prj — no cpg in this distribution).
  # Files are at the zip root, so use a flat pattern (no leading */).
  # -j flattens paths anyway; -o overwrites if rerun.
  echo "Extracting PRG gmina boundaries only..."
  unzip -j -o "$PRG_ZIP" "A03_Granice_gmin.*" -d data/raw/prg/
fi

# === Eurostat NUTS-2 boundaries (2024 release) ===
EUROSTAT_NUTS_URL="https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2024_4326_LEVL_2.geojson"
NUTS_FILE="data/raw/eurostat/nuts2_2024.geojson"
if [ ! -f "$NUTS_FILE" ]; then
  echo "Downloading Eurostat NUTS-2..."
  curl -fL --retry 3 -o "$NUTS_FILE" "$EUROSTAT_NUTS_URL"
else
  echo "NUTS-2 already present, skipping."
fi

# === Eurostat population per NUTS-2 ===
# demo_r_pjangrp3: Population on 1 January by age, sex and NUTS-2 region
EUROSTAT_POP_URL="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/demo_r_pjangrp3?format=TSV&compressed=true&age=TOTAL&sex=T&time=2024"
POP_FILE="data/raw/eurostat/population_nuts2_2024.tsv.gz"
if [ ! -f "$POP_FILE" ]; then
  echo "Downloading Eurostat population..."
  curl -fL --retry 3 -o "$POP_FILE" "$EUROSTAT_POP_URL"
else
  echo "Eurostat pop already present, skipping."
fi

# === GUS BDL: gmina units list (BDL_ID → TERYT mapping) ===
# The /units endpoint at level=6 returns gmina admin units with their TERYT.
# Required because the /data endpoint returns BDL internal IDs only.
GUS_UNITS_OUT="data/raw/gus/units_gmina.json"
if [ ! -f "$GUS_UNITS_OUT" ]; then
  echo "Downloading GUS BDL gmina units (level=6)..."
  uv run --no-project python scripts/download_bdl_units.py "$GUS_UNITS_OUT"
else
  echo "GUS BDL units already present, skipping."
fi

# === GUS BDL: PL gmina population ===
# Variable 72305 = "ludność ogółem, stan na 31 XII". The variable already
# declares level=6 (gmina) in its own metadata; passing unit-level=6 as a
# query param triggers HTTP 404. Endpoint accepts the bare variable id.
# API is anonymous-friendly for ~hundreds of req/day; we make ~25.
GUS_DIR="data/raw/gus"
GUS_OUT="$GUS_DIR/population_gmina_2024.json"
if [ ! -f "$GUS_OUT" ]; then
  echo "Downloading GUS BDL population (paginated)..."
  # Use a stand-alone Python helper instead of curl+jq — the data endpoint
  # returns ~45 pages of mixed unit-level records (country/voj/powiat/gmina);
  # the bdl_loader.py filters to gmina at load time via len(teryt)==7.
  # `uv run --no-project python` works on both Linux (project canonical) and
  # Windows (bare `python` is intercepted by the MS Store stub).
  uv run --no-project python scripts/download_bdl.py "$GUS_OUT"
  # Clean up any leftover page files from previous bash+curl attempts
  rm -f "$GUS_DIR"/page_*.json
else
  echo "GUS BDL already present, skipping."
fi

echo "=== All downloads complete ==="
ls -lh data/raw/prg/A03_Granice_gmin.shp \
       data/raw/eurostat/*.geojson \
       data/raw/eurostat/*.tsv.gz \
       data/raw/gus/*.json
