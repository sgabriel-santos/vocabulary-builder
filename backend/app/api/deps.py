"""Dependências compartilhadas da camada HTTP."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.container import get_db_session, get_settings_dep

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def verify_origin(request: Request, settings: SettingsDep) -> None:
    """Proteção CSRF: métodos que alteram estado exigem Origin conhecido."""
    if request.method in _UNSAFE_METHODS:
        origin = request.headers.get("origin")
        if origin is None or origin not in settings.allowed_origins:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid origin")
