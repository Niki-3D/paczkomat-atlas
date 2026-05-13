"""Locker queries — list with filters, detail by name."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from paczkomat_atlas_api.schemas import LockerDetail, LockerSummary


class LockerRepo:
    """Reads from lockers table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_lockers(
        self,
        country: str | None = None,
        is_locker: bool | None = None,
        status: str | None = None,
        location_247: bool | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> tuple[list[LockerSummary], int]:
        """Filtered list with pagination."""
        where_clauses = ["1=1"]
        params: dict[str, str | int | bool] = {"limit": limit, "offset": offset}

        if country is not None:
            where_clauses.append("country = :country")
            params["country"] = country.upper()
        if is_locker is not None:
            where_clauses.append("is_locker = :is_locker")
            params["is_locker"] = is_locker
        if status is not None:
            where_clauses.append("status = :status")
            params["status"] = status
        if location_247 is not None:
            where_clauses.append("location_247 = :loc_247")
            params["loc_247"] = location_247

        where_sql = " AND ".join(where_clauses)

        # where_sql is hardcoded; user values flow through bound :params.
        count_sql = text(f"SELECT count(*) FROM lockers WHERE {where_sql}")  # noqa: S608
        total = (await self._session.execute(count_sql, params)).scalar_one()

        list_sql = text(f"""
            SELECT name, country, status, is_locker, physical_type, location_247,
                   ST_Y(geom::geometry) AS latitude,
                   ST_X(geom::geometry) AS longitude
            FROM lockers
            WHERE {where_sql}
            ORDER BY name
            LIMIT :limit OFFSET :offset
        """)  # noqa: S608
        result = await self._session.execute(list_sql, params)
        rows = [
            LockerSummary(
                name=r.name, country=r.country, status=r.status,
                is_locker=r.is_locker, physical_type=r.physical_type,
                location_247=r.location_247,
                latitude=float(r.latitude), longitude=float(r.longitude),
            )
            for r in result
        ]
        return rows, total

    async def get_by_name(self, name: str) -> LockerDetail | None:
        sql = text("""
            SELECT name, country, status, is_locker, physical_type, location_247,
                   ST_Y(geom::geometry) AS latitude,
                   ST_X(geom::geometry) AS longitude,
                   gmina_teryt, nuts2_id, updated_at
            FROM lockers WHERE name = :name
        """)
        result = await self._session.execute(sql, {"name": name})
        row = result.first()
        if row is None:
            return None
        return LockerDetail(
            name=row.name, country=row.country, status=row.status,
            is_locker=row.is_locker, physical_type=row.physical_type,
            location_247=row.location_247,
            latitude=float(row.latitude), longitude=float(row.longitude),
            gmina_teryt=row.gmina_teryt, nuts2_id=row.nuts2_id,
            updated_at=row.updated_at,
        )
