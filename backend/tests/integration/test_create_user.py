import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import User
from app.application.auth.create_user import create_user
from app.application.auth.errors import InvalidUserInput, UserAlreadyExists
from tests.fakes.password_hasher import FakePasswordHasher

hasher = FakePasswordHasher()


async def test_create_user_normalizes_email_and_hashes_password(db_session: AsyncSession) -> None:
    created = await create_user(db_session, hasher, email=" New@Example.com ", password="12345678")

    stored = await db_session.scalar(select(User).where(User.id == created.id))
    assert stored is not None
    assert stored.email == "new@example.com"
    assert stored.password_hash == "fake$12345678"


async def test_create_user_rejects_password_shorter_than_8(db_session: AsyncSession) -> None:
    with pytest.raises(InvalidUserInput):
        await create_user(db_session, hasher, email="a@example.com", password="1234567")


@pytest.mark.parametrize("email", ["no-at-sign", "@example.com", "user@", "a@b@c"])
async def test_create_user_rejects_invalid_email(db_session: AsyncSession, email: str) -> None:
    with pytest.raises(InvalidUserInput):
        await create_user(db_session, hasher, email=email, password="12345678")


async def test_create_user_rejects_duplicate_email(db_session: AsyncSession) -> None:
    await create_user(db_session, hasher, email="dup@example.com", password="12345678")

    with pytest.raises(UserAlreadyExists):
        await create_user(db_session, hasher, email="DUP@example.com", password="12345678")
