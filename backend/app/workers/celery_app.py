from celery import Celery

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
celery_app = Celery("insightflow", broker=settings.redis_url, backend=settings.redis_url, include=["app.workers.tasks"])
celery_app.conf.update(
    task_track_started=True,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_store_eager_result=False,
    worker_hijack_root_logger=False,
)
