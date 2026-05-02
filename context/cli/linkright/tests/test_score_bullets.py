"""Unit tests for score_bullets tool — BRS 5-factor scoring model."""
from linkright.tools.score_bullets import (
    score_bullets,
    ScoreBulletsInput,
    CandidateBullet,
)


def _make_bullet(raw_text: str, project_id: str = "proj-1", **interview_data):
    return CandidateBullet(
        project_id=project_id,
        raw_text=raw_text,
        interview_data=interview_data,
    )


class TestScoreBullets:
    def test_basic_scoring(self):
        result = score_bullets(ScoreBulletsInput(
            bullets=[
                _make_bullet("Reduced bid turnaround by 40% using ML models", tools=["Python", "ML"]),
                _make_bullet("Organized team meetings weekly", tools=[]),
            ],
            jd_keywords=[
                {"keyword": "ML", "category": "skill"},
                {"keyword": "Python", "category": "tool"},
            ],
            career_level="senior",
            total_bullet_budget=8,
        ))
        assert len(result.scored_bullets) == 2
        # ML bullet should score higher
        assert result.scored_bullets[0].brs >= result.scored_bullets[1].brs

    def test_tier_assignment(self):
        result = score_bullets(ScoreBulletsInput(
            bullets=[
                _make_bullet("Drove $2.3M savings via data strategy", tools=["SQL"]),
                _make_bullet("Updated documentation for onboarding"),
                _make_bullet("Built CI/CD pipeline reducing deploy time by 60%", tools=["Jenkins"]),
            ],
            jd_keywords=[
                {"keyword": "data strategy", "category": "skill"},
                {"keyword": "SQL", "category": "tool"},
            ],
            career_level="mid",
            total_bullet_budget=8,
        ))
        # All bullets should have a tier (1, 2, or 3)
        for b in result.scored_bullets:
            assert b.tier in (1, 2, 3)

    def test_tier_counts_sum(self):
        bullets = [_make_bullet(f"Achievement {i}") for i in range(5)]
        result = score_bullets(ScoreBulletsInput(
            bullets=bullets,
            jd_keywords=[{"keyword": "test", "category": "skill"}],
            career_level="entry",
            total_bullet_budget=8,
        ))
        assert result.tier_1_count + result.tier_2_count + result.tier_3_count == 5

    def test_keyword_match_detection(self):
        result = score_bullets(ScoreBulletsInput(
            bullets=[_make_bullet("Built ML pipeline for real-time prediction", tools=["Python", "ML"])],
            jd_keywords=[
                {"keyword": "ML", "category": "skill"},
                {"keyword": "real-time", "category": "domain"},
            ],
            career_level="mid",
            total_bullet_budget=8,
        ))
        scored = result.scored_bullets[0]
        assert len(scored.keyword_matches) > 0

    def test_sorted_by_brs_descending(self):
        bullets = [
            _make_bullet("Weak achievement with no keywords"),
            _make_bullet("Strong ML pipeline with 40% improvement", tools=["Python", "ML"]),
            _make_bullet("Medium data analysis project", tools=["SQL"]),
        ]
        result = score_bullets(ScoreBulletsInput(
            bullets=bullets,
            jd_keywords=[
                {"keyword": "ML", "category": "skill"},
                {"keyword": "Python", "category": "tool"},
            ],
            career_level="senior",
            total_bullet_budget=8,
        ))
        brs_scores = [b.brs for b in result.scored_bullets]
        assert brs_scores == sorted(brs_scores, reverse=True)
