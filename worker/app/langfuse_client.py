"""Langfuse client singleton for LLM observability.

Provides get_langfuse() for traces/generations and get_prompt() for
versioned prompt fetching from Langfuse registry with local fallback.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_client = None
_enabled: Optional[bool] = None


def is_enabled() -> bool:
    """Check if Langfuse is configured (keys present in env)."""
    global _enabled
    if _enabled is None:
        _enabled = bool(
            os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")
        )
        if not _enabled:
            logger.info("langfuse: disabled (LANGFUSE_SECRET_KEY/PUBLIC_KEY not set)")
    return _enabled


def get_langfuse():
    """Return singleton Langfuse client. Returns None if not configured."""
    global _client
    if not is_enabled():
        return None
    if _client is None:
        from langfuse import Langfuse
        _client = Langfuse()
        logger.info("langfuse: client initialized")
    return _client


def get_prompt(name: str, fallback: str, cache_ttl: int = 300) -> tuple[str, str]:
    """Fetch prompt from Langfuse registry with local fallback.

    Returns (prompt_text, version_string).
    If Langfuse is disabled or fetch fails, returns (fallback, "local").
    """
    lf = get_langfuse()
    if lf is None:
        return fallback, "local"
    try:
        prompt = lf.get_prompt(name, cache_ttl_seconds=cache_ttl)
        return prompt.compile(), str(prompt.version)
    except Exception as exc:
        logger.warning("langfuse: failed to fetch prompt '%s': %s", name, exc)
        return fallback, "local-fallback"


def trace_generation(
    trace_name: str,
    generation_name: str,
    model: str,
    system_prompt: str,
    user_input: str,
    output: str,
    user_id: str = "",
    metadata: dict | None = None,
    usage: dict | None = None,
    prompt_version: str = "",
) -> None:
    """Log an LLM generation to Langfuse. No-op if disabled."""
    lf = get_langfuse()
    if lf is None:
        return
    try:
        trace = lf.trace(
            name=trace_name,
            user_id=user_id or None,
            metadata=metadata or {},
        )
        gen = trace.generation(
            name=generation_name,
            model=model,
            input={"system": system_prompt, "user": user_input},
            output=output,
            usage=usage or {},
            metadata={"prompt_version": prompt_version} if prompt_version else {},
        )
        gen.end()
    except Exception as exc:
        logger.warning("langfuse: trace_generation failed: %s", exc)


def flush() -> None:
    """Flush pending Langfuse events. Call before process exit."""
    lf = get_langfuse()
    if lf is not None:
        try:
            lf.flush()
        except Exception:
            pass
