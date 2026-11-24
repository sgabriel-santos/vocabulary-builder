"""Login, logout e usuário atual (sessão server-side em cookie HttpOnly)."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import ClockDep, CurrentUser, DbSession, HasherDep, SettingsDep, login_rate_limit
from app.api.v1.schemas.auth import LoginRequest, MeResponse
from app.application.auth import login as login_uc
from app.application.auth import logout as logout_uc
from app.application.auth.errors import InvalidCredentials

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(login_rate_limit)],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid email or password"},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too many login attempts"},
    },
)
async def login(
    body: LoginRequest,
    response: Response,
    db: DbSession,
    hasher: HasherDep,
    clock: ClockDep,
    settings: SettingsDep,
) -> None:
    ttl = timedelta(days=settings.session_ttl_days)
    try:
        result = await login_uc.login(
            db, hasher, clock, email=body.email, password=body.password, ttl=ttl
        )
    except InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password") from None
    response.set_cookie(
        key=settings.session_cookie_name,
        value=result.token,
        max_age=int(ttl.total_seconds()),
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request, response: Response, db: DbSession, settings: SettingsDep
) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await logout_uc.logout(db, token=token)
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


@router.get(
    "/me",
    response_model=MeResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"}},
)
async def me(user: CurrentUser) -> MeResponse:
    return MeResponse(id=user.id, email=user.email)
