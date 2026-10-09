import os
import shutil

os.environ["DATABASE_URL"] = "sqlite:///./test_insightflow.db"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["UPLOAD_DIR"] = "./test_uploads"

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, engine
from app.main import app
from app.models import (  # noqa: F401
    Dataset,
    DatasetColumn,
    Experiment,
    ExperimentMetric,
    Project,
    Report,
    User,
    Visualization,
)


@pytest.fixture(autouse=True)
def reset_database():
    shutil.rmtree("./test_uploads", ignore_errors=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    shutil.rmtree("./test_uploads", ignore_errors=True)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
