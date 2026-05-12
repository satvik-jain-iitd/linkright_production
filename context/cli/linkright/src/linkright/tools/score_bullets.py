"""Tool 8: score_bullets - Bullet Relevance Score (BRS) engine.

Scores candidate bullet points against job description keywords and relevance
signals. Returns tiered, sorted bullets for LLM to decide which to include.
"""

from __future__ import annotations

import re
from pydantic import BaseModel, Field, ConfigDict


class CandidateBullet(BaseModel):
    """A single bullet point from candidate's experience."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "project_id": "proj_001_aws_migration",
        "raw_text": "Led migration of 50 microservices from on-prem to AWS, reducing costs by 40% ($2.3M annually)",
        "interview_data": {
            "entry_index": 0,
            "tools": ["AWS", "Kubernetes"],
            "team_size": 12,
            "context": "Recent project at current company"
        }
    }})

    project_id: str = Field(
        ...,
        description="Unique identifier linking to company/project in interview data"
    )
    raw_text: str = Field(
        ...,
        description="Original bullet text from candidate (plain text, no HTML)"
    )
    interview_data: dict = Field(
        default_factory=dict,
        description="Metrics, tools, team size, context from Phase C"
    )


class ScoredBullet(BaseModel):
    """A bullet point with its relevance score and components."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "project_id": "proj_001_aws_migration",
        "raw_text": "Led migration of 50 microservices from on-prem to AWS, reducing costs by 40% ($2.3M annually)",
        "brs": 0.85,
        "tier": 1,
        "keyword_matches": ["AWS", "migration", "costs"],
        "score_breakdown": {
            "keyword_overlap": 0.9,
            "metric_magnitude": 1.0,
            "recency": 1.0,
            "leadership": 1.0,
            "uniqueness": 0.75
        }
    }})

    project_id: str = Field(
        ...,
        description="Links back to CandidateBullet"
    )
    raw_text: str = Field(
        ...,
        description="Original bullet text"
    )
    brs: float = Field(
        ...,
        description="Bullet Relevance Score (0.0-1.0)"
    )
    tier: int = Field(
        ...,
        description="1=must-include (BRS >= 0.7), 2=should-include (0.4-0.7), 3=nice-to-have (< 0.4)"
    )
    keyword_matches: list[str] = Field(
        ...,
        description="JD keywords found in this bullet"
    )
    score_breakdown: dict = Field(
        ...,
        description="{keyword_overlap: float, metric_magnitude: float, recency: float, leadership: float, uniqueness: float}"
    )


class ScoreBulletsInput(BaseModel):
    """Input for resume_score_bullets tool."""

    model_config = ConfigDict(json_schema_extra={})

    bullets: list[CandidateBullet] = Field(
        ...,
        description="List of candidate bullets from interview"
    )
    jd_keywords: list[dict] = Field(
        ...,
        description="[{keyword: str, category: 'skill'|'tool'|'action'|'domain'}, ...]"
    )
    career_level: str = Field(
        ...,
        description="'fresher'|'entry'|'mid'|'senior'|'executive'"
    )
    total_bullet_budget: int = Field(
        ...,
        description="Maximum bullets that fit the page budget"
    )


class ScoreBulletsOutput(BaseModel):
    """Output from resume_score_bullets tool."""

    model_config = ConfigDict(json_schema_extra={})

    scored_bullets: list[ScoredBullet] = Field(
        ...,
        description="All bullets scored, sorted by BRS descending"
    )
    tier_1_count: int = Field(
        ...,
        description="Count of Tier 1 bullets (BRS >= 0.7)"
    )
    tier_2_count: int = Field(
        ...,
        description="Count of Tier 2 bullets (0.4-0.7)"
    )
    tier_3_count: int = Field(
        ...,
        description="Count of Tier 3 bullets (< 0.4)"
    )
    recommended_bullets: list[str] = Field(
        ...,
        description="project_ids of top N bullets to include (by total_bullet_budget)"
    )
    dropped_bullets: list[str] = Field(
        ...,
        description="project_ids of bullets that don't fit the budget"
    )


