"""Groq LLM provider — ultra-fast inference."""

from __future__ import annotations

import asyncio
import logging

import httpx

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

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
        for attempt in range(4):
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
                if resp.status_code == 413:
                    # TPM limit exhausted — wait for next minute window and retry
                    wait = 65 * (attempt + 1)
                    logger.warning(
                        "Groq 413 TPM limit on %s — waiting %ds (attempt %d/4)",
                        self.model_id, wait, attempt + 1,
                    )
                    await asyncio.sleep(wait)
                    continue
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
        raise httpx.HTTPStatusError(
            "Groq 413 TPM limit persisted after 4 retries",
            request=resp.request,
            response=resp,
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
