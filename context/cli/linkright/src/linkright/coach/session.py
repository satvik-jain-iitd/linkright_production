"""Coach session — main interactive loop.

Run flow:
  1. Validate prerequisites (profile + coaching_kb built)
  2. classify_session() once → SessionProfile (cached for whole run)
  3. Init coaching log with frontmatter + Session Profile MD
  4. Round selection menu
  5. Greeting via TTS + on-screen text
  6. Per-question loop (practice or simulation)
  7. Round close → debrief
  8. End-of-session scorecard
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import click

from linkright.coaching_kb.build import is_kb_built
from linkright.evidence.store import EvidenceStore
from linkright.profile.v2_store import load_canonical_profile

from . import coaching_log as log
from . import answer_gen, rag, tts
from .scorecard import Scorecard, generate_scorecard
from .session_profile import SessionProfile, classify_session
from .tables import ROUND_BUDGETS_S, ROUND_INFO


@dataclass
class CoachSession:
    profile: SessionProfile
    company: str
    role: str
    round_type: str = "hm"
    mode: str = "practice"  # practice | sim
    log_path: Path = field(default_factory=lambda: Path())
    q_count: int = 0
    started_at: float = 0.0
    history: list[dict] = field(default_factory=list)
    last_answer: Optional[str] = None
    force_exit: bool = False  # set when user types `done` mid-round

    def elapsed_s(self) -> float:
        return time.time() - self.started_at if self.started_at else 0.0

    def remaining_s(self) -> float:
        budget = ROUND_BUDGETS_S.get(self.round_type, 30 * 60)
        return max(0.0, budget - self.elapsed_s())

    def remaining_minutes(self) -> int:
        return int(self.remaining_s() / 60)

    def should_continue(self) -> bool:
        """True iff we have time AND user hasn't asked to end."""
        return not self.force_exit and self.remaining_s() > 60


# ════════════════════════════════════════════════════════════════════════════
# Top-level orchestration
# ════════════════════════════════════════════════════════════════════════════

def run_session(
    *,
    jd_text: str,
    company: str,
    role: str,
    candidate_name_hint: str = "",
    round_override: Optional[str] = None,
    mode_override: Optional[str] = None,
    voice: Optional[str] = None,
    no_tts: bool = False,
) -> int:
    """Run one full coach session. Returns exit code (0 = clean)."""

    # Lazy embedder — sticky tier with profile/evidence
    from linkright.resume.lib.embedder import embed as _embed

    # Prereq checks
    profile_canonical = load_canonical_profile()
    if not profile_canonical:
        click.echo("✖ No CareerProfile found. Run: linkright onboard -r resume.pdf", err=True)
        return 1
    if not is_kb_built():
        click.echo("✖ Coaching KB not built. Run: linkright coaching-kb build", err=True)
        return 1

    # TTS setup
    if no_tts:
        cfg = tts.get_config()
        cfg.enabled = False
    elif voice:
        tts.set_voice(voice)

    # Step 1 — Classify session (1 Groq call)
    click.echo("→ Classifying session...")
    try:
        sp = classify_session(
            jd_text=jd_text, company=company, role=role,
            candidate_name=candidate_name_hint or profile_canonical.full_name,
        )
    except RuntimeError as e:
        click.echo(f"✖ {e}", err=True)
        return 1

    # Step 2 — Init coaching log
    log_path = log.new_log_path(
        candidate=sp.candidate_name or "Candidate",
        company=company, role=role,
    )
    log.init_log(
        log_path,
        candidate=sp.candidate_name or "Candidate",
        target_role=role, target_company=company,
        archetype=profile_canonical.current_archetype,
        extra_profile_md=sp.to_summary_md(),
    )

    # Step 3 — On-screen session brief (≤ 7 lines per skill)
    _render_session_brief(sp, company, role, log_path)

    # Step 4 — Round selection
    round_type = round_override or _prompt_round()
    if round_type is None:
        click.echo("Cancelled.")
        return 0

    # Step 5 — Mode selection
    mode = mode_override or _prompt_mode()

    # Step 6 — Round
    session = CoachSession(
        profile=sp, company=company, role=role,
        round_type=round_type, mode=mode, log_path=log_path,
        started_at=time.time(),
    )
    log.append_round_header(log_path, round_type)
    _run_round(session, embed_fn=_embed)

    # Step 7 — End-of-session scorecard
    click.echo("\n→ Generating final scorecard...")
    sc = generate_scorecard(
        profile=sp, round_type=round_type, company=company, role=role,
        question_log=session.history,
    )
    click.echo("\n━━━ Final Scorecard ━━━\n")
    click.echo(sc.to_screen_md())
    click.echo(f"\nFull scorecard + per-question detail: {log_path}")
    log.append_scorecard(log_path, sc.to_log_md())

    return 0