def _find_keyword_matches(raw_text: str, jd_keywords: list[dict]) -> tuple[list[str], float]:
    """Find all JD keywords that appear in bullet text.

    Case-insensitive substring matching.

    Args:
        raw_text: Bullet text to search
        jd_keywords: List of {keyword, category} dicts

    Returns:
        Tuple of (matched_keywords list, keyword_overlap score 0.0-1.0)
    """
    text_lower = raw_text.lower()
    matches = []

    for kw_dict in jd_keywords:
        keyword = kw_dict.get("keyword", "").lower()
        if not keyword:
            continue

        # Case-insensitive substring match
        if keyword in text_lower:
            matches.append(keyword)

    # Calculate overlap score: count / total, capped at 1.0
    if len(jd_keywords) == 0:
        overlap = 0.0
    else:
        overlap = min(len(matches) / len(jd_keywords), 1.0)

    return matches, overlap


def _calculate_metric_magnitude(raw_text: str) -> float:
    """Determine metric magnitude score based on quantification in text.

    - Dollar amounts ($500K, 500K) or percentages (25%, 300%): 1.0
    - Counts/numbers (5 projects, 1000 users): 0.7
    - Qualitative only: 0.3

    Args:
        raw_text: Bullet text

    Returns:
        Metric magnitude score 0.3-1.0
    """
    text_lower = raw_text.lower()

    # Check for dollar amounts
    if re.search(r'\$[\d,.KMB]+', raw_text) or re.search(r'[\d,.]+[KMB]', text_lower):
        return 1.0

    # Check for percentages
    if re.search(r'\d+%', raw_text):
        return 1.0

    # Check for other numbers (counts, rates, etc.)
    if re.search(r'\d+', raw_text):
        return 0.7

    # No quantification
    return 0.3


def _calculate_recency(bullet: CandidateBullet) -> float:
    """Calculate recency score based on entry_index from interview_data.

    - entry_index 0 (most recent): 1.0
    - entry_index 1: 0.8
    - entry_index 2: 0.6
    - entry_index 3+: 0.4

    Args:
        bullet: CandidateBullet with interview_data

    Returns:
        Recency score 0.4-1.0
    """
    entry_index = bullet.interview_data.get("entry_index", 999)

    if entry_index == 0:
        return 1.0
    elif entry_index == 1:
        return 0.8
    elif entry_index == 2:
        return 0.6
    else:
        return 0.4


def _calculate_leadership(raw_text: str) -> float:
    """Calculate leadership score based on verbs in text.

    - Contains lead/manage/mentor/direct/oversee/coordinate/led: 1.0
    - Contains collaborate/work with/support/contribute/assist/partner: 0.5
    - Otherwise: 0.0

    Args:
        raw_text: Bullet text

    Returns:
        Leadership score 0.0-1.0
    """
    text_lower = raw_text.lower()

    # Strong leadership indicators
    leadership_verbs = ["team", "lead", "manage", "mentor", "direct", "oversee", "coordinate", "led"]
    for verb in leadership_verbs:
        if verb in text_lower:
            return 1.0

    # Collaborative indicators
    collaborative_verbs = ["collaborate", "work with", "support", "contribute", "assist", "partner"]
    for verb in collaborative_verbs:
        if verb in text_lower:
            return 0.5

    return 0.0


def _extract_skills_and_verbs(raw_text: str) -> set[str]:
    """Extract simple skills and action verbs from bullet text.

    Looks for common action verbs (led, built, created, etc.) and
    potential skill keywords (AWS, Python, SQL, etc.).

    Args:
        raw_text: Bullet text

    Returns:
        Set of extracted skill/verb tokens
    """
    text_lower = raw_text.lower()
    skills = set()

    # Common action verbs
    verbs = [
        "led", "built", "created", "developed", "managed", "directed",
        "launched", "increased", "reduced", "improved", "optimized",
        "designed", "implemented", "deployed", "architected", "mentored"
    ]

    for verb in verbs:
        if verb in text_lower:
            skills.add(verb)

    # Common skills/tools (case-insensitive match)
    common_skills = [
        "python", "java", "javascript", "sql", "aws", "azure", "gcp",
        "kubernetes", "docker", "react", "angular", "terraform", "ci/cd",
        "machine learning", "data science", "analytics", "leadership"
    ]

    for skill in common_skills:
        if skill in text_lower:
            skills.add(skill)

    return skills


