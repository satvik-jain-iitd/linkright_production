"""Groq generators for the coach session.

Five generators, all session-profile-aware:
  generate_question        next interview question
  generate_ideal_answer    structured answer grounded in retrieved context
  generate_followup        sharp probe after a sim-mode answer
  generate_inference       2-4 line assessor note (per question)
  generate_feedback        KEEP/CUT/ADD/GOLD/TONE/TIME structured (sim mode)

All return (text/dict, metadata). All accept SessionProfile so per-question
prompts inject seniority + warmth + role + risk parameters from lookup
tables — Groq generates language only.
"""
from __future__ import annotations

import json
import random
from typing import Any, Optional

from linkright.llm.direct import LLMError, gemini_chat_json, groq_chat

from .rag import RetrievalBundle
from .session_profile import SessionProfile
from .tables import (
    ANSWER_BUDGET_S,
    CLOSING_VARIANTS,
    GREETING_FRAMES,
    ROUND_RISKS,
    question_weights,
)


# ════════════════════════════════════════════════════════════════════════════
# Greeting (round opener — TTS-spoken before first question)
# ════════════════════════════════════════════════════════════════════════════

def generate_greeting(
    *,
    profile: SessionProfile,
    round_type: str,
    company: str,
    role: str,
    model: Optional[str] = None,
) -> str:
    frame = GREETING_FRAMES.get(round_type, GREETING_FRAMES["hm"])
    system = (
        "You are an interviewer opening a round. "
        f"Tone calibration: {profile.warmth_level} warmth. {frame}"
    )
    user = (
        f"You are interviewing a {profile.seniority} {profile.role_category} candidate "
        f"for {role} at {company}. Round: {round_type}. "
        f"Generate ONLY the spoken greeting (no preamble, no quotes, no markdown)."
    )
    try:
        text, _usage = groq_chat(system, user, temperature=0.4, max_tokens=200)
        return text.strip().strip('"')
    except LLMError:
        # Fallback static greeting so session never breaks
        return f"Thanks for joining today. Let's dive in for the {round_type} round."


# ════════════════════════════════════════════════════════════════════════════
# Question generation
# ════════════════════════════════════════════════════════════════════════════

def generate_question(
    *,
    profile: SessionProfile,
    round_type: str,
    company: str,
    role: str,
    q_history: list[str],
    prev_answer: Optional[str] = None,
    remaining_minutes: int = 30,
    model: Optional[str] = None,
) -> str:
    """One Groq call → one question. Lookup tables inject every parameter."""
    risks = ROUND_RISKS.get(round_type, ["execution"])
    target_risk = random.choice(risks)
    weights = question_weights(profile.role_category, round_type)
    chosen_category = _weighted_pick(weights)

    system = (
        f"You are a {profile.warmth_level}-warmth interviewer for a {profile.seniority} "
        f"{profile.role_category} role. Round: {round_type}. "
        f"Generate ONE interview question (one sentence, no preamble). "
        f"Target hiring risk: {target_risk}. Question category: {chosen_category}. "
        f"Expected candidate answer length: ~{profile.answer_length_s}s spoken. "
        "Be specific to the company + role; never generic. "
        "Never explain the question. Output ONLY the question itself."
    )
    history_block = "\n".join(f"- {q}" for q in q_history[-6:]) or "(none yet)"
    prev_block = f"Candidate's last answer: {prev_answer[:600]}" if prev_answer else "Candidate's last answer: (none yet)"

    user = (
        f"Company: {company}\nRole: {role}\nStage: {profile.company_stage}\n"
        f"Previous questions in this round:\n{history_block}\n\n"
        f"{prev_block}\n\n"
        f"Time remaining in round: ~{remaining_minutes} min\n\n"
        "Generate the next question."
    )
    try:
        text, _usage = groq_chat(system, user, temperature=0.5, max_tokens=200)
        return _scrub_filler(text.strip().strip('"'))
    except LLMError:
        return f"Tell me about a recent {chosen_category}-style situation you handled at your current role."


def _weighted_pick(weights: dict[str, float]) -> str:
    items = list(weights.items())
    if not items:
        return "behavioral"
    r = random.random()
    cum = 0.0
    for cat, w in items:
        cum += w
        if r <= cum:
            return cat
    return items[-1][0]


_FILLER_PHRASES = (
    "Great answer", "Excellent", "That's great", "Wonderful", "Awesome",
    "Thanks for sharing", "Thank you for that", "I love that",
)


def _scrub_filler(text: str) -> str:
    """Strip skill-violation filler phrases that Groq sometimes prefixes."""
    for f in _FILLER_PHRASES:
        if text.startswith(f):
            text = text.split(".", 1)[-1].strip() if "." in text else text[len(f):].strip()
    return text


# ════════════════════════════════════════════════════════════════════════════
# Ideal answer generation — the headline RAG-grounded call
# ════════════════════════════════════════════════════════════════════════════

