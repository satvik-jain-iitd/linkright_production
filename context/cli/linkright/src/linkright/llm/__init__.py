"""LinkRight LLM layer — three modes: direct, agent (MCP/file), Oracle.

Default routing philosophy (per plan + user's Local LLM First memory):
  - Short-form rewrite / condense → Oracle gemma3:1b (free, self-hosted)
  - Embedding                      → Oracle nomic-embed-text (768-dim)
  - Structured JSON reasoning      → Gemini Flash Lite (cheapest tier)
  - Fallback cascade               → Groq 70B → Cerebras → OpenRouter

Agent mode (MCP server) delegates LLM calls back to the host agent (Claude Code /
Cursor / Gemini CLI) — cost to us = ₹0. See mcp.py (to be ported in next phase).
"""
from __future__ import annotations

from .base import LLMResponse
from .oracle import (
    OracleUnavailable,
    oracle_embed,
    oracle_generate,
    oracle_health,
    oracle_rewrite,
)

# Re-export the tested iter-08 direct-mode helpers under a stable name.
from . import direct

__all__ = [
    "LLMResponse",
    "OracleUnavailable",
    "oracle_embed",
    "oracle_generate",
    "oracle_health",
    "oracle_rewrite",
    "direct",
]
