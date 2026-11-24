"""Modelos ORM. Importados aqui para o Alembic enxergar o metadata completo."""

from app.adapters.db.models.session import UserSession
from app.adapters.db.models.user import User

__all__ = ["User", "UserSession"]
