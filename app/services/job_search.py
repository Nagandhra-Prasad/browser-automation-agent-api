import re
from urllib.parse import quote_plus

_INDIAN_CITIES = (
    "Chennai",
    "Bangalore",
    "Bengaluru",
    "Mumbai",
    "Delhi",
    "Hyderabad",
    "Pune",
    "Kolkata",
    "Coimbatore",
    "Noida",
    "Gurgaon",
    "Gurugram",
    "Remote",
)


class JobSearchService:
    """Build job board URLs from natural language (no manual link from user)."""

    @staticmethod
    def parse_location(message: str) -> str:
        for city in _INDIAN_CITIES:
            if re.search(rf"\b{re.escape(city)}\b", message, re.I):
                return city if city != "Bengaluru" else "Bangalore"
        return ""

    @staticmethod
    def build_query(message: str) -> str:
        query = message.strip()
        if "job" not in query.lower():
            query = f"{query} jobs"
        return query

    @classmethod
    def build_indeed_url(cls, message: str) -> str:
        q = quote_plus(cls.build_query(message))
        location = cls.parse_location(message)
        if location:
            return f"https://in.indeed.com/jobs?q={q}&l={quote_plus(location)}"
        return f"https://in.indeed.com/jobs?q={q}"

    @classmethod
    def build_search_url(cls, message: str) -> str:
        """Primary target: Indeed India (more scrape-friendly than Google Jobs)."""
        return cls.build_indeed_url(message)

    @staticmethod
    def label_for_url(url: str) -> str:
        if "indeed.com" in url:
            return "Indeed India (auto)"
        if "google.com" in url:
            return "Google Jobs (auto)"
        return url

    @staticmethod
    def fallback_google_url(message: str) -> str:
        encoded = quote_plus(JobSearchService.build_query(message))
        return f"https://www.google.com/search?q={encoded}&ibp=htl;jobs"
