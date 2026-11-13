from datetime import timedelta

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import User, UserSession
from tests.api.conftest import USER_EMAIL, USER_PASSWORD
from tests.fakes.clock import FakeClock

LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
COOKIE = "vocab_session"

pytestmark = pytest.mark.usefixtures("user")


async def _login(
    client: AsyncClient, email: str = USER_EMAIL, password: str = USER_PASSWORD
) -> Response:
    return await client.post(LOGIN, json={"email": email, "password": password})


async def test_login_sets_http_only_cookie_and_me_returns_user(
    client: AsyncClient, user: User
) -> None:
    response = await _login(client)

    assert response.status_code == 204
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{COOKIE}=")
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie
    assert f"Max-Age={60 * 86400}" in set_cookie

    me = await client.get(ME)
    assert me.status_code == 200
    assert me.json() == {"id": str(user.id), "email": USER_EMAIL}


async def test_login_with_wrong_password_returns_generic_401(client: AsyncClient) -> None:
    response = await _login(client, password="wrong-password")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}
    assert "set-cookie" not in response.headers


async def test_login_with_unknown_email_returns_same_401(client: AsyncClient) -> None:
    wrong_password = await _login(client, password="wrong-password")
    unknown_email = await _login(client, email="nobody@example.com")

    assert unknown_email.status_code == wrong_password.status_code == 401
    assert unknown_email.json() == wrong_password.json()


async def test_login_normalizes_email(client: AsyncClient) -> None:
    response = await _login(client, email=" User@Example.com ")

    assert response.status_code == 204


async def test_me_without_cookie_returns_401(client: AsyncClient) -> None:
    response = await client.get(ME)

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_logout_invalidates_session(client: AsyncClient) -> None:
    await _login(client)
    old_token = client.cookies[COOKIE]

    response = await client.post(LOGOUT)

    assert response.status_code == 204
    assert COOKIE not in client.cookies
    # Reenviar o cookie antigo não reabre a sessão: ela foi apagada no servidor.
    client.cookies.set(COOKIE, old_token)
    me = await client.get(ME)
    assert me.status_code == 401


async def test_logout_without_session_returns_204(client: AsyncClient) -> None:
    response = await client.post(LOGOUT)

    assert response.status_code == 204


async def test_expired_session_returns_401(
    client: AsyncClient, fake_clock: FakeClock, db_session: AsyncSession
) -> None:
    await _login(client)
    fake_clock.advance(timedelta(days=61))

    response = await client.get(ME)

    assert response.status_code == 401
    # A sessão expirada é apagada.
    assert (await db_session.scalar(select(UserSession))) is None


async def test_session_is_renewed_after_one_hour(
    client: AsyncClient, fake_clock: FakeClock, db_session: AsyncSession
) -> None:
    await _login(client)
    session = await db_session.scalar(select(UserSession))
    assert session is not None
    first_expiry = session.expires_at

    fake_clock.advance(timedelta(minutes=30))
    await client.get(ME)
    await db_session.refresh(session)
    assert session.expires_at == first_expiry

    fake_clock.advance(timedelta(hours=1))
    assert (await client.get(ME)).status_code == 200
    await db_session.refresh(session)
    assert session.last_seen_at == fake_clock.now()
    assert session.expires_at == fake_clock.now() + timedelta(days=60)


async def test_post_without_origin_returns_403(client: AsyncClient) -> None:
    del client.headers["Origin"]

    response = await _login(client)

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid origin"}


async def test_post_with_foreign_origin_returns_403(client: AsyncClient) -> None:
    response = await client.post(
        LOGIN,
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
        headers={"Origin": "https://evil.example.com"},
    )

    assert response.status_code == 403


async def test_login_rate_limit_returns_429_after_five_attempts(client: AsyncClient) -> None:
    statuses = [(await _login(client, password="wrong")).status_code for _ in range(6)]

    assert statuses == [401] * 5 + [429]
    # O limite vale também para a senha certa.
    assert (await _login(client)).status_code == 429
