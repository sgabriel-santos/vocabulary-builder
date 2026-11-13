from datetime import UTC, datetime, timedelta

from app.domain.auth import (
    SESSION_RENEW_INTERVAL,
    hash_session_token,
    is_session_expired,
    normalize_email,
    session_expires_at,
    should_renew_session,
)
from tests.fakes.clock import FakeClock

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def test_normalize_email_lowercases_and_strips() -> None:
    assert normalize_email("  User@Example.COM \n") == "user@example.com"


def test_session_expires_at_adds_ttl() -> None:
    assert session_expires_at(NOW, timedelta(days=60)) == NOW + timedelta(days=60)


def test_session_is_expired_at_exact_expiry() -> None:
    assert is_session_expired(expires_at=NOW, now=NOW)


def test_session_not_expired_before_expiry() -> None:
    assert not is_session_expired(expires_at=NOW + timedelta(seconds=1), now=NOW)


def test_session_renewed_only_after_one_hour() -> None:
    clock = FakeClock(NOW)
    last_seen_at = clock.now()

    clock.advance(SESSION_RENEW_INTERVAL)
    assert not should_renew_session(last_seen_at, clock.now())

    clock.advance(timedelta(seconds=1))
    assert should_renew_session(last_seen_at, clock.now())


def test_hash_session_token_is_deterministic_and_not_plaintext() -> None:
    token = "some-random-token"
    digest = hash_session_token(token)

    assert digest == hash_session_token(token)
    assert digest != token
    assert len(digest) == 64
    assert digest != hash_session_token("another-token")
