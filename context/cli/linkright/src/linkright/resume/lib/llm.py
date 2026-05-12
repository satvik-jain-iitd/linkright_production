"""Compatibility shim — re-exports from linkright.llm.direct.

The resume pipeline (ported from e2e_diagnostic_run/run_pipeline.py) imports
`from lib import llm` and then calls `llm.groq_chat`, `llm.gemini_chat_best`,
`llm.chat_with_fallback`, `llm.LLMError`, etc. The canonical source lives at
linkright.llm.direct; this shim prevents code duplication.
"""
from ...llm.direct import *  # noqa: F401,F403
from ...llm.direct import (  # re-export common handles explicitly
    LLMError,
    chat_with_fallback,
    groq_chat,
    gemini_chat,
    gemini_chat_best,
    gemini_chat_json,
    cerebras_chat,
    cerebras_8b_chat,
    cerebras_qwen_chat,
    openrouter_chat,
    extract_json,
    subst,
)
