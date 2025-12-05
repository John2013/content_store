import pytest
from decimal import Decimal
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.store.models import (
    Category,
    Product,
    CartItem,
    Order,
    OrderItem,
    Review,
    Purchase,
)


@pytest.mark.asyncio
async def test_category_model(db_session: AsyncSession):
    """Test Category model creation and properties."""
    category = Category(
        name="Electronics", description="Electronic gadgets and devices"
    )

    db_session.add(category)
    await db_session.commit()

    assert category.name == "Electronics"
    assert category.description == "Electronic gadgets and devices"
    assert isinstance(category.created_at, datetime)
    assert str(category) == f"<Category {category.id}: Electronics>"


@pytest.mark.asyncio
async def test_product_model(db_session: AsyncSession):
    """Test Product model creation and properties."""
    # First create a category
    category = Category(name="Electronics")
    db_session.add(category)
    await db_session.commit()

    product = Product(
        title="Smartphone",
        description="Latest smartphone model",
        content_text="Detailed smartphone specifications and features",
        price=Decimal("699.99"),
        category_id=category.id,
    )

    db_session.add(product)
    await db_session.commit()

    assert product.title == "Smartphone"
    assert product.price == Decimal("699.99")
    assert product.category_id == category.id
    assert str(product) == f"<Product {product.id}: Smartphone>"


@pytest.mark.asyncio
async def test_cart_item_model(db_session: AsyncSession, test_user):
    """Test CartItem model creation and properties."""
    category = Category(name="Electronics")
    product = Product(
        title="Laptop",
        price=Decimal("1299.99"),
        content_text="High-performance laptop specifications",
        category=category,
    )

    cart_item = CartItem(user=test_user, product=product, quantity=1)

    db_session.add_all([category, product, cart_item])
    await db_session.commit()

    assert cart_item.user_id == test_user.id
    assert cart_item.product_id == product.id
    assert cart_item.quantity == 1
    assert (
        str(cart_item)
        == f"<CartItem {cart_item.id}: {product.title} x {cart_item.quantity}>"
    )


@pytest.mark.asyncio
async def test_order_models(db_session: AsyncSession, test_user):
    """Test Order and OrderItem models together."""
    # Create category and product
    category = Category(name="Books")
    product = Product(
        title="Python Programming",
        price=Decimal("59.99"),
        content_text="Comprehensive guide to Python programming",
        category=category,
    )

    # Create order
    order = Order(user=test_user, total_amount=Decimal("119.98"), status="pending")

    # Create order item
    order_item = OrderItem(
        order=order, product=product, quantity=2, price_at_purchase=Decimal("59.99")
    )

    db_session.add_all([category, product, order, order_item])
    await db_session.commit()

    # Test order
    assert order.user_id == test_user.id
    assert order.total_amount == Decimal("119.98")
    assert order.status == "pending"
    assert len(order.order_items) == 1

    # Test order item
    assert order_item.order_id == order.id
    assert order_item.product_id == product.id
    assert order_item.quantity == 2
    assert order_item.price_at_purchase == Decimal("59.99")


@pytest.mark.asyncio
async def test_review_model(db_session: AsyncSession, test_user):
    """Test Review model creation and properties."""
    category = Category(name="Electronics")
    product = Product(
        title="Wireless Earbuds",
        price=Decimal("129.99"),
        content_text="High-quality wireless earbuds with noise cancellation",
        category=category,
    )

    review = Review(
        user=test_user, product=product, rating=5, comment="Great sound quality!"
    )

    db_session.add_all([category, product, review])
    await db_session.commit()

    assert review.user_id == test_user.id
    assert review.product_id == product.id
    assert review.rating == 5
    assert review.comment == "Great sound quality!"
    assert str(review) == f"<Review {review.id}>"


@pytest.mark.asyncio
async def test_purchase_model(db_session: AsyncSession, test_user):
    """Test Purchase model creation and properties."""
    category = Category(name="Electronics")
    product = Product(
        title="Smart Watch",
        price=Decimal("299.99"),
        content_text="Feature-rich smartwatch with health tracking",
        category=category,
    )

    order = Order(user=test_user, total_amount=Decimal("299.99"), status="completed")

    purchase = Purchase(user=test_user, order=order, product=product)

    db_session.add_all([category, product, order, purchase])
    await db_session.commit()

    assert purchase.user_id == test_user.id
    assert purchase.order_id == order.id
    assert purchase.product_id == product.id
    assert isinstance(purchase.purchased_at, datetime)
    assert str(purchase) == f"<Purchase {purchase.id}>"
