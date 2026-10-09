from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_SECRETS = {
    "development-only-change-before-deployment",
    "local-development-secret-change-before-deployment",
}


class Settings(BaseSettings):
    app_name: str = "InsightFlow API"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "sqlite:///./insightflow.db"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    jwt_secret: str = "development-only-change-before-deployment"
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_minutes: int = 60
    upload_dir: Path = Path("uploads")
    max_upload_bytes: int = 25 * 1024 * 1024
    max_csv_columns: int = 500
    celery_task_always_eager: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e2b"
    ollama_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    @model_validator(mode="after")
    def validate_runtime_configuration(self):
        if self.access_token_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_MINUTES must be positive")
        if self.max_upload_bytes <= 0 or self.max_csv_columns <= 0:
            raise ValueError("Upload limits must be positive")
        if self.ollama_timeout_seconds <= 0:
            raise ValueError("OLLAMA_TIMEOUT_SECONDS must be positive")
        if self.environment.lower() in {"production", "staging"} and self.jwt_secret in DEVELOPMENT_JWT_SECRETS:
            raise ValueError("JWT_SECRET must be replaced before running in staging or production")
        if self.environment.lower() in {"production", "staging"} and len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters in staging or production")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
