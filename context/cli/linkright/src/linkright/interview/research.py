"""Company research digest — LLM-generated (not live-crawled)."""
from __future__ import annotations

import json
from typing import Any

from linkright.llm.direct import gemini_chat_json, LLMError


_RESEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "news_snippets": {"type": "array", "items": {"type": "string"}},
        "culture_signals": {"type": "array", "items": {"type": "string"}},
        "interview_process": {"type": "array", "items": {"type": "string"}},
        "likely_interviewer_archetypes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["news_snippets", "culture_signals", "interview_process"],
}

_SYSTEM = (
    "You are an interview-prep researcher. Produce a concise JSON digest for a candidate "
    "about to interview. Use your best general knowledge; do NOT fabricate specific dated news. "
    "Prefer evergreen signals (product, values, known interview style)."
)


def research_company(company: str, role: str) -> dict[str, Any]:
    """Return a structured research digest for `company` / `role`.

    Always includes a `sources_disclaimer` key noting that this is LLM-generated
    from general knowledge, not a live web crawl.
    """
    user = (
        f"Company: {company}\nRole: {role}\n\n"
        "Produce 3-5 entries per field:\n"
        "- news_snippets: recent/notable milestones or public product moves (evergreen ok)\n"
        "- culture_signals: values, working style, public reputation signals\n"
        "- interview_process: typical stages + what each stage evaluates\n"
        "- likely_interviewer_archetypes: who the candidate will likely meet"
    )
    digest: dict[str, Any]
    try:
        text, usage = gemini_chat_json(_SYSTEM, user, response_schema=_RESEARCH_SCHEMA, max_output_tokens=2000)
        digest = json.loads(text)
        digest["_llm"] = {"provider": usage.get("provider"), "model": usage.get("model")}
    except (LLMError, json.JSONDecodeError, KeyError) as e:
        digest = {
            "news_snippets": [],
            "culture_signals": [],
            "interview_process": [],
            "likely_interviewer_archetypes": [],
            "_error": f"research unavailable: {type(e).__name__}: {str(e)[:200]}",
        }
    digest["sources_disclaimer"] = (
        "This digest is LLM-generated from general training data. It is NOT a live web crawl. "
        "Verify time-sensitive facts (funding, leadership, recent launches) on the company site before the interview."
    )
    return digest