# ════════════════════════════════════════════════════════════════════════════
# Round loop
# ════════════════════════════════════════════════════════════════════════════

def _run_round(session: CoachSession, *, embed_fn) -> None:
    """Per-question loop. Exits on time-budget exhaustion or user `done`."""
    q_history_titles: list[str] = []
    coach_phase = _coach_phase_for_round(session.round_type, session.profile.role_category)

    # Greeting (TTS + screen)
    greeting = answer_gen.generate_greeting(
        profile=session.profile, round_type=session.round_type,
        company=session.company, role=session.role,
    )
    tts.speak(greeting, blocking=True)
    click.echo(f"\n[Interviewer] {greeting}\n")

    while session.should_continue():
        session.q_count += 1
        question = answer_gen.generate_question(
            profile=session.profile,
            round_type=session.round_type,
            company=session.company, role=session.role,
            q_history=q_history_titles,
            prev_answer=session.last_answer,
            remaining_minutes=session.remaining_minutes(),
        )
        q_history_titles.append(question[:80])

        # TTS first, text after — preserves interview cadence
        tts.speak(question)
        click.echo(f"\n[Q{session.q_count}] {question}\n")

        # Retrieve grounding
        bundle = rag.retrieve_for_question(
            question, coach_phase=coach_phase, embed_fn=embed_fn,
        )

        if session.mode == "practice":
            _handle_practice_turn(session, question, bundle)
        else:
            _handle_sim_turn(session, question, bundle, embed_fn=embed_fn)

        # Time check + early-exit option
        if session.remaining_s() <= 60:
            break

    # Closing question via TTS
    closing = answer_gen.closing_question(session.round_type)
    tts.speak(closing)
    click.echo(f"\n[Interviewer] {closing}\n")
    candidate_qs = click.prompt(
        "(your questions for me — type 'done' to skip)",
        default="done", show_default=False,
    )
    if candidate_qs and candidate_qs.lower() != "done":
        log.append(session.log_path, f"\n### Closing questions\n\n{candidate_qs.strip()}\n")


def _handle_practice_turn(session: CoachSession, question: str, bundle: rag.RetrievalBundle) -> None:
    """Generate ideal answer, display, log, wait for `next`."""
    prose, structured = answer_gen.generate_ideal_answer(
        profile=session.profile, round_type=session.round_type,
        company=session.company, role=session.role,
        question=question, bundle=bundle,
    )

    click.echo("[Ideal answer — read aloud, build muscle memory]\n")
    click.echo(prose)
    click.echo()

    # Background coaching log write (inference + structured table)
    inference = answer_gen.generate_inference(
        profile=session.profile, question=question, ideal_answer=prose,
    )
    log.append_question_block(
        session.log_path, q_idx=session.q_count, question=question,
        candidate_answer="", feedback_md="", ideal_md=structured, inference_md=inference,
    )

    session.history.append({"q": question, "a": "", "mode": "practice"})

    # Wait for `next` or other commands
    while True:
        cmd = click.prompt("[next/skip/done]", default="next", show_default=False).strip().lower()
        if cmd in ("next", "n", ""):
            return
        if cmd in ("skip", "s"):
            return
        if cmd == "done":
            session.force_exit = True
            session.history[-1]["a"] = "(user ended round)"
            return
        click.echo(f"  (commands: next, skip, done)")


