from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    filename: str
    size_bytes: int
    created_at: datetime
