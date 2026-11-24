"""Configuração da aplicação a partir de variáveis de ambiente e de /run/secrets."""

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

_SECRETS_DIR = Path("/run/secrets")
_RATE_LIMIT_PATTERN = re.compile(r"^\s*(\d+)\s*/\s*(second|minute|hour)\s*$")
_RATE_LIMIT_WINDOWS = {"second": 1, "minute": 60, "hour": 3600}


class Settings(BaseSettings):
    """Precedência: variáveis de ambiente > arquivos em /run/secrets > defaults.

    Não há `env_file`: o `justfile` carrega o `.env` em dev e o Compose injeta
    o `env_file` em produção. Os defaults servem para desenvolvimento.
    """

    model_config = SettingsConfigDict(
        secrets_dir=_SECRETS_DIR if _SECRETS_DIR.is_dir() else None,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_domain: str = "localhost"
    api_port: int = 8000  # Porta da API em dev (uvicorn e origem permitida)
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "vocab"
    postgres_user: str = "vocab"
    postgres_password: SecretStr = SecretStr("vocab")

    session_cookie_name: str = "vocab_session"
    session_ttl_days: int = 60
    session_cookie_secure: bool = False
    login_rate_limit: str = "5/minute"

    seed_user_email: str = "dev@example.com"
    seed_user_password: SecretStr = SecretStr("dev-password-123")

    @model_validator(mode="after")
    def _validate(self) -> Self:
        # Valida o formato cedo para falhar no boot, não no primeiro login.
        _ = self.login_rate_limit_parsed
        if self.app_env == "production":
            if not self.session_cookie_secure:
                raise ValueError("SESSION_COOKIE_SECURE deve ser true em produção")
            if self.log_format != "json":
                raise ValueError("LOG_FORMAT deve ser json em produção")
        return self

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def allowed_origins(self) -> list[str]:
        if self.app_env == "production":
            return [f"https://{self.app_domain}"]
        return ["http://localhost:5173", f"http://localhost:{self.api_port}"]

    @property
    def login_rate_limit_parsed(self) -> tuple[int, int]:
        """`"5/minute"` → `(5, 60)`: (limite, janela em segundos)."""
        match = _RATE_LIMIT_PATTERN.match(self.login_rate_limit)
        if match is None:
            raise ValueError(
                f"LOGIN_RATE_LIMIT inválido: {self.login_rate_limit!r} "
                "(esperado '<n>/second|minute|hour')"
            )
        return int(match.group(1)), _RATE_LIMIT_WINDOWS[match.group(2)]


@lru_cache
def get_settings() -> Settings:
    return Settings()
