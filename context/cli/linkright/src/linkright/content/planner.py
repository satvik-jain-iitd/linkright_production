"""Content-calendar planner. N-weeks × content-items JSON plan, persisted to Mongo."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from linkright.config import Config
from linkright.db.collections import ContentCalendar, ContentItem
from linkright.llm.direct import gemini_chat_json, LLMError


_KINDS = ["linkedin_post", "twitter_thread", "blog_outline"]


def _voice_summary(voice: dict) -> str:
    return (
        f"tone={', '.join(voice.get('tone_adjectives', []))}; "
        f"hook_style={voice.get('hook_style')}; "
        f"avg_sentence_len={voice.get('sentence_length_mean')}; "
        f"avoid={', '.join(voice.get('avoid_list', [])[:5])}"
    )


def plan_calendar(weeks: int, theme: str, voice: dict) -> dict:
    """Generate a weekly content calendar, persist, return the plan dict."""
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "week": {"type": "integer"},
                        "day_of_week": {"type": "string"},
                        "kind": {"type": "string", "enum": _KINDS},
                        "topic": {"type": "string"},
                        "hook": {"type": "string"},
                        "angle": {"type": "string"},
                    },
                    "required": ["week", "day_of_week", "kind", "topic", "hook", "angle"],
                },
            }
        },
        "required": ["items"],
    }
    system = (
        "You are a content-calendar planner for a solo operator. "
        "Produce 3 posts/week mixing LinkedIn posts, one Twitter thread/week, "
        "and one blog outline per two weeks. Respect the writer's voice."
    )
    user = (
        f"Theme: {theme}\nWeeks: {weeks}\nVoice: {_voice_summary(voice)}\n"
        "Produce a concrete plan. Each hook must be a real opening line."
    )
    plan: dict[str, Any] = {"theme": theme, "weeks": weeks, "items": []}
    try:
        raw, _ = gemini_chat_json(system, user, schema, temperature=0.4, max_output_tokens=4000)
        plan = {"theme": theme, "weeks": weeks, **json.loads(raw)}
    except (LLMError, ValueError, Exception) as e:
        plan["error"] = f"planner fell back to empty plan: {e}"

    _persist(plan)
    return plan


def _persist(plan: dict) -> None:
    """Persist ContentCalendar + placeholder ContentItem docs; disk fallback if Mongo down."""
    items_ids: list[str] = []
    items_docs: list[dict] = []
    for it in plan.get("items", []):
        ci = ContentItem(
            kind=it.get("kind", "linkedin_post"),
            topic=it.get("topic", ""),
            draft=f"[placeholder] hook: {it.get('hook','')}  angle: {it.get('angle','')}",
            status="draft",
        )
        items_docs.append(ci.model_dump())
    cal = ContentCalendar(theme=plan.get("theme", ""), weeks=plan.get("weeks", 0), items=items_ids)

    try:
        from linkright.db.mongo import get_db
        db = get_db()
        if items_docs:
            res = db["content_items"].insert_many(items_docs)
            items_ids = [str(i) for i in res.inserted_ids]
        cal.items = items_ids
        db["content_calendar"].insert_one(cal.model_dump())
        return
    except Exception:
        pass

    # Disk fallback
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Config.load().runs_dir() / ts / "content"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "calendar.json").write_text(json.dumps(plan, indent=2, default=str))
