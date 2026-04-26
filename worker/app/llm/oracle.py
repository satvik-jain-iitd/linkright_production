"""Oracle ARM local LLM provider.

Routes rewrite calls to the Oracle backend's /lifeos/rewrite endpoint
(gemma3:1b via Ollama as of 2026-04-22). Used for Phase 5 bullet width
optimization and Phase 3.5a summary tweaking — replacing Groq for these phases.

If Oracle is unavailable, caller should fall back to Groq gracefully.

To update model: change REWRITE_MODEL / GENERATE_MODEL in oracle-backend/lifeos/local_llm.py
To disable: unset ORACLE_BACKEND_URL env var
"""
from __future__ import annotations

import httpx
import logging

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


# Default model name echoed in telemetry when Oracle's response doesn't carry one.
# Oracle backend returns the actual chosen model in the response "model" field —
# this is only the pre-response placeholder.
_DEFAULT_MODEL = "gemma3:1b"


class OracleProvider(LLMProvider):
    """Calls Oracle ARM /lifeos/rewrite (gemma3:1b) or /lifeos/generate (gemma3:1b)."""

    def __init__(self, base_url: str, secret: str, endpoint: str = "rewrite"):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.endpoint = endpoint  # "rewrite" or "generate"

    @property
    def model_id(self) -> str:
        return _DEFAULT_MODEL

    async def complete(self, system: str, user: str, temperature: float = 0.2) -> LLMResponse:
        url = f"{self.base_url}/lifeos/{self.endpoint}"
        payload = {"prompt": user, "system": system, "temperature": temperature}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self.secret}"},
            )
            resp.raise_for_status()
            data = resp.json()

        text = data.get("text", "")
        return LLMResponse(
            text=text,
            model=data.get("model", self.model_id),
            input_tokens=0,   # local model — no token billing
            output_tokens=0,
        )

    async def validate_key(self) -> bool:
        """Check Oracle backend is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"{self.base_url}/health",
                    headers={"Authorization": f"Bearer {self.secret}"},
                )
                return r.status_code == 200
        except Exception:
            return False
