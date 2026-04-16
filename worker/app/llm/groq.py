"""Groq LLM provider — ultra-fast inference."""

from __future__ import annotations

import httpx

from .base import LLMProvider, LLMResponse

BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(LLMProvider):
    # Groq free tier TPM limits: 70B=12000, 8B=6000.
    # Keep input+max_tokens under the model's TPM limit.
    _MAX_TOKENS_BY_MODEL: dict[str, int] = {
        "llama-3.3-70b-versatile": 6000,   # 4739 input + 6000 = 10739 < 12000 TPM
        "llama-3.1-70b-versatile": 6000,
        "llama-3.1-8b-instant": 3500,      # ~1500 input + 3500 = 5000 < 6000 TPM
        "mixtral-8x7b-32768": 5000,
    }
    _DEFAULT_MAX_TOKENS = 4000

    async def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        max_tokens = self._MAX_TOKENS_BY_MODEL.get(self.model_id, self._DEFAULT_MAX_TOKENS)
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
                    "max_tokens": max_tokens,
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
