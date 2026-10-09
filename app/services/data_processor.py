import re
from typing import Any


class DataProcessor:
    @staticmethod
    def clean_text(text: str, max_len: int = 500) -> str:
        collapsed = re.sub(r"\s+", " ", text).strip()
        if len(collapsed) > max_len:
            return collapsed[: max_len - 3] + "..."
        return collapsed

    @classmethod
    def structure_extracted(cls, raw: dict[str, Any], command: str) -> dict[str, Any]:
        snippets = raw.get("text_snippets") or []
        cleaned = [cls.clean_text(s) for s in snippets if s and str(s).strip()]
        cleaned = [s for s in cleaned if len(s) > 20][:25]

        return {
            "command": command,
            "page_title": raw.get("page_title"),
            "page_url": raw.get("page_url"),
            "items": cleaned,
            "item_count": len(cleaned),
            "screenshots": raw.get("screenshots") or [],
            "step_log": raw.get("step_log") or [],
        }
