import asyncio
import os
import sys

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# Ensure project root is on sys.path so that `import app` works in tests
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Use separate in-memory SQLite DB for tests to avoid asyncpg/Proactor issues
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, future=True)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


async def _setup_db():
    # Import here so that PROJECT_ROOT is already on sys.path
    from app.db.base import Base
    from app.db import session as db_session
    from app.main import app

    # Create all tables in the test database
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Make application use the test engine & session for the DB dependency
    db_session.engine = test_engine
    app.dependency_overrides[db_session.get_db] = _override_get_db


async def _teardown_db():
    await test_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _setup_test_environment():
    """Initialize and tear down test DB for the whole test session."""
    asyncio.run(_setup_db())
    yield
    asyncio.run(_teardown_db())
