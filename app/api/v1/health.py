from fastapi import APIRouter

from app.config import get_settings
from app.database import get_database
from app.services.llm_client import LLMClient

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    settings = get_settings()
    mongo_ok = False
    try:
        await get_database().command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False

    llm = LLMClient(settings)

    return {
        "status": "ok" if mongo_ok else "degraded",
        "app": settings.app_name,
        "mongodb": "connected" if mongo_ok else "disconnected",
        "ai_provider": settings.ai_provider,
        "ai_model": llm.model if llm.is_available else None,
        "ai_configured": llm.is_available,
    }
