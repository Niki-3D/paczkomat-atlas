-- Default search path so PostGIS + h3 + topology types resolve cleanly.
-- This applies globally for the cluster — fine for a single-DB project.
ALTER SYSTEM SET search_path TO public, topology;
SELECT pg_reload_conf();
