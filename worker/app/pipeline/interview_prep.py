"""Interview Prep Pipeline — STAR stories from career nuggets + company research.

Single Gemini Flash call. Adapts career-ops' 6-dimension research framework
and STAR+Reflection story format. Sources stories from nuggets with
leadership_signal=true and high importance (P0/P1).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from pydantic import BaseModel, Field

from ..llm.gemini import GeminiProvider
from ..llm.rate_limiter import gemini_limiter
from ..tools.hybrid_retrieval import hybrid_retrieve, NuggetResult
from .. import config as worker_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------

class ResearchDimension(BaseModel):
    dimension: str
    findings: str = Field(description="2-4 sentences of analysis")
    sources: list[str] = Field(default_factory=list, description="Evidence from JD or general knowledge")


class InterviewRound(BaseModel):
    round_name: str = Field(description="e.g., 'Phone Screen', 'Technical', 'System Design', 'Behavioral', 'Hiring Manager'")
    likely_format: str = Field(description="e.g., '45 min, 1-on-1, coding on shared editor'")
    question_categories: list[str] = Field(description="Types of questions expected")
    prep_priority: str = Field(description="high | medium | low")


class STARStory(BaseModel):
    question_type: str = Field(description="The behavioral question category this addresses")
    example_question: str = Field(description="A specific question this story answers")
    situation: str
    task: str
    action: str
    result: str
    reflection: str = Field(description="What you learned or would do differently — signals seniority")
    source_nugget: str = Field(description="Which career achievement this is based on")


class TalkingPoint(BaseModel):
    theme: str = Field(description="e.g., 'Technical Leadership', 'Scale Experience'")
    key_message: str = Field(description="The 1-2 sentence message to convey")
    supporting_evidence: list[str] = Field(description="Specific metrics or achievements backing this")


class QuestionToAsk(BaseModel):
    question: str
    why_ask: str = Field(description="What signal this question gives — shows you've done research")
    when_to_ask: str = Field(description="Which round or to whom")


class InterviewPrep(BaseModel):
    company_research: list[ResearchDimension] = Field(description="6 research dimensions from career-ops")
    round_breakdown: list[InterviewRound] = Field(description="Expected interview rounds")
    star_stories: list[STARStory] = Field(description="6-10 STAR+Reflection stories mapped to questions")
    talking_points: list[TalkingPoint] = Field(description="3-5 key themes to weave into answers")
    questions_to_ask: list[QuestionToAsk] = Field(description="5-8 smart questions for the interviewer")


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

INTERVIEW_PREP_SYSTEM = """You are an expert interview coach preparing a candidate for a specific role.

## Research Framework (6 dimensions from career-ops)
Analyze the company across:
1. AI/ML implementation — How does the company use AI in their products?
2. Recent moves — Recent hires, acquisitions, product launches, funding rounds
3. Engineering operations — Tech stack, deployment practices, team structure, remote policy
4. Technical pain points — Scaling challenges, technical debt, infrastructure gaps
5. Competitive landscape — Key competitors, market position, differentiation
6. Personal fit — How the candidate's specific background maps to the company's needs

## STAR+Reflection Format
Each story must follow:
- Situation: Context and background (1-2 sentences)
- Task: What you were responsible for (1 sentence)
- Action: Specific steps YOU took (2-3 sentences, use "I" not "we")
- Result: Quantified outcome with metrics (1-2 sentences)
- Reflection: What you learned or would do differently — this signals seniority (1 sentence)

## Rules
- Use the candidate's ACTUAL career achievements for STAR stories — never invent
- Map each story to a specific behavioral question type
- Prioritize stories with leadership signals and high importance (P0/P1)
- Questions to ask should demonstrate research, not generic curiosity
- Round breakdown should be realistic for the role level and company type

## Output
Return a JSON object matching the schema exactly. No markdown, no code fences."""


def build_interview_prep_prompt(
    company: str,
    role: str,
    jd_text: str,
    nuggets: list[NuggetResult],
    score_data: dict | None = None,
) -> str:
    """Build the user prompt for interview prep generation."""

    nugget_lines = []
    for i, n in enumerate(nuggets, 1):
        nugget_lines.append(
            f"{i}. [{n.importance}] {n.answer}"
            f"\n   Company: {n.company} | Role: {n.role} | Skills: {', '.join(n.tags[:5])}"
        )
    nuggets_text = "\n".join(nugget_lines) if nugget_lines else "(No career data available)"

    score_context = ""
    if score_data:
        score_context = f"""
