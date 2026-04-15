"""Tests for assemble_html bug fixes: double-nested links and missing section wrappers."""

import re
import sys
import os

# Add the parent package to the path so we can import the module directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.assemble_html import _replace_header_content, _replace_section_content, HeaderData, SectionContent


def _make_template_with_header():
    """Minimal HTML template with header elements for testing."""
    return (
        '<header>'
        '<div class="name">PLACEHOLDER</div>'
        '<div class="role">PLACEHOLDER</div>'
        '<div class="contact-info"><span>placeholder</span></div>'
        '</header>'
    )


def _make_template_with_section():
    """Minimal HTML template with a section comment + div for testing."""
    return (
        '<!-- 1. EXPERIENCE -->\n'
        '<div class="section">OLD CONTENT</div>'
    )


# --- Bug 1 tests: double-nested <a> tags ---

def test_prelinked_contact_not_double_wrapped():
    """If a contact value already contains <a href="...">, it must not be wrapped again."""
    header = HeaderData(
        name="Test User",
        role="Engineer",
        contacts=[
            'LinkedIn: <a href="https://linkedin.com/in/test">linkedin.com/in/test</a>',
        ],
    )
    html = _make_template_with_header()
    result = _replace_header_content(html, header)

    # Count occurrences of opening <a tags — should be exactly 1
    a_tags = re.findall(r"<a\s", result, re.IGNORECASE)
    assert len(a_tags) == 1, f"Expected 1 <a> tag but found {len(a_tags)} in: {result}"


def test_plain_contact_gets_wrapped():
    """A plain contact value (no existing <a>) should be wrapped in a link."""
    header = HeaderData(
        name="Test User",
        role="Engineer",
        contacts=[
            "Email: test@example.com",
        ],
    )
    html = _make_template_with_header()
    result = _replace_header_content(html, header)

    # Should contain exactly one <a href="mailto:..."> tag
    a_tags = re.findall(r"<a\s", result, re.IGNORECASE)
    assert len(a_tags) == 1, f"Expected 1 <a> tag but found {len(a_tags)} in: {result}"
    assert "mailto:test@example.com" in result


# --- Bug 2 test: section wrapper ---

def test_section_content_gets_wrapper_div():
    """Injected section HTML must be wrapped in exactly one <div class="section">."""
    sections = [
        SectionContent(section_html='<div class="entry">My Entry</div>', section_order=1),
    ]
    html = _make_template_with_section()
    result = _replace_section_content(html, sections)

    # The replacement should contain exactly one <div class="section"> wrapper
    wrappers = re.findall(r'<div class="section">', result)
    assert len(wrappers) == 1, f"Expected 1 section wrapper but found {len(wrappers)} in: {result}"

    # The inner content should be present inside the wrapper
    assert '<div class="entry">My Entry</div>' in result


if __name__ == "__main__":
    test_prelinked_contact_not_double_wrapped()
    print("PASS: test_prelinked_contact_not_double_wrapped")

    test_plain_contact_gets_wrapped()
    print("PASS: test_plain_contact_gets_wrapped")

    test_section_content_gets_wrapper_div()
    print("PASS: test_section_content_gets_wrapper_div")

    print("\nAll tests passed.")
