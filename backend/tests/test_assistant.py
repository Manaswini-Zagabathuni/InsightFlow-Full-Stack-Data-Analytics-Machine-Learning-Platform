import io

import pytest

from app.services.ollama import (
    OllamaUnavailable,
    generate_local_answer,
    get_ollama_status,
)

CSV = b"region,age,income,satisfaction,churn\nNorth,22,42000,6.8,no\nSouth,31,58000,7.4,yes\nEast,45,76000,8.2,no\nNorth,,51000,7.1,yes\nSouth,37,68000,8.0,no\nEast,52,91000,8.8,no\nNorth,28,49000,6.9,yes\nSouth,41,73000,8.1,no\nEast,35,65000,7.7,no\nNorth,48,82000,8.5,no\nSouth,26,47000,6.5,yes\nEast,39,70000,7.9,no\n"


def setup_dataset(client, email="assistant@example.com"):
    registered = client.post("/api/auth/register", json={"email": email, "full_name": "Assistant Owner", "password": "SecurePass123"}).json()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    project = client.post("/api/projects", json={"name": "Assistant project"}, headers=headers).json()
    uploaded = client.post(
        f"/api/projects/{project['id']}/datasets",
        files={"file": ("customers.csv", io.BytesIO(CSV), "text/csv")},
        headers=headers,
    ).json()["dataset"]
    return headers, project, uploaded


