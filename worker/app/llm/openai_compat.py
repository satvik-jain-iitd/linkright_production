"""Generic OpenAI-compatible LLM provider.

All providers that follow the OpenAI /chat/completions API format use this class.
Only the base_url differs.
"""

from __future__ import annotations

import httpx

from .base import LLMProvider, LLMResponse


class OpenAICompatProvider(LLMProvider):
    """Generic OpenAI-compatible provider with configurable base URL."""

    def __init__(self, api_key: str, model_id: str, base_url: str, extra_headers: dict | None = None):
        super().__init__(api_key=api_key, model_id=model_id)
        self.base_url = base_url.rstrip("/")
        self.extra_headers = extra_headers or {}

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }

    def _url(self) -> str:
        return f"{self.base_url}/chat/completions"

    async def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self._url(),
                headers=self._headers(),
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
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            return LLMResponse(
                text=content,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                model=data.get("model", self.model_id),
            )

    async def validate_key(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
