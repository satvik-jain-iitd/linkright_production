"""`linkright stories` — Pillar 3 Story Bank CRUD.

STAR-format career narratives that bridge resume bullets to interview prep.
Each story has Title + S/T/A/R + tags + JD-requirement linkages.

Commands:
  list                       List all stories (filterable by tag)
  add [--from-nugget Q]      Add new story (optionally pre-filled from a nugget)
  edit <id-or-prefix>        Edit an existing story interactively
  delete <id-or-prefix>      Delete a story (with confirmation)
  search <query>             Vector + text search across titles/bodies/tags

Aliases: ls→list, rm→delete, find→search.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from typing import Any, Optional

import click
from rich.console import Console
from rich.table import Table

from linkright.cli_aliases import AliasedGroup

console = Console()


# ── Group ────────────────────────────────────────────────────────────────

@click.group(cls=AliasedGroup, name="stories")
def stories_group() -> None:
    """Pillar 3 — STAR-format career story bank.

    \b
    Persistent narratives that bridge resume nuggets to interview prep.
    Each story has Title, Situation, Task, Action, Result, Tags, and
    JD-requirement linkages.

    \b
    Quick start:
      linkright stories add                       Interactive — fill all fields
      linkright stories add --from-nugget "AML"   Pre-fill from a resume nugget
      linkright stories list                       See all your stories
      linkright stories search "led migration"     Find by topic
    """


stories_group.add_aliases({
    "ls": "list",
    "rm": "delete",
    "find": "search",
})


# ── Helpers ──────────────────────────────────────────────────────────────

def _get_collection() -> Any:
    """Return the career_stories MongoDB collection or exit with helpful error."""
    from linkright.db.mongo import get_db, ping
    if not ping():
        click.echo(
            click.style(
                "MongoDB unreachable. Run `linkright init` first, "
                "or start mongod on localhost:27017.",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)
    return get_db()["career_stories"]


def _resolve_story(coll: Any, id_or_prefix: str, user_id: str = "local") -> Optional[dict]:
    """Look up a story by ObjectId or by short title prefix.

    Allows `linkright stories edit a1b2c3d4` instead of typing full ObjectId.
    Falls back to title-prefix match if string is not a valid ObjectId.
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
    except ImportError:
        ObjectId = None  # type: ignore
        InvalidId = ValueError  # type: ignore

    if ObjectId is not None:
        try:
            doc = coll.find_one({"_id": ObjectId(id_or_prefix), "user_id": user_id})
            if doc:
                return doc
        except (InvalidId, Exception):
            pass

    if len(id_or_prefix) >= 3:
        cursor = list(coll.find({
            "user_id": user_id,
            "title": {"$regex": f"^{re.escape(id_or_prefix)}", "$options": "i"},
        }).limit(2))
        if len(cursor) == 1:
            return cursor[0]
        if len(cursor) > 1:
            click.echo(
                f"Ambiguous prefix '{id_or_prefix}' matches {len(cursor)}+ stories. "
                "Use full title or ObjectId.",
                err=True,
            )
            sys.exit(1)
    return None


def _resolve_nugget(query: str) -> tuple[Optional[str], Optional[str]]:
    """Find a nugget matching `query`. Returns (text, id) or (None, None).

    Search order:
      1. MongoDB `nuggets` collection (regex on text)
      2. Local file ~/.linkright/profile/nuggets.jsonl
    """
    try:
        from linkright.db.mongo import get_db, ping
        if ping():
            coll = get_db()["nuggets"]
            doc = coll.find_one({
                "user_id": "local",
                "text": {"$regex": re.escape(query), "$options": "i"},
            })
            if doc:
                return doc.get("text"), str(doc.get("_id"))
    except Exception:
        pass

    try:
        from linkright.profile.pipeline import _profile_dir, load_nuggets
        nuggets = load_nuggets(_profile_dir())
        for n in nuggets:
            text = n.get("text") or n.get("nugget_text", "")
            if re.search(re.escape(query), text, re.IGNORECASE):
                return text, n.get("nugget_id") or str(n.get("nugget_index", ""))
    except Exception:
        pass

    return None, None


