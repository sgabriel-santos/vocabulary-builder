import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import User, UserSession
from app.application.auth.dto import LoginResult
from app.application.auth.errors import InvalidCredentials
from app.domain.auth import hash_session_token, normalize_email, session_expires_at
from app.ports.clock import Clock
from app.ports.password_hasher import PasswordHasher

# Um hash descartável por tipo de hasher, gerado uma vez por processo. Verificar a senha
# contra ele quando o e-mail não existe iguala o tempo de resposta ao de uma senha errada.
_dummy_hashes: dict[type, str] = {}


def _dummy_hash(hasher: PasswordHasher) -> str:
    key = type(hasher)
    if key not in _dummy_hashes:
        _dummy_hashes[key] = hasher.hash("dummy-password")
    return _dummy_hashes[key]


async def login(
    db: AsyncSession,
    hasher: PasswordHasher,
    clock: Clock,
    *,
    email: str,
    password: str,
    ttl: timedelta,
) -> LoginResult:
    user = await db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        hasher.verify(_dummy_hash(hasher), password)
        raise InvalidCredentials
    if not hasher.verify(user.password_hash, password):
        raise InvalidCredentials
    if hasher.needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(password)

    token = secrets.token_urlsafe(32)
    now = clock.now()
    expires_at = session_expires_at(now, ttl)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            created_at=now,
            last_seen_at=now,
            expires_at=expires_at,
        )
    )
    await db.commit()
    return LoginResult(token=token, expires_at=expires_at)
