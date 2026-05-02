"""Content drafter — topic + kind + voice → markdown draft."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from linkright.config import Config
from linkright.db.collections import ContentItem
from linkright.llm.direct import chat_with_fallback, LLMError

try:
    from linkright.llm.oracle import oracle_rewrite, OracleUnavailable
except Exception:  # pragma: no cover
    oracle_rewrite = None
    OracleUnavailable = Exception


_LENGTH_CHAR_TARGETS = {"short": 600, "medium": 1200, "long": 2000}


def _slugify(s: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:limit] or "draft"


def _voice_block(voice: dict) -> str:
    return (
        "VOICE PROFILE:\n"
        f"- Tone adjectives: {', '.join(voice.get('tone_adjectives', []))}\n"
        f"- Hook style: {voice.get('hook_style')}\n"
        f"- Avg sentence length (words): {voice.get('sentence_length_mean')}\n"
        f"- Exclamation ratio: {voice.get('exclamation_ratio')}\n"
        f"- Question ratio: {voice.get('question_ratio')}\n"
        f"- Avoid: {', '.join(voice.get('avoid_list', []))}\n"
    )


def _system_for(kind: str, voice: dict, length: str) -> str:
    target = _LENGTH_CHAR_TARGETS.get(length, 1200)
    base = _voice_block(voice)
    if kind == "linkedin_post":
        return (
            base
            + f"\nWrite a LinkedIn post of approximately {target} characters. "
            "Structure: scroll-stopping hook line, blank line, 3-4 short paragraphs, "
            "concrete example, one-line CTA. No hashtags spam (max 3). Return markdown."
        )
    if kind == "twitter_thread":
        return (
            base
            + "\nWrite a Twitter/X thread of 5-8 tweets. Each tweet MUST be <= 280 chars. "
            "Format the output as a markdown numbered list, one tweet per item. "
            "Tweet 1 is the hook; last tweet is the CTA."
        )
    if kind == "blog_outline":
        return (
            base
            + "\nWrite a blog post outline: H1 title, 1-sentence thesis, "
            "then 4-6 H2 sections each with 2-3 bullet sub-points. Markdown."
        )
    return base + "\nWrite a short piece in markdown."


def draft_content(topic: str, kind: str, voice: dict, length: str = "medium") -> str:
    """Generate a draft, normalize via Oracle if available, persist, return markdown."""
    system = _system_for(kind, voice, length)
    user = f"Topic: {topic}"
    try:
        draft, _usage = chat_with_fallback(system, user, temperature=0.6, max_tokens=2500)
    except LLMError as e:
        draft = f"# Draft failed\n\nLLM error: {e}\n\nTopic: {topic}"

    # Optional Oracle tone pass (free, local gemma3:1b) — best-effort
    if oracle_rewrite is not None and kind == "linkedin_post":
        try:
            resp = oracle_rewrite(
                user=f"Lightly tighten this draft while keeping its voice intact. Return only the rewrite.\n\n{draft}",
                system="You are a concise editor. Do not change the meaning.",
                temperature=0.2,
            )
            if resp.text and len(resp.text) > 100:
                draft = resp.text
        except OracleUnavailable:
            pass
        except Exception:
            pass

    _persist(topic=topic, kind=kind, draft=draft)
    return draft


def _persist(topic: str, kind: str, draft: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(topic)
    run_dir = Config.load().runs_dir() / ts / "drafts"
    run_dir.mkdir(parents=True, exist_ok=True)
    out_file = run_dir / f"{kind}-{slug}.md"
    out_file.write_text(draft, encoding="utf-8")

    ci = ContentItem(kind=kind, topic=topic, draft=draft, status="draft")
    try:
        from linkright.db.mongo import get_db
        get_db()["content_items"].insert_one(ci.model_dump())
    except Exception:
        pass
