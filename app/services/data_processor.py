import re
from typing import Any

from app.services.job_parser import JobParserService


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

        structured = raw.get("structured_jobs") or []
        if structured:
            jobs = JobParserService.listings_from_rows(structured)
        else:
            jobs = JobParserService().parse(command, raw)

        return {
            "command": command,
            "page_title": raw.get("page_title"),
            "page_url": raw.get("page_url"),
            "items": cleaned,
            "item_count": len(cleaned),
            "jobs": [j.model_dump() for j in jobs],
            "job_count": len(jobs),
            "screenshots": raw.get("screenshots") or [],
            "step_log": raw.get("step_log") or [],
        }
