import os
from pathlib import Path

_CONFIGURED = False


def configure_playwright_env(custom_path: str | None = None) -> str:
    """Set PLAYWRIGHT_BROWSERS_PATH before Playwright is imported (project-local by default)."""
    global _CONFIGURED
    if _CONFIGURED and not custom_path:
        return os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")

    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        _CONFIGURED = True
        return os.environ["PLAYWRIGHT_BROWSERS_PATH"]

    root = Path(__file__).resolve().parent.parent
    path = Path(custom_path) if custom_path else root / ".pw-browsers"
    path.mkdir(parents=True, exist_ok=True)
    resolved = str(path.resolve())
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = resolved
    _CONFIGURED = True
    return resolved
