"""Response envelope and pagination — used by every endpoint."""

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    """Pagination metadata."""

    total: int = Field(..., description="Total items matching the query")
    offset: int = Field(0, description="Items skipped before returning the page")
    limit: int = Field(100, description="Maximum items in this page")


class ApiResponse[T](BaseModel):
    """Standard response envelope.

    Always returns: { "data": ..., "meta": { ... } }
    Errors return: { "errors": [...] } via FastAPI exception handlers.
    """

    data: T
    meta: dict[str, str | int | float | None] = Field(default_factory=dict)
