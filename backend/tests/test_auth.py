from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import User

REGISTER_PAYLOAD = {
    "email": "ada@example.com",
    "full_name": "Ada Lovelace",
    "password": "Analytical123",
}


def register(client, payload=None):
    return client.post("/api/auth/register", json=payload or REGISTER_PAYLOAD)


def test_successful_registration_hashes_password(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "ada@example.com"
    assert "password" not in body["user"]

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "ada@example.com"))
        assert user is not None
        assert user.password_hash != REGISTER_PAYLOAD["password"]
        assert REGISTER_PAYLOAD["password"] not in user.password_hash


def test_duplicate_email_is_rejected_case_insensitively(client):
    assert register(client).status_code == 201
    duplicate = register(client, {**REGISTER_PAYLOAD, "email": "ADA@example.com"})

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "An account with this email already exists"


def test_successful_login(client):
    register(client)
    response = client.post(
        "/api/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )

    assert response.status_code == 200
    assert response.json()["user"]["full_name"] == "Ada Lovelace"
    assert response.json()["access_token"]


def test_invalid_password_is_rejected(client):
    register(client)
    response = client.post(
        "/api/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "WrongPassword123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_protected_endpoint_without_token(client):
    response = client.get("/api/users/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_protected_endpoint_with_valid_token(client):
    token = register(client).json()["access_token"]
    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == REGISTER_PAYLOAD["email"]


def test_logout_requires_authentication_and_accepts_valid_token(client):
    assert client.post("/api/auth/logout").status_code == 401
    token = register(client).json()["access_token"]
    assert client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"}).status_code == 204


def test_registration_validation(client):
    response = register(client, {"email": "not-an-email", "full_name": "A", "password": "password"})
    assert response.status_code == 422
