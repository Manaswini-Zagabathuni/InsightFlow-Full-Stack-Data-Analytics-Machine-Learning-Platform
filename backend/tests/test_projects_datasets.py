import io
import stat
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Dataset


def auth_headers(client, email: str = "owner@example.com") -> dict[str, str]:
    response = client.post("/api/auth/register", json={"email": email, "full_name": "Dataset Owner", "password": "SecurePass123"})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_project(client, headers, name: str = "Customer analysis") -> dict:
    response = client.post("/api/projects", json={"name": name, "description": "Retention dataset"}, headers=headers)
    assert response.status_code == 201
    return response.json()


def upload_csv(client, project_id: str, headers, content: bytes, filename: str = "customers.csv"):
    return client.post(
        f"/api/projects/{project_id}/datasets",
        files={"file": (filename, io.BytesIO(content), "text/csv")},
        headers=headers,
    )


SAMPLE_CSV = b"customer_id,age,segment,churn\n1,31,SMB,no\n2,,Enterprise,yes\n2,,Enterprise,yes\n4,48,SMB,no\n"


def test_project_crud_and_ownership(client):
    owner = auth_headers(client)
    outsider = auth_headers(client, "outsider@example.com")
    project = create_project(client, owner)

    listed = client.get("/api/projects", headers=owner)
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "Customer analysis"
    assert client.get("/api/projects", headers=outsider).json() == []
    assert client.get(f"/api/projects/{project['id']}", headers=outsider).status_code == 404
    renamed = client.patch(f"/api/projects/{project['id']}", json={"name": "Churn analysis"}, headers=owner)
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Churn analysis"
    assert client.delete(f"/api/projects/{project['id']}", headers=outsider).status_code == 404
    assert client.delete(f"/api/projects/{project['id']}", headers=owner).status_code == 204


def test_csv_upload_profiles_and_stores_file_safely(client):
    headers = auth_headers(client)
    project = create_project(client, headers)
    response = upload_csv(client, project["id"], headers, SAMPLE_CSV, "../unsafe customers.csv")

    assert response.status_code == 202
    dataset = response.json()["dataset"]
    assert dataset["status"] == "ready"
    assert dataset["row_count"] == 4
    assert dataset["column_count"] == 4
    assert dataset["missing_cells"] == 2
    assert dataset["duplicate_rows"] == 1
    assert 0 <= dataset["quality_score"] < 100
    assert any("missing" in issue for issue in dataset["quality_issues"])
    assert any("duplicate" in issue for issue in dataset["quality_issues"])

    with SessionLocal() as db:
        stored = db.scalar(select(Dataset).where(Dataset.id == dataset["id"]))
        assert stored is not None
        storage_path = Path(stored.storage_path)
        assert storage_path.name == f"{stored.id}.csv"
        assert "unsafe customers.csv" not in stored.storage_path
        assert storage_path.exists()
        assert stat.S_IMODE(storage_path.stat().st_mode) == 0o600
        assert len(stored.columns) == 4
        age = next(column for column in stored.columns if column.name == "age")
        assert age.missing_count == 2
        assert age.data_type == "numeric"


def test_dataset_authorization_and_project_ownership(client):
    owner = auth_headers(client)
    outsider = auth_headers(client, "other@example.com")
    project = create_project(client, owner)
    dataset = upload_csv(client, project["id"], owner, SAMPLE_CSV).json()["dataset"]

    assert client.get(f"/api/datasets/{dataset['id']}", headers=outsider).status_code == 404
    assert client.get(f"/api/datasets/{dataset['id']}/profile", headers=outsider).status_code == 404
    assert client.get(f"/api/datasets/{dataset['id']}/rows", headers=outsider).status_code == 404
    assert upload_csv(client, project["id"], outsider, SAMPLE_CSV).status_code == 404


def test_invalid_files_are_rejected(client):
    headers = auth_headers(client)
    project = create_project(client, headers)

    wrong_type = upload_csv(client, project["id"], headers, b"print('unsafe')", "script.py")
    empty = upload_csv(client, project["id"], headers, b"", "empty.csv")
    header_only = upload_csv(client, project["id"], headers, b"a,b\n", "header.csv")
    duplicate_headers = upload_csv(client, project["id"], headers, b"a,a\n1,2\n", "duplicate.csv")
    malformed_later_row = upload_csv(client, project["id"], headers, b"a,b\n1,2\n3,4,5\n", "malformed.csv")
    blank_document = upload_csv(client, project["id"], headers, b"\n", "blank.csv")

    assert wrong_type.status_code == 415
    assert empty.status_code == 400
    assert header_only.status_code == 422
    assert duplicate_headers.status_code == 422
    assert malformed_later_row.status_code == 422
    assert "row 3" in malformed_later_row.json()["detail"]
    assert blank_document.status_code == 422


def test_explorer_paginates_searches_sorts_and_marks_missing_values(client):
    headers = auth_headers(client)
    project = create_project(client, headers)
    dataset = upload_csv(client, project["id"], headers, SAMPLE_CSV).json()["dataset"]

    page = client.get(f"/api/datasets/{dataset['id']}/rows?page=1&page_size=2&sort_by=age&sort_order=desc", headers=headers)
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 4
    assert body["total_pages"] == 2
    assert len(body["rows"]) == 2
    assert body["rows"][0]["age"] == 48.0
    assert len(body["columns"]) == 4

    searched = client.get(f"/api/datasets/{dataset['id']}/rows?search=Enterprise", headers=headers)
    assert searched.status_code == 200
    assert searched.json()["total"] == 2
    assert "age" in searched.json()["rows"][0]["_missing"]

    invalid_sort = client.get(f"/api/datasets/{dataset['id']}/rows?sort_by=unknown", headers=headers)
    assert invalid_sort.status_code == 422