def generate_ideal_answer(
    *,
    profile: SessionProfile,
    round_type: str,
    company: str,
    role: str,
    question: str,
    bundle: RetrievalBundle,
    model: Optional[str] = None,
) -> tuple[str, str]:
    """Returns (display_prose, structured_table_md).

    display_prose: 2-3 paragraphs, natural spoken — what the candidate reads
                   aloud. Prefixed with ⚑ note when bundle.has_non_resume_tier.
    structured_table_md: 2-column intent | script table — for coaching log
                         only, NEVER displayed on screen.
    """
    facts_block = _facts_block(bundle)
    atoms_block = _atoms_block(bundle)
    playbook_block = _playbook_block(bundle)

    system = (
        "You are an expert interview coach. Write the ideal answer to the question below.\n\n"
        "RULES:\n"
        "- Use ONLY facts from the candidate's actual career data shown below. Never invent.\n"
        "- Use first-person 'I' (not 'we') for owned decisions.\n"
        "- Open with a direct declarative sentence. Main point first.\n"
        "- One sentence to establish situation. One sentence to name the tension/stakes.\n"
        "- 2-3 sentences of specific actions. One sentence stating the result with a metric.\n"
        "- Close with a bridge to the target company's context.\n"
        f"- Match seniority: ~{profile.answer_length_s}s spoken (calibrate length).\n"
        f"- Tone calibration: {profile.warmth_level}-warmth round, {profile.culture_type} culture.\n\n"
        "OUTPUT: Return JSON with two fields:\n"
        "  prose            — 2-3 short paragraphs, natural spoken language\n"
        "  structured_table — markdown table with two columns: 'Structural intent' | 'Script'\n"
    )
    user = (
        f"Round: {round_type} | Company: {company} | Role: {role}\n"
        f"Candidate seniority: {profile.seniority} {profile.role_category}\n"
        f"Question:\n{question}\n\n"
        f"COACHING METHODOLOGY (from playbook):\n{playbook_block}\n\n"
        f"CANDIDATE FACTS:\n{facts_block}\n\n"
        f"SUPPORTING ATOMS (deeper context):\n{atoms_block}\n\n"
        "Generate the ideal answer JSON."
    )

    schema = {
        "type": "object",
        "properties": {
            "prose": {"type": "string"},
            "structured_table": {"type": "string"},
        },
        "required": ["prose", "structured_table"],
    }

    try:
        text, _usage = gemini_chat_json(system, user, response_schema=schema, max_output_tokens=2000)
        data = json.loads(text)
        prose = data.get("prose", "").strip()
        table = data.get("structured_table", "").strip()
    except (LLMError, json.JSONDecodeError):
        prose = _fallback_answer_from_facts(bundle, question)
        table = "| Structural intent | Script |\n|---|---|\n| Open | (fallback — Groq unavailable) |"

    # Tier flag: prefix prose when any cited atom is non-resume-canonical.
    if bundle.has_non_resume_tier:
        prose = (
            "⚑ Note: this answer uses info not on your submitted resume — "
            "they'll probe it fresh.\n\n" + prose
        )

    return prose, table


def _facts_block(bundle: RetrievalBundle) -> str:
    if not bundle.facts:
        return "(no facts retrieved — answer must be very generic)"
    lines = []
    for f in bundle.facts:
        meta = ""
        if f.metric_extracted:
            bits = [f"{k}={v}" for k, v in f.metric_extracted.items() if v not in (None, "")]
            if bits:
                meta = " [" + ", ".join(bits) + "]"
        lines.append(f"  - [fact_id={f.id}] {f.text}{meta}")
    return "\n".join(lines)


def _atoms_block(bundle: RetrievalBundle) -> str:
    if not bundle.atoms:
        return "(no supporting atoms)"
    lines = []
    for c in bundle.atoms:
        atom = c.atom
        flag = " ⚑" if c.tier != "resume_visible" else ""
        meta = []
        if atom.role:
            meta.append(f"role={atom.role}")
        if atom.company:
            meta.append(f"company={atom.company}")
        if atom.date:
            meta.append(f"date={atom.date}")
        meta_str = " (" + ", ".join(meta) + ")" if meta else ""
        lines.append(f"  - [atom_id={atom.id}, tier={c.tier}]{flag}{meta_str}\n    {atom.text[:400]}")
    return "\n".join(lines)


def _playbook_block(bundle: RetrievalBundle) -> str:
    if not bundle.playbook_chunks:
        return "(no playbook chunks retrieved)"
    lines = []
    for c in bundle.playbook_chunks:
        path = " > ".join(c.headings_path)
        lines.append(f"  - [{path}]\n    {c.text[:700]}")
    return "\n".join(lines)


def _fallback_answer_from_facts(bundle: RetrievalBundle, question: str) -> str:
    """Deterministic fallback when Groq is unavailable."""
    if not bundle.facts:
        return f"(Groq unavailable — please retry. Question was: {question})"
    bits = [f"At {bundle.facts[0].text}." if bundle.facts else ""]
    return " ".join(b for b in bits if b)[:600]


# ════════════════════════════════════════════════════════════════════════════
# Inference update (per-question assessor note → coaching log)
# ════════════════════════════════════════════════════════════════════════════

