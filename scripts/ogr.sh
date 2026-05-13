#!/usr/bin/env bash
# Run ogr2ogr inside the OSGeo GDAL container with the current dir mounted.
# Usage: ./scripts/ogr.sh <ogr2ogr args>
set -euo pipefail
# MSYS_NO_PATHCONV stops Git Bash on Windows from translating /work into C:\...
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd):/work" -w //work \
  --network paczkomat-atlas_default \
  ghcr.io/osgeo/gdal:ubuntu-small-3.10.0 ogr2ogr "$@"
