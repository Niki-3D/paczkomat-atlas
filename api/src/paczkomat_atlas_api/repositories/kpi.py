"""Network and country KPIs from mv_country_kpi."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.schemas import CountryKpi, NetworkSummary


class KpiRepo:
    """Reads from mv_country_kpi and lockers for headline metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_countries(self) -> list[CountryKpi]:
        """All countries with at least one record."""
        sql = text("""
            SELECT country, n_lockers, n_pudo, n_total, n_247, pct_247
            FROM mv_country_kpi
            ORDER BY n_total DESC
        """)
        result = await self._session.execute(sql)
        return [
            CountryKpi(
                country=row.country,
                n_lockers=row.n_lockers,
                n_pudo=row.n_pudo,
                n_total=row.n_total,
                n_247=row.n_247,
                pct_247=float(row.pct_247) if row.pct_247 is not None else None,
            )
            for row in result
        ]

    async def get_country(self, country: str) -> CountryKpi | None:
        sql = text("""
            SELECT country, n_lockers, n_pudo, n_total, n_247, pct_247
            FROM mv_country_kpi WHERE country = :country
        """)
        result = await self._session.execute(sql, {"country": country.upper()})
        row = result.first()
        if row is None:
            return None
        return CountryKpi(
            country=row.country,
            n_lockers=row.n_lockers,
            n_pudo=row.n_pudo,
            n_total=row.n_total,
            n_247=row.n_247,
            pct_247=float(row.pct_247) if row.pct_247 is not None else None,
        )

    async def network_summary(self) -> NetworkSummary:
        """Headline numbers for landing page hero strip."""
        sql = text("""
            SELECT
                SUM(n_lockers)::bigint AS n_lockers_total,
                SUM(n_pudo)::bigint AS n_pudo_total,
                SUM(n_total)::bigint AS n_network_total,
                count(*) AS n_countries_active,
                MAX(n_lockers) FILTER (WHERE country = 'PL') AS pl_lockers,
                MAX(pct_247) FILTER (WHERE country = 'PL') AS pl_pct_247
            FROM mv_country_kpi
            WHERE n_total > 0
        """)
        result = await self._session.execute(sql)
        row = result.first()
        if row is None:
            return NetworkSummary(
                n_lockers_total=0, n_pudo_total=0, n_network_total=0,
                n_countries_active=0, pl_lockers=0, pl_pct_247=None,
            )
        return NetworkSummary(
            n_lockers_total=row.n_lockers_total or 0,
            n_pudo_total=row.n_pudo_total or 0,
            n_network_total=row.n_network_total or 0,
            n_countries_active=row.n_countries_active or 0,
            pl_lockers=row.pl_lockers or 0,
            pl_pct_247=float(row.pl_pct_247) if row.pl_pct_247 is not None else None,
        )
