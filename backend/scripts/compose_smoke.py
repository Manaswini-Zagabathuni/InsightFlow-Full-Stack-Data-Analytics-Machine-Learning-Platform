"""Exercise the critical API flow against a running Compose stack."""

import io
import time
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8000/api"
CSV_DATA = b"""region,age,income,tenure,churn
North,22,42000,1,no
South,31,58000,4,yes
East,45,76000,8,no
West,36,65000,5,no
North,29,51000,2,yes
South,52,88000,12,no
East,41,72000,7,no
West,27,47000,1,yes
North,34,61000,4,no
South,48,81000,10,no
East,25,45000,2,yes
West,39,69000,6,no
North,55,93000,15,no
South,30,54000,3,yes
East,44,74000,9,no
West,28,49000,2,yes
"""


def expect(response: httpx.Response, status_code: int, step: str) -> dict:
    if response.status_code != status_code:
        raise RuntimeError(f"{step}: {response.status_code} {response.text}")
    return response.json() if response.content else {}


def wait_for(client: httpx.Client, path: str, headers: dict[str, str], terminal: set[str], timeout: int) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = expect(client.get(path, headers=headers), 200, f"poll {path}")
        if body["status"] in terminal:
            return body
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for {path}")


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        suffix = uuid.uuid4().hex[:12]
        credentials = {
            "email": f"compose-{suffix}@example.com",
            "full_name": "Compose Verification",
            "password": "Production123",
        }
        expect(client.get("/health"), 200, "health")
        registration = expect(client.post("/auth/register", json=credentials), 201, "register")
        headers = {"Authorization": f"Bearer {registration['access_token']}"}
        project = expect(
            client.post("/projects", json={"name": f"Compose check {suffix}"}, headers=headers),
            201,
            "create project",
        )
        uploaded = expect(
            client.post(
                f"/projects/{project['id']}/datasets",
                files={"file": ("customers.csv", io.BytesIO(CSV_DATA), "text/csv")},
                headers=headers,
            ),
            202,
            "upload dataset",
        )["dataset"]
        dataset = wait_for(client, f"/datasets/{uploaded['id']}", headers, {"ready", "failed"}, 90)
        if dataset["status"] != "ready":
            raise RuntimeError(f"profiling failed: {dataset.get('profile_error')}")
        rows = expect(client.get(f"/datasets/{dataset['id']}/rows?page_size=5", headers=headers), 200, "explore")
        if rows["total"] != 16:
            raise RuntimeError("unexpected explored row count")
        expect(
            client.post(
                "/visualizations",
                json={
                    "project_id": project["id"],
                    "dataset_id": dataset["id"],
                    "name": "Income by region",
                    "chart_type": "bar",
                    "x_axis": "region",
                    "y_axis": "income",
                    "group_column": None,
                },
                headers=headers,
            ),
            201,
            "visualize",
        )
        experiment = expect(
            client.post(
                "/experiments",
                json={
                    "project_id": project["id"],
                    "dataset_id": dataset["id"],
                    "name": "Compose decision tree",
                    "task_type": "classification",
                    "target_column": "churn",
                    "features": ["region", "age", "income", "tenure"],
                    "preprocessing": {
                        "numeric_imputer": "median",
                        "categorical_imputer": "most_frequent",
                        "scaler": "standard",
                        "categorical_encoder": "onehot",
                        "test_size": 0.25,
                    },
                    "selected_models": ["decision_tree"],
                    "model_parameters": {"decision_tree": {"max_depth": 3}},
                },
                headers=headers,
            ),
            202,
            "start experiment",
        )
        experiment = wait_for(client, f"/experiments/{experiment['id']}", headers, {"completed", "failed"}, 180)
        if experiment["status"] != "completed":
            raise RuntimeError(f"training failed: {experiment.get('error')}")
        metrics = expect(client.get(f"/experiments/{experiment['id']}/metrics", headers=headers), 200, "metrics")
        explanations = expect(
            client.get(f"/experiments/{experiment['id']}/explainability", headers=headers), 200, "explainability"
        )
        if not metrics or not explanations:
            raise RuntimeError("experiment evidence is missing")
        report = expect(client.post(f"/reports/{project['id']}", headers=headers), 201, "generate report")
        download = client.get(f"/reports/{report['id']}/download", headers=headers)
        if download.status_code != 200 or not download.content.startswith(b"%PDF-"):
            raise RuntimeError("report download was not a PDF")
        print("Compose core flow passed")


if __name__ == "__main__":
    main()
