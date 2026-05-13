"""H3 hex aggregations from mv_h3_density_r8."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.schemas import H3Cell


class H3Repo:
    """Reads from mv_h3_density_r8."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_cells(
        self,
        country: str | None = None,
        min_count: int = 1,
        limit: int = 5000,
    ) -> list[H3Cell]:
        """Hex cells with counts. Used for the heatmap data endpoint.

        For map rendering, prefer the vector-tile endpoint (Phase 6) — this JSON
        endpoint is for tabular inspection and small queries.
        """
        where_clauses = ["n_total >= :min_count"]
        params: dict[str, str | int] = {"min_count": min_count, "limit": limit}

        if country is not None:
            where_clauses.append("country = :country")
            params["country"] = country.upper()

        where_sql = " AND ".join(where_clauses)
        # where_sql is hardcoded; user values flow through bound :params.
        sql = text(f"""
            SELECT h3::text AS h3, country, n_lockers, n_pudo, n_total
            FROM mv_h3_density_r8
            WHERE {where_sql}
            ORDER BY n_total DESC
            LIMIT :limit
        """)  # noqa: S608
        result = await self._session.execute(sql, params)
        return [
            H3Cell(
                h3=r.h3, country=r.country,
                n_lockers=r.n_lockers, n_pudo=r.n_pudo, n_total=r.n_total,
            )
            for r in result
        ]
