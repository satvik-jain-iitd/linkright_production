"""Per-provider liveness probes — send a 1-token completion to verify a key.

Architecture constraints (HARD):
  - Each key is tested ONLY against its own provider.
  - No key is ever sent to a different provider's API.
  - Keys are never logged, printed, or included in any error message.
  - Test payloads use max_tokens=1 to minimize quota consumption.
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Optional

import httpx

from linkright.keys.catalogue import ProviderSpec


class LivenessStatus(str, Enum):
    ALIVE = "alive"
    RATE_LIMITED = "rate_limited"
    INVALID = "invalid"
    NO_KEY = "no_key"
    ERROR = "error"


STATUS_SYMBOLS = {
    LivenessStatus.ALIVE:        ("✓", "\033[32m"),   # green
    LivenessStatus.RATE_LIMITED: ("⚠", "\033[33m"),   # yellow
    LivenessStatus.INVALID:      ("✗", "\033[31m"),   # red
    LivenessStatus.NO_KEY:       ("—", "\033[2m"),    # dim
    LivenessStatus.ERROR:        ("?", "\033[33m"),   # yellow
}


def _openai_compat_probe(url: str, api_key: str, model: str) -> LivenessStatus:
    """Fire a 1-token chat completion to an OpenAI-compatible endpoint."""
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                },
            )
        if resp.status_code == 200:
            return LivenessStatus.ALIVE
        if resp.status_code == 429:
            return LivenessStatus.RATE_LIMITED
        if resp.status_code in (401, 403):
            return LivenessStatus.INVALID
        # 404 on model → key valid, model name changed (treat as alive)
        if resp.status_code == 404:
            return LivenessStatus.ALIVE
        return LivenessStatus.ERROR
    except Exception:
        return LivenessStatus.ERROR


def probe_key(provider: ProviderSpec, api_key: str,
              paired_value: Optional[str] = None) -> LivenessStatus:
    """Test a single key against its provider. Never logs the key value.

    `paired_value` is only used for Cloudflare (account_id).
    """
    key = provider.key

    if key == "groq":
        return _openai_compat_probe(
            "https://api.groq.com/openai/v1/chat/completions",
            api_key,
            os.environ.get("GROQ_MODEL_70B", "llama-3.1-8b-instant"),
        )

    if key == "cerebras":
        return _openai_compat_probe(
            "https://api.cerebras.ai/v1/chat/completions",
            api_key,
            os.environ.get("CEREBRAS_8B_MODEL", "llama3.1-8b"),
        )

    if key == "sambanova":
        return _openai_compat_probe(
            "https://api.sambanova.ai/v1/chat/completions",
            api_key,
            os.environ.get("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct"),
        )

    if key == "cloudflare":
        account_id = paired_value
        if not account_id:
            return LivenessStatus.ERROR
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
            "/ai/v1/chat/completions"
        )
        return _openai_compat_probe(
            url,
            api_key,
            os.environ.get("CLOUDFLARE_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
        )

    if key == "zai":
        return _openai_compat_probe(
            "https://api.z.ai/api/paas/v4/chat/completions",
            api_key,
            os.environ.get("ZHIPU_MODEL", "glm-4.5-flash"),
        )

    if key == "gemini":
        # Gemini uses a different API shape
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.0-flash-lite:generateContent?key={api_key}"
            )
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    url,
                    json={"contents": [{"parts": [{"text": "hi"}]}],
                          "generationConfig": {"maxOutputTokens": 1}},
                )
            if resp.status_code == 200:
                return LivenessStatus.ALIVE
            if resp.status_code == 429:
                return LivenessStatus.RATE_LIMITED
            if resp.status_code in (400, 401, 403):
                return LivenessStatus.INVALID
            if resp.status_code == 404:
                return LivenessStatus.ALIVE  # model changed, key valid
            return LivenessStatus.ERROR
        except Exception:
            return LivenessStatus.ERROR

    if key == "openrouter":
        return _openai_compat_probe(
            "https://openrouter.ai/api/v1/chat/completions",
            api_key,
            os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
        )

    return LivenessStatus.ERROR
