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


def _pick_interview_id_interactive(message: str = "Pick an interview:") -> Optional[str]:
    """Prompt user to pick an interview from recent Mongo records.

    Returns the picked interview_id (string), or None on cancel / no
    records / Mongo unavailable. On Mongo failure, falls back to a
    free-text ID prompt so the picker degrades gracefully.
    """
    if _mongo_ok():
        try:
            from linkright.db.mongo import get_db
            rows = list(
                get_db()["interviews"]
                .find()
                .sort("created_at", -1)
                .limit(20)
            )
            if rows:
                from linkright.prompts import prompt_for_id_from_list
                return prompt_for_id_from_list(
                    rows,
                    label_fn=lambda r: (
                        f"{(r.get('company') or '?')[:24]:<24} / "
                        f"{(r.get('role') or '?')[:24]:<24} "
                        f"({r.get('stage') or '?'})  "
                        f"{(r.get('date') or r.get('created_at') or '')!s:.16}"
                    ),
                    id_fn=lambda r: str(r.get("_id")),
                    message=message,
                    flag_hint="INTERVIEW_ID",
                )
        except Exception:
            pass
    # Fallback: free-text prompt
    from linkright.prompts import prompt_for_text
    return prompt_for_text(
        "Interview ID (from `linkright interview schedule`):",
        flag_hint="INTERVIEW_ID",
    )


@click.group("interview")
def interview_group() -> None:
    """Pillar 3 — Interview prep + mock sessions."""


# ── coach (Memory v2 Phase 6) ─────────────────────────────────────────────
# Registered eagerly so `linkright interview coach` works without import side
# effects in the existing schedule/prep/mock/debrief commands.
def _register_coach() -> None:
    from linkright.coach.cli import coach_cmd
    interview_group.add_command(coach_cmd, name="coach")


_register_coach()


@interview_group.command("schedule")
@click.option("--company", required=False, default=None,
              help="(optional) Company name — prompted if omitted")
@click.option("--role", required=False, default=None,
              help="(optional) Role title — prompted if omitted")
@click.option("--date", "date_iso", default=None, help="ISO 8601 datetime (optional)")
@click.option("--stage", default="loop", type=click.Choice(["phone", "loop", "onsite", "hm"]))
def schedule(company: Optional[str], role: Optional[str], date_iso: Optional[str], stage: str) -> None:
    """Create an Interview record. Prints the id.

    Run with no flags to be prompted for company + role.
    """
    if company is None or role is None:
        from linkright.prompts import prompt_for_text
        if company is None:
            company = prompt_for_text("Company name:", flag_hint="--company")
        if role is None:
            role = prompt_for_text("Role title:", flag_hint="--role")

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
@click.argument("interview_id", required=False, default=None)
@click.option("--jd-file", type=click.Path(exists=True), default=None)
@click.option("-n", "n_questions", default=10, show_default=True)
def prep(interview_id: Optional[str], jd_file: Optional[str], n_questions: int) -> None:
    """Run research + predict_questions + retrieve_stars. Writes prep-packet.md.

    Run with no arg to be prompted from a picker of recent interviews.
    """
    if interview_id is None:
        interview_id = _pick_interview_id_interactive("Pick an interview to prep for:")
        if not interview_id:
            click.echo("Cancelled.", err=True)
            import sys
            sys.exit(1)

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
@click.argument("interview_id", required=False, default=None)
def mock(interview_id: Optional[str]) -> None:
    """Mock session (interactive mode runs via MCP).

    Run with no arg to be prompted from a picker of recent interviews.
    """
    if interview_id is None:
        interview_id = _pick_interview_id_interactive("Pick an interview to mock:")
        if not interview_id:
            click.echo("Cancelled.", err=True)
            import sys
            sys.exit(1)

    click.echo(f"[mock {interview_id}] interactive mock session runs via agent MCP — "
               "start `linkright mcp serve` in your agent client.")


@interview_group.command("debrief")
@click.argument("interview_id", required=False, default=None)
@click.option("--notes", required=False, default=None,
              help="(optional) Raw notes from the interview — prompted if omitted")
@click.option("--title", default=None)
def debrief(interview_id: Optional[str], notes: Optional[str], title: Optional[str]) -> None:
    """Capture post-interview notes; append as a user_context story.

    Run with no flags: bare command prompts for interview ID + notes.
    For notes (multi-line), you'll be asked for a file path first;
    press Enter at the path prompt to paste in-terminal instead.
    """
    if interview_id is None:
        interview_id = _pick_interview_id_interactive("Pick an interview to debrief:")
        if not interview_id:
            click.echo("Cancelled.", err=True)
            import sys
            sys.exit(1)
    if notes is None:
        # File-path-first, paste-fallback (per locked product decision).
        # If user types a path → read file. If user just presses Enter →
        # multi-line paste mode.
        from linkright.prompts import prompt_for_text, prompt_for_paste_block
        path_hint = prompt_for_text(
            "Path to notes file (or press Enter to paste in terminal):",
            allow_empty=True,
            flag_hint="--notes",
        )
        if path_hint:
            from pathlib import Path as _P
            try:
                notes = _P(path_hint).expanduser().read_text(encoding="utf-8")
            except Exception as e:
                click.echo(f"  Could not read {path_hint}: {e} — falling back to paste mode", err=True)
                notes = prompt_for_paste_block(
                    "Paste your interview notes (Esc + Enter when done):",
                    flag_hint="--notes",
                )
        else:
            notes = prompt_for_paste_block(
                "Paste your interview notes (Esc + Enter when done):",
                flag_hint="--notes",
            )

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
