from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.schemas import HealthResponse
from app.rag.semantic_provider import configured_embedding_provider

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
    semantic = configured_embedding_provider().status()
    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "version": settings.app_version,
        "semantic_embeddings": {
            "enabled": settings.semantic_embeddings_enabled,
            "ready": semantic.ready,
            "provider": semantic.provider,
            "model_alias": semantic.model_alias,
            "embedding_version": semantic.version,
            "detail": semantic.detail,
        },
        "reranker": {
            "enabled": settings.reranker_enabled,
            "provider": settings.reranker_provider.value,
        },
    }


@router.get("/runtime")
async def runtime_identity() -> dict:
    """Expose only public build/profile identity for strict E2E preflight."""
    return {
        "application": "ekip-backend",
        "version": settings.app_version,
        "build_commit": settings.build_commit,
        "environment": settings.app_env.value,
        "compatibility_id": settings.runtime_compatibility_id,
        "features": {
            "agentic_rag": settings.agentic_rag_enabled,
            "agentic_research": settings.agent_research_enabled,
            "external_apis": settings.agent_external_apis_enabled,
            "semantic_embeddings": settings.semantic_embeddings_enabled,
            "reranker": settings.reranker_enabled,
        },
    }
