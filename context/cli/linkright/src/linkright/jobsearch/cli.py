"""`linkright jobsearch` subcommand group.

Subcommands:
  evaluate --jd <path>      — 10-dim JD scorecard (persists to MongoDB)
  recommend [--top N]       — list top-N evaluations by score
  apply <jd_hash>           — mark an application as 'applied'
"""
from __future__ import annotations

import json
from pathlib import Path

import click


@click.group(name="jobsearch")
def jobsearch_group() -> None:
    """Pillar 2 — Job evaluation + matching."""


@jobsearch_group.command("evaluate")
@click.option("--jd", "jd_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Path to JD text/markdown file")
@click.option("--jd-url", default=None, help="Optional source URL for the JD")
@click.option("--no-persist", is_flag=True, help="Do not write to MongoDB / disk")
def evaluate(jd_path: Path, jd_url: str | None, no_persist: bool) -> None:
    """Run 10-dimension evaluation on a JD."""
    from .evaluator import evaluate_jd
    jd_text = jd_path.read_text()
    try:
        result = evaluate_jd(jd_text, persist=not no_persist, jd_url=jd_url)
    except RuntimeError as e:
        raise click.ClickException(str(e))
    click.echo(f"Grade: {result['grade']}  •  Score: {result['overall_score']}/100  "
               f"•  Recommendation: {result['recommendation']}")
    click.echo("")
    click.echo("Dimensions:")
    for name, score in result["dimensions"].items():
        reason = result["dimension_reasons"].get(name, "")[:80]
        click.echo(f"  {name:22s} {score:5.1f}  — {reason}")
    click.echo("")
    click.echo(f"Persisted: {result['persisted_to']}")


@jobsearch_group.command("recommend")
@click.option("--top", "top_n", default=5, type=int, help="How many evaluations to list")
def recommend(top_n: int) -> None:
    """List top-N evaluations by overall score (queries MongoDB)."""
    try:
        from ..db.mongo import get_db, ping
        if not ping():
            raise click.ClickException("MongoDB unreachable — run `linkright init`.")
        db = get_db()
        rows = list(db["evaluations"].find().sort("overall_score", -1).limit(top_n))
    except click.ClickException:
        raise
    except Exception as e:  # noqa: BLE001
        raise click.ClickException(f"Mongo query failed: {e}")
    if not rows:
        click.echo("No evaluations yet. Run `linkright jobsearch evaluate --jd <path>`.")
        return
    for i, r in enumerate(rows, 1):
        click.echo(f"{i}. [{r.get('grade', '?')}] {r.get('overall_score', 0):.1f}  "
                   f"{r.get('recommendation', '?'):9s}  jd={r.get('jd_hash', '')[:10]}  "
                   f"url={r.get('jd_url') or '-'}")


@jobsearch_group.command("apply")
@click.argument("jd_hash")
@click.option("--status", default="applied",
              type=click.Choice(["drafted", "applied", "responded", "interview", "offer", "rejected"]))
@click.option("--notes", default="")
def apply(jd_hash: str, status: str, notes: str) -> None:
    """Record / update an application row for a given JD."""
    from datetime import datetime, timezone
    from ..db.collections import Application
    try:
        from ..db.mongo import get_db, ping
        if not ping():
            raise click.ClickException("MongoDB unreachable — run `linkright init`.")
        db = get_db()
        existing = db["applications"].find_one({"jd_hash": jd_hash})
        if existing:
            db["applications"].update_one(
                {"_id": existing["_id"]},
                {"$set": {"status": status, "notes": notes,
                          "submitted_at": datetime.now(timezone.utc),
                          "updated_at": datetime.now(timezone.utc)}},
            )
            click.echo(f"Updated application for jd={jd_hash[:10]} → {status}")
        else:
            app = Application(jd_hash=jd_hash, status=status, notes=notes,
                              submitted_at=datetime.now(timezone.utc))
            res = db["applications"].insert_one(app.model_dump())
            click.echo(f"Created application {res.inserted_id} for jd={jd_hash[:10]} → {status}")
    except click.ClickException:
        raise
    except Exception as e:  # noqa: BLE001
        raise click.ClickException(f"Mongo write failed: {e}")
