from fastapi import status


# Test categories


def test_get_categories(client):
    """Test getting all categories (public endpoint)."""
    response = client.get("/api/store/categories")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


def test_create_category_unauthorized(client):
    """Test creating a category without authentication."""
    category_data = {"name": "Test Category", "description": "Test Description"}
    response = client.post("/api/store/categories", json=category_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_category_not_staff(authorized_client):
    """Test creating a category as non-staff user."""
    category_data = {"name": "Test Category", "description": "Test Description"}
    response = authorized_client.post("/api/store/categories", json=category_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_category_staff(staff_authorized_client):
    """Test creating a category as staff user."""
    category_data = {"name": "Test Category", "description": "Test Description"}
    response = staff_authorized_client.post("/api/store/categories", json=category_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == category_data["name"]
    assert data["description"] == category_data["description"]
    assert "id" in data


# Test products


def test_get_products(client, db_session, test_category):
    """Test getting all products (public endpoint)."""
    # Create a test product
    product_data = {
        "title": "Test Product",
        "description": "Test Description",
        "content_text": "Detailed test product description",
        "price": 99.99,
        "category_id": test_category.id,
    }

    # Add product directly to the database for testing
    from app.store.models import Product

    product = Product(**product_data)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    # Test getting all products
    response = client.get("/api/store/products")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(p["title"] == "Test Product" for p in data)


def test_create_product_staff(staff_authorized_client, test_category, test_user):
    """Test creating a product as staff user."""
    product_data = {
        "title": "New Product",
        "description": "Product description",
        "content_text": "Detailed new product description",
        "price": 199.99,
        "category_id": test_category.id,
    }

    response = staff_authorized_client.post("/api/store/products", json=product_data)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == product_data["title"]
    assert data["price"] == str(product_data["price"])
    assert data["category_id"] == test_category.id


def test_create_products_staff(staff_authorized_client, test_category):
    """Test creating multiple products as staff user."""
    products_data = {
        "products": [
            {
                "title": "Product 1",
                "description": "First test product",
                "content_text": "Content of first product",
                "price": 99.99,
                "category_id": test_category.id,
            },
            {
                "title": "Product 2",
                "description": "Second test product",
                "content_text": "Content of second product",
                "price": 149.99,
                "category_id": test_category.id,
            },
        ]
    }

    response = staff_authorized_client.post(
        "/api/store/products/create-many", json=products_data
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["title"] == "Product 1"
    assert data[1]["title"] == "Product 2"
    assert data[0]["price"] == "99.99"
    assert data[1]["price"] == "149.99"


# Test cart functionality


def test_add_to_cart_anonymous(client, db_session, test_product):
    """Test adding an item to cart as anonymous user (using session_id)."""
    session_id = "test-session-123"
    cart_item = {"product_id": test_product.id, "quantity": 2, "session_id": session_id}

    response = client.post("/api/store/cart", json=cart_item)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["product_id"] == test_product.id
    assert data["quantity"] == 2
    assert data["session_id"] == session_id


def test_add_to_cart_authenticated(authorized_client, test_product):
    """Test adding an item to cart as authenticated user."""
    cart_item = {"product_id": test_product.id, "quantity": 1}

    response = authorized_client.post("/api/store/cart", json=cart_item)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["product_id"] == test_product.id
    assert data["quantity"] == 1


# Test orders


def test_create_order(authorized_client, test_product):
    """Test creating an order from cart."""
    # First add item to cart
    cart_item = {"product_id": test_product.id, "quantity": 1}
    authorized_client.post("/api/store/cart", json=cart_item)

    # Create order
    order_data = {
        "shipping_address": "123 Test St, Test City",
        "payment_method": "credit_card",
    }

    response = authorized_client.post("/api/store/orders", json=order_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "pending"
    assert data["total_amount"] == str(test_product.price)
    assert len(data["order_items"]) == 1
    assert data["order_items"][0]["product_id"] == test_product.id


# Test reviews


def test_create_review(authorized_client, test_product, test_purchase):
    """Test creating a product review."""
    review_data = {"rating": 5, "comment": "Great product!"}

    response = authorized_client.post(
        f"/api/store/products/{test_product.id}/reviews", json=review_data
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["rating"] == 5
    assert data["comment"] == "Great product!"
    assert data["product_id"] == test_product.id


# Test purchases


def test_get_purchases(authorized_client, test_purchase):
    """Test getting user's purchase history."""
    response = authorized_client.get("/api/store/purchases")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(p["id"] == test_purchase.id for p in data)
