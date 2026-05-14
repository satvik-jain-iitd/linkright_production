"""10-dimension JD evaluator.

Flow:
  1. Load JD text + user profile (MongoDB nuggets → else profile.yaml → else {}).
  2. Call gemini_chat_json with a JSON schema that forces
     {dimension_name: {score, reason}} for all 10 dims.
  3. Fallback to chat_with_fallback + json-parse if no GEMINI_API_KEY.
  4. Map into JobSearchScorecard (weights = 0.1 each) → overall score + grade.
  5. Persist to MongoDB `evaluations` collection; on failure, dump JSON to
     ~/.linkright/runs/<ts>/evaluation.json.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..config import Config
from ..db.collections import Evaluation
from ..llm.direct import LLMError, chat_with_fallback, extract_json, gemini_chat_json
from .scorecard import DIMENSIONS_10, JobSearchScorecard

# Import grade_from_score via scorecard module (adds harness/ to sys.path)
from linkright._scorecard_base import DimensionResult, grade_from_score  # noqa: E402


SYSTEM_PROMPT = (
    "You are a career-coach JD evaluator. Score a job description against a "
    "candidate profile across 10 dimensions. Each score is 0-100 (100 = perfect). "
    "Be concise and honest — a poor fit must score low. Return strict JSON."
)


def _response_schema() -> dict[str, Any]:
    dim_schema = {
        "type": "object",
        "properties": {
            "score": {"type": "number"},
            "reason": {"type": "string"},
        },
        "required": ["score", "reason"],
    }
    return {
        "type": "object",
        "properties": {name: dim_schema for name in DIMENSIONS_10},
        "required": DIMENSIONS_10,
    }


def _build_user_prompt(jd_text: str, profile: dict[str, Any]) -> str:
    prof_blob = json.dumps(profile, indent=2, default=str)[:4000] if profile else "(no profile)"
    dims = ", ".join(DIMENSIONS_10)
    return (
        f"## Candidate profile\n{prof_blob}\n\n"
        f"## Job description\n{jd_text[:6000]}\n\n"
        f"## Task\nScore on all 10 dimensions: {dims}. "
        "Respond with a JSON object where each dimension maps to "
        '{"score": number, "reason": string}.'
    )


def _load_profile() -> dict[str, Any]:
    """Best-effort profile load: Mongo nuggets → profile.yaml → {}."""
    try:
        from ..db.mongo import get_db, ping
        if ping():
            db = get_db()
            nuggets = list(db["nuggets"].find({}, {"text": 1, "kind": 1, "company": 1, "role": 1}).limit(40))
            ctx = list(db["user_context"].find({}, {"title": 1, "body": 1}).limit(10))
            if nuggets or ctx:
                return {"nuggets": [{k: v for k, v in n.items() if k != "_id"} for n in nuggets],
                        "user_context": [{k: v for k, v in c.items() if k != "_id"} for c in ctx]}
    except Exception:
        pass
    cfg = Config.load()
    yml = cfg.profile_dir() / "profile.yaml"
    if yml.exists():
        import yaml
        try:
            return yaml.safe_load(yml.read_text()) or {}
        except Exception:
            return {}
    return {}


def _call_llm(system: str, user: str) -> dict[str, Any]:
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY_3") or os.environ.get("GEMINI_API_KEY_1"):
        try:
            text, _ = gemini_chat_json(system=system, user=user, response_schema=_response_schema())
            return json.loads(text)
        except (LLMError, json.JSONDecodeError):
            pass
    # Fallback path — ask for JSON in plain chat
    text, _ = chat_with_fallback(system=system, user=user + "\n\nReturn ONLY valid JSON, no prose.")
    return json.loads(extract_json(text))


def _fallback_dump(payload: dict[str, Any]) -> Path:
    cfg = Config.load()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    run_dir = cfg.runs_dir() / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "evaluation.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def _recommendation(score: float) -> str:
    if score >= 80:
        return "apply"
    if score >= 65:
        return "consider"
    return "skip"


def evaluate_jd(
    jd_text: str,
    profile: Optional[dict[str, Any]] = None,
    *,
    persist: bool = True,
    jd_url: Optional[str] = None,
) -> dict[str, Any]:
    """Run 10-dim evaluation. Returns dict with grade, score, dims, persisted_to."""
    profile = profile if profile is not None else _load_profile()
    try:
        parsed = _call_llm(SYSTEM_PROMPT, _build_user_prompt(jd_text, profile))
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"LLM evaluation failed: {e}") from e

    # Build scorecard
    sc = JobSearchScorecard(run_id=datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S"))
    dim_scores: dict[str, float] = {}
    for d in JobSearchScorecard.dimensions:
        item = parsed.get(d.name) or {}
        raw = float(item.get("score", 0.0))
        raw = max(0.0, min(100.0, raw))
        dim_scores[d.name] = raw
        sc.results.append(DimensionResult(
            name=d.name, score=raw, grade=grade_from_score(raw),
            weight=d.weight, notes=str(item.get("reason", ""))[:200],
        ))

    overall = round(sc.overall_score, 2)
    grade = sc.overall_grade
    jd_hash = hashlib.sha256(jd_text.encode("utf-8")).hexdigest()

    eval_doc = Evaluation(
        jd_hash=jd_hash, jd_url=jd_url, grade=grade, overall_score=overall,
        dimensions=dim_scores, recommendation=_recommendation(overall),
        notes=json.dumps({k: v.get("reason", "") for k, v in parsed.items()})[:2000],
    )

    persisted_to: str
    if persist:
        try:
            from ..db.mongo import get_db, ping
            if ping():
                db = get_db()
                res = db["evaluations"].insert_one(eval_doc.model_dump())
                persisted_to = f"mongo:evaluations/{res.inserted_id}"
            else:
                raise RuntimeError("mongo unreachable")
        except Exception:
            path = _fallback_dump(eval_doc.model_dump())
            persisted_to = str(path)
    else:
        persisted_to = "(not persisted)"

    return {
        "jd_hash": jd_hash,
        "grade": grade,
        "overall_score": overall,
        "recommendation": eval_doc.recommendation,
        "dimensions": dim_scores,
        "dimension_reasons": {k: v.get("reason", "") for k, v in parsed.items()},
        "persisted_to": persisted_to,
    }
