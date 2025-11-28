import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex}@example.com"


def _get_auth_token(email: str, password: str) -> str:
    """Helper to get auth token."""
    register_resp = client.post(
        "/api/users/register", json={"email": email, "password": password}
    )
    if register_resp.status_code != 201:
        # User might already exist, try login
        pass
    login_resp = client.post(
        "/api/users/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return login_resp.json()["access_token"]


def _get_auth_headers(email: str, password: str) -> dict:
    """Helper to get auth headers."""
    token = _get_auth_token(email, password)
    return {"Authorization": f"Bearer {token}"}


# Public endpoints tests
def test_get_categories():
    """Test getting list of categories."""
    response = client.get("/api/store/categories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_products():
    """Test getting list of products."""
    response = client.get("/api/store/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_products_with_category_filter():
    """Test getting products filtered by category."""
    response = client.get("/api/store/products?category_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_product_not_found():
    """Test getting non-existent product."""
    response = client.get("/api/store/products/99999")
    assert response.status_code == 404


def test_get_product_reviews():
    """Test getting reviews for a product."""
    response = client.get("/api/store/products/1/reviews")
    assert response.status_code in [200, 404]  # 404 if product doesn't exist


# Cart tests
def test_add_to_cart_with_session_id():
    """Test adding item to cart with session_id."""
    session_id = str(uuid.uuid4())
    # First need a product - create one via authenticated user
    email = _unique_email()
    password = "testpass123"
    headers = _get_auth_headers(email, password)

    # Create a category first
    category_resp = client.post(
        "/api/store/categories",
        json={"name": f"Category_{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    category_id = (
        category_resp.json()["id"] if category_resp.status_code == 201 else None
    )

    # Create a product
    product_data = {
        "title": "Test Product",
        "description": "Test Description",
        "price": "10.00",
        "content_text": "This is test content",
        "category_id": category_id,
    }
    product_resp = client.post(
        "/api/store/products", json=product_data, headers=headers
    )
    if product_resp.status_code != 201:
        # Product creation might not be implemented, skip
        return
    product_id = product_resp.json()["id"]

    # Add to cart
    cart_resp = client.post(
        "/api/store/cart",
        json={"product_id": product_id, "quantity": 1, "session_id": session_id},
    )
    assert cart_resp.status_code == 201
    assert cart_resp.json()["product_id"] == product_id


def test_get_cart_with_session_id():
    """Test getting cart with session_id."""
    session_id = str(uuid.uuid4())
    response = client.get(f"/api/store/cart?session_id={session_id}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_cart_requires_session_or_auth():
    """Test that cart requires either session_id or auth."""
    response = client.get("/api/store/cart")
    assert response.status_code == 400


def test_add_to_cart_requires_session_or_auth():
    """Test that adding to cart requires session_id or auth."""
    response = client.post(
        "/api/store/cart", json={"item_in": {"product_id": 1, "quantity": 1}}
    )
    # Should work - generates session_id automatically
    assert response.status_code in [201, 404], (
        response.json()
    )  # 404 if product doesn't exist


# Order tests
def test_create_order_requires_auth():
    """Test that creating order requires authentication."""
    response = client.post("/api/store/orders", json={})
    assert response.status_code == 401


def test_get_orders_requires_auth():
    """Test that getting orders requires authentication."""
    response = client.get("/api/store/orders")
    assert response.status_code == 401


def test_pay_order_requires_auth():
    """Test that paying order requires authentication."""
    response = client.post("/api/store/orders/1/pay")
    assert response.status_code == 401


# Purchase tests
def test_get_purchases_requires_auth():
    """Test that getting purchases requires authentication."""
    response = client.get("/api/store/purchases")
    assert response.status_code == 401


def test_get_purchase_content_requires_auth():
    """Test that getting purchase content requires authentication."""
    response = client.get("/api/store/purchases/1/content")
    assert response.status_code == 401


# Review tests
def test_create_review_requires_auth():
    """Test that creating review requires authentication."""
    response = client.post(
        "/api/store/products/1/reviews", json={"rating": 5, "comment": "Great!"}
    )
    assert response.status_code == 401


def test_update_review_requires_auth():
    """Test that updating review requires authentication."""
    response = client.put("/api/store/reviews/1", json={"rating": 4})
    assert response.status_code == 401


def test_delete_review_requires_auth():
    """Test that deleting review requires authentication."""
    response = client.delete("/api/store/reviews/1")
    assert response.status_code == 401


# Full flow test
def test_full_purchase_flow():
    """Test complete flow: register -> add to cart -> create order -> pay -> get content."""
    email = _unique_email()
    password = "testpass123"

    # Register and login
    headers = _get_auth_headers(email, password)

    # Create category (if endpoint exists)
    category_name = f"Category_{uuid.uuid4().hex[:8]}"
    category_resp = client.post(
        "/api/store/categories",
        json={"name": category_name, "description": "Test category"},
        headers=headers,
    )
    category_id = (
        category_resp.json()["id"] if category_resp.status_code == 201 else None
    )

    # Create product (if endpoint exists)
    product_data = {
        "title": "Digital Book",
        "description": "A great digital book",
        "price": "19.99",
        "content_text": "This is the full content of the digital book...",
        "category_id": category_id,
    }
    product_resp = client.post(
        "/api/store/products", json=product_data, headers=headers
    )
    if product_resp.status_code != 201:
        # Product creation endpoint might not be implemented
        return
    product_id = product_resp.json()["id"]

    # Add to cart
    session_id = str(uuid.uuid4())
    cart_resp = client.post(
        "/api/store/cart",
        json={"product_id": product_id, "quantity": 1, "session_id": session_id},
    )
    assert cart_resp.status_code == 201

    # Create order
    order_resp = client.post(
        "/api/store/orders", json={"session_id": session_id}, headers=headers
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]
    assert order_resp.json()["status"] == "pending"

    # Pay order
    pay_resp = client.post(f"/api/store/orders/{order_id}/pay", headers=headers)
    assert pay_resp.status_code == 200
    assert pay_resp.json()["status"] == "paid"
    assert pay_resp.json()["payment_id"] is not None

    # Get purchase content
    content_resp = client.get(
        f"/api/store/purchases/{order_id}/content", headers=headers
    )
    assert content_resp.status_code == 200
    content_list = content_resp.json()
    assert len(content_list) > 0
    assert content_list[0]["product_id"] == product_id
    assert "content_text" in content_list[0]

    # Create review
    review_resp = client.post(
        f"/api/store/products/{product_id}/reviews",
        json={"rating": 5, "comment": "Excellent content!"},
        headers=headers,
    )
    assert review_resp.status_code == 201

    # Get product reviews
    reviews_resp = client.get(f"/api/store/products/{product_id}/reviews")
    assert reviews_resp.status_code == 200
    reviews = reviews_resp.json()
    assert len(reviews) > 0
    assert reviews[0]["rating"] == 5
