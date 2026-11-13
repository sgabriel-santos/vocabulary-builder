"""Fixtures compartilhadas.

O container do Postgres só sobe quando algum teste pede uma fixture de banco,
então `pytest -m unit` roda sem Docker. `integration/` e `api/` compartilham
um único container por sessão.
"""

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.core.config import Settings
from tests.fakes.clock import FakeClock

# Mesma imagem do compose.yaml (dev) e da produção.
POSTGRES_IMAGE = "postgres:18.7-alpine"
BACKEND_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
_FOLDER_MARKERS = {"unit", "integration", "api"}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Aplica o marker da pasta (unit/integration/api) a cada teste."""
    for item in items:
        folder = item.path.relative_to(TESTS_DIR).parts[0]
        if folder in _FOLDER_MARKERS:
            item.add_marker(getattr(pytest.mark, folder))


@pytest.fixture
def test_settings() -> Settings:
    # Valores explícitos: o `just` carrega o .env local (ex.: API_PORT=8001) no ambiente.
    return Settings(
        app_env="test",
        api_port=8000,
        session_cookie_name="vocab_session",
        session_ttl_days=60,
        session_cookie_secure=False,
        login_rate_limit="5/minute",
    )


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))


def alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        command.upgrade(alembic_config(url), "head")
        yield url


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(postgres_url)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Sessão dentro de uma transação externa desfeita no fim do teste.

    Os `commit()` dos casos de uso viram savepoints.
    """
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
