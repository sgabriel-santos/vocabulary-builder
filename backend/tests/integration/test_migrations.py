import uuid
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import User, UserSession
from tests.conftest import alembic_config


def test_migrations_downgrade_to_base_and_upgrade_to_head(postgres_url: str) -> None:
    cfg = alembic_config(postgres_url)
    command.downgrade(cfg, "base")
    # Termina em head para não afetar os outros testes.
    command.upgrade(cfg, "head")


async def test_users_email_is_unique(db_session: AsyncSession) -> None:
    db_session.add(User(email="dup@example.com", password_hash="x"))
    await db_session.flush()
    db_session.add(User(email="dup@example.com", password_hash="y"))

    with pytest.raises(IntegrityError, match="uq_users_email"):
        await db_session.flush()


async def test_deleting_user_cascades_sessions(db_session: AsyncSession) -> None:
    user = User(email="cascade@example.com", password_hash="x")
    db_session.add(user)
    await db_session.flush()
    now = datetime.now(UTC)
    db_session.add(
        UserSession(
            user_id=user.id,
            token_hash=uuid.uuid4().hex * 2,
            last_seen_at=now,
            expires_at=now + timedelta(days=1),
        )
    )
    await db_session.flush()

    await db_session.execute(delete(User).where(User.id == user.id))

    count = await db_session.scalar(
        select(func.count()).select_from(UserSession).where(UserSession.user_id == user.id)
    )
    assert count == 0
