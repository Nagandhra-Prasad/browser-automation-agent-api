import re

from app.schemas.automation import TaskPlan
from app.services.ai_planner import AIPlannerService
from app.services.job_search import JobSearchService

_JOB_HINT = re.compile(
    r"\b(job|jobs|developer|engineer|hiring|career|vacancy|opening)\b",
    re.I,
)

_GOOGLE_ONLY_SELECTORS = ("name=q", "input[name='q']", 'input[name="q"]', "#searchform")


def is_job_search(command: str, website: str) -> bool:
    if "indeed.com" in website.lower():
        return True
    if "google.com" in website.lower() and "ibp=htl" in website.lower():
        return True
    return bool(_JOB_HINT.search(command))


def ensure_job_search_plan(plan: TaskPlan, command: str, website: str) -> TaskPlan:
    """Use a safe Indeed navigate/wait/extract plan for job searches (avoids bad AI selectors)."""
    if not is_job_search(command, website):
        return _strip_risky_steps(plan)

    indeed_url = JobSearchService.build_indeed_url(command)
    return AIPlannerService._fallback_plan(command, indeed_url)


def _strip_risky_steps(plan: TaskPlan) -> TaskPlan:
    cleaned = []
    for step in plan.steps:
        if step.action in ("type", "click") and step.selector:
            sel = step.selector.lower()
            if any(token in sel for token in _GOOGLE_ONLY_SELECTORS):
                continue
        cleaned.append(step)
    if not cleaned:
        return plan
    return TaskPlan(
        intent=plan.intent,
        extraction_goal=plan.extraction_goal,
        steps=cleaned,
    )
