"""Groq LLM provider — ultra-fast inference."""

from __future__ import annotations

import httpx

from .base import LLMProvider, LLMResponse

BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(LLMProvider):
    async def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model_id,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return LLMResponse(
                text=choice,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                model=data.get("model", self.model_id),
            )

    async def validate_key(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{BASE_URL}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
