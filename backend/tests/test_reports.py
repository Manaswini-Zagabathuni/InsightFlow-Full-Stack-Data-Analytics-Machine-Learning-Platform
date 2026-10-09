import io
import stat
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Report


def register(client, email: str) -> dict[str, str]:
    response = client.post("/api/auth/register", json={"email": email, "full_name": "Report Owner", "password": "SecurePass123"})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_profiled_project(client, headers: dict[str, str]) -> dict:
    project_response = client.post("/api/projects", json={"name": "Revenue <Review>", "description": "Quarterly analysis & validation"}, headers=headers)
    assert project_response.status_code == 201
    project = project_response.json()
    upload = client.post(
        f"/api/projects/{project['id']}/datasets",
        files={"file": ("revenue.csv", io.BytesIO(b"region,revenue,cost\nNorth,120,80\nSouth,100,72\nWest,150,90\n"), "text/csv")},
        headers=headers,
    )
    assert upload.status_code == 202
    return project


def test_generate_list_and_download_report(client):
    headers = register(client, "reports@example.com")
    project = create_profiled_project(client, headers)

    generated = client.post(f"/api/reports/{project['id']}", headers=headers)
    assert generated.status_code == 201
    body = generated.json()
    assert body["filename"].endswith(".pdf")
    assert body["size_bytes"] > 1000
    assert "storage_path" not in body

    listed = client.get(f"/api/reports/project/{project['id']}", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [body["id"]]

    downloaded = client.get(f"/api/reports/{body['id']}/download", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/pdf"
    assert "attachment" in downloaded.headers["content-disposition"]
    assert downloaded.content.startswith(b"%PDF-")

    with SessionLocal() as db:
        report = db.scalar(select(Report).where(Report.id == body["id"]))
        assert report is not None
        assert Path(report.storage_path).is_file()
        assert stat.S_IMODE(Path(report.storage_path).stat().st_mode) == 0o600


def test_report_authorization_and_missing_file_are_safe(client):
    owner = register(client, "report-owner@example.com")
    outsider = register(client, "report-outsider@example.com")
    project = create_profiled_project(client, owner)
    report = client.post(f"/api/reports/{project['id']}", headers=owner).json()

    assert client.post(f"/api/reports/{project['id']}", headers=outsider).status_code == 404
    assert client.get(f"/api/reports/project/{project['id']}", headers=outsider).status_code == 404
    assert client.get(f"/api/reports/{report['id']}/download", headers=outsider).status_code == 404

    with SessionLocal() as db:
        stored = db.get(Report, report["id"])
        assert stored is not None
        Path(stored.storage_path).unlink()
    assert client.get(f"/api/reports/{report['id']}/download", headers=owner).status_code == 404