def _embed_story(title: str, situation: str, task: str, action: str, result: str) -> Optional[list[float]]:
    """Try to embed the combined story text via Oracle. Returns None on failure.

    No-op if Oracle env not set — vector search just falls back to text regex.
    """
    try:
        from linkright.llm.oracle import oracle_embed
        text = " ".join(filter(None, [title, situation, task, action, result]))
        vecs = oracle_embed([text])
        if vecs and vecs[0]:
            return vecs[0]
    except Exception:
        pass
    return None


def _print_hits(hits: list[dict]) -> None:
    for d in hits:
        title = d.get("title", "(untitled)")
        score = d.get("_score", 0.0)
        click.echo(f"\n{click.style(title, bold=True)}  (score={score:.2f})")
        if d.get("action"):
            click.echo(f"  Action: {d['action'][:120]}")
        if d.get("result"):
            click.echo(f"  Result: {d['result'][:120]}")
        if d.get("tags"):
            click.echo(f"  Tags:   {', '.join(d['tags'])}")


# ── Commands ─────────────────────────────────────────────────────────────

@stories_group.command("list")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--limit", type=int, default=50)
def list_cmd(tag: Optional[str], limit: int) -> None:
    """List all career stories (most-recent first)."""
    coll = _get_collection()
    query: dict = {"user_id": "local"}
    if tag:
        query["tags"] = tag

    docs = list(coll.find(query).sort("updated_at", -1).limit(limit))
    if not docs:
        msg = (
            f"No stories with tag '{tag}'."
            if tag
            else "No stories yet — run `linkright stories add` to create one."
        )
        click.echo(msg)
        return

    table = Table(title=f"Career Stories ({len(docs)})")
    table.add_column("ID", style="dim")
    table.add_column("Title", style="bold")
    table.add_column("Tags")
    table.add_column("Used")
    table.add_column("Last", style="dim")

    for d in docs:
        # First 8 hex chars of ObjectId (timestamp-based, more visually
        # distinguishable than tail-8). Title-prefix is the primary lookup
        # mechanism though — uniqueness enforced via Mongo index.
        story_id = str(d.get("_id", ""))[:8]
        title = d.get("title", "(untitled)")
        tag_list = d.get("tags", []) or []
        tags_str = ", ".join(tag_list[:3])
        if len(tag_list) > 3:
            tags_str += "…"
        used = str(d.get("use_count", 0))
        last = d.get("last_used_at")
        last_str = last.strftime("%Y-%m-%d") if isinstance(last, datetime) else "—"
        table.add_row(story_id, title, tags_str, used, last_str)

    console.print(table)


@stories_group.command("add")
@click.option("--from-nugget", "from_nugget", default=None,
              help="Pre-fill `result` field from a resume nugget (text query)")
@click.option("--title", default=None)
@click.option("--situation", default=None)
@click.option("--task", default=None)
@click.option("--action", default=None)
@click.option("--result", default=None)
@click.option("--tags", default=None, help="Comma-separated")
@click.option("--yes", is_flag=True,
              help="Skip interactive prompts (--title, --action, --result required)")
