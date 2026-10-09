from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ColumnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    position: int
    data_type: str
    pandas_dtype: str
    missing_count: int
    missing_percentage: float
    unique_count: int
    statistics: dict[str, Any]


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    original_filename: str
    size_bytes: int
    status: str
    row_count: int | None
    column_count: int | None
    memory_bytes: int | None
    missing_cells: int | None
    duplicate_rows: int | None
    quality_score: float | None
    quality_issues: list[str] | None
    profile_error: str | None
    created_at: datetime
    columns: list[ColumnResponse] = Field(default_factory=list)


class DatasetRowsResponse(BaseModel):
    rows: list[dict[str, Any]]
    columns: list[ColumnResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