def _calculate_uniqueness(
    bullet: CandidateBullet,
    higher_scored_bullets: list[CandidateBullet],
    all_scored: list[dict]  # track of already calculated scores
) -> float:
    """Calculate uniqueness score relative to higher-scored bullets.

    - If bullet contains skill/verb not in higher-scored: 1.0
    - If partial overlap (same verb, different domain): 0.5
    - If exact duplicate: 0.0

    Args:
        bullet: Current bullet being scored
        higher_scored_bullets: Bullets with higher BRS scores
        all_scored: List of already-scored bullet info for lookup

    Returns:
        Uniqueness score 0.0-1.0
    """
    current_skills = _extract_skills_and_verbs(bullet.raw_text)

    if not current_skills:
        return 0.5  # No identifiable skills: medium uniqueness

    # Extract skills from higher-scored bullets
    higher_skills = set()
    for higher_bullet in higher_scored_bullets:
        higher_skills.update(_extract_skills_and_verbs(higher_bullet.raw_text))

    # Check for overlap
    exact_matches = current_skills & higher_skills
    unique_skills = current_skills - higher_skills

    if not exact_matches:
        # All skills are unique to this bullet
        return 1.0
    elif unique_skills:
        # Partial overlap: some unique, some shared
        return 0.5
    else:
        # All skills are duplicates of higher-scored bullets
        return 0.0


def _calculate_brs(
    bullet: CandidateBullet,
    jd_keywords: list[dict],
    higher_scored_bullets: list[CandidateBullet]
) -> tuple[float, dict, list[str]]:
    """Calculate Bullet Relevance Score (BRS) for a single bullet.

    BRS = (keyword_overlap x 0.35) + (metric_magnitude x 0.25) +
          (recency x 0.20) + (leadership x 0.10) + (uniqueness x 0.10)

    All component scores are normalized to [0.0, 1.0].

    Args:
        bullet: CandidateBullet to score
        jd_keywords: List of JD keywords to match against
        higher_scored_bullets: Bullets already scored (for uniqueness calc)

    Returns:
        Tuple of (brs_score, score_breakdown dict, keyword_matches list)
    """
    # 1. Keyword overlap (35%)
    keyword_matches, keyword_overlap = _find_keyword_matches(bullet.raw_text, jd_keywords)

    # 2. Metric magnitude (25%)
    metric_magnitude = _calculate_metric_magnitude(bullet.raw_text)

    # 3. Recency (20%)
    recency = _calculate_recency(bullet)

    # 4. Leadership (10%)
    leadership = _calculate_leadership(bullet.raw_text)

    # 5. Uniqueness (10%)
    uniqueness = _calculate_uniqueness(bullet, higher_scored_bullets, [])

    # Weighted sum
    brs = (
        keyword_overlap * 0.35 +
        metric_magnitude * 0.25 +
        recency * 0.20 +
        leadership * 0.10 +
        uniqueness * 0.10
    )

    score_breakdown = {
        "keyword_overlap": round(keyword_overlap, 3),
        "metric_magnitude": round(metric_magnitude, 3),
        "recency": round(recency, 3),
        "leadership": round(leadership, 3),
        "uniqueness": round(uniqueness, 3)
    }

    return round(brs, 3), score_breakdown, keyword_matches


def _assign_tier(brs: float) -> int:
    """Assign tier based on BRS score.

    - BRS >= 0.7: Tier 1 (must-include)
    - 0.4 <= BRS < 0.7: Tier 2 (should-include)
    - BRS < 0.4: Tier 3 (nice-to-have)

    Args:
        brs: Bullet Relevance Score

    Returns:
        Tier number (1, 2, or 3)
    """
    if brs >= 0.7:
        return 1
    elif brs >= 0.4:
        return 2
    else:
        return 3


def _recommend_bullets(
    scored_bullets: list[ScoredBullet],
    total_bullet_budget: int
) -> tuple[list[str], list[str]]:
    """Recommend top N bullets based on BRS and tier.

    Prioritizes Tier 1, then Tier 2, then Tier 3, up to total_bullet_budget.

    Args:
        scored_bullets: List of ScoredBullet objects (already sorted by BRS desc)
        total_bullet_budget: Maximum number of bullets to recommend

    Returns:
        Tuple of (recommended project_ids, dropped project_ids)
    """
    recommended = []
    dropped = []

    # Sort by tier first (ascending: 1, 2, 3), then by BRS (descending)
    tier_sorted = sorted(scored_bullets, key=lambda b: (b.tier, -b.brs))

    for bullet in tier_sorted:
        if len(recommended) < total_bullet_budget:
            recommended.append(bullet.project_id)
        else:
            dropped.append(bullet.project_id)

    return recommended, dropped


