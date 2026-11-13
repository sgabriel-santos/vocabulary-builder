from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import User
from app.application.auth.dto import AuthenticatedUser
from app.application.auth.errors import InvalidUserInput, UserAlreadyExists
from app.domain.auth import normalize_email
from app.ports.password_hasher import PasswordHasher

MIN_PASSWORD_LENGTH = 8


def _is_valid_email(email: str) -> bool:
    local, sep, domain = email.partition("@")
    return bool(sep and local and domain) and "@" not in domain


async def create_user(
    db: AsyncSession, hasher: PasswordHasher, *, email: str, password: str
) -> AuthenticatedUser:
    email = normalize_email(email)
    if not _is_valid_email(email):
        raise InvalidUserInput("E-mail inválido")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidUserInput(f"A senha precisa ter pelo menos {MIN_PASSWORD_LENGTH} caracteres")
    if await db.scalar(select(User.id).where(User.email == email)) is not None:
        raise UserAlreadyExists(email)

    user = User(email=email, password_hash=hasher.hash(password))
    db.add(user)
    await db.commit()
    return AuthenticatedUser(id=user.id, email=user.email)
