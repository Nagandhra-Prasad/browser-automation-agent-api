import json
import logging
from typing import Any

from app.schemas.automation import PlanStep, TaskPlan
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a browser automation planner. Given a user command and target website URL,
output a JSON object with this exact shape:
{
  "intent": "short description of what the user wants",
  "extraction_goal": "what data to collect from the page",
  "steps": [
    {
      "action": "navigate|click|type|wait|extract|screenshot",
      "selector": "CSS selector or null for navigate/wait/screenshot",
      "value": "URL, text to type, or wait ms as string",
      "description": "why this step"
    }
  ]
}
Rules:
- First step must be navigate to the website URL provided (do not change domain).
- For indeed.com: ONLY use navigate, wait, extract on body — do NOT use input[name=q] or Google selectors.
- Never use input[name=q] unless the website is google.com.
- Prefer at most 8 steps.
- Return ONLY valid JSON, no markdown."""


class AIPlannerService:
    def __init__(self) -> None:
        self._llm = LLMClient()

    def plan_task(self, command: str, website: str) -> TaskPlan:
        if not self._llm.is_available:
            return self._fallback_plan(command, website)

        user_content = f"Command: {command}\nWebsite: {website}"
        try:
            data = self._llm.chat_json(SYSTEM_PROMPT, user_content)
            return TaskPlan.model_validate(data)
        except Exception as exc:
            msg = str(exc)
            if "Connection" in msg or "connect" in msg.lower():
                logger.info("AI planning skipped (LLM unreachable), using fallback plan")
            else:
                logger.warning("AI planning failed, using fallback: %s", exc)
            return self._fallback_plan(command, website)

    @staticmethod
    def _fallback_plan(command: str, website: str) -> TaskPlan:
        from app.services.job_search import JobSearchService

        target = website if "indeed.com" in website else JobSearchService.build_indeed_url(command)
        return TaskPlan(
            intent=command,
            extraction_goal="Job titles, companies, locations, and salaries from listings",
            steps=[
                PlanStep(
                    action="navigate",
                    value=target,
                    description="Open Indeed job search results",
                ),
                PlanStep(
                    action="wait",
                    value="4000",
                    description="Wait for listings to load",
                ),
                PlanStep(
                    action="extract",
                    selector="body",
                    description="Extract job listing text",
                ),
            ],
        )

    def summarize_results(self, command: str, extracted: dict[str, Any]) -> str:
        if not self._llm.is_available:
            items = extracted.get("items") or extracted.get("text_snippets") or []
            if isinstance(items, list) and items:
                return f"Found {len(items)} items for: {command}"
            return f"Automation completed for: {command}"

        try:
            return self._llm.chat(
                "Summarize extracted web data in 2-4 sentences for the user.",
                json.dumps({"command": command, "extracted": extracted}, default=str)[:12000],
                json_mode=False,
            )
        except Exception as exc:
            msg = str(exc)
            if "Connection" in msg or "connect" in msg.lower() or "not reachable" in msg.lower():
                logger.debug("AI summarize skipped (LLM unreachable)")
            else:
                logger.warning("AI summarize failed: %s", exc)
            return f"Automation completed for: {command}"
