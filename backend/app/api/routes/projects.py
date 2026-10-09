import logging
import shutil

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.ownership import require_owned_project
from app.core.config import settings
from app.db.session import get_db
from app.models import Dataset, Project, User
from app.schemas import DatasetResponse, ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger("insightflow.projects")


def project_response(project: Project, dataset_count: int = 0) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        dataset_count=dataset_count,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProjectResponse:
    project = Project(owner_id=user.id, name=payload.name, description=payload.description.strip())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project_response(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ProjectResponse]:
    rows = db.execute(
        select(Project, func.count(Dataset.id))
        .outerjoin(Dataset, Dataset.project_id == Project.id)
        .where(Project.owner_id == user.id)
        .group_by(Project.id)
        .order_by(Project.updated_at.desc())
    ).all()
    return [project_response(project, count) for project, count in rows]


@router.get("/{project_id}")
def open_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    project = require_owned_project(project_id, user, db)
    datasets = db.scalars(select(Dataset).where(Dataset.project_id == project.id).order_by(Dataset.created_at.desc())).all()
    return {"project": project_response(project, len(datasets)), "datasets": [DatasetResponse.model_validate(dataset) for dataset in datasets]}


@router.patch("/{project_id}", response_model=ProjectResponse)
def rename_project(project_id: str, payload: ProjectUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProjectResponse:
    project = require_owned_project(project_id, user, db)
    project.name = payload.name
    db.commit()
    db.refresh(project)
    count = db.scalar(select(func.count(Dataset.id)).where(Dataset.project_id == project.id)) or 0
    return project_response(project, count)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    project = require_owned_project(project_id, user, db)
    project_storage = settings.upload_dir.resolve() / user.id / project.id
    db.delete(project)
    db.commit()
    if settings.upload_dir.resolve() in project_storage.parents:
        try:
            shutil.rmtree(project_storage)
        except FileNotFoundError:
            pass
        except OSError:
            logger.exception("project_storage_cleanup_failed", extra={"project_id": project.id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
