"""Regras puras de autenticação: sem I/O, sem framework."""

import hashlib
from datetime import datetime, timedelta

# Intervalo mínimo entre renovações da expiração deslizante (evita um UPDATE por request).
SESSION_RENEW_INTERVAL = timedelta(hours=1)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_session_token(token: str) -> str:
    """SHA-256 (hex) do token: o banco nunca guarda o token em texto puro."""
    return hashlib.sha256(token.encode()).hexdigest()


def session_expires_at(now: datetime, ttl: timedelta) -> datetime:
    return now + ttl


def is_session_expired(expires_at: datetime, now: datetime) -> bool:
    return expires_at <= now


def should_renew_session(last_seen_at: datetime, now: datetime) -> bool:
    return now - last_seen_at > SESSION_RENEW_INTERVAL
