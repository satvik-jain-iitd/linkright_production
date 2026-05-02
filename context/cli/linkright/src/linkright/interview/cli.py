"""Pillar 3 CLI — `linkright interview {schedule,prep,mock,debrief}`."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from linkright.config import Config
from linkright.db.collections import Interview, UserContext


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _runs_dir(cfg: Config) -> Path:
    d = cfg.runs_dir() / _now_stamp()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _mongo_ok() -> bool:
    try:
        from linkright.db.mongo import ping
        return ping()
    except Exception:
        return False


def _get_interview(interview_id: str) -> Optional[dict]:
    if not _mongo_ok():
        return None
    from linkright.db.mongo import get_db
    from bson import ObjectId
    try:
        return get_db()["interviews"].find_one({"_id": ObjectId(interview_id)})
    except Exception:
        return None


@click.group("interview")
def interview_group() -> None:
    """Pillar 3 — Interview prep + mock sessions."""


@interview_group.command("schedule")
@click.option("--company", required=True)
@click.option("--role", required=True)
@click.option("--date", "date_iso", default=None, help="ISO 8601 datetime")
@click.option("--stage", default="loop", type=click.Choice(["phone", "loop", "onsite", "hm"]))
def schedule(company: str, role: str, date_iso: Optional[str], stage: str) -> None:
    """Create an Interview record. Prints the id."""
    cfg = Config.load()
    dt = None
    if date_iso:
        try:
            dt = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
        except ValueError:
            click.echo(f"⚠ bad --date (ISO8601 expected): {date_iso}", err=True)
    iv = Interview(user_id=cfg.user_id, company=company, role=role, date=dt, stage=stage)
    if _mongo_ok():
        from linkright.db.mongo import get_db
        res = get_db()["interviews"].insert_one(iv.model_dump())
        click.echo(str(res.inserted_id))
    else:
        # Disk fallback
        out = _runs_dir(cfg) / "interview.json"
        out.write_text(json.dumps(iv.model_dump(), default=str, indent=2))
        click.echo(f"mongo-unavailable:{out}")


@interview_group.command("prep")
@click.argument("interview_id")
@click.option("--jd-file", type=click.Path(exists=True), default=None)
@click.option("-n", "n_questions", default=10, show_default=True)
def prep(interview_id: str, jd_file: Optional[str], n_questions: int) -> None:
    """Run research + predict_questions + retrieve_stars. Writes prep-packet.md."""
    from .research import research_company
    from .question_predictor import predict_questions, persist_questions
    from .star_retriever import retrieve_stars
    from .scorecard import InterviewScorecard

    cfg = Config.load()
    iv = _get_interview(interview_id) or {}
    company = iv.get("company", "Unknown")
    role = iv.get("role", "Unknown")
    stage = iv.get("stage", "loop")

    jd_text = Path(jd_file).read_text() if jd_file else ""

    click.echo(f"→ researching {company} / {role} ...")
    digest = research_company(company, role)

    click.echo(f"→ predicting {n_questions} questions ...")
    questions = predict_questions(jd_text or f"Role: {role} at {company}", company, role, stage, n=n_questions)
    written = persist_questions(interview_id, questions, user_id=cfg.user_id)

    click.echo("→ retrieving STAR stories ...")
    query = " ".join([role, company] + [q["question"] for q in questions[:3]])
    stars = retrieve_stars(query, k=5, user_id=cfg.user_id)

    # Scorecard
    sc = InterviewScorecard(run_id=f"prep-{interview_id}")
    sc.score({
        "questions": questions, "stars": stars, "research": digest,
        "jd_text": jd_text, "interview": iv, "confidence": 60.0,
    })

    run_dir = _runs_dir(cfg)
    md = _render_packet(company, role, stage, digest, questions, stars)
    (run_dir / "prep-packet.md").write_text(md)
    sc.write(run_dir)
    click.echo(f"\n✓ prep packet → {run_dir/'prep-packet.md'}")
    click.echo(f"  scorecard   → {run_dir/'scorecard.md'} ({sc.overall_grade} {round(sc.overall_score,1)}/100)")
    click.echo(f"  mongo:      questions_persisted={written}")


@interview_group.command("mock")
@click.argument("interview_id")
def mock(interview_id: str) -> None:
    """Mock session (interactive mode runs via MCP)."""
    click.echo(f"[mock {interview_id}] interactive mock session runs via agent MCP — "
               "start `linkright mcp serve` in your agent client.")


@interview_group.command("debrief")
@click.argument("interview_id")
@click.option("--notes", required=True, help="Raw notes from the interview")
@click.option("--title", default=None)
def debrief(interview_id: str, notes: str, title: Optional[str]) -> None:
    """Capture post-interview notes; append as a user_context story."""
    cfg = Config.load()
    t = title or f"Interview debrief {interview_id}"
    story = UserContext(
        user_id=cfg.user_id, kind="story", title=t, body=notes,
        tags=["debrief", f"interview:{interview_id}"],
    )
    if _mongo_ok():
        from linkright.db.mongo import get_db
        res = get_db()["user_context"].insert_one(story.model_dump())
        # update the interview notes field too
        try:
            from bson import ObjectId
            get_db()["interviews"].update_one(
                {"_id": ObjectId(interview_id)},
                {"$set": {"notes": notes, "updated_at": datetime.now(timezone.utc)}},
            )
        except Exception:
            pass
        click.echo(f"✓ debrief stored → user_context {res.inserted_id}")
    else:
        out = _runs_dir(cfg) / f"debrief-{interview_id}.json"
        out.write_text(json.dumps(story.model_dump(), default=str, indent=2))
        click.echo(f"mongo-unavailable:{out}")


def _render_packet(company, role, stage, digest, questions, stars) -> str:
    lines = [
        f"# Interview Prep — {company} / {role} ({stage})",
        "",
        "## Company Research",
        "",
        f"> {digest.get('sources_disclaimer','')}",
        "",
        "### News snippets",
        *[f"- {s}" for s in digest.get("news_snippets", [])],
        "",
        "### Culture signals",
        *[f"- {s}" for s in digest.get("culture_signals", [])],
        "",
        "### Interview process",
        *[f"- {s}" for s in digest.get("interview_process", [])],
        "",
        "### Likely interviewer archetypes",
        *[f"- {s}" for s in digest.get("likely_interviewer_archetypes", [])],
        "",
        f"## Predicted Questions ({len(questions)})",
        "",
    ]
    for i, q in enumerate(questions, 1):
        lines += [
            f"### {i}. [{q.get('category','?')}] {q.get('question','')}",
            f"- confidence: {q.get('confidence',0):.2f}",
            f"- why: {q.get('rationale','')}",
            "",
        ]
    lines += [f"## STAR Stories Retrieved ({len(stars)})", ""]
    if not stars:
        lines.append("_No matching stories found. Add stories via `linkright profile import` or debriefs._")
    for s in stars:
        lines += [
            f"### {s.get('title','(untitled)')} (score={s.get('_score',0):.2f})",
            s.get("body", "")[:500],
            "",
        ]
    return "\n".join(lines) + "\n"
