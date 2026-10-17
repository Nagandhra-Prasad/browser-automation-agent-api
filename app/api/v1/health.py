from fastapi import APIRouter

from app.config import get_settings
from app.database import get_database
from app.services.llm_client import LLMClient, ping_ollama

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

    ollama_up = None
    if settings.ai_provider.lower() == "ollama":
        ollama_up = ping_ollama(settings.ollama_base_url)

    groq_key_set = bool(
        (settings.groq_api_key or "").strip()
        and not (settings.groq_api_key or "").strip().startswith("your-key")
    )

    return {
        "status": "ok" if mongo_ok else "degraded",
        "app": settings.app_name,
        "mongodb": "connected" if mongo_ok else "disconnected",
        "ai_provider": settings.ai_provider,
        "ai_model": llm.model if llm.is_available else None,
        "ai_configured": llm.is_available,
        "ollama_reachable": ollama_up,
        "groq_api_key_set": groq_key_set if settings.ai_provider.lower() == "groq" else None,
    }
