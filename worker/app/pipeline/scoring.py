"""Job Scoring Pipeline — 10-dimension A-F scoring adapted from career-ops.

Evaluates a job description against a user's career profile (nuggets) across
10 weighted dimensions, producing a structured score with grade, gaps, and
recommended action.

Uses Gemini Flash for quality-sensitive structured output.
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

class ScoringDimension(BaseModel):
    score: float = Field(ge=1.0, le=5.0, description="Score from 1.0 to 5.0")
    weight: float = Field(description="Weight for this dimension (sums to 1.0)")
    reasoning: str = Field(description="2-3 sentence justification citing specific evidence")
    evidence: list[str] = Field(default_factory=list, description="Specific JD requirements or nugget excerpts cited")


class SkillMatchDimension(ScoringDimension):
    gaps: list[str] = Field(default_factory=list, description="Skills required by JD but missing from profile")
    hard_blockers: list[str] = Field(default_factory=list, description="Deal-breaker gaps (e.g., 10+ years required, has 4)")


class JobScore(BaseModel):
    overall_score: float = Field(ge=1.0, le=5.0, description="Weighted average across all dimensions")
    overall_grade: str = Field(description="A (>=4.5), B (>=3.5), C (>=2.5), D (>=1.5), F (<1.5)")
    role_alignment: ScoringDimension
    skill_match: SkillMatchDimension
    level_fit: ScoringDimension
    compensation_fit: ScoringDimension
    growth_potential: ScoringDimension
    remote_quality: ScoringDimension
    company_reputation: ScoringDimension
    tech_stack: ScoringDimension
    speed_to_offer: ScoringDimension
    culture_signals: ScoringDimension
    role_archetype: str = Field(description="Detected archetype: SWE, PM, DS, Design, Ops, Leadership, LLMOps, Agentic, SA, FDE, Transformation")
    recommended_action: str = Field(description="apply_now | worth_it | maybe | skip")
    skill_gaps: list[str] = Field(default_factory=list, description="All identified skill gaps")
    hard_blockers: list[str] = Field(default_factory=list, description="Deal-breaker gaps")
    keywords_matched: list[str] = Field(default_factory=list, description="JD keywords found in career profile")
    legitimacy_tier: str = Field(default="unknown", description="high_confidence | proceed_with_caution | suspicious | unknown")


# ---------------------------------------------------------------------------
# Dimension weights (from career-ops multi-offer comparison matrix)
# ---------------------------------------------------------------------------

DIMENSION_WEIGHTS = {
    "role_alignment": 0.25,
    "skill_match": 0.15,
    "level_fit": 0.15,
    "compensation_fit": 0.10,
    "growth_potential": 0.10,
    "remote_quality": 0.05,
    "company_reputation": 0.05,
    "tech_stack": 0.05,
    "speed_to_offer": 0.05,
    "culture_signals": 0.05,
}

# Grade boundaries (from career-ops)
GRADE_BOUNDARIES = [
    (4.5, "A"),
    (3.5, "B"),
    (2.5, "C"),
    (1.5, "D"),
    (0.0, "F"),
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


# ---------------------------------------------------------------------------
# Archetype detection keywords (from career-ops _shared.md)
# ---------------------------------------------------------------------------

ARCHETYPE_SIGNALS = {
    "LLMOps": ["observability", "evals", "pipelines", "monitoring", "reliability", "mlops", "model serving"],
    "Agentic": ["agent", "hitl", "orchestration", "workflow", "multi-agent", "autonomous"],
    "PM": ["prd", "roadmap", "discovery", "stakeholder", "product manager", "product management"],
    "SA": ["architecture", "enterprise", "integration", "systems design", "solutions architect"],
    "FDE": ["client-facing", "deploy", "prototype", "field engineer", "forward deployed"],
    "Transformation": ["change management", "adoption", "enablement", "transformation", "digital transformation"],
}


# ---------------------------------------------------------------------------
# Scoring prompt
# ---------------------------------------------------------------------------

SCORING_SYSTEM_PROMPT = """You are an expert career advisor evaluating job fit.

You will receive a candidate's career profile (extracted achievements and skills) and a job description.
Score the match across 10 dimensions using the weights provided.

## Scoring Rules
- Each dimension is scored 1.0-5.0 (1=poor fit, 5=excellent fit)
- Be specific in reasoning — cite exact JD requirements and candidate achievements
- Identify hard blockers (deal-breakers like "requires 10+ years, candidate has 4")
- Detect the role archetype from the JD keywords
- Assess posting legitimacy if signals are visible in the JD

## Archetype Detection
Classify into one of: SWE, PM, DS, Design, Ops, Leadership, LLMOps, Agentic, SA, FDE, Transformation
Use keyword signals from the JD to determine the closest match.

## Legitimacy Assessment
- high_confidence: specific requirements, clear team/project description, reasonable expectations
- proceed_with_caution: vague requirements, very broad scope, no team context
- suspicious: unrealistic expectations, buzzword-heavy with no substance, signs of ghost posting

