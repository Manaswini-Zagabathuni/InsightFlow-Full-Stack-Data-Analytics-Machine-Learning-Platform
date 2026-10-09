from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Dataset, Project, User


def require_owned_project(project_id: str, user: User, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def require_owned_dataset(dataset_id: str, user: User, db: Session) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    require_owned_project(dataset.project_id, user, db)
    return dataset
