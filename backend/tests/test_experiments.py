import io

import pytest

from app.core.config import settings
from app.services import machine_learning


def ml_csv(rows: int = 60) -> bytes:
    output = ["segment,age,income,tenure,churn,revenue"]
    segments = ["SMB", "Mid-market", "Enterprise"]
    for index in range(rows):
        segment = segments[index % 3]
        age = "" if index in {7, 31} else str(20 + index % 38)
        income = 35000 + index * 1400 + (index % 4) * 900
        tenure = 1 + index % 12
        churn = "yes" if index % 4 in {0, 1} else "no"
        revenue = round(income * 0.72 + tenure * 1250 + (index % 5) * 300, 2)
        output.append(f"{segment},{age},{income},{tenure},{churn},{revenue}")
    return "\n".join(output).encode()


def setup_ml_dataset(client, email="ml-owner@example.com"):
    registration = client.post("/api/auth/register", json={"email": email, "full_name": "ML Owner", "password": "SecurePass123"})
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    project = client.post("/api/projects", json={"name": "ML project"}, headers=headers).json()
    uploaded = client.post(
        f"/api/projects/{project['id']}/datasets",
        files={"file": ("training.csv", io.BytesIO(ml_csv()), "text/csv")},
        headers=headers,
    )
    assert uploaded.status_code == 202
    return headers, project, uploaded.json()["dataset"]


def payload(project, dataset, task, models, target=None):
    features = ["segment", "age", "income", "tenure"]
    return {
        "project_id": project["id"], "dataset_id": dataset["id"], "name": f"{task.title()} comparison",
        "task_type": task, "target_column": target, "features": features,
        "preprocessing": {"numeric_imputer": "median", "categorical_imputer": "most_frequent", "scaler": "standard", "categorical_encoder": "onehot", "test_size": 0.2},
        "selected_models": models, "model_parameters": {},
    }


def test_classification_models_train_with_metrics_and_leakage_safe_fit(client, monkeypatch):
    headers, project, dataset = setup_ml_dataset(client)
    fit_sizes = []
    original_fit = machine_learning.SimpleImputer.fit

    def recording_fit(self, x, y=None):
        fit_sizes.append(len(x))
        return original_fit(self, x, y)

    monkeypatch.setattr(machine_learning.SimpleImputer, "fit", recording_fit)
    response = client.post(
        "/api/experiments",
        json=payload(project, dataset, "classification", ["logistic_regression", "decision_tree", "random_forest", "gradient_boosting"], "churn"),
        headers=headers,
    )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "completed" and body["progress"] == 100
    assert {metric["model_name"] for metric in body["metrics"]} == {"logistic_regression", "decision_tree", "random_forest", "gradient_boosting"}
    assert all({"accuracy", "precision", "recall", "f1", "confusion_matrix"} <= set(metric["metrics"]) for metric in body["metrics"])
    assert fit_sizes and all(size == 48 for size in fit_sizes), "Preprocessing must fit on the training split, never all 60 rows"


def test_regression_models_train_and_persist_comparison_metrics(client):
    headers, project, dataset = setup_ml_dataset(client)
    response = client.post(
        "/api/experiments",
        json=payload(project, dataset, "regression", ["linear_regression", "ridge", "random_forest_regressor", "gradient_boosting_regressor"], "revenue"),
        headers=headers,
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["metrics"]) == 4
    assert all({"mae", "mse", "rmse", "r2", "train_rows", "test_rows"} <= set(metric["metrics"]) for metric in body["metrics"])
    persisted = client.get(f"/api/experiments/{body['id']}/metrics", headers=headers)
    assert persisted.status_code == 200 and len(persisted.json()) == 4


def test_clustering_models_train_with_cluster_metrics(client):
    headers, project, dataset = setup_ml_dataset(client)
    request = payload(project, dataset, "clustering", ["kmeans", "dbscan"])
    request["model_parameters"] = {"kmeans": {"n_clusters": 3}, "dbscan": {"eps": 0.8, "min_samples": 3}}
    response = client.post("/api/experiments", json=request, headers=headers)
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["metrics"]) == 2
    assert all("cluster_sizes" in metric["metrics"] and "silhouette_score" in metric["metrics"] for metric in body["metrics"])


@pytest.mark.parametrize(
    "change, expected",
    [
        ({"features": ["unknown"]}, "Unknown dataset column"),
        ({"task_type": "regression", "target_column": "segment", "features": ["age", "income", "tenure"], "selected_models": ["linear_regression"]}, "Regression target must be numeric"),
        ({"selected_models": ["linear_regression"]}, "not valid for classification"),
        ({"model_parameters": {"logistic_regression": {"n_estimators": 10}}}, "Unsupported parameter"),
        ({"model_parameters": {"random_forest": {"n_estimators": 10}}}, "only be supplied for selected models"),
    ],
)
def test_invalid_experiment_configurations_are_rejected(client, change, expected):
    headers, project, dataset = setup_ml_dataset(client)
    request = payload(project, dataset, "classification", ["logistic_regression"], "churn")
    request.update(change)
    response = client.post("/api/experiments", json=request, headers=headers)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert expected in (detail if isinstance(detail, str) else str(detail))