def score_bullets(params: ScoreBulletsInput) -> ScoreBulletsOutput:
    """Score candidate bullets against job description keywords and signals.

    Computes Bullet Relevance Score (BRS) for every candidate bullet using
    five weighted components: keyword overlap, metric magnitude, recency,
    leadership indicators, and uniqueness. Returns tiered and sorted bullets
    for LLM to decide which to include in the final resume.

    Algorithm:
    1. For each bullet, compute BRS using weighted formula:
       - keyword_overlap (35%): how many JD keywords appear in bullet
       - metric_magnitude (25%): does bullet have dollar/percentage/count metrics
       - recency (20%): is this from recent experience (entry_index)
       - leadership (10%): does bullet show team/mentoring signals
       - uniqueness (10%): is the skill/verb unique vs higher-scored bullets

    2. Assign tier based on BRS:
       - Tier 1: BRS >= 0.7 (must-include)
       - Tier 2: 0.4-0.7 (should-include)
       - Tier 3: < 0.4 (nice-to-have)

    3. Recommend top N bullets by BRS (where N = total_bullet_budget),
       prioritizing Tier 1 first

    4. Return sorted list of all scored bullets plus recommended selection

    Args:
        params: ScoreBulletsInput with bullets, JD keywords, career_level, budget

    Returns:
        ScoreBulletsOutput containing scored bullets, tiers, and recommendations
    """
    # Score each bullet
    scored_bullets_list = []
    higher_scored = []  # Track bullets in descending score order for uniqueness calc

    # First pass: score all bullets
    for bullet in params.bullets:
        brs, breakdown, matches = _calculate_brs(
            bullet,
            params.jd_keywords,
            higher_scored
        )

        tier = _assign_tier(brs)

        scored = ScoredBullet(
            project_id=bullet.project_id,
            raw_text=bullet.raw_text,
            brs=brs,
            tier=tier,
            keyword_matches=matches,
            score_breakdown=breakdown
        )

        scored_bullets_list.append(scored)
        higher_scored.append(bullet)

    # Sort by BRS descending
    scored_bullets_list.sort(key=lambda b: -b.brs)

    # Recalculate uniqueness with proper higher-scored list
    for i, scored_bullet in enumerate(scored_bullets_list):
        if i > 0:
            # Get the bullets that scored higher
            higher = [sb.project_id for sb in scored_bullets_list[:i]]
            original_bullet = next(b for b in params.bullets if b.project_id == scored_bullet.project_id)
            higher_scored_bullets = [b for b in params.bullets if b.project_id in higher]

            uniqueness = _calculate_uniqueness(original_bullet, higher_scored_bullets, [])
            scored_bullet.score_breakdown["uniqueness"] = round(uniqueness, 3)

            # Recalculate BRS with new uniqueness
            brs = (
                scored_bullet.score_breakdown["keyword_overlap"] * 0.35 +
                scored_bullet.score_breakdown["metric_magnitude"] * 0.25 +
                scored_bullet.score_breakdown["recency"] * 0.20 +
                scored_bullet.score_breakdown["leadership"] * 0.10 +
                uniqueness * 0.10
            )
            scored_bullet.brs = round(brs, 3)
            scored_bullet.tier = _assign_tier(brs)

    # Re-sort after uniqueness recalculation
    scored_bullets_list.sort(key=lambda b: -b.brs)

    # Count tiers
    tier_1 = sum(1 for b in scored_bullets_list if b.tier == 1)
    tier_2 = sum(1 for b in scored_bullets_list if b.tier == 2)
    tier_3 = sum(1 for b in scored_bullets_list if b.tier == 3)

    # Recommend bullets
    recommended, dropped = _recommend_bullets(scored_bullets_list, params.total_bullet_budget)

    return ScoreBulletsOutput(
        scored_bullets=scored_bullets_list,
        tier_1_count=tier_1,
        tier_2_count=tier_2,
        tier_3_count=tier_3,
        recommended_bullets=recommended,
        dropped_bullets=dropped
    )
