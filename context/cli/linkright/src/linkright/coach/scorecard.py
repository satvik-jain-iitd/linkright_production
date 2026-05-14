"""8-dimension end-of-session scorecard.

5 answer-quality dims + 3 interviewer-perception dims + headline triplet
(strongest asset / primary risk / pre-interview action).

Per the skill: terse on-screen (just the 8 ratings + triplet) — full
per-signal evidence sentences land in coaching log under
'## Final Scorecard'.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from linkright.llm.direct import LLMError, gemini_chat_json

from .session_profile import SessionProfile


_RATING_VALUES = ["Strong", "Solid", "Developing", "Needs Work"]


_SCORECARD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer_quality": {
            "type": "object",
            "properties": {
                "signal_coverage":     {"type": "string", "enum": _RATING_VALUES},
                "specificity":         {"type": "string", "enum": _RATING_VALUES},
                "ownership_clarity":   {"type": "string", "enum": _RATING_VALUES},
                "narrative_structure": {"type": "string", "enum": _RATING_VALUES},
                "authenticity":        {"type": "string", "enum": _RATING_VALUES},
            },
            "required": ["signal_coverage", "specificity", "ownership_clarity", "narrative_structure", "authenticity"],
        },
        "interviewer_perception": {
            "type": "object",
            "properties": {
                "confidence":       {"type": "string", "enum": _RATING_VALUES},
                "question_quality": {"type": "string", "enum": _RATING_VALUES},
                "presence":         {"type": "string", "enum": _RATING_VALUES},
            },
            "required": ["confidence", "question_quality", "presence"],
        },
        "strongest_asset":    {"type": "string"},
        "primary_risk":       {"type": "string"},
        "pre_interview_action": {"type": "string"},
        "per_signal_evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimension": {"type": "string"},
                    "evidence":  {"type": "string"},
                },
                "required": ["dimension", "evidence"],
            },
        },
    },
    "required": ["answer_quality", "interviewer_perception", "strongest_asset", "primary_risk", "pre_interview_action"],
}


_SYSTEM = (
    "You produce an end-of-session interview scorecard. Score 8 dimensions on a 4-point "
    "scale (Strong / Solid / Developing / Needs Work) calibrated to the candidate's "
    "seniority. Then write 3 headline sentences: strongest asset, primary risk, one "
    "specific pre-real-interview action. Then write per_signal_evidence — one short "
    "sentence per dimension citing the specific Q# that supports the rating. "
    "Honest, no flattery, no false modesty. Calibrate to the candidate's level — "
    "'Solid' for a senior may be 'Strong' for an IC1."
)


@dataclass
class Scorecard:
    answer_quality: dict[str, str] = field(default_factory=dict)
    interviewer_perception: dict[str, str] = field(default_factory=dict)
    strongest_asset: str = ""
    primary_risk: str = ""
    pre_interview_action: str = ""
    per_signal_evidence: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Scorecard:
        return cls(
            answer_quality=dict(d.get("answer_quality") or {}),
            interviewer_perception=dict(d.get("interviewer_perception") or {}),
            strongest_asset=d.get("strongest_asset", ""),
            primary_risk=d.get("primary_risk", ""),
            pre_interview_action=d.get("pre_interview_action", ""),
            per_signal_evidence=list(d.get("per_signal_evidence") or []),
        )

    def to_screen_md(self) -> str:
        aq = self.answer_quality
        ip = self.interviewer_perception
        return (
            "Answer Quality:\n"
            f"  Signal coverage:     {aq.get('signal_coverage', '—')}\n"
            f"  Specificity:         {aq.get('specificity', '—')}\n"
            f"  Ownership clarity:   {aq.get('ownership_clarity', '—')}\n"
            f"  Narrative structure: {aq.get('narrative_structure', '—')}\n"
            f"  Authenticity:        {aq.get('authenticity', '—')}\n\n"
            "Interviewer Perception:\n"
            f"  Confidence:          {ip.get('confidence', '—')}\n"
            f"  Question quality:    {ip.get('question_quality', '—')}\n"
            f"  Presence:            {ip.get('presence', '—')}\n\n"
            f"Strongest asset:      {self.strongest_asset}\n"
            f"Primary risk:         {self.primary_risk}\n"
            f"Pre-interview action: {self.pre_interview_action}"
        )

    def to_log_md(self) -> str:
        screen = self.to_screen_md()
        evidence = "\n".join(
            f"- **{e.get('dimension', '?')}** — {e.get('evidence', '')}"
            for e in self.per_signal_evidence
        ) or "_(no per-signal evidence)_"
        return f"```\n{screen}\n```\n\n### Per-signal evidence\n\n{evidence}\n"


def generate_scorecard(
    *,
    profile: SessionProfile,
    round_type: str,
    company: str,
    role: str,
    question_log: list[dict[str, Any]],
    model: Optional[str] = None,
) -> Scorecard:
    """One Groq call → Scorecard. question_log = list of {q, a, mode} dicts."""
    if not question_log:
        return Scorecard(
            strongest_asset="(no questions answered)",
            primary_risk="No data captured",
            pre_interview_action="Run a fresh session in simulation mode",
        )

    qa_block = "\n\n".join(
        f"Q{i+1} ({entry.get('mode', '?')}): {entry.get('q', '')}\n"
        f"A: {entry.get('a', '(skipped)')[:600]}"
        for i, entry in enumerate(question_log)
    )

    user = (
        f"Candidate: {profile.candidate_name} ({profile.seniority} {profile.role_category})\n"
        f"Round: {round_type} | Company: {company} | Role: {role}\n\n"
        f"Q+A history:\n{qa_block}\n\n"
        "Produce the structured scorecard."
    )

    try:
        text, _usage = gemini_chat_json(_SYSTEM, user, response_schema=_SCORECARD_SCHEMA, max_output_tokens=2500)
        return Scorecard.from_dict(json.loads(text))
    except (LLMError, json.JSONDecodeError):
        return Scorecard(
            strongest_asset="(scorecard generation unavailable)",
            primary_risk="Groq error during final scoring",
            pre_interview_action="Retry the session or check API connectivity",
        )
