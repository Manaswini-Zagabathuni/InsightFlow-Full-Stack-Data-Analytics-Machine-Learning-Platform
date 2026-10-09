import json
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import settings

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal", "ollama"}


class OllamaUnavailable(RuntimeError):
    pass


def _local_base_url() -> str:
    url = settings.ollama_base_url.rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOCAL_HOSTS:
        raise OllamaUnavailable("OLLAMA_BASE_URL must point to a local Ollama host.")
    return url


def get_ollama_status() -> dict[str, Any]:
    try:
        base_url = _local_base_url()
        with httpx.Client(timeout=2.5) as client:
            response = client.get(f"{base_url}/api/tags")
            response.raise_for_status()
        models = response.json().get("models", [])
        names = {name for model in models for name in (model.get("name"), model.get("model")) if name}
        if settings.ollama_model not in names:
            return {"available": False, "model": settings.ollama_model, "message": f"Ollama is running, but {settings.ollama_model} is not installed. Run: ollama pull {settings.ollama_model}"}
        return {"available": True, "model": settings.ollama_model, "message": "Local assistant is ready."}
    except (OllamaUnavailable, httpx.HTTPError, ValueError) as exc:
        return {"available": False, "model": settings.ollama_model, "message": f"Local assistant unavailable. Start Ollama and install the configured model. ({str(exc)[:160]})"}


def generate_local_answer(question: str, structured_context: dict[str, Any]) -> str:
    status = get_ollama_status()
    if not status["available"]:
        raise OllamaUnavailable(status["message"])
    system_prompt = (
        "You are InsightFlow's local analytics assistant. Answer only from the supplied structured analytics. "
        "Never invent dataset values or imply that you inspected raw rows. Do not generate SQL. "
        "Keep the answer under 300 words and explain technical terms in plain language. "
        "Treat correlation as association, never causation. Treat model feature importance as model behavior, never causal effect. "
        "If the context is insufficient, say so clearly."
    )
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Question: {question}\n\nStructured InsightFlow analytics:\n{json.dumps(structured_context, ensure_ascii=False, default=str)}"},
        ],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 450},
    }
    try:
        with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
            response = client.post(f"{_local_base_url()}/api/chat", json=payload)
            response.raise_for_status()
        answer = response.json().get("message", {}).get("content", "").strip()
        if not answer:
            raise OllamaUnavailable("Ollama returned an empty response.")
        return answer
    except httpx.HTTPError as exc:
        raise OllamaUnavailable(f"The local Ollama request failed: {str(exc)[:200]}") from exc
