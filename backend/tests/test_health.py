import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_health_endpoint_reports_database_connection(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "insightflow-api",
        "version": "0.1.0",
        "database": "connected",
    }


def test_openapi_document_is_available(client):
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "InsightFlow API"


def test_cors_preflight_allows_mutating_project_methods(client):
    response = client.options(
        "/api/projects/example",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "PATCH"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_production_rejects_development_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET must be replaced"):
        Settings(environment="production", jwt_secret="development-only-change-before-deployment")

    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(environment="production", jwt_secret="too-short")

    with pytest.raises(ValidationError, match="JWT_SECRET must be replaced"):
        Settings(environment="production", jwt_secret="generate-a-long-random-secret-for-shared-environments")
