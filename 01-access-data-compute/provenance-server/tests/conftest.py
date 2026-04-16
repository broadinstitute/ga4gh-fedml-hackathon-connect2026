"""Shared pytest fixtures for the provenance server test suite."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from provenance_server.config import Settings
from provenance_server.database import get_session
from provenance_server.models import Base

# ---------------------------------------------------------------------------
# In-memory SQLite engine for tests
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """Return an HTTPX AsyncClient wired to the FastAPI app with an in-memory DB."""
    from provenance_server.main import app

    # Override the DB dependency
    async def override_session():
        yield db_session

    # Override settings to use test site name
    def override_settings():
        return Settings(
            database_url=TEST_DB_URL,
            service_id="test-node",
            site="test-site",
        )

    from provenance_server.config import get_settings
    from provenance_server.database import get_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