## Job Score Context
Overall: {score_data.get('overall_grade', 'N/A')} ({score_data.get('overall_score', 'N/A')})
Archetype: {score_data.get('role_archetype', 'Unknown')}
Skill Gaps: {', '.join(score_data.get('skill_gaps', [])) or 'None identified'}
Strengths: Focus on dimensions scored 4.0+ in your talking points.
"""

    return f"""Prepare interview prep materials for:

## Company: {company}
## Role: {role}
{score_context}
## Job Description
{jd_text[:4000]}

## Candidate's Top Career Achievements (for STAR stories)
{nuggets_text}

Generate:
1. company_research: 6 dimensions of company analysis
2. round_breakdown: Expected interview rounds with question categories
3. star_stories: 6-10 STAR+Reflection stories from the candidate's achievements
4. talking_points: 3-5 key themes with supporting evidence
5. questions_to_ask: 5-8 smart, research-backed questions"""


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

async def generate_interview_prep(
    user_id: str,
    company: str,
    role: str,
    jd_text: str,
    supabase_client,
    score_data: dict | None = None,
) -> InterviewPrep:
    """Generate structured interview prep from career data + JD.

    Returns a validated InterviewPrep Pydantic model.
    """
    started = time.time()

    # 1. Get leadership-focused nuggets for STAR stories
    nuggets, _method = await hybrid_retrieve(
        sb=supabase_client,
        user_id=user_id,
        query=jd_text,
        limit=12,
    )
    logger.info(f"InterviewPrep: retrieved {len(nuggets)} nuggets via {_method}")

    # Also fetch nuggets with leadership signal specifically
    try:
        leader_result = (
            supabase_client.table("career_nuggets")
            .select("id, answer, importance, section_type, company, role, tags")
            .eq("user_id", user_id)
            .eq("leadership_signal", True)
            .in_("importance", ["P0", "P1"])
            .order("resume_relevance", {"ascending": False})
            .limit(5)
            .execute()
        )
        # Merge leadership nuggets that aren't already in the hybrid results
        existing_ids = {n.nugget_id for n in nuggets}
        for row in (leader_result.data or []):
            if row["id"] not in existing_ids:
                nuggets.append(NuggetResult(
                    nugget_id=row["id"],
                    answer=row.get("answer", ""),
                    nugget_text=row.get("answer", ""),
                    importance=row.get("importance", "P1"),
                    section_type=row.get("section_type", ""),
                    company=row.get("company", "") or "",
                    role=row.get("role", "") or "",
                    tags=row.get("tags", []) or [],
                    rrf_score=0.0,
                    retrieval_method="leadership_boost",
                ))
    except Exception as exc:
        logger.warning(f"InterviewPrep: leadership nugget fetch failed — {exc}")

    # 2. Build prompt
    user_prompt = build_interview_prep_prompt(company, role, jd_text, nuggets, score_data)

    # 3. Gemini Flash call with rate limiting (world knowledge needed for company research)
    gemini = GeminiProvider(
        api_key=worker_config.GEMINI_API_KEY,
        model_id=worker_config.GEMINI_MODEL_ID,
    )

    async with gemini_limiter:
        response = await gemini.complete(
            system=INTERVIEW_PREP_SYSTEM,
            user=user_prompt,
            temperature=0.3,
        )

    logger.info(
        f"InterviewPrep: Gemini call done ({response.input_tokens} in, {response.output_tokens} out)"
    )

    # 4. Parse JSON
    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

    try:
        raw_json = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(f"InterviewPrep: JSON parse failed: {e}\nRaw: {raw_text[:500]}")
        raise ValueError(f"Gemini returned invalid JSON: {e}")

    # 5. Validate with Pydantic
    prep = InterviewPrep.model_validate(raw_json)

    elapsed = time.time() - started
    logger.info(
        f"InterviewPrep: complete — {len(prep.star_stories)} stories, "
        f"{len(prep.questions_to_ask)} questions, {elapsed:.1f}s total"
    )

    return prep
