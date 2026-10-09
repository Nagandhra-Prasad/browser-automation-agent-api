from typing import Any, Literal

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    action: Literal["navigate", "click", "type", "wait", "extract", "screenshot"]
    selector: str | None = None
    value: str | None = None
    description: str = ""


class TaskPlan(BaseModel):
    intent: str
    steps: list[PlanStep]
    extraction_goal: str


class AutomationStartRequest(BaseModel):
    """Optional override; normally automation is started via task id."""

    headless: bool | None = None


class AutomationRunResponse(BaseModel):
    task_id: str
    session_id: str
    result_id: str | None
    status: str
    message: str
    plan: dict[str, Any] | None = None
