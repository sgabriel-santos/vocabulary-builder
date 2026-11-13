"""Health check da API e do banco (usado pelo smoke test do deploy)."""

import asyncio

import structlog
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import DbSession
from app.api.v1.schemas.health import HealthResponse

DB_CHECK_TIMEOUT_SECONDS = 2.0

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}},
)
async def get_health(db: DbSession, response: Response) -> HealthResponse:
    try:
        async with asyncio.timeout(DB_CHECK_TIMEOUT_SECONDS):
            await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("health_database_unavailable")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="degraded", database="unavailable")
    return HealthResponse(status="ok", database="ok")
