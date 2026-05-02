"""Pillar 3 — Interview Prep.

Public surface:
    research_company       — LLM-generated company/role digest
    predict_questions      — schema-guaranteed Q list, persisted to Mongo
    retrieve_stars         — STAR story retrieval (vector → text fallback)
    InterviewScorecard     — 10-dim readiness grade
    interview_group        — Click CLI (schedule / prep / mock / debrief)
"""
from __future__ import annotations

from . import research, question_predictor, star_retriever, scorecard  # noqa: F401
from .scorecard import InterviewScorecard  # noqa: F401

__all__ = [
    "research",
    "question_predictor",
    "star_retriever",
    "scorecard",
    "InterviewScorecard",
]