## Output Format
Respond with a single JSON object matching the schema exactly. No markdown, no code fences, just JSON."""


def build_scoring_prompt(
    nuggets: list[NuggetResult],
    jd_text: str,
    career_graph: dict | None = None,
) -> str:
    """Build the user prompt for job scoring."""

    # Format nuggets into readable context
    nugget_lines = []
    for i, n in enumerate(nuggets, 1):
        nugget_lines.append(
            f"{i}. [{n.importance}] {n.answer}"
            f"\n   Company: {n.company} | Role: {n.role} | Skills: {', '.join(n.tags[:5])}"
        )
    nuggets_text = "\n".join(nugget_lines) if nugget_lines else "(No career data available)"

    # Career graph context (target roles, if available)
    target_roles_text = ""
    if career_graph and career_graph.get("target_roles"):
        target_roles_text = f"\n## Target Roles\n{', '.join(career_graph['target_roles'])}"

    weights_table = "\n".join(
        f"- {dim.replace('_', ' ').title()}: {w*100:.0f}%"
        for dim, w in DIMENSION_WEIGHTS.items()
    )

    return f"""## Candidate Career Profile
{nuggets_text}
{target_roles_text}

## Job Description
{jd_text}

## Dimension Weights
{weights_table}

Score this job against the candidate's profile. Return JSON with these fields:
overall_score, overall_grade, role_alignment, skill_match (include gaps and hard_blockers arrays),
level_fit, compensation_fit, growth_potential, remote_quality, company_reputation, tech_stack,
speed_to_offer, culture_signals, role_archetype, recommended_action, skill_gaps, hard_blockers,
keywords_matched, legitimacy_tier.

Each dimension must have: score (1.0-5.0), weight, reasoning (2-3 sentences), evidence (list of strings)."""


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

async def score_application(
    user_id: str,
    jd_text: str,
    supabase_client,
    career_graph: dict | None = None,
) -> JobScore:
    """Score a job description against a user's career nuggets.

    Returns a validated JobScore Pydantic model.
    """
    started = time.time()

    # 1. Hybrid retrieve top 15 nuggets (reuse existing infrastructure)
    #    hybrid_retrieve gets JINA_API_KEY from env internally
    nuggets, _method = await hybrid_retrieve(
        sb=supabase_client,
        user_id=user_id,
        query=jd_text,
        limit=15,
    )
    logger.info(f"Scoring: retrieved {len(nuggets)} nuggets via {_method} in {time.time()-started:.1f}s")

    # 2. Build prompt
    user_prompt = build_scoring_prompt(nuggets, jd_text, career_graph)

    # 3. Call Gemini Flash with rate limiting (quality-sensitive structured output)
    gemini = GeminiProvider(
        api_key=worker_config.GEMINI_API_KEY,
        model_id=worker_config.GEMINI_MODEL_ID,
    )
    async with gemini_limiter(user_id):
        response = await gemini.complete(
            system=SCORING_SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.2,  # low temperature for consistent scoring
        )
    logger.info(
        f"Scoring: Gemini call done in {time.time()-started:.1f}s "
        f"({response.input_tokens} in, {response.output_tokens} out)"
    )

    # 4. Parse JSON response
    raw_text = response.text.strip()
    # Strip markdown code fences if Gemini wraps the JSON
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]  # remove first line
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

    try:
        raw_json = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(f"Scoring: JSON parse failed: {e}\nRaw: {raw_text[:500]}")
        raise ValueError(f"Gemini returned invalid JSON: {e}")

    # 5. Validate with Pydantic
    score = JobScore.model_validate(raw_json)

    # 6. Recalculate overall_score from dimension weights (don't trust LLM math)
    dimensions = {
        "role_alignment": score.role_alignment,
        "skill_match": score.skill_match,
        "level_fit": score.level_fit,
        "compensation_fit": score.compensation_fit,
        "growth_potential": score.growth_potential,
        "remote_quality": score.remote_quality,
        "company_reputation": score.company_reputation,
        "tech_stack": score.tech_stack,
        "speed_to_offer": score.speed_to_offer,
        "culture_signals": score.culture_signals,
    }
    recalc_score = sum(
        dim.score * DIMENSION_WEIGHTS[name]
        for name, dim in dimensions.items()
    )
    score.overall_score = round(recalc_score, 2)
    score.overall_grade = score_to_grade(recalc_score)

    # Merge gaps from skill_match dimension
    if score.skill_match.gaps:
        score.skill_gaps = list(set(score.skill_gaps + score.skill_match.gaps))
    if score.skill_match.hard_blockers:
        score.hard_blockers = list(set(score.hard_blockers + score.skill_match.hard_blockers))

    # Set recommended action based on recalculated grade
    score.recommended_action = grade_to_action(score.overall_grade, bool(score.hard_blockers))

    elapsed = time.time() - started
    logger.info(
        f"Scoring complete: {score.overall_grade} ({score.overall_score:.2f}) "
        f"| archetype={score.role_archetype} | action={score.recommended_action} "
        f"| gaps={len(score.skill_gaps)} | blockers={len(score.hard_blockers)} "
        f"| {elapsed:.1f}s total"
    )

    return score
