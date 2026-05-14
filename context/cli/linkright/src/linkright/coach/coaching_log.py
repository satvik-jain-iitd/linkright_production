"""Background-thread markdown writer for the coaching log.

Per skill design: heavy coaching content (structured feedback, inference
notes, ideal-answer two-column tables) is silently appended to a markdown
file the candidate reads at session end. On-screen output during the
round stays minimal — interview cadence dominates.

All appends are non-blocking: the session loop fires-and-forgets so the
next on-screen render never waits on disk I/O.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _runs_dir() -> Path:
    home = os.environ.get("LINKRIGHT_HOME")
    base = Path(home) if home else Path.home() / ".linkright"
    return base / "runs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_log_path(*, candidate: str = "Candidate", company: str = "", role: str = "") -> Path:
    """Mint a session-unique log path. Returns the path; caller initializes."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    base = _runs_dir() / f"interview-{ts}"
    base.mkdir(parents=True, exist_ok=True)
    return base / "coaching_log.md"


def init_log(
    log_path: Path,
    *,
    candidate: str,
    target_role: str,
    target_company: str,
    archetype: str = "",
    extra_profile_md: str = "",
) -> None:
    """Write frontmatter + Session Profile section. Synchronous (one-time)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        f"---\n"
        f"candidate: {candidate}\n"
        f"target_role: {target_role}\n"
        f"target_company: {target_company}\n"
        f"archetype: {archetype}\n"
        f"session_start: {_now_iso()}\n"
        f"---\n\n"
        f"## Session Profile\n\n"
        f"{extra_profile_md or '(profile pending classification)'}\n"
    )
    log_path.write_text(body, encoding="utf-8")


def append(log_path: Path, content: str, *, blocking: bool = False) -> None:
    """Append a chunk to the coaching log.

    blocking=False (default): fires-and-forgets via daemon thread so the
    interview cadence is never blocked by disk I/O.
    blocking=True: useful for end-of-session writes where ordering matters.
    """
    if not content.endswith("\n"):
        content = content + "\n"

    def _do_append() -> None:
        try:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(content)
        except OSError:
            # Never let log failure break the interview. Errors surface in
            # debrief if catastrophic.
            pass

    if blocking:
        _do_append()
        return

    t = threading.Thread(target=_do_append, daemon=True)
    t.start()


def append_round_header(log_path: Path, round_type: str, *, idx: int = 1) -> None:
    """Section header for a round. Synchronous so subsequent appends land
    after it in file order."""
    append(log_path, f"\n## Round {idx}: {round_type.upper()}\n", blocking=True)


def append_pre_round_inference(log_path: Path, body_md: str) -> None:
    append(log_path, f"\n### Pre-round inference\n\n{body_md}\n")


def append_question_block(
    log_path: Path,
    *,
    q_idx: int,
    question: str,
    candidate_answer: str = "",
    feedback_md: str = "",
    ideal_md: str = "",
    inference_md: str = "",
) -> None:
    """Per-question markdown block — fired non-blocking from session loop."""
    parts = [f"\n### Q{q_idx}: {question.strip()[:120]}\n"]
    parts.append(f"**Asked:** {question.strip()}")
    if candidate_answer:
        parts.append(f"**Candidate answer:** {candidate_answer.strip()}")
    else:
        parts.append("**Candidate answer:** _(skipped — practice mode)_")
    if feedback_md:
        parts.append(f"**Structured feedback:**\n\n{feedback_md.strip()}")
    if ideal_md:
        parts.append(f"**Ideal answer (structured):**\n\n{ideal_md.strip()}")
    if inference_md:
        parts.append(f"**Inference update:** {inference_md.strip()}")
    append(log_path, "\n\n".join(parts) + "\n")


def append_debrief(log_path: Path, debrief_md: str) -> None:
    """End-of-round debrief block. Synchronous so close menu sees it written."""
    append(log_path, f"\n### Debrief\n\n{debrief_md.strip()}\n", blocking=True)


def append_scorecard(log_path: Path, scorecard_md: str) -> None:
    """End-of-session scorecard. Synchronous (final write)."""
    append(log_path, f"\n## Final Scorecard\n\n{scorecard_md.strip()}\n", blocking=True)
