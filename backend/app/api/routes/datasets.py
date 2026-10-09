import csv
import io
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.ownership import require_owned_dataset, require_owned_project
from app.core.config import settings
from app.db.session import get_db
from app.models import Dataset, User
from app.schemas import ColumnResponse, DatasetResponse, DatasetRowsResponse
from app.workers.tasks import profile_dataset

router = APIRouter(tags=["datasets"])
logger = logging.getLogger("insightflow.datasets")
ALLOWED_CONTENT_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"}


def validate_csv(filename: str, content_type: str | None, data: bytes) -> list[str]:
    if Path(filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=415, detail="Only .csv files are supported")
    if content_type and content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported CSV content type")
    if not data:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="CSV exceeds the configured upload limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="CSV must use UTF-8 encoding")
    try:
        rows = csv.reader(io.StringIO(text))
        header = next(rows)
    except StopIteration:
        raise HTTPException(status_code=422, detail="CSV must contain a header row")
    except csv.Error:
        raise HTTPException(status_code=422, detail="CSV is malformed")
    header = [column.strip() for column in header]
    if not header or any(not column for column in header):
        raise HTTPException(status_code=422, detail="Every CSV column must have a name")
    if len(set(header)) != len(header):
        raise HTTPException(status_code=422, detail="CSV column names must be unique")
    if len(header) > settings.max_csv_columns:
        raise HTTPException(status_code=422, detail=f"CSV exceeds the {settings.max_csv_columns}-column limit")
    data_rows = 0
    try:
        for row_number, row in enumerate(rows, start=2):
            if not any(cell.strip() for cell in row):
                continue
            data_rows += 1
            if len(row) != len(header):
                raise HTTPException(status_code=422, detail=f"CSV row {row_number} does not match the header column count")
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail="CSV is malformed") from exc
    if data_rows == 0:
        raise HTTPException(status_code=422, detail="CSV must contain at least one data row")
    return header


@router.post("/projects/{project_id}/datasets", status_code=status.HTTP_202_ACCEPTED)
async def upload_dataset(project_id: str, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    project = require_owned_project(project_id, user, db)
    original_filename = Path((file.filename or "dataset.csv").replace("\\", "/")).name[:255]
    content = await file.read(settings.max_upload_bytes + 1)
    validate_csv(original_filename, file.content_type, content)

    dataset = Dataset(
        project_id=project.id,
        name=Path(original_filename).stem[:255],
        original_filename=original_filename,
        storage_path="pending",
        size_bytes=len(content),
        status="queued",
    )
    db.add(dataset)
    db.flush()
    root = settings.upload_dir.resolve()
    destination = (root / user.id / project.id / f"{dataset.id}.csv").resolve()
    if root not in destination.parents:
        raise HTTPException(status_code=400, detail="Unsafe storage destination")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        destination.chmod(0o600)
        dataset.storage_path = str(destination)
        db.commit()
        db.refresh(dataset)
    except Exception as exc:
        db.rollback()
        destination.unlink(missing_ok=True)
        logger.exception("dataset_storage_failed", extra={"dataset_id": dataset.id})
        raise HTTPException(status_code=500, detail="Dataset storage failed") from exc
    try:
        profile_dataset.delay(dataset.id)
    except Exception as exc:
        dataset.status = "failed"
        dataset.profile_error = "Background profiling service is unavailable"
        db.commit()
        raise HTTPException(status_code=503, detail="Background profiling service is unavailable") from exc
    db.refresh(dataset)
    return {"dataset": DatasetResponse.model_validate(dataset), "message": "Dataset accepted for background profiling"}


@router.get("/projects/{project_id}/datasets", response_model=list[DatasetResponse])
def list_datasets(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Dataset]:
    require_owned_project(project_id, user, db)
    return list(db.scalars(select(Dataset).where(Dataset.project_id == project_id).order_by(Dataset.created_at.desc())).all())


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dataset:
    return require_owned_dataset(dataset_id, user, db)


@router.get("/datasets/{dataset_id}/profile", response_model=DatasetResponse)
def get_profile(dataset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dataset:
    return require_owned_dataset(dataset_id, user, db)


def native_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


@router.get("/datasets/{dataset_id}/rows", response_model=DatasetRowsResponse)
def explore_dataset(
    dataset_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    sort_by: str | None = None,
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetRowsResponse:
    dataset = require_owned_dataset(dataset_id, user, db)
    if dataset.status != "ready":
        raise HTTPException(status_code=409, detail="Dataset profiling is not complete")
    frame = pd.read_csv(dataset.storage_path, low_memory=False)
    if search:
        mask = frame.astype(str).apply(lambda column: column.str.contains(search, case=False, regex=False, na=False)).any(axis=1)
        frame = frame.loc[mask]
    if sort_by:
        if sort_by not in frame.columns:
            raise HTTPException(status_code=422, detail="Unknown sort column")
        frame = frame.sort_values(sort_by, ascending=sort_order == "asc", na_position="last", kind="mergesort")
    total = len(frame)
    start = (page - 1) * page_size
    page_frame = frame.iloc[start:start + page_size]
    rows: list[dict[str, Any]] = []
    for _, row in page_frame.iterrows():
        values = {str(column): native_value(value) for column, value in row.items()}
        values["_missing"] = [str(column) for column, value in row.items() if pd.isna(value)]
        rows.append(values)
    return DatasetRowsResponse(
        rows=rows,
        columns=[ColumnResponse.model_validate(column) for column in dataset.columns],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )
