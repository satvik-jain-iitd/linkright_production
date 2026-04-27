"""Job Scoring Pipeline — rule-based 10-dimension A-F scoring.

Replaces the LLM-backed scorer (Gemini Flash → Groq 70B fallback) which was
brittle under free-tier RPD/TPM quotas and emitted schema-invalid JSON. This
version is deterministic, zero-API, sub-millisecond per discovery, and drives
off three structured sources:

  1. user_preferences (target_roles, location_preference, visa_status, stages,
     tier_flags, industries, min_comp_usd)
  2. companies_global (stage, brand_tier, tier_flags, industry_tags, ATS
     provider, supports_remote, visa sponsorship, hq_country)
  3. career_nuggets.tags (skills keyword bag per user)

Signature is backward-compatible with prior call sites (main.py, recommender).
Recommender passes the full discovery dict via the optional `discovery` kwarg
so company_slug-based lookups light up; main.py's existing 3-arg call still
works (company-dependent dimensions default to neutral 3.0).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from pydantic import BaseModel, Field

from .rubric_builder import build_rubric, get_default_rubric
from .llm_scorer import score_with_llm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic output models — schema preserved for backward compat with callers
# that read .role_alignment.score, .skill_match.gaps, etc.
# ---------------------------------------------------------------------------

class ScoringDimension(BaseModel):
    score: float = Field(ge=1.0, le=5.0)
    weight: float
    reasoning: str
    evidence: list[str] = Field(default_factory=list)
    # Populated for skill_match only; harmless on other dims.
    gaps: list[str] = Field(default_factory=list)
    hard_blockers: list[str] = Field(default_factory=list)


class JobScore(BaseModel):
    overall_score: float = Field(ge=1.0, le=5.0)
    overall_grade: str
    role_alignment: ScoringDimension
    skill_match: ScoringDimension
    level_fit: ScoringDimension
    compensation_fit: ScoringDimension
    growth_potential: ScoringDimension
    remote_quality: ScoringDimension
    company_reputation: ScoringDimension
    tech_stack: ScoringDimension
    speed_to_offer: ScoringDimension
    culture_signals: ScoringDimension
    role_archetype: str
    recommended_action: str
    skill_gaps: list[str] = Field(default_factory=list)
    hard_blockers: list[str] = Field(default_factory=list)
    keywords_matched: list[str] = Field(default_factory=list)
    legitimacy_tier: str = "unknown"

    @property
    def dimensions(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name in (
            "role_alignment", "skill_match", "level_fit", "compensation_fit",
            "growth_potential", "remote_quality", "company_reputation",
            "tech_stack", "speed_to_offer", "culture_signals",
        ):
            dim: ScoringDimension = getattr(self, name)
            d: dict[str, Any] = {
                "score": dim.score,
                "weight": dim.weight,
                "reasoning": dim.reasoning,
                "evidence": dim.evidence,
            }
            if name == "skill_match":
                d["gaps"] = dim.gaps
                d["hard_blockers"] = dim.hard_blockers
            out[name] = d
        return out


# ---------------------------------------------------------------------------
# Weights & grade boundaries
# ---------------------------------------------------------------------------

DIMENSION_WEIGHTS: dict[str, float] = {
    "role_alignment":     0.25,
    "skill_match":        0.15,
    "level_fit":          0.15,
    "compensation_fit":   0.10,
    "growth_potential":   0.10,
    "remote_quality":     0.05,
    "company_reputation": 0.05,
    "tech_stack":         0.05,
    "speed_to_offer":     0.05,
    "culture_signals":    0.05,
}

GRADE_BOUNDARIES: list[tuple[float, str]] = [
    (4.5, "A"), (3.5, "B"), (2.5, "C"), (1.5, "D"), (0.0, "F"),
]


def score_to_grade(score: float) -> str:
    for threshold, grade in GRADE_BOUNDARIES:
        if score >= threshold:
            return grade
    return "F"


def grade_to_action(grade: str, has_blockers: bool) -> str:
    if has_blockers:
        return "skip"
    return {"A": "apply_now", "B": "worth_it", "C": "maybe", "D": "skip", "F": "skip"}[grade]


def score_to_action(score: float, has_blockers: bool) -> str:
    """Career-ops-style score-based recommended action (tighter thresholds than grade-based)."""
    if has_blockers:
        return "skip"
    if score >= 4.5:
        return "apply_now"
    if score >= 4.0:
        return "worth_it"
    if score >= 3.5:
        return "maybe"
    return "skip"


# ---------------------------------------------------------------------------
# Archetype detection — keyword bags on JD title + body
# ---------------------------------------------------------------------------

ARCHETYPE_SIGNALS: dict[str, list[str]] = {
    "LLMOps":         ["observability", "evals", "mlops", "model serving", "inference platform"],
    "Agentic":        ["agent", "hitl", "multi-agent", "autonomous workflow", "tool use"],
    "PM":             ["product manager", "product management", "prd", "roadmap", "discovery"],
    "SA":             ["solutions architect", "systems design", "enterprise integration"],
    "FDE":            ["forward deployed", "field engineer", "client-facing engineer"],
    "Transformation": ["change management", "adoption", "enablement", "digital transformation"],
    "DS":             ["data scientist", "machine learning", "statistical model"],
    "Design":         ["designer", "ux", "ui design", "figma"],
    "Ops":            ["operations", "devops", "sre", "reliability engineer"],
    "Leadership":     ["director", "vp of", "head of", "chief"],
    "SWE":            ["software engineer", "backend", "frontend", "fullstack", "full-stack"],
}


def _detect_archetype(jd_text: str) -> str:
    body = jd_text.lower()
    best: tuple[int, str] = (0, "SWE")  # default
    for archetype, signals in ARCHETYPE_SIGNALS.items():
        hits = sum(1 for s in signals if s in body)
        if hits > best[0]:
            best = (hits, archetype)
    return best[1]


# ---------------------------------------------------------------------------
# Seniority detection
# ---------------------------------------------------------------------------

# Explicit seniority prefixes only — avoids the "manager" trap where a
# product manager IC role is mistaken for a people-manager role. Prefixes are
# probed in descending-rank order so "VP of Product" doesn't match "mid".
_SENIORITY_PREFIXES: list[tuple[int, list[str]]] = [
    (9, [r"\bchief\b", r"\bcxo\b", r"\bceo\b", r"\bcto\b", r"\bcfo\b"]),
    (8, [r"\bvp\b", r"\bvice\s+president\b"]),
    (7, [r"\bdirector\b", r"\bhead\s+of\b"]),
    (6, [r"\bprincipal\b", r"\bdistinguished\b"]),
    (5, [r"\bstaff\b", r"\blead\b"]),
    (4, [r"\bsenior\b", r"\bsr\.?\b"]),
    (2, [r"\bassociate\b"]),
    (1, [r"\bjunior\b", r"\bjr\.?\b", r"\bintern\b", r"\bentry[-\s]?level\b"]),
]


def _rank_title(title: str) -> int:
    t = (title or "").lower()
    for rank, patterns in _SENIORITY_PREFIXES:
        for p in patterns:
            if re.search(p, t):
                return rank
    return 3  # mid default


# ---------------------------------------------------------------------------
# Per-dimension rule functions
# ---------------------------------------------------------------------------

def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9+#./-]+", (s or "").lower()) if len(w) > 1}


def _score_role_alignment(jd_title: str, target_roles: list[str]) -> ScoringDimension:
    w = DIMENSION_WEIGHTS["role_alignment"]
    if not target_roles:
        return ScoringDimension(score=3.0, weight=w,
            reasoning="No target roles set — neutral default.", evidence=[])
    title_toks = _tokens(jd_title)
    best_overlap = 0.0
    best_match = ""
    for tr in target_roles:
        tr_toks = _tokens(tr)
        if not tr_toks:
            continue
        overlap = len(title_toks & tr_toks) / max(1, len(tr_toks))
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = tr
    if best_overlap >= 0.9:
        score = 5.0
    elif best_overlap >= 0.6:
        score = 4.0
    elif best_overlap >= 0.3:
        score = 3.0
    elif best_overlap > 0.0:
        score = 2.0
    else:
        score = 1.0
    return ScoringDimension(
        score=score, weight=w,
        reasoning=f"Title '{jd_title}' vs target '{best_match}': overlap={best_overlap:.0%}.",
        evidence=[jd_title, best_match] if best_match else [jd_title],
    )


def _score_skill_match(jd_text: str, nugget_tags: list[str]) -> ScoringDimension:
    """Count distinct user skill tags that appear as whole-word hits in the JD."""
    w = DIMENSION_WEIGHTS["skill_match"]
    if not nugget_tags:
        return ScoringDimension(score=1.5, weight=w,
            reasoning="No skill tags available from user's nuggets.", evidence=[])
    body = jd_text.lower()
    hits: list[str] = []
    for tag in nugget_tags:
        t = (tag or "").strip().lower()
        if not t or len(t) < 2:
            continue
        if re.search(rf"(?:^|[^a-z0-9]){re.escape(t)}(?:[^a-z0-9]|$)", body):
            hits.append(tag)
    n = len(set(hits))
    if n >= 8:
        score = 5.0
    elif n >= 5:
        score = 4.0
    elif n >= 3:
        score = 3.5
    elif n >= 1:
        score = 2.5
    else:
        score = 1.5
    return ScoringDimension(
        score=score, weight=w,
        reasoning=f"{n} distinct skill tags matched from user profile.",
        evidence=hits[:10],
    )


def _score_level_fit(jd_title: str, target_roles: list[str]) -> ScoringDimension:
    w = DIMENSION_WEIGHTS["level_fit"]
    jd_rank = _rank_title(jd_title)
    if not target_roles:
        return ScoringDimension(score=3.0, weight=w,
            reasoning=f"JD level rank={jd_rank}; no target roles to compare.", evidence=[jd_title])
    target_rank = max((_rank_title(tr) for tr in target_roles), default=3)
    delta = abs(jd_rank - target_rank)
    if delta == 0:
        score = 5.0
    elif delta == 1:
        score = 4.0
    elif delta == 2:
        score = 3.0
    elif delta == 3:
        score = 2.0
    else:
        score = 1.0
    return ScoringDimension(
        score=score, weight=w,
        reasoning=f"JD seniority={jd_rank}, user target={target_rank}, delta={delta}.",
        evidence=[jd_title],
    )


def _score_compensation_fit(jd_text: str, min_comp_usd: int | None) -> ScoringDimension:
    """Very coarse: if user has min_comp and JD mentions a $ number, compare."""
    w = DIMENSION_WEIGHTS["compensation_fit"]
    if not min_comp_usd:
        return ScoringDimension(score=3.0, weight=w,
            reasoning="User has no min_comp_usd set — neutral.", evidence=[])
    m = re.search(r"\$\s?(\d{2,3})[,.]?(\d{3})?", jd_text)
    if not m:
        return ScoringDimension(score=3.0, weight=w,
            reasoning="JD has no visible comp range — neutral.", evidence=[])
    n = int(m.group(1)) * (1000 if not m.group(2) else 1000) + (int(m.group(2)) if m.group(2) else 0)
    # Heuristic — the regex above is loose; treat n as "JD-indicated comp" in USD
    ratio = n / max(1, min_comp_usd)
    if ratio >= 1.3:
        score = 5.0
    elif ratio >= 1.1:
        score = 4.5
    elif ratio >= 0.95:
        score = 4.0
    elif ratio >= 0.8:
        score = 3.0
    else:
        score = 2.0
    return ScoringDimension(
        score=score, weight=w,
        reasoning=f"JD comp ~${n:,} vs user min ${min_comp_usd:,} (ratio {ratio:.2f}).",
        evidence=[m.group(0)],
    )


def _score_growth_potential(company: dict | None) -> ScoringDimension:
    w = DIMENSION_WEIGHTS["growth_potential"]
    if not company:
        return ScoringDimension(score=3.0, weight=w,
            reasoning="Company stage unknown.", evidence=[])
    stage = (company.get("stage") or "").lower()
    stage_map = {
        "seed":          5.0,
        "series_a":      5.0,
        "series_b":      4.5,
        "series_c":      4.0,
        "series_d_plus": 3.5,
        "bootstrapped":  3.5,
        "public":        3.0,
    }
    score = stage_map.get(stage, 3.0)
    return ScoringDimension(
        score=score, weight=w,
        reasoning=f"Stage={stage or 'unknown'} → growth {score}/5.",
        evidence=[stage] if stage else [],
    )


_REMOTE_MATRIX: dict[tuple[str, str], float] = {
    # (user_pref, company_supports_remote) → score
    ("remote_only", "TRUE"):      5.0,
    ("remote_only", "hybrid_ok"): 2.5,
    ("remote_only", "FALSE"):     1.0,
    ("hybrid_ok",  "TRUE"):       5.0,
    ("hybrid_ok",  "hybrid_ok"):  5.0,
    ("hybrid_ok",  "FALSE"):      2.5,
    ("onsite_ok",  "TRUE"):       3.5,
    ("onsite_ok",  "hybrid_ok"):  4.5,
    ("onsite_ok",  "FALSE"):      4.5,
    ("any",        "TRUE"):       4.0,
    ("any",        "hybrid_ok"):  4.0,
    ("any",        "FALSE"):      3.5,
}


def _score_remote_quality(user_pref: str | None, company: dict | None) -> ScoringDimension:
    w = DIMENSION_WEIGHTS["remote_quality"]
    pref = (user_pref or "any").lower()
    comp_remote = (company or {}).get("supports_remote") or ""
    score = _REMOTE_MATRIX.get((pref, comp_remote), 3.0)
    return ScoringDimension(
        score=score, weight=w,
        reasoning=f"User={pref} ↔ company={comp_remote or 'unknown'}.",
        evidence=[pref, comp_remote] if comp_remote else [pref],
    )


def _score_company_reputation(company: dict | None) -> ScoringDimension:
    w = DIMENSION_WEIGHTS["company_reputation"]
    if not company:
        return ScoringDimension(score=3.0, weight=w, reasoning="Unknown company.", evidence=[])
    tier = (company.get("brand_tier") or "").lower()
    flags = company.get("tier_flags") or []
    base_map = {"top": 5.0, "strong": 4.0, "moderate": 3.0, "emerging": 2.5}
    score = base_map.get(tier, 3.0)
    if any(f in ("faang", "public_tier1") for f in flags):
        score = max(score, 5.0)
    elif any(f in ("unicorn", "yc_backed", "proven_founders") for f in flags):
        score = max(score, 4.0)
    return ScoringDimension(
        score=score, weight=w,
        reasoning=f"brand_tier={tier or 'unknown'} flags={flags}.",
        evidence=[tier, *flags] if tier else list(flags),
    )


def _score_tech_stack(jd_text: str, nugget_tags: list[str]) -> ScoringDimension:
    """Subset of skill_match specifically for tech tooling keywords. For
    zero-config use, reuses the nugget-tag overlap bag; callers can swap in a
    tech-specific token list later."""
    base = _score_skill_match(jd_text, nugget_tags)
    # Use same score magnitude but tagged with this dim's weight
    return ScoringDimension(
        score=base.score, weight=DIMENSION_WEIGHTS["tech_stack"],
        reasoning=base.reasoning, evidence=base.evidence,
    )


def _score_speed_to_offer(company: dict | None) -> ScoringDimension:
    w = DIMENSION_WEIGHTS["speed_to_offer"]
    ats = ((company or {}).get("ats_provider") or "").lower()
    ats_map = {
        "greenhouse":     4.0,
        "lever":          4.0,
        "ashby":          4.0,
        "workable":       3.5,
        "recruitee":      3.5,
        "smartrecruiters":3.0,
        "bamboohr":       2.5,
        "workday":        2.0,
        "icims":          2.0,
        "custom":         3.0,
        "none":           3.0,
    }
    score = ats_map.get(ats, 3.0)
    return ScoringDimension(
        score=score, weight=w,
        reasoning=f"ATS={ats or 'unknown'}.",
        evidence=[ats] if ats else [],
    )


def _score_culture_signals(
    llm_culture_score: float | None = None,
    llm_seeking_score: float | None = None,
    llm_reasoning: str = "",
) -> ScoringDimension:
    w = DIMENSION_WEIGHTS["culture_signals"]
    if llm_culture_score is not None:
        # Blend culture + seeking scores (equal weight)
        seeking = llm_seeking_score if llm_seeking_score is not None else llm_culture_score
        score = round((llm_culture_score + seeking) / 2.0, 2)
        score = max(1.0, min(5.0, score))
        reasoning = llm_reasoning or f"LLM culture={llm_culture_score:.1f}, seeking_fit={seeking:.1f}."
        return ScoringDimension(score=score, weight=w, reasoning=reasoning, evidence=[])
    # Fallback — no LLM available
    return ScoringDimension(
        score=3.0, weight=w,
        reasoning="LLM unavailable — neutral default.",
        evidence=[],
    )


# ---------------------------------------------------------------------------
# Hard blockers + skill gaps
# ---------------------------------------------------------------------------

def _hard_blockers(user_prefs: dict, company: dict | None) -> list[str]:
    blockers: list[str] = []
    visa = (user_prefs.get("visa_status") or "unknown").lower()
    pref_locs = [l.lower() for l in (user_prefs.get("preferred_locations") or [])]
    if company:
        if visa == "needs_sponsorship":
            hq = (company.get("hq_country") or "").lower()
            if hq in ("usa", "us", "united states") and (company.get("sponsors_visa_usa") == "FALSE"):
                blockers.append("No USA visa sponsorship")
            if hq in ("uk", "united kingdom") and (company.get("sponsors_visa_uk") == "FALSE"):
                blockers.append("No UK visa sponsorship")
        loc_pref = (user_prefs.get("location_preference") or "any").lower()
        if loc_pref == "remote_only" and (company.get("supports_remote") == "FALSE"):
            blockers.append("Company requires onsite; user is remote-only")
    return blockers


def _skill_gaps(jd_text: str, nugget_tags: list[str]) -> list[str]:
    """Candidate JD technical keywords NOT present in the user's tag bag.

    Extracts capitalized or hyphenated tokens of length >= 3, filters out
    common English stop-noise, and subtracts the user's tag set. Kept small —
    this is a heuristic, not an NLP model.
    """
    user_tags = {t.lower() for t in nugget_tags if t}
    # Pull short-cap tokens: TypeScript, React, GraphQL, CI/CD, etc.
    candidates = re.findall(r"\b([A-Z][A-Za-z0-9+#./-]{2,})\b", jd_text)
    gaps: list[str] = []
    seen: set[str] = set()
    stop = {
        "The", "This", "That", "With", "From", "They", "And", "For",
        "You", "Your", "Our", "We're", "You'll", "What", "About",
    }
    for c in candidates:
        cl = c.lower()
        if c in stop or cl in user_tags or cl in seen:
            continue
        seen.add(cl)
        gaps.append(c)
        if len(gaps) >= 8:
            break
    return gaps


def _keywords_matched(jd_text: str, nugget_tags: list[str]) -> list[str]:
    body = jd_text.lower()
    hits: list[str] = []
    seen: set[str] = set()
    for t in nugget_tags:
        tl = (t or "").strip().lower()
        if not tl or tl in seen:
            continue
        if re.search(rf"(?:^|[^a-z0-9]){re.escape(tl)}(?:[^a-z0-9]|$)", body):
            hits.append(t)
            seen.add(tl)
    return hits[:20]


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _fetch_user_preferences(sb, user_id: str) -> dict:
    try:
        r = (
            sb.table("user_preferences")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        return (r.data or {}) if r else {}
    except Exception as exc:
        logger.debug("scoring: user_preferences fetch failed — %s", exc)
        return {}


def _fetch_company(sb, company_slug: str | None) -> dict | None:
    if not company_slug:
        return None
    try:
        r = (
            sb.table("companies_global")
            .select("*")
            .eq("company_slug", company_slug)
            .maybe_single()
            .execute()
        )
        return (r.data if r else None) or None
    except Exception as exc:
        logger.debug("scoring: companies_global fetch failed — %s", exc)
        return None


def _fetch_nugget_tags(sb, user_id: str, limit: int = 500) -> list[str]:
    """Flatten `tags` arrays across the user's career_nuggets. Dedup, cap at
    ~200 distinct tags so rule matching stays fast."""
    try:
        r = (
            sb.table("career_nuggets")
            .select("tags")
            .eq("user_id", user_id)
            .limit(limit)
            .execute()
        )
        rows = r.data or []
    except Exception as exc:
        logger.debug("scoring: career_nuggets fetch failed — %s", exc)
        return []
    bag: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for t in (row.get("tags") or []):
            tl = (t or "").strip().lower()
            if not tl or tl in seen:
                continue
            seen.add(tl)
            bag.append(t)
            if len(bag) >= 200:
                return bag
    return bag


# ---------------------------------------------------------------------------
# Main scoring function — signature preserved
# ---------------------------------------------------------------------------

async def score_application(
    user_id: str,
    jd_text: str,
    supabase_client,
    career_graph: dict | None = None,
    discovery: dict | None = None,
    prefs: dict | None = None,
    nugget_tags: list[str] | None = None,
) -> JobScore:
    """Rule-based job scoring.

    Args:
        user_id: the candidate.
        jd_text: the job description (title + body, or whatever the caller has).
        supabase_client: service-role client for lookups.
        career_graph: legacy param — target_roles fall back here when
            user_preferences.target_roles is empty. Other fields ignored.
        discovery: optional full job_discoveries row. When present we read
            `title` and `company_slug` for better dim signals.
        prefs: optional pre-fetched user_preferences row. Skips per-job DB read
            when caller batches. Falls back to fetching when None.
        nugget_tags: optional pre-fetched nugget tag list. Same rationale.
    """
    started = time.time()

    if prefs is None:
        prefs = _fetch_user_preferences(supabase_client, user_id)
    target_roles: list[str] = list(prefs.get("target_roles") or [])
    if not target_roles and career_graph:
        target_roles = list(career_graph.get("target_roles") or [])

    company_slug = (discovery or {}).get("company_slug")
    company = _fetch_company(supabase_client, company_slug)

    tags = nugget_tags if nugget_tags is not None else _fetch_nugget_tags(supabase_client, user_id)

    jd_title = (discovery or {}).get("title") or ""
    if not jd_title:
        first_line = jd_text.strip().split("\n", 1)[0]
        jd_title = first_line[:120]

    # ── Build personalized rubric (cached per user, any career profile) ───────
    try:
        rubric = await build_rubric(user_id, tags, prefs)
    except Exception as exc:
        logger.warning("scoring: rubric_builder failed user=%s — %s", user_id, exc)
        rubric = get_default_rubric()

    # ── LLM soft-signal scoring (culture, red_flags, seeking/avoiding) ────────
    llm = None
    try:
        llm = await score_with_llm(user_id=user_id, rubric=rubric, jd_text=jd_text, company=company)
    except Exception as exc:
        logger.warning("scoring: llm_scorer failed user=%s — %s", user_id, exc)

    # ── Deterministic half (reliable, zero-API) ───────────────────────────────
    role_alignment     = _score_role_alignment(jd_title, target_roles)
    skill_match        = _score_skill_match(jd_text, tags)
    level_fit          = _score_level_fit(jd_title, target_roles)
    compensation_fit   = _score_compensation_fit(jd_text, prefs.get("min_comp_usd"))
    growth_potential   = _score_growth_potential(company)
    remote_quality     = _score_remote_quality(prefs.get("location_preference"), company)
    company_reputation = _score_company_reputation(company)
    tech_stack         = _score_tech_stack(jd_text, tags)
    speed_to_offer     = _score_speed_to_offer(company)

    # ── LLM half — culture_signals filled from llm result ────────────────────
    culture_signals = _score_culture_signals(
        llm_culture_score=llm.culture_score if llm else None,
        llm_seeking_score=llm.seeking_score if llm else None,
        llm_reasoning=llm.one_line_why if llm else "",
    )

    # ── Aggregate with per-user rubric weights (or fallback to defaults) ──────
    weights = rubric.get("weights") or DIMENSION_WEIGHTS
    # Ensure all dims present in weights — fill missing from DIMENSION_WEIGHTS
    for dim_name in DIMENSION_WEIGHTS:
        if dim_name not in weights:
            weights[dim_name] = DIMENSION_WEIGHTS[dim_name]
    # Re-normalize weights to sum to 1.0
    w_total = sum(weights.values()) or 1.0
    weights = {k: v / w_total for k, v in weights.items()}

    dims = {
        "role_alignment":     role_alignment,
        "skill_match":        skill_match,
        "level_fit":          level_fit,
        "compensation_fit":   compensation_fit,
        "growth_potential":   growth_potential,
        "remote_quality":     remote_quality,
        "company_reputation": company_reputation,
        "tech_stack":         tech_stack,
        "speed_to_offer":     speed_to_offer,
        "culture_signals":    culture_signals,
    }
    # Update each dim's weight field to reflect rubric-derived weight
    for dim_name, dim_obj in dims.items():
        dim_obj.weight = round(weights.get(dim_name, DIMENSION_WEIGHTS[dim_name]), 4)

    overall = sum(d.score * d.weight for d in dims.values())
    overall = round(overall, 2)
    grade = score_to_grade(overall)

    blockers = _hard_blockers(prefs, company)
    # LLM-detected dealbreakers added to hard_blockers
    if llm and llm.dealbreaker_triggered and llm.dealbreaker_evidence:
        blockers.append(f"Dealbreaker: {llm.dealbreaker_evidence[:120]}")
    # LLM red_flags surfaced as soft blockers (don't auto-skip but show user)
    red_flags_list: list[str] = (llm.red_flags if llm else [])

    gaps = _skill_gaps(jd_text, tags)
    skill_match.gaps = gaps
    skill_match.hard_blockers = blockers

    action = score_to_action(overall, bool(blockers))
    archetype = _detect_archetype(jd_text)
    matched = _keywords_matched(jd_text, tags)

    result = JobScore(
        overall_score=overall,
        overall_grade=grade,
        role_alignment=role_alignment,
        skill_match=skill_match,
        level_fit=level_fit,
        compensation_fit=compensation_fit,
        growth_potential=growth_potential,
        remote_quality=remote_quality,
        company_reputation=company_reputation,
        tech_stack=tech_stack,
        speed_to_offer=speed_to_offer,
        culture_signals=culture_signals,
        role_archetype=archetype,
        recommended_action=action,
        skill_gaps=gaps,
        hard_blockers=blockers + red_flags_list,
        keywords_matched=matched,
        legitimacy_tier="unknown",
    )

    logger.info(
        "Scoring[rule+llm]: %s (%.2f) archetype=%s action=%s gaps=%d blockers=%d "
        "culture=%.1f red_flags=%d llm_calls=%s rubric_conf=%.2f tags=%d in %.3fs",
        grade, overall, archetype, action, len(gaps), len(blockers),
        llm.culture_score if llm else 3.0,
        len(llm.red_flags) if llm else 0,
        llm.llm_calls_made if llm else "none",
        rubric.get("confidence", 0.0),
        len(tags),
        time.time() - started,
    )
    return result
