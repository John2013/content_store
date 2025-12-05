import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.auth.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app.user.models import User
from app.store.models import (
    Category,
    Product,
    CartItem,
    Order,
    OrderItem,
    Purchase,
)
from decimal import Decimal
from datetime import datetime, timedelta

# Use in-memory SQLite for testing
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# Override the database URL for testing
os.environ["DATABASE_URL"] = TEST_DB_URL


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each test case."""
    # Set up the test database
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create a new session for testing
    async with AsyncSession(bind=engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> TestClient:
    """Create a test client that uses the override_get_db fixture."""

    # Override the database dependency
    async def override_get_db():
        try:
            yield db_session
        finally:
            await db_session.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    client = TestClient(fastapi_app)
    return client


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user_data = {
        "email": "test@example.com",
        "hashed_password": get_password_hash("testpassword"),
        "is_active": True,
        "is_staff": False,
    }
    user = User(**user_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_staff_user(db_session: AsyncSession) -> User:
    """Create a test staff user."""
    user_data = {
        "email": "staff@example.com",
        "hashed_password": get_password_hash("staffpassword"),
        "is_active": True,
        "is_staff": True,
    }
    user = User(**user_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
def user_token(test_user: User) -> str:
    """Generate a token for the test user."""
    return create_access_token(test_user.id, None, {"is_staff": test_user.is_staff})


@pytest_asyncio.fixture(scope="function")
def staff_token(test_staff_user: User) -> str:
    """Generate a token for the staff user."""
    return create_access_token(
        test_staff_user.id, None, {"is_staff": test_staff_user.is_staff}
    )


@pytest_asyncio.fixture(scope="function")
def authorized_client(client: TestClient, user_token: str) -> TestClient:
    """Create an authorized test client with a valid token."""
    client.headers.update({"Authorization": f"Bearer {user_token}"})
    return client


@pytest_asyncio.fixture(scope="function")
def staff_authorized_client(client: TestClient, staff_token: str) -> TestClient:
    """Create an authorized test client with a staff token."""
    client.headers.update({"Authorization": f"Bearer {staff_token}"})
    return client


# Store fixtures


@pytest_asyncio.fixture(scope="function")
async def test_category(db_session: AsyncSession) -> Category:
    """Create a test category."""
    category = Category(name="Test Category", description="Test category description")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture(scope="function")
async def test_product(db_session: AsyncSession, test_category: Category) -> Product:
    """Create a test product."""
    product = Product(
        title="Test Product",
        description="Test product description",
        content_text="Detailed test product description",
        price=Decimal("99.99"),
        category_id=test_category.id,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture(scope="function")
async def test_cart_item(
    db_session: AsyncSession, test_user: User, test_product: Product
) -> CartItem:
    """Create a test cart item."""
    cart_item = CartItem(user=test_user, product=test_product, quantity=1)
    db_session.add(cart_item)
    await db_session.commit()
    await db_session.refresh(cart_item)
    return cart_item


@pytest_asyncio.fixture(scope="function")
async def test_order(db_session: AsyncSession, test_user: User) -> Order:
    """Create a test order."""
    order = Order(user=test_user, total_amount=Decimal("199.98"), status="completed")
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest_asyncio.fixture(scope="function")
async def test_order_item(
    db_session: AsyncSession, test_order: Order, test_product: Product
) -> OrderItem:
    """Create a test order item."""
    order_item = OrderItem(
        order=test_order,
        product=test_product,
        quantity=2,
        price_at_purchase=test_product.price,
    )
    db_session.add(order_item)
    await db_session.commit()
    await db_session.refresh(order_item)
    return order_item


@pytest_asyncio.fixture(scope="function")
async def test_purchase(
    db_session: AsyncSession, test_user: User, test_order: Order, test_product: Product
) -> Purchase:
    """Create a test purchase."""
    purchase = Purchase(
        user=test_user,
        order=test_order,
        product=test_product,
        purchased_at=datetime.utcnow() - timedelta(days=1),
    )
    db_session.add(purchase)
    await db_session.commit()
    await db_session.refresh(purchase)
    return purchase
