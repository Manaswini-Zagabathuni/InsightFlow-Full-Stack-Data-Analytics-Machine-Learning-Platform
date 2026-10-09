from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.api.ownership import require_owned_dataset, require_owned_project
from app.core.config import settings
from app.db.session import get_db
from app.models import Experiment, ExperimentMetric, Project, User
from app.schemas import (
    ExperimentCreate,
    ExperimentMetricResponse,
    ExperimentResponse,
    ModelCatalog,
    ModelExplanationResponse,
)
from app.services.machine_learning import (
    build_estimator,
    model_catalog,
    validate_experiment_configuration,
)
from app.workers.tasks import train_experiment

router = APIRouter(prefix="/experiments", tags=["experiments"])


def require_owned_experiment(experiment_id: str, user: User, db: Session) -> Experiment:
    experiment = db.scalar(select(Experiment).options(selectinload(Experiment.metrics)).where(Experiment.id == experiment_id))
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    require_owned_project(experiment.project_id, user, db)
    return experiment


@router.get("/catalog", response_model=ModelCatalog)
def get_model_catalog(_: User = Depends(get_current_user)) -> dict:
    return model_catalog()


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_202_ACCEPTED)
def create_experiment(payload: ExperimentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Experiment:
    require_owned_project(payload.project_id, user, db)
    active_experiments = db.scalar(
        select(func.count(Experiment.id))
        .join(Project, Project.id == Experiment.project_id)
        .where(Project.owner_id == user.id, Experiment.status.in_(("queued", "training")))
    ) or 0
    if active_experiments >= settings.max_active_experiments_per_user:
        raise HTTPException(status_code=429, detail="Too many experiments are already active")
    dataset = require_owned_dataset(payload.dataset_id, user, db)
    if dataset.project_id != payload.project_id:
        raise HTTPException(status_code=422, detail="Dataset does not belong to the selected project")
    if dataset.status != "ready":
        raise HTTPException(status_code=409, detail="Dataset profiling must complete before training")
    try:
        validate_experiment_configuration(dataset, payload.task_type, payload.target_column, payload.features, payload.selected_models)
        for model_id in payload.selected_models:
            build_estimator(payload.task_type, model_id, payload.model_parameters.get(model_id, {}))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    experiment = Experiment(**payload.model_dump(mode="json"), status="queued", progress=0)
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    try:
        train_experiment.delay(experiment.id)
    except Exception as exc:
        experiment.status = "failed"
        experiment.error = "Background training service is unavailable"
        db.commit()
        raise HTTPException(status_code=503, detail="Background training service is unavailable") from exc
    db.expire_all()
    return require_owned_experiment(experiment.id, user, db)


@router.get("/project/{project_id}", response_model=list[ExperimentResponse])
def list_experiments(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Experiment]:
    require_owned_project(project_id, user, db)
    return list(db.scalars(select(Experiment).options(selectinload(Experiment.metrics)).where(Experiment.project_id == project_id).order_by(Experiment.created_at.desc())).all())


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Experiment:
    return require_owned_experiment(experiment_id, user, db)


@router.get("/{experiment_id}/metrics", response_model=list[ExperimentMetricResponse])
def get_experiment_metrics(experiment_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ExperimentMetric]:
    return require_owned_experiment(experiment_id, user, db).metrics


@router.get("/{experiment_id}/explainability", response_model=list[ModelExplanationResponse])
def get_experiment_explainability(experiment_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    experiment = require_owned_experiment(experiment_id, user, db)
    return [{"model_name": metric.model_name, "explainability": ExperimentMetricResponse.model_validate(metric).explainability} for metric in experiment.metrics]
