import json
import logging
import re
import time
from typing import Any

import httpx
from openai import OpenAI

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_OLLAMA_CACHE: dict[str, tuple[bool, float]] = {}
_OLLAMA_CACHE_TTL_SEC = 30.0


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


def ollama_server_root(ollama_base_url: str) -> str:
    return ollama_base_url.rstrip("/").removesuffix("/v1")


def ping_ollama(ollama_base_url: str, timeout_sec: float = 2.0) -> bool:
    root = ollama_server_root(ollama_base_url)
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            response = client.get(f"{root}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


def ollama_model_present(ollama_base_url: str, model: str) -> bool:
    root = ollama_server_root(ollama_base_url)
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{root}/api/tags")
            if response.status_code != 200:
                return False
            names = [m.get("name", "") for m in response.json().get("models", [])]
            prefix = model.split(":")[0]
            return any(n == model or n.startswith(f"{prefix}:") or n == prefix for n in names)
    except Exception:
        return False


def log_llm_startup_status() -> None:
    settings = get_settings()
    provider = settings.ai_provider.lower().strip()
    if provider == "none":
        logger.info("AI_PROVIDER=none — using rule-based planning only")
        return
    if provider == "groq":
        key = (settings.groq_api_key or "").strip()
        if key and not key.startswith("your-key"):
            logger.info("AI provider: groq (model %s)", settings.groq_model)
        else:
            logger.warning(
                "AI_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Add your key to .env from https://console.groq.com/keys"
            )
        return
    if provider == "ollama":
        url = settings.ollama_base_url
        if ping_ollama(url):
            if ollama_model_present(url, settings.ollama_model):
                logger.info(
                    "Ollama is running at %s (model %s)",
                    ollama_server_root(url),
                    settings.ollama_model,
                )
            else:
                logger.warning(
                    "Ollama is running but model '%s' may be missing. Run: ollama pull %s",
                    settings.ollama_model,
                    settings.ollama_model,
                )
        else:
            logger.warning(
                "Ollama is not reachable at %s. Start the Ollama app or run: ollama serve\n"
                "Then: ollama pull %s\n"
                "Or set AI_PROVIDER=none in .env to skip AI (browser automation still works).",
                ollama_server_root(url),
                settings.ollama_model,
            )
        return
    logger.info("AI provider: %s", provider)


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
                max_retries=0,
                timeout=60.0,
            )
            return

        if self.provider == "groq":
            key = (self._settings.groq_api_key or "").strip()
            if not key or key.startswith("your-key"):
                logger.warning(
                    "AI_PROVIDER=groq but GROQ_API_KEY is missing. "
                    "Paste your key from https://console.groq.com/keys into .env"
                )
                return
            self._openai_compat = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=key,
                max_retries=2,
                timeout=60.0,
            )
            return

        if self.provider == "openai":
            if not self._settings.openai_api_key:
                logger.warning("AI_PROVIDER=openai but OPENAI_API_KEY is empty")
                return
            self._openai_compat = OpenAI(
                api_key=self._settings.openai_api_key,
                max_retries=2,
                timeout=60.0,
            )
            return

        if self.provider == "gemini":
            if not self._settings.gemini_api_key:
                logger.warning("AI_PROVIDER=gemini but GEMINI_API_KEY is empty")
            return

        logger.warning("Unknown AI_PROVIDER=%s; set to ollama, groq, gemini, openai, or none", self.provider)

    def _ollama_reachable(self) -> bool:
        cache_key = self._settings.ollama_base_url
        now = time.monotonic()
        cached = _OLLAMA_CACHE.get(cache_key)
        if cached and now - cached[1] < _OLLAMA_CACHE_TTL_SEC:
            return cached[0]
        ok = ping_ollama(self._settings.ollama_base_url)
        _OLLAMA_CACHE[cache_key] = (ok, now)
        return ok

    @property
    def is_available(self) -> bool:
        if self.provider == "none":
            return False
        if self.provider == "gemini":
            return bool(self._settings.gemini_api_key)
        if self.provider == "groq":
            key = (self._settings.groq_api_key or "").strip()
            return bool(key) and not key.startswith("your-key") and self._openai_compat is not None
        if self.provider == "ollama":
            return self._openai_compat is not None and self._ollama_reachable()
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
            raise RuntimeError("LLM is not configured or not reachable")

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
