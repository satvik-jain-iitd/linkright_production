"""Lookup tables — converts Claude-skill "internal reasoning" into Python.

Every parameter that the skill reasoned about per-question (warmth, time
budget, follow-up pressure, question category mix, expected answer length)
becomes a static dict here. Result: per-question Groq calls only generate
language; everything else is one-line lookup. Big token savings.

All tables keyed by classification output of session_profile.py.
"""
from __future__ import annotations


# ── Round budgets (seconds) ────────────────────────────────────────────────

ROUND_BUDGETS_S: dict[str, int] = {
    "hr":      25 * 60,
    "hm":      50 * 60,
    "cto":     50 * 60,
    "case":    50 * 60,
    "founder": 37 * 60,
}


# ── Per-seniority answer length expectation (seconds spoken) ───────────────

ANSWER_BUDGET_S: dict[str, int] = {
    "ic1":      90,
    "mid":      120,
    "senior":   150,
    "staff":    180,
    "director": 150,
    "vp":       120,
    "c_level":  90,
}


# ── Follow-up pressure (probability of forced follow-up after sim answer) ──

FOLLOWUP_PRESSURE: dict[str, float] = {
    "ic1":      0.25,
    "mid":      0.45,
    "senior":   0.60,
    "staff":    0.70,
    "director": 0.70,
    "vp":       0.65,
    "c_level":  0.60,
}


# ── Hiring risks each round primarily targets ─────────────────────────────

ROUND_RISKS: dict[str, list[str]] = {
    "hr":      ["interpersonal", "motivation"],
    "hm":      ["execution", "interpersonal"],
    "cto":     ["capability", "execution"],
    "case":    ["analytical"],
    "founder": ["organizational", "vision_alignment"],
}


# ── Question category weights per (role_category, round) ──────────────────

Q_WEIGHTS: dict[tuple[str, str], dict[str, float]] = {
    ("pm", "hr"):      {"behavioral": 0.50, "culture": 0.30, "role_specific": 0.20},
    ("pm", "hm"):      {"behavioral": 0.40, "case": 0.30, "role_specific": 0.30},
    ("pm", "case"):    {"case": 0.80, "behavioral": 0.20},
    ("pm", "cto"):     {"technical": 0.50, "case": 0.30, "behavioral": 0.20},
    ("pm", "founder"): {"behavioral": 0.40, "vision": 0.40, "culture": 0.20},
    ("eng", "hr"):     {"behavioral": 0.50, "culture": 0.40, "role_specific": 0.10},
    ("eng", "hm"):     {"technical": 0.40, "behavioral": 0.40, "case": 0.20},
    ("eng", "cto"):    {"technical": 0.60, "behavioral": 0.30, "case": 0.10},
    ("eng", "case"):   {"technical": 0.70, "case": 0.30},
    ("data", "hm"):    {"technical": 0.40, "case": 0.40, "behavioral": 0.20},
    ("data", "case"):  {"case": 0.50, "technical": 0.40, "behavioral": 0.10},
    ("design", "hm"):  {"portfolio": 0.40, "behavioral": 0.30, "case": 0.30},
    ("sales", "hm"):   {"behavioral": 0.50, "role_specific": 0.30, "case": 0.20},
}

# Default fallback when (role_category, round) not in table
DEFAULT_Q_WEIGHTS: dict[str, float] = {"behavioral": 0.50, "case": 0.30, "role_specific": 0.20}


def question_weights(role_category: str, round_type: str) -> dict[str, float]:
    return Q_WEIGHTS.get((role_category, round_type), DEFAULT_Q_WEIGHTS)


# ── Warmth level by company stage ─────────────────────────────────────────

WARMTH: dict[str, str] = {
    "seed":       "high",
    "series_a":   "high",
    "series_b":   "medium",
    "growth":     "medium",
    "enterprise": "low",
    "faang":      "low",
    "public":     "low",
}


# ── Specificity bar — sim mode evasion-detection threshold by seniority ───

SPECIFICITY_BAR: dict[str, float] = {
    "ic1":      0.40,
    "mid":      0.55,
    "senior":   0.70,
    "staff":    0.80,
    "director": 0.80,
    "vp":       0.75,
    "c_level":  0.70,
}


# ── Closing question variants per round (TTS-spoken at round end) ─────────

CLOSING_VARIANTS: dict[str, str] = {
    "hr":      "We're at time. Before we wrap up — do you have any questions about the role, the team, or the process?",
    "hm":      "We're at time. Before we wrap — any questions about the team or how we actually work?",
    "cto":     "We're at time. Before we wrap up — any questions about the architecture, the stack, or how engineering operates?",
    "case":    "We're at time. Before we wrap up — any questions for me?",
    "founder": "We're at time. Before we wrap — what would you like to know about the company, the vision, or what comes next?",
}


# ── Greeting templates per round (TTS-spoken at round start, Groq-tuned) ──

GREETING_FRAMES: dict[str, str] = {
    "hr":      "Warm, conversational, fit-checking. 2-3 sentences. Acknowledge the role, set tone.",
    "hm":      "Direct, professional, execution-oriented. 2-3 sentences. Name the role + your role.",
    "cto":     "Focused, technical, lower warmth (not cold). 2-3 sentences. Set expectations.",
    "case":    "Brief, structured. 2 sentences. Outline what you'll cover.",
    "founder": "Conversational, peer-to-peer. 3 sentences. Establish two-way evaluation tone.",
}


# ── Round display names + descriptions for menu ───────────────────────────

ROUND_INFO: dict[str, tuple[str, str]] = {
    "hr":      ("HR / Recruiter screen",      "Surface fit, motivation, interpersonal — 20-30 min"),
    "hm":      ("Hiring Manager",             "Execution risk + cross-functional patterns — 45-60 min"),
    "cto":     ("CTO / Technical",            "Capability + technical depth — 45-60 min"),
    "case":    ("Case / Analytical",          "Reasoning quality on a real problem — 45-60 min"),
    "founder": ("Founder / Executive",        "Vision alignment + organizational fit — 30-45 min"),
}
