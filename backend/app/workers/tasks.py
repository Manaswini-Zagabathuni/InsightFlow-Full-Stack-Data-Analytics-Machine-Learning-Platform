import logging
from datetime import datetime, timezone

from sqlalchemy import delete

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Dataset, DatasetColumn, Experiment, ExperimentMetric
from app.services.machine_learning import train_models
from app.services.profiling import profile_csv
from app.workers.celery_app import celery_app

logger = logging.getLogger("insightflow.worker")


@celery_app.task(
    name="insightflow.profile_dataset",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=settings.profile_job_time_limit_seconds - 5,
    time_limit=settings.profile_job_time_limit_seconds,
)
def profile_dataset(dataset_id: str) -> None:
    db = SessionLocal()
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        db.close()
        return
    try:
        dataset.status = "profiling"
        dataset.profile_error = None
        db.commit()
        summary, columns = profile_csv(dataset.storage_path)
        db.execute(delete(DatasetColumn).where(DatasetColumn.dataset_id == dataset.id))
        for key, value in summary.items():
            setattr(dataset, key, value)
        db.add_all(DatasetColumn(dataset_id=dataset.id, **column) for column in columns)
        dataset.status = "ready"
        db.commit()
        logger.info("dataset_profile_completed", extra={"dataset_id": dataset.id})
    except Exception as exc:
        logger.exception("dataset_profile_failed", extra={"dataset_id": dataset.id})
        dataset.status = "failed"
        dataset.profile_error = str(exc)[:1000]
        db.commit()
        raise
    finally:
        db.close()


@celery_app.task(
    name="insightflow.train_experiment",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=settings.training_job_time_limit_seconds - 10,
    time_limit=settings.training_job_time_limit_seconds,
)
def train_experiment(experiment_id: str) -> None:
    db = SessionLocal()
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        db.close()
        return
    try:
        experiment.status = "training"
        experiment.progress = 10
        experiment.started_at = datetime.now(timezone.utc)
        experiment.error = None
        db.commit()
        def report_progress(completed: int, total: int) -> None:
            experiment.progress = 10 + int((completed / total) * 80)
            db.commit()

        results = train_models(experiment, experiment.dataset, report_progress)
        db.execute(delete(ExperimentMetric).where(ExperimentMetric.experiment_id == experiment.id))
        for result in results:
            db.add(ExperimentMetric(experiment_id=experiment.id, status="completed", **result))
        experiment.status = "completed"
        experiment.progress = 100
        experiment.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("experiment_training_completed", extra={"experiment_id": experiment.id})
    except Exception as exc:
        logger.exception("experiment_training_failed", extra={"experiment_id": experiment.id})
        experiment.status = "failed"
        experiment.error = str(exc)[:1000]
        experiment.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise
    finally:
        db.close()
