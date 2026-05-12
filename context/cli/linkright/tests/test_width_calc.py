"""Unit tests for measure_width tool — the core width engine."""
from linkright.tools.measure_width import measure_width, MeasureWidthInput
from linkright.utils.html_parser import parse_bold_segments


class TestBoldParsing:
    """Verify the fixed bold regex works correctly."""

    def test_simple_bold(self):
        segments = parse_bold_segments("<b>hello</b> world")
        assert segments[0] == ("hello", True)
        assert segments[1] == (" world", False)

    def test_multi_word_bold(self):
        """This was the original bug — .? only captured first char."""
        segments = parse_bold_segments("<b>Software Engineer</b> at Google")
        bold_text = [s[0] for s in segments if s[1]]
        assert "Software Engineer" in bold_text

    def test_strong_tag(self):
        segments = parse_bold_segments("<strong>metrics</strong> matter")
        assert segments[0] == ("metrics", True)

    def test_no_bold(self):
        segments = parse_bold_segments("plain text only")
        assert len(segments) == 1
        assert segments[0] == ("plain text only", False)

    def test_multiple_bold_spans(self):
        segments = parse_bold_segments("Drove <b>$2.3M</b> savings across <b>4 teams</b>")
        bold_texts = [s[0] for s in segments if s[1]]
        assert "$2.3M" in bold_texts
        assert "4 teams" in bold_texts


class TestMeasureWidth:
    """Verify width measurement returns sensible results."""

    def test_bullet_returns_output(self, template_config):
        result = measure_width(
            MeasureWidthInput(text_html="Built a product that grew revenue by 40%", line_type="bullet"),
            template_config=template_config,
        )
        assert result.weighted_total > 0
        assert result.target_95 > 0
        assert result.fill_percentage > 0
        assert result.status in ("PASS", "TOO_SHORT", "OVERFLOW")

    def test_empty_text(self, template_config):
        result = measure_width(
            MeasureWidthInput(text_html="", line_type="bullet"),
            template_config=template_config,
        )
        assert result.weighted_total == 0
        assert result.status == "TOO_SHORT"

    def test_bold_adds_weight(self, template_config):
        plain = measure_width(
            MeasureWidthInput(text_html="revenue growth of 40 percent", line_type="bullet"),
            template_config=template_config,
        )
        bold = measure_width(
            MeasureWidthInput(text_html="revenue growth of <b>40 percent</b>", line_type="bullet"),
            template_config=template_config,
        )
        # Bold text should have higher weighted total (bold chars are wider)
        assert bold.weighted_total >= plain.weighted_total

    def test_different_line_types(self, template_config):
        text = "Senior Product Manager"
        bullet = measure_width(
            MeasureWidthInput(text_html=text, line_type="bullet"),
            template_config=template_config,
        )
        header = measure_width(
            MeasureWidthInput(text_html=text, line_type="entry_header"),
            template_config=template_config,
        )
        # Different line types have different budgets
        assert bullet.target_95 != header.target_95

    def test_fill_percentage_calculation(self, template_config):
        result = measure_width(
            MeasureWidthInput(
                text_html="Drove $2.3M annual savings by optimizing data acquisition strategy across 4 vendor contracts",
                line_type="bullet",
            ),
            template_config=template_config,
        )
        assert 0 < result.fill_percentage < 200
        assert result.weighted_total > 0
        assert result.raw_budget > 0
