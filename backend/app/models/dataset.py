import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project import Project


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(700), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", index=True)
    row_count: Mapped[int | None] = mapped_column(Integer)
    column_count: Mapped[int | None] = mapped_column(Integer)
    memory_bytes: Mapped[int | None] = mapped_column(Integer)
    missing_cells: Mapped[int | None] = mapped_column(Integer)
    duplicate_rows: Mapped[int | None] = mapped_column(Integer)
    quality_score: Mapped[float | None] = mapped_column(Float)
    quality_issues: Mapped[list[str] | None] = mapped_column(JSON)
    profile_error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="datasets")
    columns: Mapped[list["DatasetColumn"]] = relationship(back_populates="dataset", cascade="all, delete-orphan", order_by="DatasetColumn.position")


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    data_type: Mapped[str] = mapped_column(String(30), nullable=False)
    pandas_dtype: Mapped[str] = mapped_column(String(80), nullable=False)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    unique_count: Mapped[int] = mapped_column(Integer, nullable=False)
    statistics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    dataset: Mapped[Dataset] = relationship(back_populates="columns")
