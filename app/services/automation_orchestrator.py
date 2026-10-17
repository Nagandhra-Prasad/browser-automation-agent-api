from app.repositories.result_repository import ResultRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.automation import AutomationRunResponse, TaskPlan
from app.schemas.task import TaskStatus
from app.services.ai_planner import AIPlannerService
from app.services.browser_automation import BrowserAutomationService
from app.services.data_processor import DataProcessor
from app.services.plan_sanitizer import ensure_job_search_plan


class AutomationOrchestrator:
    def __init__(self) -> None:
        self._tasks = TaskRepository()
        self._sessions = SessionRepository()
        self._results = ResultRepository()
        self._planner = AIPlannerService()
        self._processor = DataProcessor()

    async def run_task(self, task_id: str, user_id: str, headless: bool | None = None) -> AutomationRunResponse:
        task = await self._tasks.get_by_id(task_id, user_id=user_id)
        if not task:
            return AutomationRunResponse(
                task_id=task_id,
                session_id="",
                result_id=None,
                status="failed",
                message="Task not found",
            )

        if task["status"] in (TaskStatus.RUNNING.value, TaskStatus.PLANNING.value):
            return AutomationRunResponse(
                task_id=task_id,
                session_id="",
                result_id=None,
                status="failed",
                message="Task is already running",
            )

        await self._tasks.update_status(task_id, TaskStatus.PLANNING)
        plan: TaskPlan = self._planner.plan_task(task["command"], task["website"])
        plan = ensure_job_search_plan(plan, task["command"], task["website"])
        plan_dict = plan.model_dump()
        await self._tasks.update_status(task_id, TaskStatus.RUNNING, plan=plan_dict)

        session = await self._sessions.create(task_id)
        session_id = session["id"]

        try:
            browser = BrowserAutomationService(headless=headless)
            raw = await browser.execute_plan(plan, session_id, command=task["command"])
            structured = self._processor.structure_extracted(raw, task["command"])
            summary = self._planner.summarize_results(task["command"], structured)

            result = await self._results.create(
                session_id=session_id,
                task_id=task_id,
                data=structured,
                summary=summary,
                user_id=user_id,
            )
            await self._sessions.complete(session_id, "completed")
            await self._tasks.update_status(task_id, TaskStatus.COMPLETED)

            return AutomationRunResponse(
                task_id=task_id,
                session_id=session_id,
                result_id=result["id"],
                status="completed",
                message="Automation finished successfully",
                plan=plan_dict,
            )
        except Exception as exc:
            await self._sessions.complete(session_id, "failed")
            await self._tasks.update_status(task_id, TaskStatus.FAILED)
            return AutomationRunResponse(
                task_id=task_id,
                session_id=session_id,
                result_id=None,
                status="failed",
                message=str(exc),
                plan=plan_dict,
            )
