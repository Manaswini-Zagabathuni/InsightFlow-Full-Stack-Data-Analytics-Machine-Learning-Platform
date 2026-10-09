import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.project import Project


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_column: Mapped[str | None] = mapped_column(String(255))
    features: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    preprocessing: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    selected_models: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    model_parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="experiments")
    dataset: Mapped["Dataset"] = relationship()
    metrics: Mapped[list["ExperimentMetric"]] = relationship(back_populates="experiment", cascade="all, delete-orphan", order_by="ExperimentMetric.created_at")


class ExperimentMetric(Base):
    __tablename__ = "experiment_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    hyperparameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    explainability: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    experiment: Mapped[Experiment] = relationship(back_populates="metrics")