def test_training_is_dispatched_and_http_request_remains_queued(client, monkeypatch):
    headers, project, dataset = setup_ml_dataset(client)
    dispatched = []
    monkeypatch.setattr("app.api.routes.experiments.train_experiment.delay", lambda experiment_id: dispatched.append(experiment_id))
    response = client.post("/api/experiments", json=payload(project, dataset, "classification", ["logistic_regression"], "churn"), headers=headers)
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert dispatched == [response.json()["id"]]


def test_active_experiment_limit_is_enforced_per_user(client, monkeypatch):
    headers, project, dataset = setup_ml_dataset(client)
    monkeypatch.setattr(settings, "max_active_experiments_per_user", 1)
    monkeypatch.setattr("app.api.routes.experiments.train_experiment.delay", lambda _experiment_id: None)
    request = payload(project, dataset, "classification", ["logistic_regression"], "churn")

    first = client.post("/api/experiments", json=request, headers=headers)
    second = client.post("/api/experiments", json=request, headers=headers)

    assert first.status_code == 202
    assert first.json()["status"] == "queued"
    assert second.status_code == 429


def test_experiment_catalog_and_owner_authorization(client):
    headers, project, dataset = setup_ml_dataset(client)
    catalog = client.get("/api/experiments/catalog", headers=headers)
    assert catalog.status_code == 200
    assert {model["id"] for model in catalog.json()["classification"]} >= {"logistic_regression", "decision_tree", "random_forest", "gradient_boosting", "xgboost"}
    created = client.post("/api/experiments", json=payload(project, dataset, "classification", ["logistic_regression"], "churn"), headers=headers).json()
    other = client.post("/api/auth/register", json={"email": "other-ml@example.com", "full_name": "Other", "password": "SecurePass123"}).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/experiments/{created['id']}", headers=other_headers).status_code == 404
    assert client.get(f"/api/experiments/project/{project['id']}", headers=other_headers).status_code == 404
    assert client.get(f"/api/experiments/{created['id']}/explainability", headers=other_headers).status_code == 404


def test_tree_shap_generates_global_and_individual_explanations(client):
    headers, project, dataset = setup_ml_dataset(client)
    created = client.post(
        "/api/experiments",
        json=payload(project, dataset, "classification", ["decision_tree"], "churn"),
        headers=headers,
    )
    assert created.status_code == 202, created.text
    explanation = created.json()["metrics"][0]["explainability"]
    assert explanation["status"] == "available"
    assert explanation["method"] == "Tree SHAP"
    assert {row["feature"] for row in explanation["global_importance"]} == {"segment", "age", "income", "tenure"}
    assert sum(row["share"] for row in explanation["global_importance"]) == pytest.approx(1, abs=1e-5)
    assert explanation["individual"]["prediction"] in {"yes", "no"}
    assert {row["feature"] for row in explanation["individual"]["contributions"]} == {"segment", "age", "income", "tenure"}
    assert explanation["interpretation"]["importance_kind"] == "model-derived"
    assert "not causal" in explanation["interpretation"]["causal_note"].lower()
    endpoint = client.get(f"/api/experiments/{created.json()['id']}/explainability", headers=headers)
    assert endpoint.status_code == 200
    assert endpoint.json()[0]["explainability"] == explanation


def test_linear_shap_explains_regression_prediction(client):
    headers, project, dataset = setup_ml_dataset(client)
    created = client.post(
        "/api/experiments",
        json=payload(project, dataset, "regression", ["linear_regression"], "revenue"),
        headers=headers,
    )
    assert created.status_code == 202, created.text
    explanation = created.json()["metrics"][0]["explainability"]
    assert explanation["status"] == "available"
    assert explanation["method"] == "Linear SHAP"
    assert isinstance(explanation["individual"]["prediction"], float)
    assert explanation["sample_rows"] == 12


def test_explainability_falls_back_to_permutation_without_fake_local_values(client, monkeypatch):
    headers, project, dataset = setup_ml_dataset(client)

    def unavailable_shap(*_args, **_kwargs):
        raise ValueError("explainer unavailable")

    monkeypatch.setattr("app.services.explainability._shap_values", unavailable_shap)
    created = client.post(
        "/api/experiments",
        json=payload(project, dataset, "classification", ["logistic_regression"], "churn"),
        headers=headers,
    )
    explanation = created.json()["metrics"][0]["explainability"]
    assert explanation["status"] == "partial"
    assert explanation["method"] == "Permutation importance fallback"
    assert explanation["global_importance"]
    assert explanation["individual"] is None
    assert "compatible SHAP" in explanation["individual_unavailable_reason"]


def test_clustering_explainability_is_explicitly_unsupported(client):
    headers, project, dataset = setup_ml_dataset(client)
    created = client.post(
        "/api/experiments",
        json=payload(project, dataset, "clustering", ["kmeans"]),
        headers=headers,
    )
    explanation = created.json()["metrics"][0]["explainability"]
    assert explanation["status"] == "unavailable"
    assert explanation["global_importance"] == []
    assert explanation["individual"] is None
    assert "no supervised target" in explanation["reason"]
