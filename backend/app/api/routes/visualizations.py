from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.ownership import require_owned_dataset, require_owned_project
from app.db.session import get_db
from app.models import User, Visualization
from app.schemas import VisualizationCreate, VisualizationResponse, VisualizationResult
from app.services.visualization import generate_visualization_data

router = APIRouter(prefix="/visualizations", tags=["visualizations"])


def require_owned_visualization(visualization_id: str, user: User, db: Session) -> Visualization:
    visualization = db.get(Visualization, visualization_id)
    if visualization is None:
        raise HTTPException(status_code=404, detail="Visualization not found")
    require_owned_project(visualization.project_id, user, db)
    return visualization


def render(visualization: Visualization) -> VisualizationResult:
    try:
        data, meta = generate_visualization_data(
            visualization.dataset,
            visualization.chart_type,
            visualization.x_axis,
            visualization.y_axis,
            visualization.group_column,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return VisualizationResult(visualization=visualization, data=data, meta=meta)


@router.post("", response_model=VisualizationResult, status_code=status.HTTP_201_CREATED)
def create_visualization(payload: VisualizationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> VisualizationResult:
    require_owned_project(payload.project_id, user, db)
    dataset = require_owned_dataset(payload.dataset_id, user, db)
    if dataset.project_id != payload.project_id:
        raise HTTPException(status_code=422, detail="Dataset does not belong to the selected project")
    if dataset.status != "ready":
        raise HTTPException(status_code=409, detail="Dataset profiling must complete before visualization")
    try:
        data, meta = generate_visualization_data(dataset, payload.chart_type, payload.x_axis, payload.y_axis, payload.group_column)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    visualization = Visualization(**payload.model_dump())
    db.add(visualization)
    db.commit()
    db.refresh(visualization)
    return VisualizationResult(visualization=visualization, data=data, meta=meta)


@router.get("/project/{project_id}", response_model=list[VisualizationResponse])
def list_visualizations(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Visualization]:
    require_owned_project(project_id, user, db)
    return list(db.scalars(select(Visualization).where(Visualization.project_id == project_id).order_by(Visualization.created_at.desc())).all())


@router.get("/{visualization_id}", response_model=VisualizationResult)
def get_visualization(visualization_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> VisualizationResult:
    return render(require_owned_visualization(visualization_id, user, db))


@router.delete("/{visualization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visualization(visualization_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    visualization = require_owned_visualization(visualization_id, user, db)
    db.delete(visualization)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
