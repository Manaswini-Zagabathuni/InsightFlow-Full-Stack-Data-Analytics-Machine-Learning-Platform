import io

import pytest

CHART_CSV = b"segment,age,income,score,churn\nSMB,21,42000,0.22,no\nEnterprise,34,88000,0.78,yes\nSMB,45,67000,0.51,no\nMid-market,29,59000,0.47,yes\nEnterprise,52,105000,0.91,no\nSMB,38,71000,0.63,yes\n"


def setup_dataset(client, email="charts@example.com"):
    registered = client.post("/api/auth/register", json={"email": email, "full_name": "Chart Owner", "password": "SecurePass123"})
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    project = client.post("/api/projects", json={"name": "Chart project"}, headers=headers).json()
    uploaded = client.post(
        f"/api/projects/{project['id']}/datasets",
        files={"file": ("charts.csv", io.BytesIO(CHART_CSV), "text/csv")},
        headers=headers,
    )
    assert uploaded.status_code == 202
    return headers, project, uploaded.json()["dataset"]


@pytest.mark.parametrize(
    ("chart_type", "x_axis", "y_axis", "group_column"),
    [
        ("bar", "segment", "income", "churn"),
        ("line", "age", "income", "segment"),
        ("scatter", "age", "score", "segment"),
        ("histogram", "income", None, "segment"),
        ("box", "segment", "income", None),
        ("pie", "segment", "income", None),
        ("heatmap", None, None, None),
    ],
)
def test_supported_chart_configurations_generate_dataset_data(client, chart_type, x_axis, y_axis, group_column):
    headers, project, dataset = setup_dataset(client)
    response = client.post(
        "/api/visualizations",
        json={
            "project_id": project["id"],
            "dataset_id": dataset["id"],
            "name": f"Saved {chart_type}",
            "chart_type": chart_type,
            "x_axis": x_axis,
            "y_axis": y_axis,
            "group_column": group_column,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["visualization"]["chart_type"] == chart_type
    assert body["data"]
    assert body["meta"]
    saved = client.get(f"/api/visualizations/project/{project['id']}", headers=headers)
    assert saved.status_code == 200
    assert saved.json()[0]["name"] == f"Saved {chart_type}"


def test_invalid_requested_column_is_rejected(client):
    headers, project, dataset = setup_dataset(client)
    response = client.post(
        "/api/visualizations",
        json={"project_id": project["id"], "dataset_id": dataset["id"], "name": "Invalid", "chart_type": "scatter", "x_axis": "unknown", "y_axis": "income"},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown dataset column: unknown"


def test_chart_specific_type_and_required_axis_validation(client):
    headers, project, dataset = setup_dataset(client)
    categorical_scatter = client.post(
        "/api/visualizations",
        json={"project_id": project["id"], "dataset_id": dataset["id"], "name": "Bad scatter", "chart_type": "scatter", "x_axis": "segment", "y_axis": "income"},
        headers=headers,
    )
    missing_y = client.post(
        "/api/visualizations",
        json={"project_id": project["id"], "dataset_id": dataset["id"], "name": "Bad line", "chart_type": "line", "x_axis": "age"},
        headers=headers,
    )
    duplicate_group = client.post(
        "/api/visualizations",
        json={"project_id": project["id"], "dataset_id": dataset["id"], "name": "Bad group", "chart_type": "bar", "x_axis": "segment", "y_axis": "income", "group_column": "segment"},
        headers=headers,
    )

    assert categorical_scatter.status_code == 422
    assert "numeric" in categorical_scatter.json()["detail"]
    assert missing_y.status_code == 422
    assert "Y-axis" in missing_y.json()["detail"]
    assert duplicate_group.status_code == 422


def test_saved_visualizations_are_owner_scoped(client):
    headers, project, dataset = setup_dataset(client)
    created = client.post(
        "/api/visualizations",
        json={"project_id": project["id"], "dataset_id": dataset["id"], "name": "Private chart", "chart_type": "bar", "x_axis": "segment"},
        headers=headers,
    ).json()
    other = client.post("/api/auth/register", json={"email": "viewer@example.com", "full_name": "Other User", "password": "SecurePass123"}).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    assert client.get(f"/api/visualizations/{created['visualization']['id']}", headers=other_headers).status_code == 404
    assert client.get(f"/api/visualizations/project/{project['id']}", headers=other_headers).status_code == 404
