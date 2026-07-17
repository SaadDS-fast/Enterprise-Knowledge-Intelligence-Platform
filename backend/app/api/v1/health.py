from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse(
        status="ok", version=settings.app_version, environment=settings.app_env.value
    )


@router.get("/ready")
async def ready() -> dict:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "version": settings.app_version,
    }
