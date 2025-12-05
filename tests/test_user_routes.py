from fastapi import status
from fastapi.testclient import TestClient


def test_register_user(client: TestClient):
    """Test user registration."""
    user_data = {
        "email": "newuser@example.com",
        "password": "testpassword123",
    }

    response = client.post("/api/users/register", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["email"] == user_data["email"]
    assert "id" in data
    assert "hashed_password" not in data


def test_login_user(client: TestClient, test_user):
    """Test user login."""
    login_data = {"username": "test@example.com", "password": "testpassword"}

    response = client.post("/api/users/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_read_users_me(authorized_client: TestClient, test_user):
    """Test getting current user info."""
    response = authorized_client.get("/api/users/me")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True


def test_update_user_me(authorized_client: TestClient, test_user):
    """Test updating current user."""
    update_data = {"email": "updated@example.com"}

    response = authorized_client.patch("/api/users/me", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["email"] == update_data["email"]


def test_read_users(
    authorized_client: TestClient, test_user, test_staff_user, staff_token
):
    """Test getting all users (staff only)."""
    # Regular user should be forbidden
    response = authorized_client.get("/api/users/")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Staff user should be allowed
    staff_client = TestClient(authorized_client.app)
    staff_client.headers.update({"Authorization": f"Bearer {staff_token}"})

    response = staff_client.get("/api/users/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # At least test_user and test_staff_user


def test_read_user(
    authorized_client: TestClient, test_user, test_staff_user, staff_token
):
    """Test getting a specific user by ID (staff only)."""
    user_id = test_user.id

    # Regular user should be forbidden
    response = authorized_client.get(f"/api/users/{user_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Staff user should be allowed
    staff_client = TestClient(authorized_client.app)
    staff_client.headers.update({"Authorization": f"Bearer {staff_token}"})

    response = staff_client.get(f"/api/users/{user_id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == "test@example.com"


def test_update_user(
    authorized_client: TestClient, test_user, test_staff_user, staff_token
):
    """Test updating a user (staff only)."""
    user_id = test_user.id
    update_data = {"is_active": False, "is_staff": True}

    # Regular user should be forbidden
    response = authorized_client.patch(f"/api/users/{user_id}", json=update_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Staff user should be allowed
    staff_client = TestClient(authorized_client.app)
    staff_client.headers.update({"Authorization": f"Bearer {staff_token}"})

    response = staff_client.patch(f"/api/users/{user_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["is_active"] == update_data["is_active"]
    assert data["is_staff"] == update_data["is_staff"]