def _handle_sim_turn(
    session: CoachSession, question: str, bundle: rag.RetrievalBundle,
    *, embed_fn,
) -> None:
    """Wait for candidate answer; write structured feedback + ideal silently;
    optionally fire follow-up."""
    answer = click.prompt(
        "(your answer — type 'skip' to see ideal, 'done' to end round)",
        default="", show_default=False,
    ).strip()

    if answer.lower() in ("done", ""):
        if answer.lower() == "done":
            session.force_exit = True
        # Treat empty as skip
        prose, structured = answer_gen.generate_ideal_answer(
            profile=session.profile, round_type=session.round_type,
            company=session.company, role=session.role,
            question=question, bundle=bundle,
        )
        click.echo("\n[Ideal answer — for reference]\n")
        click.echo(prose)
        inference = answer_gen.generate_inference(
            profile=session.profile, question=question, ideal_answer=prose,
        )
        log.append_question_block(
            session.log_path, q_idx=session.q_count, question=question,
            candidate_answer="", ideal_md=structured, inference_md=inference,
        )
        session.history.append({"q": question, "a": "", "mode": "sim_skipped"})
        return

    if answer.lower() == "skip":
        return  # next question without ideal display

    session.last_answer = answer
    session.history.append({"q": question, "a": answer, "mode": "sim"})

    # Background: feedback + ideal + inference (all write to log silently)
    prose, structured = answer_gen.generate_ideal_answer(
        profile=session.profile, round_type=session.round_type,
        company=session.company, role=session.role,
        question=question, bundle=bundle,
    )
    feedback = answer_gen.generate_feedback(
        profile=session.profile, question=question,
        candidate_answer=answer, ideal_answer=prose,
    )
    inference = answer_gen.generate_inference(
        profile=session.profile, question=question,
        candidate_answer=answer, ideal_answer=prose,
    )
    log.append_question_block(
        session.log_path, q_idx=session.q_count, question=question,
        candidate_answer=answer,
        feedback_md=answer_gen.feedback_as_md(feedback),
        ideal_md=structured, inference_md=inference,
    )

    # Probabilistic follow-up
    if answer_gen.should_followup(session.profile):
        followup = answer_gen.generate_followup(
            profile=session.profile, question=question, candidate_answer=answer,
        )
        tts.speak(followup)
        click.echo(f"\n[Follow-up] {followup}\n")
        followup_ans = click.prompt(
            "(your follow-up answer — Enter to skip)",
            default="", show_default=False,
        ).strip()
        if followup_ans:
            session.last_answer = followup_ans
            session.history.append({
                "q": followup, "a": followup_ans, "mode": "sim_followup",
            })


# ════════════════════════════════════════════════════════════════════════════
# UI helpers
# ════════════════════════════════════════════════════════════════════════════

def _render_session_brief(sp: SessionProfile, company: str, role: str, log_path: Path) -> None:
    click.echo()
    click.echo(f"━━━ Session Brief ━━━")
    click.echo(f"Candidate: {sp.candidate_name or 'Candidate'} → {role} at {company}")
    click.echo(f"Read:      {sp.seniority} {sp.role_category}, {sp.company_stage}, {sp.culture_type} culture")
    primary = ", ".join(sp.jd_decoded.get('explicit_requirements', [])[:3])
    fears = ", ".join(sp.jd_decoded.get('hidden_rejection_fears', [])[:3])
    click.echo(f"Top requirements: {primary or '—'}")
    click.echo(f"Hidden fears:     {fears or '—'}")
    click.echo(f"Full analysis:    {log_path}")
    click.echo()


def _prompt_round() -> Optional[str]:
    click.echo("Rounds available:")
    keys = list(ROUND_INFO.keys())
    for i, k in enumerate(keys, 1):
        name, desc = ROUND_INFO[k]
        click.echo(f"  {i}) {k:<8} — {name} ({desc})")
    click.echo()
    raw = click.prompt(
        "Type round name or number (or 'q' to quit)",
        default="hm", show_default=True,
    ).strip().lower()
    if raw in ("q", "quit"):
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(keys):
            return keys[idx]
    if raw in ROUND_INFO:
        return raw
    click.echo(f"  Unknown round '{raw}', defaulting to hm.")
    return "hm"


def _prompt_mode() -> str:
    raw = click.prompt(
        "Mode: [P]ractice (ideal answer shown) or [S]imulation (you answer first)",
        default="practice", show_default=True,
    ).strip().lower()
    if raw in ("s", "sim", "simulation"):
        return "sim"
    return "practice"


def _coach_phase_for_round(round_type: str, role_category: str) -> str:
    """Resolve coaching_kb phase identifier for routing pre-filter.

    Maps round + role to the most relevant phase key in
    coaching_kb.routing.KB_PHASE_ROUTING.
    """
    if round_type == "hr":
        return "intro_question"
    if round_type == "case":
        return "case_round"
    if round_type == "founder":
        return "founder_round"
    if round_type == "cto":
        if role_category == "pm" and "ai" in role_category.lower():
            return "ai_pm_question"
        return "technical_round"
    # default = behavioral for hm and anything else
    return "behavioral_question"
