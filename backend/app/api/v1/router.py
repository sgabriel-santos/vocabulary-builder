from fastapi import APIRouter, Depends

from app.api.deps import verify_origin
from app.api.v1 import health

api_v1_router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_origin)])
api_v1_router.include_router(health.router)
