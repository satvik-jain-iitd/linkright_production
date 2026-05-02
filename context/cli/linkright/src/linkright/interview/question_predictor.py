"""Predict likely interview questions from JD + company + role + stage."""
from __future__ import annotations

import json
from typing import Any

from linkright.llm.direct import gemini_chat_json, LLMError


_Q_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["technical", "behavioral", "case", "role_specific", "culture"],
                    },
                    "confidence": {"type": "number"},
                    "rationale": {"type": "string"},
                },
                "required": ["question", "category", "confidence", "rationale"],
            },
        }
    },
    "required": ["questions"],
}

_SYSTEM = (
    "You are a senior interview coach. Given a JD, company, role, and stage, predict the "
    "most likely questions the candidate will be asked. Cover a mix of categories. "
    "confidence is 0-1 (your belief the question will actually be asked). rationale is 1 sentence."
)


def predict_questions(
    jd_text: str,
    company: str,
    role: str,
    stage: str,
    n: int = 10,
) -> list[dict[str, Any]]:
    """Return up to n predicted questions. Persists to Mongo when available."""
    user = (
        f"Company: {company}\nRole: {role}\nStage: {stage}\n"
        f"Count: {n}\n\n"
        f"JD:\n{jd_text[:6000]}\n\n"
        f"Emit exactly {n} questions spread across categories appropriate for this stage."
    )
    try:
        text, _usage = gemini_chat_json(_SYSTEM, user, response_schema=_Q_SCHEMA, max_output_tokens=4000)
        data = json.loads(text)
        questions = data.get("questions", [])[:n]
    except (LLMError, json.JSONDecodeError) as e:
        return [{"question": f"(predictor unavailable: {e})", "category": "behavioral",
                 "confidence": 0.0, "rationale": ""}]
    return questions


def persist_questions(
    interview_id: str,
    questions: list[dict[str, Any]],
    user_id: str = "local",
) -> int:
    """Best-effort write to MongoDB. Returns count written, 0 if Mongo down."""
    try:
        from linkright.db.mongo import get_db, ping
        from linkright.db.collections import PredictedQuestion
        if not ping():
            return 0
        coll = get_db()["predicted_questions"]
        docs = []
        for q in questions:
            try:
                pq = PredictedQuestion(
                    user_id=user_id,
                    interview_id=interview_id,
                    question=q.get("question", ""),
                    category=q.get("category", "behavioral"),
                    confidence=float(q.get("confidence", 0.0)),
                )
                docs.append(pq.model_dump())
            except Exception:
                continue
        if docs:
            coll.insert_many(docs)
        return len(docs)
    except Exception:
        return 0
