"""Tests for html_parser.parse_bold_segments."""

import sys
import os

# Allow imports from the sync directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.html_parser import parse_bold_segments


class TestParseBoldSegments:
    """Tests for the parse_bold_segments function."""

    def test_multi_character_bold_text(self):
        html = "<b>revenue growth</b>"
        result = parse_bold_segments(html)
        assert result == [("revenue growth", True)]

    def test_bold_with_numbers(self):
        html = "<b>35% to 85%</b>"
        result = parse_bold_segments(html)
        assert result == [("35% to 85%", True)]

    def test_nested_long_bold(self):
        html = "<b>100M+ accounts across 40+ markets</b>"
        result = parse_bold_segments(html)
        assert result == [("100M+ accounts across 40+ markets", True)]

    def test_no_bold_tags(self):
        html = "plain text with no bold tags"
        result = parse_bold_segments(html)
        assert result == [("plain text with no bold tags", False)]

    def test_multiple_bold_segments(self):
        html = "Drove <b>revenue growth of 40%</b> and reduced churn by <b>15%</b>"
        result = parse_bold_segments(html)
        assert result == [
            ("Drove ", False),
            ("revenue growth of 40%", True),
            (" and reduced churn by ", False),
            ("15%", True),
        ]

    def test_empty_string(self):
        result = parse_bold_segments("")
        assert result == []

    def test_strong_tag(self):
        html = "<strong>important text</strong>"
        result = parse_bold_segments(html)
        assert result == [("important text", True)]

    def test_bold_with_style_attribute(self):
        html = '<b style="font-weight:700">styled bold</b>'
        result = parse_bold_segments(html)
        assert result == [("styled bold", True)]
