"""Pillar 4 CLI — plan / draft / schedule / performance."""
from __future__ import annotations

import json
from datetime import datetime

import click


@click.group(name="content")
def content_group() -> None:
    """Pillar 4 — Social content (plan, draft, schedule, performance)."""


@content_group.command("plan")
@click.option("--weeks", type=int, default=4, show_default=True)
@click.option("--theme", required=True, help="Overall theme / topic cluster.")
def plan_cmd(weeks: int, theme: str) -> None:
    """Generate an N-week content calendar."""
    from linkright.content.voice_matcher import extract_voice_profile
    from linkright.content.planner import plan_calendar
    voice = extract_voice_profile()
    plan = plan_calendar(weeks=weeks, theme=theme, voice=voice)
    click.echo(json.dumps({"theme": plan.get("theme"), "weeks": plan.get("weeks"),
                           "item_count": len(plan.get("items", []))}, indent=2))


@content_group.command("draft")
@click.option("--topic", required=True)
@click.option("--kind", type=click.Choice(["linkedin_post", "twitter_thread", "blog_outline"]),
              default="linkedin_post", show_default=True)
@click.option("--length", type=click.Choice(["short", "medium", "long"]), default="medium", show_default=True)
def draft_cmd(topic: str, kind: str, length: str) -> None:
    """Draft a piece of content."""
    from linkright.content.voice_matcher import extract_voice_profile
    from linkright.content.drafter import draft_content
    voice = extract_voice_profile()
    md = draft_content(topic=topic, kind=kind, voice=voice, length=length)
    click.echo(md)


@content_group.command("schedule")
@click.argument("content_id")
@click.option("--platform", required=True)
@click.option("--at", "at_iso", required=True, help="ISO8601 timestamp")
def schedule_cmd(content_id: str, platform: str, at_iso: str) -> None:
    """Mark a ContentItem as scheduled at a future time."""
    try:
        when = datetime.fromisoformat(at_iso.replace("Z", "+00:00"))
    except ValueError as e:
        raise click.ClickException(f"Bad --at: {e}")
    try:
        from bson import ObjectId
        from linkright.db.mongo import get_db
        db = get_db()
        q = {"_id": ObjectId(content_id)} if ObjectId.is_valid(content_id) else {"_id": content_id}
        r = db["content_items"].update_one(
            q,
            {"$set": {"scheduled_for": when, "platform": platform, "status": "scheduled"}},
        )
        click.echo(json.dumps({"matched": r.matched_count, "modified": r.modified_count}))
    except Exception as e:
        raise click.ClickException(f"Schedule failed: {e}")


@content_group.command("performance")
@click.option("--last", default="30d", show_default=True)
def performance_cmd(last: str) -> None:
    """Performance metrics (stub in v0.1 — no platform APIs wired)."""
    click.echo(f"performance metrics deferred; no platform APIs wired in v0.1 (window={last})")
