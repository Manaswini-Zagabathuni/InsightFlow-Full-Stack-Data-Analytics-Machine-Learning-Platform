import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.api.ownership import require_owned_project
from app.core.config import settings
from app.db.session import get_db
from app.models import Dataset, Experiment, Project, Report, User
from app.schemas import ReportResponse
from app.services.reporting import build_project_report

router = APIRouter(prefix="/reports", tags=["reports"])


def _owned_report(report_id: str, user: User, db: Session) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    require_owned_project(report.project_id, user, db)
    return report


@router.post("/{project_id}", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def generate_report(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Report:
    require_owned_project(project_id, user, db)
    project = db.scalar(
        select(Project)
        .options(
            selectinload(Project.datasets).selectinload(Dataset.columns),
            selectinload(Project.visualizations),
            selectinload(Project.experiments).selectinload(Experiment.metrics),
        )
        .where(Project.id == project_id)
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    report_id = str(uuid.uuid4())
    slug = re.sub(r"[^a-z0-9]+", "-", project.name.lower()).strip("-")[:60] or "project"
    filename = f"insightflow-{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{report_id[:8]}.pdf"
    root = settings.upload_dir.resolve()
    destination = (root / user.id / project.id / "reports" / filename).resolve()
    if root not in destination.parents:
        raise HTTPException(status_code=400, detail="Unsafe report destination")
    try:
        build_project_report(project, destination)
        destination.chmod(0o600)
        report = Report(id=report_id, project_id=project.id, filename=filename, storage_path=str(destination), size_bytes=destination.stat().st_size)
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
    except Exception as exc:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Report generation failed") from exc


@router.get("/project/{project_id}", response_model=list[ReportResponse])
def list_reports(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Report]:
    require_owned_project(project_id, user, db)
    return list(db.scalars(select(Report).where(Report.project_id == project_id).order_by(Report.created_at.desc())).all())


@router.get("/{report_id}/download", response_class=FileResponse)
def download_report(report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> FileResponse:
    report = _owned_report(report_id, user, db)
    root = settings.upload_dir.resolve()
    path = Path(report.storage_path).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(path, media_type="application/pdf", filename=report.filename, content_disposition_type="attachment")
