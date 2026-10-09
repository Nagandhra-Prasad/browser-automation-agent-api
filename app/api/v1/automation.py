from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.automation import AutomationRunResponse, AutomationStartRequest
from app.services.automation_orchestrator import AutomationOrchestrator

router = APIRouter()


@router.post("/tasks/{task_id}/start", response_model=AutomationRunResponse)
async def start_automation(
    task_id: str,
    body: AutomationStartRequest | None = None,
    user_id: str = Depends(get_current_user_id),
) -> AutomationRunResponse:
    headless = body.headless if body else None
    return await AutomationOrchestrator().run_task(task_id, user_id, headless=headless)