@pytest.mark.parametrize(
    ("question", "intent", "expected_section"),
    [
        ("Give me a dataset summary", "dataset_summary", "dataset profile"),
        ("Which columns have missing values?", "missing_values", "missing-value profile"),
        ("What is the correlation between age and income?", "correlations", "Pearson correlations"),
        ("What is the mean income?", "statistics", "column statistics"),
        ("Interpret my saved visualization", "visualization", "aggregated chart digest"),
        ("Summarize my latest ML experiment", "experiment", "persisted metrics"),
    ],
)
def test_supported_questions_use_only_structured_analytics(client, monkeypatch, question, intent, expected_section):
    headers, _, dataset = setup_dataset(client, email=f"{intent}@example.com")
    captured = {}

    def answer(_question, context):
        captured.update(context)
        return "A locally generated explanation."

    monkeypatch.setattr("app.api.routes.assistant.generate_local_answer", answer)
    response = client.post("/api/assistant/query", json={"dataset_id": dataset["id"], "question": question}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["intent"] == intent
    assert expected_section in body["context_sections"]
    assert body["generated_locally"] is True
    assert "raw dataset rows were not sent" in body["data_policy"]
    assert captured["guardrails"] == {
        "raw_rows_included": False,
        "sql_generation_allowed": False,
        "correlation_is_causation": False,
        "instruction": "Use only this structured context. If it is insufficient, say what is missing.",
    }
    assert "storage_path" not in str(captured)


def test_correlation_context_contains_aggregates_not_dataset_rows(client, monkeypatch):
    headers, _, dataset = setup_dataset(client)
    captured = {}
    monkeypatch.setattr("app.api.routes.assistant.generate_local_answer", lambda _question, context: captured.update(context) or "Income and age move together in this sample.")
    response = client.post("/api/assistant/query", json={"dataset_id": dataset["id"], "question": "How are age and income correlated?"}, headers=headers)
    assert response.status_code == 200
    analysis = captured["analysis"]
    assert analysis["method"] == "Pearson"
    assert analysis["numeric_columns_considered"] == ["age", "income"]
    assert len(analysis["strongest_pairs"]) == 1
    assert "not causation" in analysis["interpretation_note"]
    assert "rows" not in analysis


def test_sql_and_unsupported_general_chat_are_rejected_before_model_call(client, monkeypatch):
    headers, _, dataset = setup_dataset(client)
    called = False

    def answer(*_args):
        nonlocal called
        called = True
        return "should not run"

    monkeypatch.setattr("app.api.routes.assistant.generate_local_answer", answer)
    sql = client.post("/api/assistant/query", json={"dataset_id": dataset["id"], "question": "Write SQL to select * from users"}, headers=headers)
    general = client.post("/api/assistant/query", json={"dataset_id": dataset["id"], "question": "Tell me a joke"}, headers=headers)
    assert sql.status_code == 422 and "SQL generation is not supported" in sql.json()["detail"]
    assert general.status_code == 422 and "currently help with" in general.json()["detail"]
    assert called is False


def test_ollama_unavailable_is_clear_and_does_not_affect_other_endpoints(client, monkeypatch):
    headers, _, dataset = setup_dataset(client)
    monkeypatch.setattr("app.api.routes.assistant.get_ollama_status", lambda: {"available": False, "model": "gemma4:e2b", "message": "Local assistant unavailable. Start Ollama."})
    status = client.get("/api/assistant/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["available"] is False
    assert "unavailable" in status.json()["message"]

    monkeypatch.setattr("app.api.routes.assistant.generate_local_answer", lambda *_args: (_ for _ in ()).throw(OllamaUnavailable("Local assistant unavailable. Start Ollama.")))
    query = client.post("/api/assistant/query", json={"dataset_id": dataset["id"], "question": "Summarize the dataset"}, headers=headers)
    assert query.status_code == 503
    assert "Local assistant unavailable" in query.json()["detail"]
    assert client.get("/api/health").status_code == 200


def test_assistant_enforces_dataset_ownership(client, monkeypatch):
    headers, _, dataset = setup_dataset(client)
    other = client.post("/api/auth/register", json={"email": "assistant-other@example.com", "full_name": "Other", "password": "SecurePass123"}).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    monkeypatch.setattr("app.api.routes.assistant.generate_local_answer", lambda *_args: "No")
    response = client.post("/api/assistant/query", json={"dataset_id": dataset["id"], "question": "Summarize the dataset"}, headers=other_headers)
    assert response.status_code == 404


def test_ollama_configuration_rejects_external_hosts(monkeypatch):
    monkeypatch.setattr("app.services.ollama.settings.ollama_base_url", "https://paid-llm.example.com")
    status = get_ollama_status()
    assert status["available"] is False
    assert "local Ollama host" in status["message"]


def test_visualization_and_experiment_contexts_use_saved_aggregates(client, monkeypatch):
    headers, project, dataset = setup_dataset(client)
    visualization = client.post(
        "/api/visualizations",
        json={"project_id": project["id"], "dataset_id": dataset["id"], "name": "Income by region", "chart_type": "bar", "x_axis": "region", "y_axis": "income"},
        headers=headers,
    )
    assert visualization.status_code == 201
    experiment = client.post(
        "/api/experiments",
        json={
            "project_id": project["id"], "dataset_id": dataset["id"], "name": "Churn model", "task_type": "classification",
            "target_column": "churn", "features": ["region", "age", "income", "satisfaction"], "selected_models": ["logistic_regression"],
            "preprocessing": {"numeric_imputer": "median", "categorical_imputer": "most_frequent", "scaler": "standard", "categorical_encoder": "onehot", "test_size": 0.25},
            "model_parameters": {},
        },
        headers=headers,
    )
    assert experiment.status_code == 202 and experiment.json()["status"] == "completed"
    contexts = []
    monkeypatch.setattr("app.api.routes.assistant.generate_local_answer", lambda _question, context: contexts.append(context) or "Local explanation")
    assert client.post("/api/assistant/query", json={"dataset_id": dataset["id"], "question": "Interpret the saved bar chart"}, headers=headers).status_code == 200
    assert client.post("/api/assistant/query", json={"dataset_id": dataset["id"], "question": "Summarize the ML experiment"}, headers=headers).status_code == 200
    chart_context, experiment_context = contexts
    assert chart_context["analysis"]["saved_visualization_count"] == 1
    chart_digest = chart_context["analysis"]["visualizations"][0]["analytical_digest"]
    assert chart_digest["record_count"] == 3
    assert len(chart_digest["leading_aggregates"]) == 3
    assert experiment_context["analysis"]["saved_experiment_count"] == 1
    model_summary = experiment_context["analysis"]["experiments"][0]["models"][0]
    assert "accuracy" in model_summary["metrics"]
    assert model_summary["top_model_derived_features"]


def test_local_ollama_client_sends_guarded_structured_prompt(monkeypatch):
    calls = []

    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self.data

    class Client:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, url):
            calls.append(("GET", url, None))
            return Response({"models": [{"name": "gemma4:e2b", "model": "gemma4:e2b"}]})

        def post(self, url, json):
            calls.append(("POST", url, json))
            return Response({"message": {"role": "assistant", "content": "  A grounded local answer.  "}})

    monkeypatch.setattr("app.services.ollama.httpx.Client", Client)
    monkeypatch.setattr("app.services.ollama.settings.ollama_base_url", "http://localhost:11434")
    monkeypatch.setattr("app.services.ollama.settings.ollama_model", "gemma4:e2b")
    answer = generate_local_answer("Summarize the dataset", {"dataset": {"rows": 12}, "guardrails": {"raw_rows_included": False}})
    assert answer == "A grounded local answer."
    method, url, payload = calls[-1]
    assert method == "POST" and url == "http://localhost:11434/api/chat"
    assert payload["stream"] is False
    assert "tools" not in payload
    assert "Do not generate SQL" in payload["messages"][0]["content"]
    assert '"raw_rows_included": false' in payload["messages"][1]["content"]
