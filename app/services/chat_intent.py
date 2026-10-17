import re
from enum import Enum


class ChatIntent(str, Enum):
    GREETING = "greeting"
    HELP = "help"
    JOB_SEARCH = "job_search"
    SMALL_TALK = "small_talk"


_GREETINGS = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "hola",
        "good morning",
        "good evening",
        "good afternoon",
        "thanks",
        "thank you",
    }
)

_JOB_HINTS = re.compile(
    r"\b(job|jobs|hiring|career|vacancy|vacancies|developer|engineer|intern|opening|recruit)\b",
    re.I,
)


class ChatIntentService:
    def detect(self, message: str) -> ChatIntent:
        text = message.strip()
        lowered = text.lower()

        if lowered in _GREETINGS or re.fullmatch(r"hi[!.\s]*", lowered):
            return ChatIntent.GREETING

        if lowered in {"help", "?", "what can you do"} or "how do" in lowered and "work" in lowered:
            return ChatIntent.HELP

        if _JOB_HINTS.search(text):
            return ChatIntent.JOB_SEARCH

        if len(text) < 12:
            return ChatIntent.SMALL_TALK

        return ChatIntent.JOB_SEARCH

    @staticmethod
    def greeting_reply(name: str | None = None) -> str:
        who = f" {name}" if name else ""
        return (
            f"Hello{who}! I can search job listings for you.\n"
            'Try: "Find Java developer jobs in Chennai" or "Python jobs in Bangalore".\n'
            "I will pick a job site and show results in a table — no website link needed."
        )

    @staticmethod
    def help_reply() -> str:
        return (
            "I am a browser automation agent for job search.\n"
            "• Say hi to start a conversation.\n"
            "• Ask for jobs in natural language (role + city).\n"
            "• Results appear as a table: title, company, location, salary, etc.\n"
            "• Use **Users** in the menu to see registered users."
        )

    @staticmethod
    def small_talk_reply() -> str:
        return (
            "Tell me what jobs you want, for example:\n"
            '"Find React developer jobs in Mumbai" or "Data analyst openings in Delhi".'
        )
