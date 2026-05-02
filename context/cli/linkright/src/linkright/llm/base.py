"""LLM provider interface shared across direct, agent (MCP/file), and Oracle modes.

Synchronous by design — CLI doesn't need async concurrency, and sync code is
easier to reason about for a single-user local tool.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    """Normalized LLM response shape.

    Produced by direct-mode calls, Oracle calls, and (post-parse) agent-mode
    file-protocol responses. MCP tool calls in agent mode return structured
    Pydantic results directly, bypassing this.
    """
    text: str
    provider: str          # "groq" | "gemini_flash_lite" | "oracle" | "cerebras" | "openrouter" | "agent_mcp" | "agent_file"
    model: str
    latency_s: float = 0.0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: float = 0.0
    cost_inr: float = 0.0
    fallback_chain: list[str] = field(default_factory=list)

    @classmethod
    def from_usage(cls, text: str, usage: dict) -> "LLMResponse":
        """Construct from the `usage` dict that direct.py helpers return."""
        return cls(
            text=text,
            provider=usage.get("provider", "unknown"),
            model=usage.get("model", "unknown"),
            latency_s=float(usage.get("latency_s") or 0.0),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            fallback_chain=list(usage.get("fallback_chain") or []),
        )
