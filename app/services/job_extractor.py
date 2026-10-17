import logging
import re
from typing import Any

from app.schemas.job import JobListing

logger = logging.getLogger(__name__)

_INDEED_SCRIPT = """
() => {
  const results = [];
  const cards = document.querySelectorAll(
    'div.job_seen_beacon, div.result, div.slider_item, div[data-testid="job-card"]'
  );
  for (const card of cards) {
    if (results.length >= 20) break;
    const titleEl =
      card.querySelector('h2.jobTitle a span, h2 a span[title], a[data-jk] h2, .jobTitle');
    const companyEl =
      card.querySelector('[data-testid="company-name"], span.companyName, .company');
    const locEl =
      card.querySelector('[data-testid="text-location"], div.companyLocation, .location');
    const salaryEl = card.querySelector('[data-testid="attribute_snippet_testid"], .salary-snippet');
    const linkEl = card.querySelector('h2.jobTitle a, a[data-jk], h2 a');
    const title = (titleEl?.innerText || titleEl?.textContent || '').trim();
    const company = (companyEl?.innerText || companyEl?.textContent || '').trim();
    const location = (locEl?.innerText || locEl?.textContent || '').trim();
    const salary = (salaryEl?.innerText || salaryEl?.textContent || '').trim();
    let link = '';
    if (linkEl) {
      link = linkEl.href || '';
      if (!link && linkEl.getAttribute('data-jk')) {
        link = 'https://in.indeed.com/viewjob?jk=' + linkEl.getAttribute('data-jk');
      }
    }
    if (title.length < 3) continue;
    results.push({ title, company, location, salary, link });
  }
  return results;
}
"""

_GOOGLE_JOBS_SCRIPT = """
() => {
  const results = [];
  const nodes = document.querySelectorAll('div[data-ved], li, div[role="listitem"]');
  for (const node of nodes) {
    if (results.length >= 15) break;
    const text = (node.innerText || '').trim();
    if (text.length < 40 || text.length > 800) continue;
    if (!/developer|engineer|analyst|manager|job/i.test(text)) continue;
    const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
    if (lines.length < 2) continue;
    results.push({
      title: lines[0],
      company: lines[1] || '',
      location: lines.find(l => /chennai|bangalore|mumbai|delhi|hyderabad|india|remote/i.test(l)) || lines[2] || '',
      salary: lines.find(l => /₹|rs\\.|lpa|salary|\\$/i.test(l)) || '',
      link: ''
    });
  }
  return results;
}
"""

_JUNK_RE = re.compile(
    r"IP address|https?://|Time:\s*\d|T\d{2}:\d{2}Z|unusual traffic|captcha|google\.com/search",
    re.I,
)


def _valid_title(title: str) -> bool:
    if len(title) < 3 or len(title) > 200:
        return False
    if _JUNK_RE.search(title):
        return False
    return True


def _to_listings(rows: list[dict[str, Any]]) -> list[JobListing]:
    jobs: list[JobListing] = []
    seen: set[str] = set()
    for row in rows:
        title = str(row.get("title") or "").strip()
        if not _valid_title(title):
            continue
        company = str(row.get("company") or "").strip()[:120]
        if _JUNK_RE.search(company):
            continue
        location = str(row.get("location") or "").strip()[:120]
        key = f"{title}|{company}".lower()
        if key in seen:
            continue
        seen.add(key)
        jobs.append(
            JobListing(
                title=title,
                company=company,
                location=location,
                address=location,
                salary=str(row.get("salary") or "").strip()[:80],
                link=str(row.get("link") or "").strip()[:500],
                description=str(row.get("description") or "")[:500],
            )
        )
    return jobs[:15]


class JobExtractor:
    async def extract_from_page(self, page: Any, page_url: str) -> list[JobListing]:
        jobs: list[JobListing] = []
        try:
            if "indeed.com" in page_url:
                raw = await page.evaluate(_INDEED_SCRIPT)
                jobs = _to_listings(raw or [])
            elif "google.com" in page_url:
                raw = await page.evaluate(_GOOGLE_JOBS_SCRIPT)
                jobs = _to_listings(raw or [])
        except Exception as exc:
            logger.warning("Structured job extract failed: %s", exc)

        if len(jobs) >= 2:
            return jobs

        try:
            generic = await page.evaluate(_GOOGLE_JOBS_SCRIPT)
            jobs = _to_listings(generic or [])
        except Exception:
            pass
        return jobs