def generate_inference(
    *,
    profile: SessionProfile,
    question: str,
    candidate_answer: str = "",
    ideal_answer: str = "",
    model: Optional[str] = None,
) -> str:
    if candidate_answer:
        system = (
            "You are an interview assessor. Write a 2-4 line first-person assessor note "
            "about what the candidate's answer revealed. What confirmed strength or raised "
            "concern? Specific vs generic? 'I' vs 'we'? Numbers matching the resume? "
            "Honest, no flattery."
        )
        user = f"Question: {question}\n\nCandidate answer: {candidate_answer[:1500]}"
    else:
        # Fallback: evaluate the ideal answer (practice mode skip)
        system = (
            "You are an interview assessor. The candidate did NOT answer; we're "
            "evaluating the IDEAL answer instead. Write a 2-4 line first-person note: "
            "what signals does this answer land if delivered cleanly? Most likely "
            "follow-up? Defensibility risks? Prefix the block with: '(evaluating ideal "
            "answer — candidate did not provide their own response)'."
        )
        user = f"Question: {question}\n\nIdeal answer: {ideal_answer[:1500]}"

    try:
        text, _usage = groq_chat(system, user, temperature=0.4, max_tokens=300)
        return text.strip()
    except LLMError:
        return "(inference unavailable — Groq error)"


# ════════════════════════════════════════════════════════════════════════════
# Structured feedback (KEEP/CUT/ADD/GOLD/TONE/TIME) — sim mode only
# ════════════════════════════════════════════════════════════════════════════

_FEEDBACK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "keep": {"type": "string"},
        "cut": {"type": "string"},
        "add": {"type": "string"},
        "gold": {"type": "string"},
        "tone": {"type": "string"},
        "time": {"type": "string"},
    },
    "required": ["keep", "cut", "add", "gold", "tone", "time"],
}


def generate_feedback(
    *,
    profile: SessionProfile,
    question: str,
    candidate_answer: str,
    ideal_answer: str = "",
    model: Optional[str] = None,
) -> dict[str, str]:
    """Returns dict with 6 keys: keep, cut, add, gold, tone, time."""
    system = (
        "You give structured per-answer feedback to an interview candidate. Six fields:\n"
        "  KEEP — quote the line/metric that landed; explain why\n"
        "  CUT  — what to remove (filler, hedging, tangent, defensive opens)\n"
        "  ADD  — what's structurally missing (the metric, tradeoff, company bridge)\n"
        "  GOLD — single most quotable sentence to own by the real interview\n"
        "  TONE — delivery observations (pace, hedging, trailing endings)\n"
        "  TIME — flag if the answer ran over/under target length\n"
        f"Target length: ~{profile.answer_length_s}s spoken (= ~{profile.answer_length_s * 2.5} words)."
    )
    user = (
        f"Question: {question}\n\n"
        f"Candidate answer: {candidate_answer[:2000]}\n\n"
        f"Ideal answer (reference): {ideal_answer[:1000] or '(not provided)'}\n\n"
        "Generate 1-3 sentences per field."
    )
    try:
        text, _usage = gemini_chat_json(system, user, response_schema=_FEEDBACK_SCHEMA, max_output_tokens=1500)
        return json.loads(text)
    except (LLMError, json.JSONDecodeError):
        return {
            "keep": "(feedback unavailable)", "cut": "", "add": "",
            "gold": "", "tone": "", "time": "",
        }


def feedback_as_md(fb: dict[str, str]) -> str:
    rows = []
    for k in ("keep", "cut", "add", "gold", "tone", "time"):
        v = fb.get(k, "").strip() or "—"
        rows.append(f"| {k.upper()} | {v} |")
    return "| Field | Observation |\n|---|---|\n" + "\n".join(rows)


# ════════════════════════════════════════════════════════════════════════════
# Follow-up question (sim mode probabilistic probe)
# ════════════════════════════════════════════════════════════════════════════

def generate_followup(
    *,
    profile: SessionProfile,
    question: str,
    candidate_answer: str,
    model: Optional[str] = None,
) -> str:
    system = (
        "You are an interviewer following up on a candidate's answer. Ask ONE sharp "
        "follow-up that probes either (a) the vaguest/most general claim, or (b) the "
        "strongest claim (pressure-test it). One sentence. Interviewer voice. No preamble."
    )
    user = f"Question: {question}\n\nCandidate answer: {candidate_answer[:1500]}\n\nGenerate the follow-up."
    try:
        text, _usage = groq_chat(system, user, temperature=0.5, max_tokens=200)
        return _scrub_filler(text.strip().strip('"'))
    except LLMError:
        return "Can you walk me through that in more detail with a specific example?"


def should_followup(profile: SessionProfile, *, force: bool = False) -> bool:
    """Probabilistic gate: profile.followup_pressure × random.random()."""
    if force:
        return True
    return random.random() < profile.followup_pressure


# ════════════════════════════════════════════════════════════════════════════
# Closing question (round end — TTS-spoken)
# ════════════════════════════════════════════════════════════════════════════

def closing_question(round_type: str) -> str:
    return CLOSING_VARIANTS.get(round_type, CLOSING_VARIANTS["hm"])
