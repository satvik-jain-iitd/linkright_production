"""Google Gemini LLM provider."""

from __future__ import annotations

import httpx

from .base import LLMProvider, LLMResponse

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    async def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{BASE_URL}/models/{self.model_id}:generateContent",
                params={"key": self.api_key},
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"parts": [{"text": user}]}],
                    "generationConfig": {"temperature": temperature},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            return LLMResponse(
                text=text,
                input_tokens=usage.get("promptTokenCount", 0),
                output_tokens=usage.get("candidatesTokenCount", 0),
                model=self.model_id,
            )

    async def validate_key(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{BASE_URL}/models",
                    params={"key": self.api_key},
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
