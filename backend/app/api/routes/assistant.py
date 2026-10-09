from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.ownership import require_owned_dataset
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.schemas import AssistantQuery, AssistantResponse, AssistantStatus
from app.services.assistant_analytics import (
    UnsupportedAssistantQuestion,
    build_assistant_context,
)
from app.services.ollama import (
    OllamaUnavailable,
    generate_local_answer,
    get_ollama_status,
)

router = APIRouter(prefix="/assistant", tags=["local assistant"])


@router.get("/status", response_model=AssistantStatus)
def assistant_status(_: User = Depends(get_current_user)) -> dict:
    return get_ollama_status()


@router.post("/query", response_model=AssistantResponse)
def query_assistant(payload: AssistantQuery, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AssistantResponse:
    dataset = require_owned_dataset(payload.dataset_id, user, db)
    if dataset.status != "ready":
        raise HTTPException(status_code=409, detail="Dataset profiling must complete before using the assistant")
    try:
        intent, context, sections = build_assistant_context(dataset, payload.question, db)
    except UnsupportedAssistantQuestion as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        answer = generate_local_answer(payload.question, context)
    except OllamaUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AssistantResponse(answer=answer, intent=intent, model=settings.ollama_model, context_sections=sections)
