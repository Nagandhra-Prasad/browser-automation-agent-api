import logging
import re
from typing import Any

from app.schemas.job import JobListing
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

SYSTEM = """Extract real job listings from scraped web text. Return JSON:
{
  "jobs": [
    {
      "title": "",
      "company": "",
      "location": "",
      "address": "",
      "salary": "",
      "job_type": "",
      "posted": "",
      "link": "",
      "description": ""
    }
  ]
}
Rules:
- Only include actual job posts (title + company).
- Ignore error pages, IP addresses, URLs alone, timestamps, captcha messages.
- Use up to 15 jobs. If address is unknown, copy location."""

_JUNK_RE = re.compile(
    r"IP address|https?://|Time:\s*\d|T\d{2}:\d{2}Z|unusual traffic|captcha|\.com/search",
    re.I,
)


class JobParserService:
    def __init__(self) -> None:
        self._llm = LLMClient()

    @staticmethod
    def listings_from_rows(rows: list[dict[str, Any]]) -> list[JobListing]:
        out: list[JobListing] = []
        for row in rows:
            try:
                job = JobListing.model_validate(row)
                if JobParserService._is_valid(job):
                    out.append(job)
            except Exception:
                continue
        return out[:15]

    def parse(self, command: str, raw: dict[str, Any]) -> list[JobListing]:
        structured = raw.get("structured_jobs") or []
        if structured:
            listings = self.listings_from_rows(structured)
            if listings:
                return listings

        snippets = raw.get("text_snippets") or []
        text = "\n".join(str(s) for s in snippets[:40])
        if not text.strip():
            text = str(raw.get("page_title") or "")

        jobs = self._parse_with_llm(command, text)
        jobs = [j for j in jobs if self._is_valid(j)]
        if jobs:
            return jobs
        return [j for j in self._parse_heuristic(text) if self._is_valid(j)]

    @staticmethod
    def _is_valid(job: JobListing) -> bool:
        if len(job.title.strip()) < 3:
            return False
        if _JUNK_RE.search(job.title) or _JUNK_RE.search(job.company):
            return False
        if job.title.lower().startswith(("url:", "time:", "ip ")):
            return False
        return True

    def _parse_with_llm(self, command: str, text: str) -> list[JobListing]:
        if not self._llm.is_available or len(text) < 40:
            return []
        try:
            data = self._llm.chat_json(
                SYSTEM,
                f"User query: {command}\n\nPage text:\n{text[:14000]}",
            )
            rows = data.get("jobs") or []
            return [JobListing.model_validate(row) for row in rows[:15]]
        except Exception as exc:
            msg = str(exc)
            if "Connection" in msg or "connect" in msg.lower() or "not reachable" in msg.lower():
                logger.debug("Job LLM parse skipped (LLM unreachable)")
            else:
                logger.warning("Job LLM parse failed: %s", exc)
            return []

    @staticmethod
    def _parse_heuristic(text: str) -> list[JobListing]:
        jobs: list[JobListing] = []
        blocks = re.split(r"\n{2,}", text)
        for block in blocks:
            lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
            if len(lines) < 2:
                continue
            title = lines[0][:120]
            if len(title) < 5 or _JUNK_RE.search(title):
                continue
            company = lines[1][:80] if len(lines) > 1 else ""
            if _JUNK_RE.search(company):
                continue
            location = ""
            for ln in lines[2:6]:
                if re.search(r"\b(India|Chennai|Bangalore|Mumbai|Delhi|Remote|Hyderabad)\b", ln, re.I):
                    location = ln[:120]
                    break
            jobs.append(
                JobListing(
                    title=title,
                    company=company,
                    location=location,
                    address=location,
                    description=" ".join(lines[:4])[:500],
                )
            )
            if len(jobs) >= 10:
                break
        return jobs
