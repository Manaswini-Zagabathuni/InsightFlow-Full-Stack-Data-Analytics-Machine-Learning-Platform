import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.project import Project


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Visualization(Base):
    __tablename__ = "visualizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    chart_type: Mapped[str] = mapped_column(String(30), nullable=False)
    x_axis: Mapped[str | None] = mapped_column(String(255))
    y_axis: Mapped[str | None] = mapped_column(String(255))
    group_column: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="visualizations")
    dataset: Mapped["Dataset"] = relationship()
