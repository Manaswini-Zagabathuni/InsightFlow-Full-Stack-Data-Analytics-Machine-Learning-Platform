import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    assistant,
    auth,
    datasets,
    experiments,
    projects,
    reports,
    users,
    visualizations,
)
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import check_database_connection

configure_logging()
logger = logging.getLogger("insightflow")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("application_starting", extra={"environment": settings.environment})
    yield
    logger.info("application_stopping")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(visualizations.router, prefix="/api")
app.include_router(experiments.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    check_database_connection()
    return {
        "status": "healthy",
        "service": "insightflow-api",
        "version": settings.app_version,
        "database": "connected",
    }
