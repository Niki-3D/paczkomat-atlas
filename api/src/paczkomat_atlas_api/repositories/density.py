"""Density queries from mv_density_gmina and mv_density_nuts2."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.schemas import (
    DensityGmina,
    DensityNuts2,
    GminaTopList,
    Nuts2TopList,
)


class DensityRepo:
    """Reads from mv_density_gmina and mv_density_nuts2."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_gminy(
        self,
        voivodeship: str | None = None,
        min_population: int = 0,
        limit: int = 500,
        offset: int = 0,
    ) -> tuple[list[DensityGmina], int]:
        """List gminy with density. Returns (rows, total_count)."""
        where_clauses = ["population >= :min_pop"]
        params: dict[str, str | int] = {"min_pop": min_population, "limit": limit, "offset": offset}

        if voivodeship is not None:
            where_clauses.append("voivodeship = :voivodeship")
            params["voivodeship"] = voivodeship

        where_sql = " AND ".join(where_clauses)

        # where_sql is composed from a closed set of hardcoded predicates;
        # all user values flow through bound :params. Safe from injection.
        count_sql = text(f"SELECT count(*) FROM mv_density_gmina WHERE {where_sql}")
        total = (await self._session.execute(count_sql, params)).scalar_one()

        list_sql = text(f"""
            SELECT teryt, name, voivodeship, population, n_lockers, n_pudo, lockers_per_10k
            FROM mv_density_gmina
            WHERE {where_sql}
            ORDER BY lockers_per_10k DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """)
        result = await self._session.execute(list_sql, params)
        rows = [
            DensityGmina(
                teryt=r.teryt, name=r.name, voivodeship=r.voivodeship,
                population=r.population or 0,
                n_lockers=r.n_lockers, n_pudo=r.n_pudo,
                lockers_per_10k=float(r.lockers_per_10k) if r.lockers_per_10k is not None else None,
            )
            for r in result
        ]
        return rows, total

    async def top_gminy(
        self,
        limit: int = 10,
        min_population: int = 5000,
        min_lockers: int = 5,
    ) -> list[GminaTopList]:
        """Top N gminy by density. Filtered to avoid tiny outliers."""
        sql = text("""
            SELECT teryt, name, voivodeship, lockers_per_10k, n_lockers, population
            FROM mv_density_gmina
            WHERE population >= :min_pop
              AND n_lockers >= :min_lockers
              AND lockers_per_10k IS NOT NULL
            ORDER BY lockers_per_10k DESC
            LIMIT :limit
        """)
        result = await self._session.execute(
            sql, {"min_pop": min_population, "min_lockers": min_lockers, "limit": limit}
        )
        return [
            GminaTopList(
                teryt=r.teryt, name=r.name, voivodeship=r.voivodeship,
                lockers_per_10k=float(r.lockers_per_10k),
                n_lockers=r.n_lockers, population=r.population or 0,
            )
            for r in result
        ]

    async def list_nuts2(
        self,
        country: str | None = None,
        min_population: int = 0,
        limit: int = 500,
        offset: int = 0,
    ) -> tuple[list[DensityNuts2], int]:
        """List NUTS-2 regions with density. Returns (rows, total_count)."""
        where_clauses = ["population >= :min_pop"]
        params: dict[str, str | int] = {"min_pop": min_population, "limit": limit, "offset": offset}

        if country is not None:
            where_clauses.append("country = :country")
            params["country"] = country.upper()

        where_sql = " AND ".join(where_clauses)

        # Same safety as list_gminy: where_sql is hardcoded, params are bound.
        count_sql = text(f"SELECT count(*) FROM mv_density_nuts2 WHERE {where_sql}")
        total = (await self._session.execute(count_sql, params)).scalar_one()

        list_sql = text(f"""
            SELECT code, name_latn, country, population, n_lockers, n_pudo, lockers_per_10k
            FROM mv_density_nuts2
            WHERE {where_sql}
            ORDER BY lockers_per_10k DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """)
        result = await self._session.execute(list_sql, params)
        rows = [
            DensityNuts2(
                code=r.code, name_latn=r.name_latn, country=r.country,
                population=r.population or 0,
                n_lockers=r.n_lockers, n_pudo=r.n_pudo,
                lockers_per_10k=float(r.lockers_per_10k) if r.lockers_per_10k is not None else None,
            )
            for r in result
        ]
        return rows, total

    async def top_nuts2(self, limit: int = 15, min_population: int = 100_000) -> list[Nuts2TopList]:
        """Top N NUTS-2 regions by density."""
        sql = text("""
            SELECT code, name_latn, country, lockers_per_10k, n_lockers, population
            FROM mv_density_nuts2
            WHERE population >= :min_pop AND lockers_per_10k IS NOT NULL
            ORDER BY lockers_per_10k DESC
            LIMIT :limit
        """)
        result = await self._session.execute(sql, {"min_pop": min_population, "limit": limit})
        return [
            Nuts2TopList(
                code=r.code, name_latn=r.name_latn, country=r.country,
                lockers_per_10k=float(r.lockers_per_10k),
                n_lockers=r.n_lockers, population=r.population or 0,
            )
            for r in result
        ]
