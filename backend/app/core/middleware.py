"""Middleware de contexto de request: request_id e log de acesso.

Nunca loga headers (Cookie/Set-Cookie) nem corpo de requests.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from starlette.routing import Match

REQUEST_ID_HEADER = "X-Request-ID"

logger = structlog.get_logger("app.http")


def _route_path(request: Request) -> str:
    """Template da rota (ex.: /api/v1/items/{id}) para não explodir a cardinalidade dos logs."""
    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            path = getattr(route, "path", None)
            if isinstance(path, str):
                return path
    return request.url.path


def add_request_context_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            logger.info(
                "http_request",
                method=request.method,
                path=_route_path(request),
                status=status,
                duration_ms=round((time.perf_counter() - start) * 1000, 1),
            )
            structlog.contextvars.unbind_contextvars("request_id")
