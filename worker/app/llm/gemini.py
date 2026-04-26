"""Google Gemini LLM provider."""

from __future__ import annotations

import logging
import httpx

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    """Gemini provider with optional multi-key rotation.

    Gemini free tier is rate-limited at ~15 RPM per key. When multiple keys are
    configured (GEMINI_API_KEY_1/_2/_3), round-robin across them so we stack
    quota without paying for a higher tier. On 429 from one key, transparently
    try the next. Single-key usage still works (backward compat).
    """

    def __init__(
        self,
        api_key: str = "",
        model_id: str = "gemini-2.0-flash",
        api_keys: list[str] | None = None,
    ):
        if api_keys:
            self._keys = [k for k in api_keys if k]
        else:
            self._keys = [api_key] if api_key else []
        if not self._keys:
            raise ValueError("GeminiProvider: no api_key(s) provided")
        super().__init__(api_key=self._keys[0], model_id=model_id)
        self._key_idx = 0

    def _next_key(self) -> str:
        key = self._keys[self._key_idx]
        self._key_idx = (self._key_idx + 1) % len(self._keys)
        return key

    async def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        last_err: Exception | None = None
        tried = 0
        while tried < len(self._keys):
            tried += 1
            key = self._next_key()
            try:
                async with httpx.AsyncClient(timeout=45) as client:
                    resp = await client.post(
                        f"{BASE_URL}/models/{self.model_id}:generateContent",
                        params={"key": key},
                        json={
                            "systemInstruction": {"parts": [{"text": system}]},
                            "contents": [{"parts": [{"text": user}]}],
                            "generationConfig": {"temperature": temperature},
                        },
                    )
                    if resp.status_code == 429:
                        logger.info(
                            "Gemini key %d/%d hit 429 — trying next key",
                            tried, len(self._keys),
                        )
                        last_err = httpx.HTTPStatusError(
                            f"429 Too Many Requests (key {tried}/{len(self._keys)})",
                            request=resp.request, response=resp,
                        )
                        continue
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
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    last_err = e
                    continue
                raise
        # Every key 429'd — surface to caller so _FallbackLLM drops to Groq.
        if last_err:
            raise last_err
        raise RuntimeError("Gemini: all keys rate-limited")

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
