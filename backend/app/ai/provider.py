from __future__ import annotations

from pathlib import Path
from typing import Protocol

import httpx

from app.config import Settings, get_settings

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "triage.txt"


class TriageProvider(Protocol):
    async def complete(self, prompt: str) -> str:
        """Return a model response for the supplied prompt."""


class DisabledProvider:
    async def complete(self, prompt: str) -> str:
        raise RuntimeError("AI provider is disabled")


class OpenAICompatibleProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.ai_api_key:
            raise RuntimeError("AI_API_KEY is required for the configured provider")
        self.base_url = settings.ai_base_url.rstrip("/")
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model

    async def complete(self, prompt: str) -> str:
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            body = response.json()
            return body["choices"][0]["message"]["content"]


def get_triage_provider() -> TriageProvider:
    settings = get_settings()
    if settings.ai_provider.lower() in {"openai", "openai_compatible"}:
        try:
            return OpenAICompatibleProvider(settings)
        except RuntimeError:
            return DisabledProvider()
    return DisabledProvider()
