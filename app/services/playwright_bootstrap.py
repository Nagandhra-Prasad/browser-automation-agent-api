import asyncio
import logging
import subprocess
import sys

from app.config import get_settings
from app.playwright_env import configure_playwright_env
from app.services.playwright_check import (
    _is_chromium_ready_sync,
    chromium_install_hint,
)

logger = logging.getLogger(__name__)


def _ensure_chromium_installed_sync() -> bool:
    settings = get_settings()
    path = configure_playwright_env(settings.playwright_browsers_path or None)

    if _is_chromium_ready_sync():
        logger.info("Playwright Chromium ready (%s)", path)
        return True

    if not settings.playwright_auto_install:
        logger.warning("Playwright Chromium missing. %s", chromium_install_hint())
        return False

    logger.info("Downloading Playwright Chromium to %s (one-time)…", path)
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("Playwright install failed: %s", exc.stderr or exc.stdout)
        return False

    ready = _is_chromium_ready_sync()
    if ready:
        logger.info("Playwright Chromium installed successfully")
    else:
        logger.error("Playwright install finished but Chromium still not launchable")
    return ready


async def ensure_chromium_installed() -> bool:
    return await asyncio.to_thread(_ensure_chromium_installed_sync)
