import json
import logging
import re
from typing import Any

import httpx
from openai import OpenAI

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
        raise


class LLMClient:
    """Unified chat client: Ollama (free/local), Groq, Gemini, or OpenAI."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.provider = self._settings.ai_provider.lower().strip()
        self._openai_compat: OpenAI | None = None
        self._configure()

    def _configure(self) -> None:
        if self.provider == "none":
            return

        if self.provider == "ollama":
            self._openai_compat = OpenAI(
                base_url=self._settings.ollama_base_url.rstrip("/"),
                api_key="ollama",
            )
            return

        if self.provider == "groq":
            if not self._settings.groq_api_key:
                logger.warning("AI_PROVIDER=groq but GROQ_API_KEY is empty")
                return
            self._openai_compat = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=self._settings.groq_api_key,
            )
            return

        if self.provider == "openai":
            if not self._settings.openai_api_key:
                logger.warning("AI_PROVIDER=openai but OPENAI_API_KEY is empty")
                return
            self._openai_compat = OpenAI(api_key=self._settings.openai_api_key)
            return

        if self.provider == "gemini":
            if not self._settings.gemini_api_key:
                logger.warning("AI_PROVIDER=gemini but GEMINI_API_KEY is empty")
            return

        logger.warning("Unknown AI_PROVIDER=%s; set to ollama, groq, gemini, openai, or none", self.provider)

    @property
    def is_available(self) -> bool:
        if self.provider == "none":
            return False
        if self.provider == "gemini":
            return bool(self._settings.gemini_api_key)
        return self._openai_compat is not None

    @property
    def model(self) -> str:
        s = self._settings
        if self.provider == "ollama":
            return s.ollama_model
        if self.provider == "groq":
            return s.groq_model
        if self.provider == "gemini":
            return s.gemini_model
        if self.provider == "openai":
            return s.openai_model
        return ""

    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        if not self.is_available:
            raise RuntimeError("LLM is not configured")

        if self.provider == "gemini":
            return self._gemini_chat(system, user, json_mode=json_mode)

        assert self._openai_compat is not None
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        if json_mode and self.provider in ("openai", "groq"):
            kwargs["response_format"] = {"type": "json_object"}

        response = self._openai_compat.chat.completions.create(**kwargs)
        return (response.choices[0].message.content or "").strip()

    def _gemini_chat(self, system: str, user: str, json_mode: bool = False) -> str:
        key = self._settings.gemini_api_key
        model = self._settings.gemini_model
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={key}"
        )
        prompt = user if not json_mode else f"{user}\n\nRespond with valid JSON only."
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        return parts[0].get("text", "").strip()

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        raw = self.chat(system, user, json_mode=True)
        return _extract_json_object(raw)
