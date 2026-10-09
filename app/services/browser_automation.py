import logging
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from app.config import get_settings
from app.schemas.automation import PlanStep, TaskPlan

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("screenshots")


class BrowserAutomationService:
    def __init__(self, headless: bool | None = None) -> None:
        settings = get_settings()
        self._headless = headless if headless is not None else settings.playwright_headless
        self._timeout = settings.playwright_timeout_ms
        self._max_steps = settings.automation_max_steps
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async def execute_plan(self, plan: TaskPlan, session_id: str) -> dict[str, Any]:
        step_log: list[dict[str, Any]] = []
        text_snippets: list[str] = []
        screenshots: list[str] = []
        page_title = ""
        page_url = ""

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self._headless)
            context = await browser.new_context()
            page = await context.new_page()
            page.set_default_timeout(self._timeout)

            steps = plan.steps[: self._max_steps]
            for index, step in enumerate(steps):
                try:
                    await self._run_step(page, step, session_id, index, screenshots)
                    step_log.append({"step": index + 1, "action": step.action, "ok": True})
                except Exception as exc:
                    logger.exception("Step %s failed: %s", index + 1, exc)
                    step_log.append(
                        {
                            "step": index + 1,
                            "action": step.action,
                            "ok": False,
                            "error": str(exc),
                        }
                    )

            if hasattr(page, "_extracted"):
                text_snippets.extend(page._extracted)

            page_title = await page.title()
            page_url = page.url

            if not text_snippets:
                body_text = await page.inner_text("body")
                for line in body_text.split("\n"):
                    line = line.strip()
                    if len(line) > 30:
                        text_snippets.append(line)
                text_snippets = text_snippets[:30]

            await browser.close()

        return {
            "page_title": page_title,
            "page_url": page_url,
            "text_snippets": text_snippets,
            "screenshots": screenshots,
            "step_log": step_log,
            "intent": plan.intent,
            "extraction_goal": plan.extraction_goal,
        }

    async def _run_step(
        self,
        page: Any,
        step: PlanStep,
        session_id: str,
        index: int,
        screenshots: list[str],
    ) -> None:
        action = step.action
        if action == "navigate":
            url = step.value or ""
            if url and not url.startswith("http"):
                url = f"https://{url}"
            await page.goto(url, wait_until="domcontentloaded")
            return

        if action == "wait":
            ms = int(step.value or "1000")
            await page.wait_for_timeout(min(ms, 10000))
            return

        if action == "click":
            if not step.selector:
                raise ValueError("click requires selector")
            await page.click(step.selector)
            return

        if action == "type":
            if not step.selector:
                raise ValueError("type requires selector")
            await page.fill(step.selector, step.value or "")
            return

        if action == "extract":
            selector = step.selector or "body"
            elements = await page.query_selector_all(selector)
            for el in elements[:15]:
                text = (await el.inner_text()).strip()
                if text:
                    # stored via caller reading page later; attach to page context
                    if not hasattr(page, "_extracted"):
                        page._extracted = []
                    page._extracted.append(text)
            if hasattr(page, "_extracted"):
                pass
            return

        if action == "screenshot":
            path = SCREENSHOT_DIR / f"{session_id}_{index}.png"
            await page.screenshot(path=str(path), full_page=False)
            screenshots.append(str(path))
            return

        raise ValueError(f"Unknown action: {action}")
