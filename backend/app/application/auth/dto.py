import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthenticatedUser:
    id: uuid.UUID
    email: str


@dataclass(frozen=True)
class LoginResult:
    token: str
    expires_at: datetime
