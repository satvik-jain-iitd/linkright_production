"""
jd_matcher.py — Composite JD requirement scorer for LinkRight.

Scoring formula:
    composite = exact_match * 0.4 + semantic_match * 0.3 + metadata_match * 0.3

Thresholds:
    >= 0.7  → "met"
    >= 0.4  → "partial"
    <  0.4  → "gap"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class RequirementScore:
    requirement: str
    requirement_type: str  # hard_skill | soft_skill | experience | certification | education
    exact_score: float = 0.0
    semantic_score: float = 0.0
    metadata_score: float = 0.0
    composite_score: float = 0.0
    status: str = "gap"  # "met" | "partial" | "gap"
    matching_nuggets: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Stop words
# ---------------------------------------------------------------------------

_STOPWORDS: frozenset[str] = frozenset(
    ["and", "or", "the", "a", "with", "in", "for", "of", "to"]
)

# ---------------------------------------------------------------------------
# Exact match
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Lower-case, strip punctuation, remove stop words, return non-empty tokens."""
    words = re.sub(r"[^a-zA-Z0-9\s+]", " ", text).lower().split()
    return [w for w in words if w not in _STOPWORDS and len(w) >= 2]


def _keyword_in_text(keyword: str, text: str) -> bool:
    """
    Return True if *keyword* appears in *text* with fuzzy tolerance:
    - exact substring match (case-insensitive), OR
    - keyword is contained within a longer word (e.g. 'sql' in 'mysql').
    """
    text_lower = text.lower()
    kw_lower = keyword.lower()
    return kw_lower in text_lower


def exact_match_score(requirement: str, nuggets: list[dict]) -> float:
    """
    Score how well a requirement's keywords appear verbatim (or as substrings)
    across the user's nuggets.

    Returns the best ratio found in any single nugget: 0.0 – 1.0.
    """
    keywords = _tokenize(requirement)
    if not keywords:
        return 0.0

    best_ratio = 0.0
    for nugget in nuggets:
        answer: str = nugget.get("answer", "") or ""
        if not answer:
            continue
        hits = sum(1 for kw in keywords if _keyword_in_text(kw, answer))
        ratio = hits / len(keywords)
        if ratio > best_ratio:
            best_ratio = ratio

    return best_ratio


# ---------------------------------------------------------------------------
# Metadata match
# ---------------------------------------------------------------------------

_FINTECH_TERMS: frozenset[str] = frozenset(
    ["bank", "finance", "capital", "amex", "visa", "mastercard",
     "stripe", "paypal", "fintech", "fintec"]
)

_LEADERSHIP_SIGNALS: frozenset[str] = frozenset(
    ["team_lead", "manager", "director"]
)

_YEARS_RE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)", re.IGNORECASE)


def _extract_required_years(requirement: str) -> Optional[int]:
    """Extract the minimum years mentioned in a requirement string."""
    m = _YEARS_RE.search(requirement)
    return int(m.group(1)) if m else None


def metadata_match_score(
    requirement: str, requirement_type: str, nuggets: list[dict]
) -> float:
    """
    Score a requirement using structured metadata fields in nuggets.

    Supported signals:
    - leadership_signal field for leadership requirements
    - event_date spans for experience-year requirements
    - company name keywords for industry (fintech/finance) requirements

    Returns 0.0 – 1.0.
    """
    req_lower = requirement.lower()

    # ── Leadership ───────────────────────────────────────────────────────────
    if any(word in req_lower for word in ("lead", "leadership", "manager", "director")):
        for nugget in nuggets:
            signal = nugget.get("leadership_signal", "")
            if signal in _LEADERSHIP_SIGNALS:
                return 1.0
        return 0.0

    # ── Experience years ─────────────────────────────────────────────────────
    required_years = _extract_required_years(requirement)
    if required_years is not None:
        # Sum durations from work_experience nuggets that carry event_date spans.
        # event_date is expected as a dict {"start": YYYY, "end": YYYY | "present"}
        import datetime
        current_year = datetime.date.today().year
        total_years = 0.0

        for nugget in nuggets:
            if nugget.get("nugget_type") != "work_experience":
                continue
            event_date = nugget.get("event_date") or {}
            if not isinstance(event_date, dict):
                continue
            try:
                start = int(event_date.get("start", 0))
                end_raw = event_date.get("end", "present")
                end = current_year if str(end_raw).lower() == "present" else int(end_raw)
                if start > 0 and end >= start:
                    total_years += end - start
            except (TypeError, ValueError):
                continue

        if total_years >= required_years:
            return 1.0
        if total_years >= required_years - 1:
            return 0.7
        return 0.0

    # ── Fintech / Finance industry ───────────────────────────────────────────
    if any(term in req_lower for term in ("fintech", "banking", "finance", "financial")):
        for nugget in nuggets:
            company: str = (nugget.get("company") or nugget.get("organization") or "").lower()
            if any(ft in company for ft in _FINTECH_TERMS):
                return 1.0
        return 0.0

    return 0.0


# ---------------------------------------------------------------------------
# Composite weighting
# ---------------------------------------------------------------------------

def weighted_composite(exact: float, semantic: float, metadata: float) -> float:
    """Combine exact + semantic + metadata scores with configurable weights."""
    EXACT_WEIGHT = 0.4
    SEMANTIC_WEIGHT = 0.3
    METADATA_WEIGHT = 0.3
    return exact * EXACT_WEIGHT + semantic * SEMANTIC_WEIGHT + metadata * METADATA_WEIGHT


# ---------------------------------------------------------------------------
# Single-requirement scorer
# ---------------------------------------------------------------------------

def score_requirement(
    requirement: str,
    requirement_type: str,
    nuggets: list[dict],
    embeddings_map: Optional[dict] = None,
) -> RequirementScore:
    """Score a single JD requirement against the user's nuggets."""
    score = RequirementScore(requirement=requirement, requirement_type=requirement_type)
    score.exact_score = exact_match_score(requirement, nuggets)
    score.metadata_score = metadata_match_score(requirement, requirement_type, nuggets)
    # semantic_score: filled in by caller when embeddings are available
    if embeddings_map:
        score.semantic_score = embeddings_map.get(requirement, 0.0)
    score.composite_score = weighted_composite(
        score.exact_score, score.semantic_score, score.metadata_score
    )
    if score.composite_score >= 0.7:
        score.status = "met"
    elif score.composite_score >= 0.4:
        score.status = "partial"
    else:
        score.status = "gap"
    return score


# ---------------------------------------------------------------------------
# Batch scorer
# ---------------------------------------------------------------------------

def batch_score_requirements(
    requirements: list[dict],
    nuggets: list[dict],
    embeddings_map: Optional[dict] = None,
) -> list[RequirementScore]:
    """
    Score a list of requirements against nuggets.

    Args:
        requirements: list of {"text": str, "type": str}
        nuggets:      user's career nuggets as dicts
        embeddings_map: optional {requirement_text: semantic_score float}

    Returns:
        list of RequirementScore (one per requirement)
    """
    results: list[RequirementScore] = []
    for req in requirements:
        text: str = req.get("text", "")
        req_type: str = req.get("type", "other")
        results.append(
            score_requirement(
                requirement=text,
                requirement_type=req_type,
                nuggets=nuggets,
                embeddings_map=embeddings_map,
            )
        )
    return results
