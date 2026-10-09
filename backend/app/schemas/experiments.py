from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TaskType = Literal["classification", "regression", "clustering"]


class PreprocessingConfig(BaseModel):
    numeric_imputer: Literal["mean", "median"] = "median"
    categorical_imputer: Literal["most_frequent"] = "most_frequent"
    scaler: Literal["standard", "minmax", "none"] = "standard"
    categorical_encoder: Literal["onehot"] = "onehot"
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)


class ExperimentCreate(BaseModel):
    project_id: str
    dataset_id: str
    name: str = Field(min_length=1, max_length=160)
    task_type: TaskType
    target_column: str | None = Field(default=None, max_length=255)
    features: list[str] = Field(min_length=1, max_length=100)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    selected_models: list[str] = Field(min_length=1, max_length=10)
    model_parameters: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Experiment name cannot be blank")
        return value

    @field_validator("features", "selected_models")
    @classmethod
    def unique_values(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Selections must not contain duplicates")
        return value

    @model_validator(mode="after")
    def validate_target(self):
        if self.task_type in {"classification", "regression"} and not self.target_column:
            raise ValueError("A target column is required for supervised learning")
        if self.task_type == "clustering" and self.target_column:
            raise ValueError("Clustering does not use a target column")
        if self.target_column and self.target_column in self.features:
            raise ValueError("Target column cannot also be a feature")
        if not set(self.model_parameters).issubset(self.selected_models):
            raise ValueError("Model parameters may only be supplied for selected models")
        return self


class ExperimentMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_name: str
    status: str
    metrics: dict[str, Any]
    hyperparameters: dict[str, Any]
    explainability: dict[str, Any]
    error: str | None
    created_at: datetime

    @field_validator("explainability", mode="before")
    @classmethod
    def normalize_legacy_explanation(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        if value:
            return value
        return {
            "status": "unavailable",
            "method": None,
            "reason": "This experiment predates explainability generation. Run a new experiment to create model attributions.",
            "global_importance": [],
            "individual": None,
            "interpretation": {
                "importance_kind": "model-derived",
                "importance_note": "Model importance describes patterns used by a fitted model.",
                "correlation_note": "Correlation is statistical association and does not establish causation.",
                "causal_note": "No causal claim is available from this experiment.",
            },
        }


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    dataset_id: str
    name: str
    task_type: str
    target_column: str | None
    features: list[str]
    preprocessing: dict[str, Any]
    selected_models: list[str]
    model_parameters: dict[str, Any]
    status: str
    progress: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    metrics: list[ExperimentMetricResponse] = Field(default_factory=list)


class ModelOption(BaseModel):
    id: str
    name: str
    available: bool
    unavailable_reason: str | None = None


class ModelCatalog(BaseModel):
    classification: list[ModelOption]
    regression: list[ModelOption]
    clustering: list[ModelOption]


class ModelExplanationResponse(BaseModel):
    model_name: str
    explainability: dict[str, Any]
