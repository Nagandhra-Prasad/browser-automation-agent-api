import logging
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from app.config import get_settings
from app.schemas.automation import PlanStep, TaskPlan
from app.services.job_extractor import JobExtractor
from app.services.job_search import JobSearchService

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("screenshots")

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_STEP_INTERACTION_TIMEOUT_MS = 8000


class BrowserAutomationService:
    def __init__(self, headless: bool | None = None) -> None:
        settings = get_settings()
        self._headless = headless if headless is not None else settings.playwright_headless
        self._timeout = settings.playwright_timeout_ms
        self._max_steps = settings.automation_max_steps
        self._job_extractor = JobExtractor()
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async def execute_plan(self, plan: TaskPlan, session_id: str, command: str = "") -> dict[str, Any]:
        step_log: list[dict[str, Any]] = []
        text_snippets: list[str] = []
        screenshots: list[str] = []
        structured_jobs: list[dict[str, Any]] = []
        page_title = ""
        page_url = ""

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self._headless)
            context = await browser.new_context(
                user_agent=_USER_AGENT,
                locale="en-IN",
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()
            page.set_default_timeout(self._timeout)

            steps = plan.steps[: self._max_steps]
            for index, step in enumerate(steps):
                step_result = await self._run_step(page, step, session_id, index, screenshots)
                step_log.append(
                    {
                        "step": index + 1,
                        "action": step.action,
                        "ok": step_result["ok"],
                        "error": step_result.get("error"),
                        "skipped": step_result.get("skipped", False),
                    }
                )

            page_title = await page.title()
            page_url = page.url

            structured_jobs = [
                j.model_dump()
                for j in await self._job_extractor.extract_from_page(page, page_url)
            ]

            if len(structured_jobs) < 2 and command:
                fallback_url = JobSearchService.build_indeed_url(command)
                if fallback_url not in page_url and "indeed.com" not in page_url:
                    try:
                        await page.goto(fallback_url, wait_until="domcontentloaded")
                        await page.wait_for_timeout(3500)
                        page_url = page.url
                        page_title = await page.title()
                        structured_jobs = [
                            j.model_dump()
                            for j in await self._job_extractor.extract_from_page(page, page_url)
                        ]
                        step_log.append({"step": "fallback", "action": "navigate_indeed", "ok": True})
                    except Exception as exc:
                        logger.warning("Indeed fallback failed: %s", exc)

            if hasattr(page, "_extracted"):
                text_snippets.extend(page._extracted)

            if not text_snippets and not structured_jobs:
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
            "structured_jobs": structured_jobs,
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
    ) -> dict[str, Any]:
        action = step.action
        try:
            if action == "navigate":
                url = step.value or ""
                if url and not url.startswith("http"):
                    url = f"https://{url}"
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(2500)
                return {"ok": True}

            if action == "wait":
                ms = int(step.value or "1000")
                await page.wait_for_timeout(min(ms, 10000))
                return {"ok": True}

            if action == "click":
                if not step.selector:
                    return {"ok": False, "error": "click requires selector"}
                if not await self._interact(page, step.selector, "click"):
                    return {
                        "ok": True,
                        "skipped": True,
                        "error": f"selector not found: {step.selector}",
                    }
                return {"ok": True}

            if action == "type":
                if not step.selector:
                    return {"ok": False, "error": "type requires selector"}
                if not await self._interact(page, step.selector, "type", step.value or ""):
                    return {
                        "ok": True,
                        "skipped": True,
                        "error": f"selector not found: {step.selector}",
                    }
                return {"ok": True}

            if action == "extract":
                selector = step.selector or "body"
                elements = await page.query_selector_all(selector)
                for el in elements[:15]:
                    text = (await el.inner_text()).strip()
                    if text:
                        if not hasattr(page, "_extracted"):
                            page._extracted = []
                        page._extracted.append(text)
                return {"ok": True}

            if action == "screenshot":
                path = SCREENSHOT_DIR / f"{session_id}_{index}.png"
                await page.screenshot(path=str(path), full_page=False)
                screenshots.append(str(path))
                return {"ok": True}

            return {"ok": False, "error": f"Unknown action: {action}"}
        except Exception as exc:
            logger.warning("Step %s (%s) failed: %s", index + 1, action, exc)
            return {"ok": False, "error": str(exc)}

    async def _interact(
        self,
        page: Any,
        selector: str,
        action: str,
        value: str = "",
    ) -> bool:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(
                state="visible",
                timeout=_STEP_INTERACTION_TIMEOUT_MS,
            )
        except Exception:
            logger.warning("Skipping %s — selector not found: %s", action, selector)
            return False

        if action == "click":
            await locator.click(timeout=_STEP_INTERACTION_TIMEOUT_MS)
        else:
            await locator.fill(value, timeout=_STEP_INTERACTION_TIMEOUT_MS)
        return True
