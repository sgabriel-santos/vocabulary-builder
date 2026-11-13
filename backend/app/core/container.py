"""Composition root: providers de dependências usados via `Depends`.

Os testes trocam providers com `app.dependency_overrides`.
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.clock import SystemClock
from app.adapters.security.argon2_hasher import Argon2PasswordHasher
from app.core.config import Settings
from app.ports.clock import Clock
from app.ports.password_hasher import PasswordHasher


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


def get_clock() -> Clock:
    return SystemClock()


@lru_cache
def get_password_hasher() -> PasswordHasher:
    # Instância única por processo.
    return Argon2PasswordHasher()
