from typing import Literal

from pydantic import BaseModel, Field, field_validator

AssistantIntent = Literal["dataset_summary", "missing_values", "correlations", "statistics", "visualization", "experiment"]


class AssistantQuery(BaseModel):
    dataset_id: str
    question: str = Field(min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Question cannot be blank")
        return value


class AssistantStatus(BaseModel):
    available: bool
    model: str
    message: str


class AssistantResponse(BaseModel):
    answer: str
    intent: AssistantIntent
    model: str
    context_sections: list[str]
    generated_locally: bool = True
    data_policy: str = "Generated from structured analytics; raw dataset rows were not sent to the model."
