-- Paczkomat Atlas — Postgres extension setup
-- This runs ONCE on first container startup (postgres-initdb hook).
-- Order matters: postgis first, then h3 family, then everything else.

\echo 'Creating PostGIS family...'
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

\echo 'Creating H3 spatial indexing...'
CREATE EXTENSION IF NOT EXISTS h3;
CREATE EXTENSION IF NOT EXISTS h3_postgis CASCADE;

\echo 'Creating TimescaleDB...'
CREATE EXTENSION IF NOT EXISTS timescaledb;

\echo 'Creating job scheduling and observability...'
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

\echo 'Verifying extension versions...'
SELECT extname, extversion
FROM pg_extension
WHERE extname IN (
  'postgis', 'postgis_topology', 'h3', 'h3_postgis',
  'timescaledb', 'pg_cron', 'pg_stat_statements'
)
ORDER BY extname;

\echo 'Verifying PostGIS subsystems...'
SELECT PostGIS_Version();

\echo 'Verifying TimescaleDB...'
SELECT default_version, installed_version
FROM pg_available_extensions
WHERE name = 'timescaledb';

\echo 'Extension setup complete.'
