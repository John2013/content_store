import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex}@example.com"


def test_register_user_success():
    email = _unique_email()
    payload = {"email": email, "password": "strongpassword123"}

    response = client.post("/api/users/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert "id" in data
    assert data["is_active"] is True


def test_login_success_and_get_me():
    email = _unique_email()
    password = "strongpassword123"

    # register user first
    register_resp = client.post(
        "/api/users/register",
        json={"email": email, "password": password},
    )
    assert register_resp.status_code == 201

    # login via OAuth2 password flow (form data)
    login_resp = client.post(
        "/api/users/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # access protected endpoint with bearer token
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_resp = client.get("/api/users/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == email


def test_get_me_unauthorized():
    response = client.get("/api/users/me")
    assert response.status_code == 401
