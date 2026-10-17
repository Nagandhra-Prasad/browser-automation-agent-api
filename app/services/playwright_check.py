import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def chromium_install_hint() -> str:
    return (
        "Playwright browsers are not installed. From the API project folder run:\n"
        "  source .venv/bin/activate\n"
        "  python -m playwright install chromium\n"
        "(Browsers are stored in .pw-browsers/ in this project.)"
    )


def _is_chromium_ready_sync() -> bool:
    """Must run outside the asyncio event loop (use asyncio.to_thread)."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            exe = p.chromium.executable_path
            if not Path(exe).exists():
                logger.warning("Chromium executable missing: %s", exe)
                return False
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception as exc:
        logger.warning("Chromium not ready: %s", exc)
        return False


async def is_chromium_ready() -> bool:
    return await asyncio.to_thread(_is_chromium_ready_sync)
