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
        """Single-shot call. Rate-limit backoff is owned by rate_governor/router
        at the outer layer — NOT retried here. Compounded internal retries were
        the root cause of 20-min test-harness hangs on 2026-04-17.

        Kept: single retry on 413 (TPM payload), because a short wait can let
        the per-minute token window reset and succeed without escalating to
        provider rotation.
        """
        max_tokens = self._MAX_TOKENS_BY_MODEL.get(self.model_id, self._DEFAULT_MAX_TOKENS)
        async with httpx.AsyncClient(timeout=120) as client:
            for attempt in range(2):  # one initial + one 413-only retry
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
                if resp.status_code == 413 and attempt == 0:
                    # TPM payload — wait ~65s for the minute window to roll
                    logger.warning(
                        "Groq 413 TPM on %s — single 65s retry before surfacing",
                        self.model_id,
                    )
                    await asyncio.sleep(65)
                    continue
                # 429 and all other errors surface immediately so the router
                # can rotate to another provider without waiting.
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
        # Only reachable if second attempt also returned 413
        resp.raise_for_status()
        raise RuntimeError(f"Groq: TPM 413 persisted on {self.model_id}")

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
