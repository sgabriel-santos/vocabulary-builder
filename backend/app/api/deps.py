"""Dependências compartilhadas da camada HTTP."""

from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.dto import AuthenticatedUser
from app.application.auth.resolve_session import resolve_session
from app.core.config import Settings
from app.core.container import (
    get_clock,
    get_db_session,
    get_password_hasher,
    get_settings_dep,
)
from app.core.rate_limit import InMemoryRateLimiter
from app.ports.clock import Clock
from app.ports.password_hasher import PasswordHasher

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
ClockDep = Annotated[Clock, Depends(get_clock)]
HasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def verify_origin(request: Request, settings: SettingsDep) -> None:
    """Proteção CSRF: métodos que alteram estado exigem Origin conhecido."""
    if request.method in _UNSAFE_METHODS:
        origin = request.headers.get("origin")
        if origin is None or origin not in settings.allowed_origins:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid origin")


def login_rate_limit(request: Request) -> None:
    # Atrás do Caddy, o IP real chega via --proxy-headers do uvicorn.
    limiter: InMemoryRateLimiter = request.app.state.login_rate_limiter
    key = request.client.host if request.client else "unknown"
    if not limiter.hit(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts")


async def current_user(
    request: Request, db: DbSession, clock: ClockDep, settings: SettingsDep
) -> AuthenticatedUser:
    token = request.cookies.get(settings.session_cookie_name)
    user = None
    if token:
        user = await resolve_session(
            db, clock, token=token, ttl=timedelta(days=settings.session_ttl_days)
        )
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


CurrentUser = Annotated[AuthenticatedUser, Depends(current_user)]
