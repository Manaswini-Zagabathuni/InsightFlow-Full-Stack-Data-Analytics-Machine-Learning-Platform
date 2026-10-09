import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.experiment import Experiment
    from app.models.report import Report
    from app.models.user import User
    from app.models.visualization import Visualization


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    owner: Mapped["User"] = relationship(back_populates="projects")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    visualizations: Mapped[list["Visualization"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="project", cascade="all, delete-orphan")
