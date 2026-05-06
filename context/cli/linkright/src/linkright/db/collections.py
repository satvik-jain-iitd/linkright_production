"""Pydantic document shapes for all LinkRight MongoDB collections.

Every doc has: user_id, created_at, updated_at, schema_version.
v1 = single-user local; schema is v2-ready (central sync + marketplace).

Collections:
  Shared:       nuggets, user_context, runs
  Pillar 1:     jds, bullets_history
  Pillar 2:     evaluations, applications
  Pillar 3:     interviews, predicted_questions, mock_sessions, career_stories
  Pillar 4:     content_items, content_calendar
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


SCHEMA_VERSION = 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(BaseModel):
    """Shared fields on every document."""
    user_id: str = "local"
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    schema_version: int = SCHEMA_VERSION


# ── Shared ─────────────────────────────────────────────────────────────

class Nugget(Base):
    """Career nugget — atomic achievement/role/skill chunk extracted from resume."""
    text: str
    kind: Literal["achievement", "role", "skill", "project", "education"] = "achievement"
    company: Optional[str] = None
    role: Optional[str] = None
    date_range: Optional[str] = None      # "Mar 2022 – Jan 2025"
    tags: list[str] = Field(default_factory=list)
    emb: Optional[list[float]] = None      # 768-dim nomic-embed-text


class UserContext(Base):
    """Story / proof-point / preference — markdown content addressable by tag."""
    kind: Literal["story", "proof_point", "preference", "voice_sample"]
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    emb: Optional[list[float]] = None


class Run(Base):
    """Per-invocation metadata + pointer to disk artifact."""
    pillar: Literal["resume", "jobsearch", "interview", "content"]
    command: str                            # "tailor", "evaluate", "prep", "draft"
    inputs: dict[str, Any] = Field(default_factory=dict)
    output_path: Optional[str] = None       # ~/.linkright/runs/<timestamp>/...
    scorecard_grade: Optional[str] = None   # "A" | "B" | "C" | "D" | "F"
    scorecard_scores: dict[str, float] = Field(default_factory=dict)
    cost_usd: float = 0.0
    cost_inr: float = 0.0
    latency_s: float = 0.0
    llm_mode: str = "agent"                 # "agent" | "direct"
    providers_used: list[str] = Field(default_factory=list)
    status: Literal["success", "partial", "failed"] = "success"


# ── Pillar 1: Resume ───────────────────────────────────────────────────

class JD(Base):
    """Job description stored for dedup + similarity search."""
    jd_hash: str                            # sha256 of normalized text
    text: str
    company: Optional[str] = None
    role: Optional[str] = None
    source_url: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    career_level: Optional[str] = None
    strategy: Optional[str] = None
    jd_emb: Optional[list[float]] = None


class BulletHistory(Base):
    """Generated bullet — retrievable for future runs to maintain voice/uniqueness."""
    bullet_text: str
    company: Optional[str] = None
    role: Optional[str] = None
    jd_hash: Optional[str] = None
    brs_score: Optional[float] = None
    emb: Optional[list[float]] = None


# ── Pillar 2: Job Search ───────────────────────────────────────────────

class Evaluation(Base):
    """10-dim A-F JD evaluation result."""
    jd_hash: str
    jd_url: Optional[str] = None
    grade: str                              # "A" | "B" | "C" | "D" | "F"
    overall_score: float                    # 0-100
    dimensions: dict[str, float]            # 10 dims → score
    recommendation: str                     # "apply" | "consider" | "skip"
    notes: str = ""


class Application(Base):
    """Submitted application tracking."""
    jd_hash: str
    jd_url: Optional[str] = None
    resume_run_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    status: Literal["drafted", "applied", "responded", "interview", "offer", "rejected"] = "drafted"
    notes: str = ""


# ── Pillar 3: Interview Prep ───────────────────────────────────────────

class Interview(Base):
    company: str
    role: str
    date: Optional[datetime] = None
    jd_hash: Optional[str] = None
    stage: Optional[str] = None             # "phone", "loop", "onsite", "hm"
    notes: str = ""


class PredictedQuestion(Base):
    interview_id: str                       # ObjectId as str
    question: str
    category: Literal["technical", "behavioral", "case", "role_specific", "culture"] = "behavioral"
    confidence: float = 0.0                 # 0-1, predictor's confidence
    matched_stories: list[str] = Field(default_factory=list)  # user_context IDs


class MockSession(Base):
    interview_id: str
    transcript: list[dict[str, str]] = Field(default_factory=list)  # [{role, text}]
    readiness_score: Optional[float] = None
    feedback: str = ""


class CareerStory(Base):
    """STAR-format career narrative — Pillar 3 Story Bank.

    Persistent reusable stories that bridge resume bullets (atomic
    achievements, see Nugget) to interview prep (mock simulator, predicted
    questions). Each story tagged with skill domains + JD requirement IDs
    so retrieval can filter by JD-relevance.

    Title + S/T/A/R fields chosen per Satvik 2026-05-03 spec ("Rich" option):
    persistent narratives with usage tracking (last_used_at / use_count) and
    JD-requirement linkage so `tailor` step_08 + `interview practice` can
    surface stories tied to the current JD's specific requirements.
    """
    title: str                                                          # short label, e.g. "AI Oracle Save (incident name)"
    situation: str = ""                                                 # context — what was the setup
    task: str = ""                                                      # what was the explicit ask
    action: str                                                         # what YOU did (verbs, tools, decisions)
    result: str                                                         # outcome with metrics
    tags: list[str] = Field(default_factory=list)                       # skill domains, e.g. ["python", "leadership"]
    jd_requirement_ids: list[str] = Field(default_factory=list)         # links to JD requirement IDs
    last_used_at: Optional[datetime] = None                             # when last surfaced in tailor/practice
    use_count: int = 0                                                  # how many times retrieved
    source_nugget_ids: list[str] = Field(default_factory=list)          # if --from-nugget, track origin
    emb: Optional[list[float]] = None                                   # 768/384-dim embedding for vector retrieval


# ── Pillar 4: Social Content ───────────────────────────────────────────

class ContentItem(Base):
    kind: Literal["linkedin_post", "twitter_thread", "blog_outline"]
    topic: str
    draft: str
    scheduled_for: Optional[datetime] = None
    platform: Optional[str] = None
    status: Literal["draft", "scheduled", "published"] = "draft"
    voice_score: Optional[float] = None
    emb: Optional[list[float]] = None


class ContentCalendar(Base):
    theme: str
    weeks: int
    items: list[str] = Field(default_factory=list)  # content_item ids


# ── Registry (used by migrations.py to create indices + collections) ────

COLLECTIONS: dict[str, type[Base]] = {
    "nuggets": Nugget,
    "user_context": UserContext,
    "runs": Run,
    "jds": JD,
    "bullets_history": BulletHistory,
    "evaluations": Evaluation,
    "applications": Application,
    "interviews": Interview,
    "predicted_questions": PredictedQuestion,
    "mock_sessions": MockSession,
    "career_stories": CareerStory,
    "content_items": ContentItem,
    "content_calendar": ContentCalendar,
}

# Which collections carry vector embeddings (for $vectorSearch / cosine fallback)
VECTOR_COLLECTIONS: dict[str, str] = {
    "nuggets": "emb",
    "user_context": "emb",
    "jds": "jd_emb",
    "bullets_history": "emb",
    "career_stories": "emb",
    "content_items": "emb",
}
