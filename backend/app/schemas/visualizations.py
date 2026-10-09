from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ChartType = Literal["bar", "line", "scatter", "histogram", "box", "pie", "heatmap"]


class VisualizationCreate(BaseModel):
    project_id: str
    dataset_id: str
    name: str = Field(min_length=1, max_length=160)
    chart_type: ChartType
    x_axis: str | None = Field(default=None, max_length=255)
    y_axis: str | None = Field(default=None, max_length=255)
    group_column: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Visualization name cannot be blank")
        return normalized


class VisualizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    dataset_id: str
    name: str
    chart_type: str
    x_axis: str | None
    y_axis: str | None
    group_column: str | None
    created_at: datetime


class VisualizationResult(BaseModel):
    visualization: VisualizationResponse
    data: Any
    meta: dict[str, Any]