def add_cmd(
    from_nugget: Optional[str],
    title: Optional[str],
    situation: Optional[str],
    task: Optional[str],
    action: Optional[str],
    result: Optional[str],
    tags: Optional[str],
    yes: bool,
) -> None:
    """Add a new STAR-format career story.

    \b
    Three paths:
      linkright stories add                       Fully interactive
      linkright stories add --from-nugget "AML"   Pre-fill from a nugget
      linkright stories add --title "..." --action "..." --result "..." --yes
    """
    coll = _get_collection()

    nugget_id: Optional[str] = None
    if from_nugget:
        nugget_text, nugget_id = _resolve_nugget(from_nugget)
        if nugget_text:
            click.echo(f"Pre-filling `result` from nugget: {nugget_text[:80]}…")
            if not result:
                result = nugget_text
        else:
            # Distinguish "no profile at all" from "profile exists, no match".
            # Directory-level check (NOT nuggets.jsonl): in partial-create states
            # (PDF ingested but extraction failed mid-run), the file is absent
            # but inputs/resume.pdf is still there — telling the user to re-run
            # `profile create` would wipe their inputs via the default _wipe path.
            # ImportError must NOT be silently swallowed — that would mask a
            # broken install as "no profile found".
            from linkright.profile.pipeline import _profile_dir
            if not _profile_dir().exists():
                raise click.ClickException(
                    "No profile found. Run `linkright profile create -r resume.pdf` first.\n"
                    "Then `--from-nugget` can pre-fill stories from your career nuggets."
                )
            click.echo(f"  (No nugget matched '{from_nugget}' — proceeding with empty fields)")

    if not yes:
        title = title or click.prompt("Title (short label)", default="")
        situation = situation or click.prompt("Situation (context)", default="")
        task = task or click.prompt("Task (explicit ask)", default="")
        action = action or click.prompt("Action (what YOU did)", default="")
        result = result or click.prompt("Result (outcome + metrics)", default="")
        tags = tags or click.prompt("Tags (comma-separated)", default="")

    # Strip BEFORE validation — whitespace-only inputs ("   ") would otherwise
    # pass the `not <field>` check and write unreachable stories (can't be
    # found by title prefix because length<3 and trailing/leading spaces)
    title = (title or "").strip()
    situation = (situation or "").strip()
    task = (task or "").strip()
    action = (action or "").strip()
    result = (result or "").strip()

    if not title or not action or not result:
        raise click.ClickException(
            "title + action + result are required and must be non-empty (got: "
            f"title={'set' if title else 'EMPTY'}, "
            f"action={'set' if action else 'EMPTY'}, "
            f"result={'set' if result else 'EMPTY'})"
        )

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    now = datetime.now(timezone.utc)

    doc = {
        "user_id": "local",
        "title": title,
        "situation": situation,
        "task": task,
        "action": action,
        "result": result,
        "tags": tag_list,
        "jd_requirement_ids": [],
        "last_used_at": None,
        "use_count": 0,
        "source_nugget_ids": [nugget_id] if nugget_id else [],
        "emb": _embed_story(title, situation, task, action, result),
        "created_at": now,
        "updated_at": now,
        "schema_version": 1,
    }

    try:
        insert = coll.insert_one(doc)
    except Exception as e:
        # DuplicateKeyError surfaces from MongoDB when the (user_id, title)
        # unique index rejects a re-add. Catch broadly because the exception
        # type lives in pymongo.errors which we don't always import here, and
        # the FakeCollection in tests raises a plain ValueError on dup.
        msg = str(e).lower()
        if "duplicate" in msg or "e11000" in msg:
            raise click.ClickException(
                f"A story titled '{title}' already exists. "
                "Use `linkright stories edit \"<title>\"` to update it, "
                "or pick a different title.",
            )
        raise
    click.echo(click.style(f"✓ Story saved: {insert.inserted_id}", fg="green"))


