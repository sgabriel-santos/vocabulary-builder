from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import User
from app.core.config import Settings
from app.core.container import get_clock, get_db_session, get_password_hasher
from app.main import create_app
from tests.fakes.clock import FakeClock
from tests.fakes.password_hasher import FakePasswordHasher

USER_EMAIL = "user@example.com"
USER_PASSWORD = "correct-password-123"
API_ORIGIN = "http://localhost:8000"


@pytest.fixture
def app(test_settings: Settings, db_session: AsyncSession, fake_clock: FakeClock) -> FastAPI:
    app = create_app(test_settings)

    async def _db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = _db_session
    app.dependency_overrides[get_password_hasher] = FakePasswordHasher
    app.dependency_overrides[get_clock] = lambda: fake_clock
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI, test_settings: Settings) -> AsyncIterator[AsyncClient]:
    # O ASGITransport não roda o lifespan (a sessão de banco vem do override)
    # e o httpx não envia Origin sozinho.
    assert API_ORIGIN in test_settings.allowed_origins
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=API_ORIGIN, headers={"Origin": API_ORIGIN}
    ) as client:
        yield client


@pytest_asyncio.fixture
async def user(db_session: AsyncSession) -> User:
    user = User(email=USER_EMAIL, password_hash=FakePasswordHasher().hash(USER_PASSWORD))
    db_session.add(user)
    await db_session.flush()
    return user
