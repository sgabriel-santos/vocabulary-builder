from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import User, UserSession
from app.application.auth.dto import AuthenticatedUser
from app.domain.auth import (
    hash_session_token,
    is_session_expired,
    session_expires_at,
    should_renew_session,
)
from app.ports.clock import Clock


async def resolve_session(
    db: AsyncSession, clock: Clock, *, token: str, ttl: timedelta
) -> AuthenticatedUser | None:
    """Usuário dono da sessão, ou None se ela não existe ou expirou.

    Renova a expiração deslizante no máximo uma vez por SESSION_RENEW_INTERVAL.
    """
    row = (
        await db.execute(
            select(UserSession, User)
            .join(User, UserSession.user_id == User.id)
            .where(UserSession.token_hash == hash_session_token(token))
        )
    ).one_or_none()
    if row is None:
        return None

    session, user = row.tuple()
    now = clock.now()
    if is_session_expired(session.expires_at, now):
        await db.delete(session)
        await db.commit()
        return None
    if should_renew_session(session.last_seen_at, now):
        session.last_seen_at = now
        session.expires_at = session_expires_at(now, ttl)
        await db.commit()
    return AuthenticatedUser(id=user.id, email=user.email)
