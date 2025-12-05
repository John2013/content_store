import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.user.models import User


@pytest.mark.asyncio
async def test_user_model(db_session: AsyncSession):
    """Test user model creation and properties."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_staff=False,
    )

    db_session.add(user)
    await db_session.commit()

    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.is_staff is False
    assert str(user) == "<User test@example.com>"


@pytest.mark.asyncio
async def test_staff_user_model(db_session: AsyncSession):
    """Test staff user model creation."""
    user = User(
        email="staff@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_staff=True,
    )

    db_session.add(user)
    await db_session.commit()

    assert user.email == "staff@example.com"
    assert user.is_staff is True
    assert user.is_active is True


@pytest.mark.asyncio
async def test_user_model_defaults(db_session: AsyncSession):
    """Test user model default values."""
    user = User(
        email="default@example.com",
        hashed_password="hashed_password",
    )

    db_session.add(user)
    await db_session.commit()

    assert user.is_active is True
    assert user.is_staff is False
