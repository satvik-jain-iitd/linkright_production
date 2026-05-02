"""Unit tests for quality judge agent — programmatic validation."""
from linkright.agents.quality_judge import judge_quality


class TestQualityJudge:
    def test_basic_quality_report(self, sample_written_bullets, sample_jd_analysis):
        report = judge_quality(
            written_bullets=sample_written_bullets,
            jd_analysis=sample_jd_analysis,
        )
        assert report.overall_grade in ("A", "B", "C", "D", "F")
        assert 0 <= report.keyword_coverage <= 100
        assert 0 <= report.width_fill_avg <= 100
        assert isinstance(report.suggestions, list)

    def test_no_duplicate_verbs(self, sample_written_bullets, sample_jd_analysis):
        report = judge_quality(
            written_bullets=sample_written_bullets,
            jd_analysis=sample_jd_analysis,
        )
        # Our fixtures have unique verbs (reduced, drove, increased)
        assert len(report.verb_duplicates) == 0

    def test_contrast_check_runs(self, sample_written_bullets, sample_jd_analysis):
        report = judge_quality(
            written_bullets=sample_written_bullets,
            jd_analysis=sample_jd_analysis,
            brand_primary="#000000",
            background="#FFFFFF",
        )
        assert report.contrast_passes is True

    def test_page_fit_check(self, sample_written_bullets, sample_jd_analysis):
        report = judge_quality(
            written_bullets=sample_written_bullets,
            jd_analysis=sample_jd_analysis,
        )
        # 3 bullets should easily fit on one page
        assert report.page_fits is True
