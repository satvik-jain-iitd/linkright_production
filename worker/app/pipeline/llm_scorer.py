"""Per-job LLM scoring via chained gemma3:1b calls on Oracle.

Seven micro-calls, each doing ONE thing. Uses the user's personalized rubric
(from rubric_builder) to evaluate a job description. Fills soft-signal dimensions
that the deterministic rule engine can't handle well:
  - culture_signals (was stuck at neutral 3.0)
  - red_flags (new)
  - seeking/avoiding fit

Call chain:
  1. JD normalizer      → structured facts from raw JD text
  2. Must-have coverage → which rubric must-haves appear in JD
  3. Dealbreaker scan   → which (if any) dealbreakers are triggered
  4. Culture signals    → culture/environment analysis of JD
  5. Seeking fit        → does role match candidate's seeking/avoiding signals
  6. Red flags          → concerning patterns in JD
  7. Synthesizer        → combine into final culture_score + one_line_why

Results cached by (user_id, jd_hash) with 7-day TTL.
All failures produce neutral defaults — pipeline never breaks.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ORACLE_URL = os.getenv("ORACLE_BACKEND_URL", "https://oracle.linkright.in")
ORACLE_SECRET = os.getenv("ORACLE_BACKEND_SECRET", "")
ORACLE_TIMEOUT = 60

LLM_SCORE_TTL_DAYS = 7
_LLM_SCORE_CACHE: dict[str, tuple["LLMScore", float]] = {}  # {key: (result, ts)}

JD_EXCERPT_LEN = 2000  # chars — keeps prompts short for gemma3:1b


@dataclass
class LLMScore:
    culture_score: float = 3.0       # 1-5, replaces hardcoded neutral
    red_flags: list[str] = field(default_factory=list)
    dealbreaker_triggered: bool = False
    dealbreaker_evidence: str = ""
    seeking_score: float = 3.0       # how well role matches user's seeking
    avoiding_score: float = 3.0      # inverse — 1=many things to avoid, 5=nothing bad
    one_line_why: str = ""           # user-facing summary reasoning
    llm_calls_made: int = 0
    cache_hit: bool = False


async def _call_oracle(client: httpx.AsyncClient, prompt: str, system: str = "") -> str:
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
        logger.debug("llm_scorer oracle error: %s", exc)
        return ""


def _parse_json(raw: str, fallback: Any = None) -> Any:
    """Parse JSON from LLM output. If a list is returned and fallback is a dict, unwrap first element."""
    if not raw:
        return fallback
    cleaned = raw
    for fence in ("```json", "```"):
        if fence in cleaned:
            cleaned = cleaned.split(fence, 1)[-1].split("```")[0]
    cleaned = cleaned.strip()
    for start_char, end_char in (("{", "}"), ("[", "]")):
        idx = cleaned.find(start_char)
        if idx != -1:
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
        parsed = json.loads(cleaned)
        # Oracle sometimes wraps object in a list — unwrap if fallback expects a dict
        if isinstance(parsed, list) and parsed and isinstance(fallback, dict):
            return parsed[0]
        return parsed
    except Exception:
        return fallback


def _clamp(v: Any, lo: float = 1.0, hi: float = 5.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return (lo + hi) / 2


async def score_with_llm(
    user_id: str,
    rubric: dict,
    jd_text: str,
    company: dict | None = None,
) -> LLMScore:
    """Run 7-call chain to score soft dimensions. Returns LLMScore (cached or fresh)."""
    jd_excerpt = jd_text[:JD_EXCERPT_LEN]
    jd_hash = hashlib.md5(jd_excerpt.encode()).hexdigest()[:8]
    rubric_hash = rubric.get("_profile_hash", "")[:8]
    cache_key = f"{user_id}:{jd_hash}:{rubric_hash}"

    cached = _LLM_SCORE_CACHE.get(cache_key)
    if cached:
        result, ts = cached
        if (time.time() - ts) < LLM_SCORE_TTL_DAYS * 86400:
            result.cache_hit = True
            return result

    result = await _score_fresh(user_id, rubric, jd_excerpt, company)
    _LLM_SCORE_CACHE[cache_key] = (result, time.time())
    return result


async def _score_fresh(
    user_id: str,
    rubric: dict,
    jd_excerpt: str,
    company: dict | None,
) -> LLMScore:
    result = LLMScore()
    company_meta = ""
    if company:
        company_meta = (
            f"Company stage: {company.get('stage','unknown')}, "
            f"Remote: {company.get('supports_remote', 'unknown')}, "
            f"Brand tier: {company.get('brand_tier','unknown')}"
        )

    must_have_str = ", ".join(rubric.get("must_have") or []) or "not specified"
    dealbreakers = rubric.get("dealbreakers") or []
    seeking = rubric.get("seeking") or []
    avoiding = rubric.get("avoiding") or []
    seeking_str = ", ".join(seeking) or "not specified"
    avoiding_str = ", ".join(avoiding) or "not specified"

    async with httpx.AsyncClient() as client:

        # ── Call 1: JD normalizer ─────────────────────────────────────────────
        raw1 = await _call_oracle(client,
            f"Extract key facts from this job description.\n\nJD:\n{jd_excerpt}\n\n"
            "Respond with ONLY a JSON object: "
            '{"role_title": "...", "seniority_hint": "entry|mid|senior|lead|executive", '
            '"remote_policy": "remote|hybrid|onsite|unknown", '
            '"comp_mentioned": true/false, '
            '"company_culture_keywords": ["word1", "word2", ... max 5]}'
        )
        call1 = _parse_json(raw1, {})
        culture_keywords = call1.get("company_culture_keywords") or []
        result.llm_calls_made += 1
        logger.debug("llm_scorer call1 user=%s keywords=%s", user_id, culture_keywords[:3])

        # ── Call 2: Must-have coverage ────────────────────────────────────────
        raw2 = await _call_oracle(client,
            f"Candidate must-have skills: {must_have_str}\n\nJob description:\n{jd_excerpt}\n\n"
            "Which of the candidate's must-have skills/requirements appear in this job description?\n"
            "Respond with ONLY a JSON object: "
            '{"matched": ["skill1", ...], "missing": ["skill1", ...], "match_rate": 0.0-1.0}'
        )
        call2 = _parse_json(raw2, {})
        result.llm_calls_made += 1

        # ── Call 3: Dealbreaker scan ──────────────────────────────────────────
        if dealbreakers:
            db_str = "; ".join(f"{d.get('type','?')}: {d.get('description','?')}" for d in dealbreakers[:4])
            raw3 = await _call_oracle(client,
                f"Candidate dealbreakers: {db_str}\n\nJob description:\n{jd_excerpt}\n"
                + (f"\nCompany info: {company_meta}" if company_meta else "") + "\n\n"
                "Are any of these dealbreakers triggered by this job? Be strict — only flag clear violations.\n"
                "Respond with ONLY a JSON object: "
                '{"triggered": true/false, "evidence": "brief reason or empty string"}'
            )
            call3 = _parse_json(raw3, {"triggered": False, "evidence": ""})
            result.dealbreaker_triggered = bool(call3.get("triggered"))
            result.dealbreaker_evidence = str(call3.get("evidence") or "")
        result.llm_calls_made += 1

        # ── Call 4: Culture signals ───────────────────────────────────────────
        raw4 = await _call_oracle(client,
            f"Job description:\n{jd_excerpt}\n"
            + (f"\nCompany info: {company_meta}" if company_meta else "") + "\n\n"
            "Analyze the work environment and culture signals in this job posting.\n"
            "Consider: team dynamics, autonomy, growth culture, communication style, values alignment.\n"
            "Respond with ONLY a JSON object: "
            '{"culture_score": 1-5, "positive_signals": ["signal1", ...], "concerns": ["concern1", ...]}'
            " where 5=excellent culture, 1=red flag culture, 3=neutral/unclear."
        )
        call4 = _parse_json(raw4, {})
        result.culture_score = _clamp(call4.get("culture_score", 3.0))
        result.llm_calls_made += 1
        logger.debug("llm_scorer call4 user=%s culture=%.1f", user_id, result.culture_score)

        # ── Call 5: Seeking/avoiding fit ──────────────────────────────────────
        raw5 = await _call_oracle(client,
            f"Candidate is seeking: {seeking_str}\n"
            f"Candidate is avoiding: {avoiding_str}\n\n"
            f"Job description:\n{jd_excerpt}\n\n"
            "How well does this role match what the candidate seeks vs. what they want to avoid?\n"
            "Respond with ONLY a JSON object: "
            '{"seeking_score": 1-5, "avoiding_score": 1-5}'
            " where seeking_score=5 means role has everything they seek, "
            "avoiding_score=5 means role has none of the things they want to avoid."
        )
        call5 = _parse_json(raw5, {})
        result.seeking_score = _clamp(call5.get("seeking_score", 3.0))
        result.avoiding_score = _clamp(call5.get("avoiding_score", 3.0))
        result.llm_calls_made += 1
        logger.debug("llm_scorer call5 user=%s seeking=%.1f avoiding=%.1f", user_id, result.seeking_score, result.avoiding_score)

        # ── Call 6: Red flags ─────────────────────────────────────────────────
        raw6 = await _call_oracle(client,
            f"Job description:\n{jd_excerpt}\n\n"
            "Identify any red flags in this job posting that a job seeker should know about.\n"
            "Look for: unrealistic requirements, vague compensation, excessive demands, "
            "signs of instability, conflicting role descriptions, bait-and-switch language.\n"
            "Respond with ONLY a JSON object: "
            '{"red_flags": ["flag1", ...] or [], "severity": 0.0-1.0}'
            " — only include genuine red flags, not normal job requirements."
        )
        call6 = _parse_json(raw6, {"red_flags": [], "severity": 0.0})
        raw_flags = call6.get("red_flags") or []
        result.red_flags = [str(f) for f in raw_flags if f][:5]
        severity = _clamp(call6.get("severity", 0.0), 0.0, 1.0)
        # Severe red flags reduce culture score
        if severity > 0.6 and result.red_flags:
            result.culture_score = max(1.0, result.culture_score - 1.0)
        result.llm_calls_made += 1
        logger.debug("llm_scorer call6 user=%s red_flags=%d severity=%.1f", user_id, len(result.red_flags), severity)

        # ── Call 7: Synthesizer ───────────────────────────────────────────────
        match_rate = float((call2 or {}).get("match_rate") or 0.5)
        blocker_note = f"dealbreaker triggered: {result.dealbreaker_evidence}" if result.dealbreaker_triggered else "no dealbreakers"
        raw7 = await _call_oracle(client,
            f"Summarize this job match assessment in ONE sentence (max 20 words).\n\n"
            f"Must-have match rate: {match_rate:.0%}\n"
            f"Culture score: {result.culture_score:.1f}/5\n"
            f"Seeking fit: {result.seeking_score:.1f}/5\n"
            f"Avoiding fit: {result.avoiding_score:.1f}/5\n"
            f"Red flags: {len(result.red_flags)}\n"
            f"Dealbreaker: {blocker_note}\n\n"
            "Write ONE sentence starting with a verb. No JSON, just a plain sentence."
        )
        result.one_line_why = (raw7 or "").strip()[:200]
        result.llm_calls_made += 1

    logger.info(
        "llm_scorer: user=%s calls=%d culture=%.1f seeking=%.1f red_flags=%d blocker=%s",
        user_id, result.llm_calls_made, result.culture_score,
        result.seeking_score, len(result.red_flags), result.dealbreaker_triggered,
    )
    return result
