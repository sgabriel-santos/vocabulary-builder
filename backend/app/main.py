"""Ponto de entrada da API: `uvicorn app.main:create_app --factory`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.adapters.db.engine import build_engine, build_sessionmaker
from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import add_request_context_middleware
from app.core.rate_limit import InMemoryRateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Conexões só nascem aqui: importar o módulo ou chamar create_app() não toca no banco.
    engine = build_engine(app.state.settings)
    app.state.engine = engine
    app.state.sessionmaker = build_sessionmaker(engine)
    try:
        yield
    finally:
        await engine.dispose()


def _operation_id(route: APIRoute) -> str:
    # operationId "<tag>-<função>"; toda rota precisa declarar tags.
    return f"{route.tags[0]}-{route.name}"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    app = FastAPI(
        title="Vocabulary Builder API",
        docs_url=None if settings.app_env == "production" else "/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        generate_unique_id_function=_operation_id,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.login_rate_limiter = InMemoryRateLimiter(*settings.login_rate_limit_parsed)
    add_request_context_middleware(app)
    app.include_router(api_v1_router)
    return app
