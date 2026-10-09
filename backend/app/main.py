import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


@app.middleware("http")
async def protect_cookie_sessions_from_csrf(request: Request, call_next):
    unsafe_method = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    public_auth_path = request.url.path in {"/api/auth/login", "/api/auth/register"}
    uses_bearer = request.headers.get("authorization", "").lower().startswith("bearer ")
    session_cookie = request.cookies.get(settings.auth_cookie_name)
    if unsafe_method and not public_auth_path and session_cookie and not uses_bearer:
        csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
        csrf_header = request.headers.get("x-csrf-token")
        if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
            return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
    return await call_next(request)

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
