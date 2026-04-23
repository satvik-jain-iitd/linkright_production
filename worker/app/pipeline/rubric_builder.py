"""Builds a personalized scoring rubric for any user profile via chained gemma3:1b calls.

Six micro-calls, each doing ONE thing. Works for any career type — designer,
biotech researcher, GTM ops, SWE, anything. No fixed archetypes.

Cache: in-memory per user with RUBRIC_TTL_HOURS TTL. Rebuilt on restart or expiry.
On any call failure, gracefully returns DEFAULT_WEIGHTS (existing behaviour preserved).

Call chain:
  1. Role family classifier    → {role_family, seniority_band, domain}
  2. Must-have skills          → {must_have: [...], nice_to_have: [...]}
  3. Dealbreakers              → {dealbreakers: [{type, description}]}
  4. Career stage signals      → {seeking: [...], avoiding: [...]}
  5. Priority scores           → {priorities: {dim: 1-5}} (normalized to weights)
  6. Confidence validator      → {confidence: 0-1, issues: [...]}
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ORACLE_URL = os.getenv("ORACLE_BACKEND_URL", "https://oracle.linkright.in")
ORACLE_SECRET = os.getenv("ORACLE_BACKEND_SECRET", "")
ORACLE_TIMEOUT = 60  # seconds per call

RUBRIC_TTL_HOURS = 6
_RUBRIC_CACHE: dict[str, tuple[dict, float]] = {}  # {user_id: (rubric, ts)}

# Fallback weights — same as scoring.py DIMENSION_WEIGHTS for backward compat
DEFAULT_WEIGHTS: dict[str, float] = {
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

_ALL_DIMS = list(DEFAULT_WEIGHTS.keys())


def _profile_hash(nugget_tags: list[str], prefs: dict) -> str:
    sig = json.dumps({"tags": sorted(nugget_tags[:50]), "roles": sorted(prefs.get("target_roles") or [])}, sort_keys=True)
    return hashlib.md5(sig.encode()).hexdigest()[:12]


async def _call_oracle(client: httpx.AsyncClient, prompt: str, system: str = "") -> str:
    """Single call to Oracle /lifeos/generate. Returns raw text or empty string."""
    if not ORACLE_SECRET:
        return ""
    payload: dict[str, Any] = {"prompt": prompt, "temperature": 0.1}
    if system:
        payload["system"] = system
    try:
        resp = await client.post(
            f"{ORACLE_URL}/lifeos/generate",
            json=payload,
            headers={"Authorization": f"Bearer {ORACLE_SECRET}"},
            timeout=ORACLE_TIMEOUT,
        )
        resp.raise_for_status()
        return (resp.json().get("text") or "").strip()
    except Exception as exc:
        logger.debug("rubric_builder oracle error: %s", exc)
        return ""


def _parse_json(raw: str, fallback: Any = None) -> Any:
    """Extract first JSON object/array from LLM output. Returns fallback on failure."""
    if not raw:
        return fallback
    # Strip markdown fences if present
    cleaned = raw
    for fence in ("```json", "```"):
        if fence in cleaned:
            cleaned = cleaned.split(fence, 1)[-1].split("```")[0]
    cleaned = cleaned.strip()
    # Find first { or [
    for start_char, end_char in (("{", "}"), ("[", "]")):
        idx = cleaned.find(start_char)
        if idx != -1:
            # Find matching close — naive but works for shallow JSON
            chunk = cleaned[idx:]
            depth = 0
            for i, ch in enumerate(chunk):
                if ch == start_char:
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(chunk[:i + 1])
                        except json.JSONDecodeError:
                            break
    try:
        return json.loads(cleaned)
    except Exception:
        return fallback


def _normalize_weights(priorities: dict[str, Any]) -> dict[str, float]:
    """Convert {dim: int 1-5} priority scores to normalized weights summing to 1.0."""
    weights: dict[str, float] = {}
    for dim in _ALL_DIMS:
        raw = priorities.get(dim, 3)
        try:
            weights[dim] = max(1, min(5, int(raw)))
        except (TypeError, ValueError):
            weights[dim] = 3
    total = sum(weights.values()) or 1
    return {k: round(v / total, 4) for k, v in weights.items()}


async def build_rubric(
    user_id: str,
    nugget_tags: list[str],
    prefs: dict,
) -> dict:
    """Build (or return cached) personalized scoring rubric for a user.

    Returns a dict with keys: role_family, seniority_band, domain,
    must_have, nice_to_have, dealbreakers, seeking, avoiding, weights,
    confidence. Falls back to DEFAULT_WEIGHTS on failure.
    """
    now = time.time()
    cached = _RUBRIC_CACHE.get(user_id)
    if cached:
        rubric, ts = cached
        if (now - ts) < RUBRIC_TTL_HOURS * 3600:
            # Check if profile changed materially
            if rubric.get("_profile_hash") == _profile_hash(nugget_tags, prefs):
                return rubric

    rubric = await _build_rubric_fresh(user_id, nugget_tags, prefs)
    _RUBRIC_CACHE[user_id] = (rubric, now)
    return rubric


async def _build_rubric_fresh(
    user_id: str,
    nugget_tags: list[str],
    prefs: dict,
) -> dict:
    tags_str = ", ".join(nugget_tags[:60]) if nugget_tags else "not provided"
    roles_str = ", ".join(prefs.get("target_roles") or []) or "not specified"
    comp_str = str(prefs.get("min_comp_usd") or "not specified")
    location_str = prefs.get("location_preference") or "not specified"
    visa_str = prefs.get("visa_status") or "not specified"

    profile_summary = (
        f"Target roles: {roles_str}\n"
        f"Skills/experience tags: {tags_str}\n"
        f"Min compensation: {comp_str}\n"
        f"Location preference: {location_str}\n"
        f"Visa status: {visa_str}"
    )

    async with httpx.AsyncClient() as client:

        # ── Call 1: Role family ────────────────────────────────────────────────
        raw1 = await _call_oracle(client,
            f"Based on this candidate profile, classify their career.\n\n{profile_summary}\n\n"
            "Respond with ONLY a JSON object: "
            '{"role_family": "one of: engineering/product/design/data/research/sales/operations/marketing/finance/other", '
            '"seniority_band": "one of: entry/mid/senior/lead/executive", '
            '"domain": "2-4 word domain description e.g. mobile_engineering, product_growth, ux_design"}'
        )
        call1 = _parse_json(raw1, {})
        role_family = str(call1.get("role_family") or "other")
        seniority_band = str(call1.get("seniority_band") or "mid")
        domain = str(call1.get("domain") or "general")
        logger.debug("rubric call1 user=%s role_family=%s", user_id, role_family)

        # ── Call 2: Must-have skills ───────────────────────────────────────────
        raw2 = await _call_oracle(client,
            f"Candidate profile:\n{profile_summary}\n\n"
            "Based on their target roles and skill tags, what skills are must-have vs nice-to-have for their next job?\n"
            "Respond with ONLY a JSON object: "
            '{"must_have": ["skill1", "skill2", ... max 8 items], '
            '"nice_to_have": ["skill1", "skill2", ... max 6 items]}'
        )
        call2 = _parse_json(raw2, {})
        must_have = call2.get("must_have") or []
        nice_to_have = call2.get("nice_to_have") or []
        if not isinstance(must_have, list):
            must_have = []
        if not isinstance(nice_to_have, list):
            nice_to_have = []
        logger.debug("rubric call2 user=%s must_have=%d", user_id, len(must_have))

        # ── Call 3: Dealbreakers ──────────────────────────────────────────────
        raw3 = await _call_oracle(client,
            f"Candidate profile:\n{profile_summary}\n\n"
            "What are absolute dealbreakers for this candidate — things that would make a job unsuitable?\n"
            "Consider: visa/sponsorship needs, remote/onsite preferences, compensation minimums, role type mismatches.\n"
            "Respond with ONLY a JSON object: "
            '{"dealbreakers": [{"type": "visa|remote|comp|role|other", "description": "brief description"}]}'
            " — max 4 dealbreakers, only include real ones."
        )
        call3 = _parse_json(raw3, {})
        dealbreakers = call3.get("dealbreakers") or []
        if not isinstance(dealbreakers, list):
            dealbreakers = []
        logger.debug("rubric call3 user=%s dealbreakers=%d", user_id, len(dealbreakers))

        # ── Call 4: Career stage signals ──────────────────────────────────────
        raw4 = await _call_oracle(client,
            f"Candidate profile:\n{profile_summary}\n\n"
            "What is this candidate actively seeking in their next role, and what are they trying to avoid?\n"
            "Respond with ONLY a JSON object: "
            '{"seeking": ["signal1", "signal2", ... max 5], '
            '"avoiding": ["signal1", "signal2", ... max 5]}'
            " — be specific, e.g. seeking: 'leadership opportunity', avoiding: 'pure execution no strategy'"
        )
        call4 = _parse_json(raw4, {})
        seeking = call4.get("seeking") or []
        avoiding = call4.get("avoiding") or []
        if not isinstance(seeking, list):
            seeking = []
        if not isinstance(avoiding, list):
            avoiding = []
        logger.debug("rubric call4 user=%s seeking=%d avoiding=%d", user_id, len(seeking), len(avoiding))

        # ── Call 5: Priority scores for 10 dimensions ────────────────────────
        dims_listed = ", ".join(_ALL_DIMS)
        raw5 = await _call_oracle(client,
            f"Candidate profile:\n{profile_summary}\n"
            f"Role family: {role_family}, seniority: {seniority_band}\n\n"
            f"Rate the importance of each job scoring dimension for THIS candidate (1=low, 5=critical).\n"
            f"Dimensions: {dims_listed}\n"
            "Respond with ONLY a JSON object where keys are the dimension names and values are integers 1-5.\n"
            'Example: {"role_alignment": 5, "skill_match": 4, "level_fit": 3, ...}'
        )
        call5 = _parse_json(raw5, {})
        # Only use LLM weights if Oracle returned at least one non-default priority score
        if isinstance(call5, dict) and any(v != 3 for v in call5.values() if isinstance(v, (int, float))):
            weights = _normalize_weights(call5)
        else:
            weights = DEFAULT_WEIGHTS.copy()
        logger.debug("rubric call5 user=%s weights_sample=%s", user_id, dict(list(weights.items())[:3]))

        # ── Call 6: Confidence / self-check ──────────────────────────────────
        rubric_summary = (
            f"role_family={role_family}, seniority={seniority_band}, domain={domain}, "
            f"must_have={must_have[:3]}, dealbreakers={[d.get('type') for d in dealbreakers]}, "
            f"seeking={seeking[:2]}"
        )
        raw6 = await _call_oracle(client,
            f"Review this scoring rubric built from a candidate's profile:\n{rubric_summary}\n\n"
            "Original profile:\n" + profile_summary[:600] + "\n\n"
            "Does this rubric accurately represent the candidate? "
            "Respond with ONLY a JSON object: "
            '{"confidence": 0.0-1.0, "issues": ["issue1", ...] or []}'
        )
        call6 = _parse_json(raw6, {})
        confidence = float(call6.get("confidence") or 0.7)
        issues = call6.get("issues") or []
        if not isinstance(issues, list):
            issues = []
        logger.debug("rubric call6 user=%s confidence=%.2f issues=%d", user_id, confidence, len(issues))

        # If low confidence, fall back to default weights but keep qualitative data
        if confidence < 0.5:
            logger.warning("rubric: low confidence=%.2f for user=%s, using default weights", confidence, user_id)
            weights = DEFAULT_WEIGHTS.copy()

    return {
        "_profile_hash": _profile_hash(nugget_tags, prefs),
        "role_family": role_family,
        "seniority_band": seniority_band,
        "domain": domain,
        "must_have": must_have[:8],
        "nice_to_have": nice_to_have[:6],
        "dealbreakers": dealbreakers[:4],
        "seeking": seeking[:5],
        "avoiding": avoiding[:5],
        "weights": weights,
        "confidence": confidence,
        "issues": issues,
    }


def get_default_rubric() -> dict:
    """Return a minimal rubric using default weights — used as fallback."""
    return {
        "_profile_hash": "",
        "role_family": "other",
        "seniority_band": "mid",
        "domain": "general",
        "must_have": [],
        "nice_to_have": [],
        "dealbreakers": [],
        "seeking": [],
        "avoiding": [],
        "weights": DEFAULT_WEIGHTS.copy(),
        "confidence": 0.0,
        "issues": ["rubric not generated — using defaults"],
    }
