from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import UserSession
from app.domain.auth import hash_session_token


async def logout(db: AsyncSession, *, token: str) -> None:
    """Apaga a sessão do token (idempotente)."""
    await db.execute(delete(UserSession).where(UserSession.token_hash == hash_session_token(token)))
    await db.commit()