@stories_group.command("edit")
@click.argument("story_id")
def edit_cmd(story_id: str) -> None:
    """Edit a story interactively. Pass ObjectId or unique title prefix."""
    coll = _get_collection()
    doc = _resolve_story(coll, story_id)
    if not doc:
        raise click.ClickException(f"Story not found: {story_id}")

    click.echo(f"Editing: {doc.get('title', '(untitled)')}")
    click.echo("Press Enter to keep existing value.\n")

    fields: list[tuple[str, str]] = [
        ("title", "Title"),
        ("situation", "Situation"),
        ("task", "Task"),
        ("action", "Action"),
        ("result", "Result"),
    ]
    updates: dict = {}
    for key, label in fields:
        current = doc.get(key, "") or ""
        new = click.prompt(label, default=current, show_default=True)
        # Strip — same guard as add_cmd, AR round-2 catch. Without strip, a user
        # who types whitespace at the prompt would corrupt the document
        # (whitespace-only title becomes unreachable by prefix; passes the
        # existing falsy check but fails practical usability).
        new = (new or "").strip()
        if new != current:
            updates[key] = new

    current_tags = ", ".join(doc.get("tags", []) or [])
    new_tags_raw = click.prompt("Tags (comma-separated)", default=current_tags)
    new_tags = [t.strip() for t in new_tags_raw.split(",") if t.strip()]
    if new_tags != (doc.get("tags", []) or []):
        updates["tags"] = new_tags

    # Required fields must remain non-empty after edit. If user cleared title /
    # action / result, refuse the edit rather than corrupt the doc.
    for required_key in ("title", "action", "result"):
        merged_value = updates.get(required_key, doc.get(required_key, ""))
        if not (merged_value or "").strip():
            raise click.ClickException(
                f"`{required_key}` cannot be empty. Use `linkright stories delete` "
                "if you want to remove this story."
            )

    if not updates:
        click.echo("No changes.")
        return

    # Re-embed if any STAR field changed
    if any(k in updates for k in ("title", "situation", "task", "action", "result")):
        merged = {**doc, **updates}
        new_emb = _embed_story(
            merged.get("title", ""), merged.get("situation", "") or "",
            merged.get("task", "") or "", merged.get("action", ""), merged.get("result", ""),
        )
        if new_emb is not None:
            updates["emb"] = new_emb

    updates["updated_at"] = datetime.now(timezone.utc)
    coll.update_one({"_id": doc["_id"]}, {"$set": updates})
    field_count = len([k for k in updates if k != "updated_at"])
    click.echo(click.style(f"✓ Updated {field_count} fields", fg="green"))


@stories_group.command("delete")
@click.argument("story_id")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def delete_cmd(story_id: str, yes: bool) -> None:
    """Delete a story. Pass ObjectId or unique title prefix."""
    coll = _get_collection()
    doc = _resolve_story(coll, story_id)
    if not doc:
        raise click.ClickException(f"Story not found: {story_id}")

    title = doc.get("title", "(untitled)")
    if not yes:
        if not click.confirm(f"Delete story '{title}'? This cannot be undone."):
            click.echo("Cancelled.")
            return

    coll.delete_one({"_id": doc["_id"]})
    click.echo(click.style(f"✓ Deleted: {title}", fg="red"))


@stories_group.command("search")
@click.argument("query")
@click.option("--limit", type=int, default=10)
def search_cmd(query: str, limit: int) -> None:
    """Search stories by text/tags (vector if available, else regex)."""
    coll = _get_collection()

    # Try vector search first (gracefully degrades if Oracle / vector_search
    # unavailable; broad except covers ImportError + OracleUnavailable + any
    # network/protocol exception from the embedder)
    try:
        from linkright.llm.oracle import oracle_embed
        from linkright.db.vector_search import vector_search
        vecs = oracle_embed([query])
        if vecs and vecs[0]:
            hits = vector_search(
                coll, query_vec=vecs[0], emb_field="emb", k=limit,
                filter_={"user_id": "local"},
            )
            if hits:
                _print_hits(hits)
                return
    except Exception:
        pass

    # Text fallback — regex on title/action/result/tags
    terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
    if not terms:
        click.echo("Query too short (need ≥3-char terms).", err=True)
        return
    regex = "|".join(re.escape(t) for t in terms[:10])
    cursor = coll.find({
        "user_id": "local",
        "$or": [
            {"title": {"$regex": regex, "$options": "i"}},
            {"action": {"$regex": regex, "$options": "i"}},
            {"result": {"$regex": regex, "$options": "i"}},
            {"tags": {"$regex": regex, "$options": "i"}},
        ],
    }).limit(limit)
    docs = list(cursor)
    if not docs:
        click.echo(f"No stories matching '{query}'.")
        return
    _print_hits([{**d, "_score": d.get("_score", 0.5)} for d in docs])
