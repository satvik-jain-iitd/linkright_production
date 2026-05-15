"""Session profile classifier — one Groq call, session start.

Converts (JD text, role title, company) → structured JSON that drives
EVERY downstream prompt + lookup-table key. Done ONCE per session;
prompts after this point cite session_profile fields instead of asking
the LLM to re-derive them.

This is the architectural unlock that lets per-question Groq calls be
small + cheap. The skill's "internal reasoning per question" becomes
"one classification at start + lookup table per question."
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from linkright.llm.direct import LLMError, gemini_chat_json

from .tables import ANSWER_BUDGET_S, FOLLOWUP_PRESSURE, WARMTH


# ── Schemas ────────────────────────────────────────────────────────────────

_PROFILE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidate_name": {"type": "string"},
        "seniority": {
            "type": "string",
            "enum": ["ic1", "mid", "senior", "staff", "director", "vp", "c_level"],
        },
        "company_stage": {
            "type": "string",
            "enum": ["seed", "series_a", "series_b", "growth", "enterprise", "faang", "public"],
        },
        "role_category": {
            "type": "string",
            "enum": ["pm", "eng", "data", "design", "sales", "ops", "marketing", "finance"],
        },
        "role_subtype": {"type": "string"},
        "culture_type": {
            "type": "string",
            "enum": ["execution", "innovation", "process", "consensus"],
        },
        "geography": {"type": "string"},
        "primary_risks": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["capability", "execution", "interpersonal", "organizational", "analytical", "vision_alignment", "motivation"],
            },
        },
        "jd_decoded": {
            "type": "object",
            "properties": {
                "explicit_requirements": {"type": "array", "items": {"type": "string"}},
                "organizational_pain": {"type": "string"},
                "cultural_signals": {"type": "array", "items": {"type": "string"}},
                "hidden_rejection_fears": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["explicit_requirements", "organizational_pain", "cultural_signals", "hidden_rejection_fears"],
        },
        "resume_risks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "flag": {"type": "string"},
                    "safe_fallback": {"type": "string"},
                },
                "required": ["flag", "safe_fallback"],
            },
        },
    },
    "required": [
        "candidate_name", "seniority", "company_stage", "role_category",
        "culture_type", "primary_risks", "jd_decoded", "resume_risks",
    ],
}


_SYSTEM = (
    "You analyze an interview opportunity and classify it into a structured profile that "
    "the interview coach will use for every downstream question. "
    "Decode the JD across 4 layers: explicit requirements, organizational pain the role "
    "solves, cultural signals, and hidden rejection fears. "
    "Identify 2-4 specific resume risks (gaps, short tenures, missing skills, weak metrics) "
    "WITH a safe defensible fallback for each. "
    "Be conservative with seniority — staff/director/vp require explicit signals in the role."
)


# ── Public dataclass ──────────────────────────────────────────────────────

@dataclass
class SessionProfile:
    candidate_name: str = ""
    seniority: str = "mid"
    seniority_score: int = 2
    company_stage: str = "growth"
    role_category: str = "pm"
    role_subtype: str = ""
    culture_type: str = "execution"
    geography: str = ""
    primary_risks: list[str] = field(default_factory=list)
    jd_decoded: dict[str, Any] = field(default_factory=dict)
    resume_risks: list[dict[str, str]] = field(default_factory=list)

    # Derived parameters (lookup tables on top of classified fields)
    answer_length_s: int = 120
    followup_pressure: float = 0.5
    warmth_level: str = "medium"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SessionProfile:
        sp = cls(
            candidate_name=d.get("candidate_name", ""),
            seniority=d.get("seniority", "mid"),
            company_stage=d.get("company_stage", "growth"),
            role_category=d.get("role_category", "pm"),
            role_subtype=d.get("role_subtype", ""),
            culture_type=d.get("culture_type", "execution"),
            geography=d.get("geography", ""),
            primary_risks=list(d.get("primary_risks") or []),
            jd_decoded=dict(d.get("jd_decoded") or {}),
            resume_risks=list(d.get("resume_risks") or []),
        )
        sp._derive_parameters()
        return sp

    def _derive_parameters(self) -> None:
        # Seniority → numeric score for prompt context (1=ic1 ... 7=c_level)
        seniority_order = ["ic1", "mid", "senior", "staff", "director", "vp", "c_level"]
        self.seniority_score = seniority_order.index(self.seniority) + 1 if self.seniority in seniority_order else 2

        self.answer_length_s = ANSWER_BUDGET_S.get(self.seniority, 120)
        self.followup_pressure = FOLLOWUP_PRESSURE.get(self.seniority, 0.5)
        self.warmth_level = WARMTH.get(self.company_stage, "medium")

    def to_summary_md(self) -> str:
        """Compact summary for coaching log Session Profile section."""
        risks = "\n".join(
            f"  - **{r.get('flag', '?')}** — fallback: {r.get('safe_fallback', '')}"
            for r in self.resume_risks
        ) or "  _(no risks identified)_"
        jd = self.jd_decoded
        return (
            f"**Candidate:** {self.candidate_name}\n"
            f"**Read:** {self.seniority} {self.role_category}, {self.company_stage}, "
            f"{self.culture_type} culture, warmth={self.warmth_level}\n"
            f"**Primary risks:** {', '.join(self.primary_risks)}\n"
            f"**Expected answer length:** ~{self.answer_length_s}s\n"
            f"**Follow-up pressure:** {self.followup_pressure:.2f}\n\n"
            f"**JD decoded:**\n"
            f"- Explicit requirements: {', '.join(jd.get('explicit_requirements', [])) or '—'}\n"
            f"- Organizational pain: {jd.get('organizational_pain', '—')}\n"
            f"- Cultural signals: {', '.join(jd.get('cultural_signals', [])) or '—'}\n"
            f"- Hidden rejection fears: {', '.join(jd.get('hidden_rejection_fears', [])) or '—'}\n\n"
            f"**Resume risks + safe fallbacks:**\n{risks}\n"
        )


# ── Classifier ────────────────────────────────────────────────────────────

def classify_session(
    *,
    jd_text: str,
    company: str,
    role: str,
    candidate_name: str = "",
    model: Optional[str] = None,
) -> SessionProfile:
    """One Groq call → SessionProfile. Stored on coach session for whole run."""
    user = (
        f"Company: {company}\nRole: {role}\nCandidate name (if known): {candidate_name or '(unknown)'}\n\n"
        f"Job description:\n{jd_text[:6000]}\n\n"
        "Classify this interview opportunity into the structured schema."
    )
    try:
        text, _usage = gemini_chat_json(
            _SYSTEM, user,
            response_schema=_PROFILE_SCHEMA,
            max_output_tokens=4000, model=model,
        )
        data = json.loads(text)
    except (LLMError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Session profile classification failed: {e}") from e

    return SessionProfile.from_dict(data)
