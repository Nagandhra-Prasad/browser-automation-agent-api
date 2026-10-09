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
- First step must be navigate to the website (or a search URL if appropriate).
- Use simple, stable CSS selectors when possible (input[name=...], button[type=submit], etc.).
- Prefer at most 12 steps.
- For job/search tasks, navigate to site then type in search box and extract listing text.
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
            logger.warning("AI planning failed, using fallback: %s", exc)
            return self._fallback_plan(command, website)

    @staticmethod
    def _fallback_plan(command: str, website: str) -> TaskPlan:
        return TaskPlan(
            intent=command,
            extraction_goal="Page title and visible text snippets related to the query",
            steps=[
                PlanStep(
                    action="navigate",
                    value=website,
                    description="Open target website",
                ),
                PlanStep(
                    action="wait",
                    value="2000",
                    description="Wait for page load",
                ),
                PlanStep(
                    action="extract",
                    selector="body",
                    description="Extract main page content",
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
            logger.warning("AI summarize failed: %s", exc)
            return f"Automation completed for: {command}"
