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
    assert me_resp.status_code == 200, (
        f"Expected 200, got {me_resp.status_code}. Response: {me_resp.text}"
    )
    me_data = me_resp.json()
    assert me_data["email"] == email


def test_get_me_unauthorized():
    response = client.get("/api/users/me")
    assert response.status_code == 401


def test_get_users_list_requires_auth():
    """Test that GET /api/users/ requires authentication."""
    response = client.get("/api/users/")
    assert response.status_code == 401


def test_get_users_list_success():
    """Test getting list of all users with authentication."""
    email1 = _unique_email()
    email2 = _unique_email()
    password = "strongpassword123"

    # Register two users
    client.post("/api/users/register", json={"email": email1, "password": password})
    client.post("/api/users/register", json={"email": email2, "password": password})

    # Login as first user
    login_resp = client.post(
        "/api/users/login",
        data={"username": email1, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login_resp.json()["access_token"]

    # Get users list
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/users/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    emails = [user["email"] for user in data]
    assert email1 in emails
    assert email2 in emails


def test_get_user_by_id_success():
    """Test getting a specific user by ID."""
    email = _unique_email()
    password = "strongpassword123"

    # Register and login
    register_resp = client.post(
        "/api/users/register", json={"email": email, "password": password}
    )
    user_id = register_resp.json()["id"]

    login_resp = client.post(
        "/api/users/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login_resp.json()["access_token"]

    # Get user by ID
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(f"/api/users/{user_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == email


def test_get_user_by_id_not_found():
    """Test getting non-existent user returns 404."""
    email = _unique_email()
    password = "strongpassword123"

    # Register and login
    client.post("/api/users/register", json={"email": email, "password": password})
    login_resp = client.post(
        "/api/users/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login_resp.json()["access_token"]

    # Try to get non-existent user
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/users/99999", headers=headers)
    assert response.status_code == 404


def test_get_user_by_id_requires_auth():
    """Test that GET /api/users/{id} requires authentication."""
    response = client.get("/api/users/1")
    assert response.status_code == 401


def test_update_user_success():
    """Test updating a user."""
    email = _unique_email()
    new_email = _unique_email()
    password = "strongpassword123"

    # Register and login
    register_resp = client.post(
        "/api/users/register", json={"email": email, "password": password}
    )
    user_id = register_resp.json()["id"]

    login_resp = client.post(
        "/api/users/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login_resp.json()["access_token"]

    # Update user
    headers = {"Authorization": f"Bearer {token}"}
    update_data = {"email": new_email, "is_active": False}
    response = client.put(f"/api/users/{user_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == new_email
    assert data["is_active"] is False


def test_update_user_not_found():
    """Test updating non-existent user returns 404."""
    email = _unique_email()
    password = "strongpassword123"

    # Register and login
    client.post("/api/users/register", json={"email": email, "password": password})
    login_resp = client.post(
        "/api/users/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login_resp.json()["access_token"]

    # Try to update non-existent user
    headers = {"Authorization": f"Bearer {token}"}
    update_data = {"email": _unique_email(), "is_active": True}
    response = client.put("/api/users/99999", json=update_data, headers=headers)
    assert response.status_code == 404


def test_update_user_requires_auth():
    """Test that PUT /api/users/{id} requires authentication."""
    response = client.put("/api/users/1", json={"email": "test@example.com"})
    assert response.status_code == 401


def test_delete_user_success():
    """Test deleting a user."""
    email1 = _unique_email()
    email2 = _unique_email()
    password = "strongpassword123"

    # Register two users
    register_resp1 = client.post(
        "/api/users/register", json={"email": email1, "password": password}
    )
    user_id = register_resp1.json()["id"]

    client.post("/api/users/register", json={"email": email2, "password": password})

    # Login as first user
    login_resp = client.post(
        "/api/users/login",
        data={"username": email1, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login_resp.json()["access_token"]

    # Delete user
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete(f"/api/users/{user_id}", headers=headers)
    assert response.status_code == 204

    # Verify user is deleted - use token from another user
    login_resp2 = client.post(
        "/api/users/login",
        data={"username": email2, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token2 = login_resp2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    get_resp = client.get(f"/api/users/{user_id}", headers=headers2)
    assert get_resp.status_code == 404


def test_delete_user_not_found():
    """Test deleting non-existent user returns 404."""
    email = _unique_email()
    password = "strongpassword123"

    # Register and login
    client.post("/api/users/register", json={"email": email, "password": password})
    login_resp = client.post(
        "/api/users/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login_resp.json()["access_token"]

    # Try to delete non-existent user
    headers = {"Authorization": f"Bearer {token}"}
    response = client.delete("/api/users/99999", headers=headers)
    assert response.status_code == 404


def test_delete_user_requires_auth():
    """Test that DELETE /api/users/{id} requires authentication."""
    response = client.delete("/api/users/1")
    assert response.status_code == 401
