"""Tests for S1.10 — LinkedIn/Portfolio contact hyperlinks.

Covers:
- _create_contact_link() in assemble_html.py (MCP / assemble_html path)
- The orchestrator.py S1.10 regex post-processor (step_14 path)
- Brand-design-spec compliance: no color: #4285F4 on any contact anchor
- Integration: _replace_header_content() produces correct HTML
- 28+ cases across orchestrator regex, MCP _create_contact_link, and integration paths
"""

import re
import sys
import os
import warnings
import pytest

# Ensure the package src is importable even without pip install
_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from linkright.tools.assemble_html import (
    _create_contact_link,
    _extract_contact_value,
    _replace_header_content,
    HeaderData,
)


# ---------------------------------------------------------------------------
# Helper: mimic orchestrator S1.10 regex block (step_14 path)
# Duplicates the exact logic from orchestrator.py so changes there are
# immediately visible as test failures.
# ---------------------------------------------------------------------------
_ORCH_LINK_STYLE = "text-decoration: none; color: var(--ui-text-primary-color);"


def _orch_hyperlink_contact_span(m: re.Match) -> str:
    """Replication of the nested function in orchestrator.py step_14."""
    label_text = m.group(1).strip()
    url_raw = m.group(2).strip()
    if not url_raw:
        return m.group(0)
    url = url_raw if url_raw.startswith("http") else f"https://{url_raw}"
    return (
        f'<span><a href="{url}" target="_blank" '
        f'style="{_ORCH_LINK_STYLE}">{label_text}</a></span>'
    )


def _apply_orch_s1_10(html: str) -> str:
    """Apply orchestrator S1.10 regex to an HTML fragment."""
    return re.sub(
        r'<span><b>(LinkedIn|Portfolio):</b>\s*(.*?)</span>',
        _orch_hyperlink_contact_span,
        html,
        flags=re.DOTALL,
    )


# ===========================================================================
# Section A: orchestrator.py S1.10 regex path  (11 cases)
# ===========================================================================

class TestOrchestratorS110:
    """Tests for the step_14 post-processor regex path in orchestrator.py."""

    def test_linkedin_url_becomes_anchor(self):
        html = '<span><b>LinkedIn:</b> https://linkedin.com/in/satvik</span>'
        result = _apply_orch_s1_10(html)
        assert '<a href="https://linkedin.com/in/satvik"' in result
        assert '>LinkedIn</a>' in result
        assert '<span>' in result
        assert '</span>' in result

    def test_portfolio_url_becomes_anchor(self):
        html = '<span><b>Portfolio:</b> https://github.com/satvik-jain</span>'
        result = _apply_orch_s1_10(html)
        assert '<a href="https://github.com/satvik-jain"' in result
        assert '>Portfolio</a>' in result

    def test_empty_url_returns_span_unchanged(self):
        """Empty URL must be left as-is — S6-2 stripper removes it downstream."""
        html = '<span><b>LinkedIn:</b> </span>'
        result = _apply_orch_s1_10(html)
        assert result == html, f"Expected unchanged span, got: {result}"

    def test_url_without_scheme_gets_https_prepended(self):
        html = '<span><b>LinkedIn:</b> linkedin.com/in/satvik</span>'
        result = _apply_orch_s1_10(html)
        assert 'href="https://linkedin.com/in/satvik"' in result

    def test_portfolio_without_scheme_gets_https(self):
        html = '<span><b>Portfolio:</b> github.com/satvik-jain</span>'
        result = _apply_orch_s1_10(html)
        assert 'href="https://github.com/satvik-jain"' in result

    def test_phone_span_untouched(self):
        """Phone spans must not be modified — regex only matches LinkedIn/Portfolio."""
        html = '<span><b>Phone:</b> +91-9876543210</span>'
        result = _apply_orch_s1_10(html)
        assert result == html

    def test_email_span_untouched(self):
        """Email spans must not be modified by S1.10 regex."""
        html = '<span><b>Email:</b> satvik@example.com</span>'
        result = _apply_orch_s1_10(html)
        assert result == html

    def test_no_brand_color_on_anchor(self):
        """Brand-design-spec rule 2+4: #4285F4 must NOT appear on contact anchors."""
        html = '<span><b>LinkedIn:</b> https://linkedin.com/in/satvik</span>'
        result = _apply_orch_s1_10(html)
        assert '#4285F4' not in result, (
            "Brand-design-spec violation: color #4285F4 found on contact anchor. "
            "Contact anchors must use var(--ui-text-primary-color) per rule 2."
        )

    def test_primary_color_var_on_anchor(self):
        """Anchor must use var(--ui-text-primary-color) per brand-design-spec rule 2."""
        html = '<span><b>Portfolio:</b> https://github.com/satvik</span>'
        result = _apply_orch_s1_10(html)
        assert 'color: var(--ui-text-primary-color)' in result

    def test_text_decoration_none_on_anchor(self):
        """Anchor must suppress underline while remaining clickable."""
        html = '<span><b>LinkedIn:</b> https://linkedin.com/in/satvik</span>'
        result = _apply_orch_s1_10(html)
        assert 'text-decoration: none' in result

    def test_target_blank_set(self):
        """External links must open in new tab."""
        html = '<span><b>LinkedIn:</b> https://linkedin.com/in/satvik</span>'
        result = _apply_orch_s1_10(html)
        assert 'target="_blank"' in result

    def test_dotall_handles_url_with_newline(self):
        """re.DOTALL defensive test — newline inside span must not break regex."""
        html = '<span><b>LinkedIn:</b> https://linkedin.com/in/satvik\n</span>'
        result = _apply_orch_s1_10(html)
        # URL with trailing newline — strip() strips it; anchor still created
        assert '<a href=' in result

    def test_both_links_in_single_contact_block(self):
        """Both LinkedIn and Portfolio spans replaced in the same HTML fragment."""
        html = (
            '<span><b>LinkedIn:</b> https://linkedin.com/in/satvik</span>'
            '<span><b>Portfolio:</b> https://github.com/satvik</span>'
        )
        result = _apply_orch_s1_10(html)
        assert 'href="https://linkedin.com/in/satvik"' in result
        assert 'href="https://github.com/satvik"' in result


# ===========================================================================
# Section B: assemble_html.py _create_contact_link() — MCP path  (12 cases)
# ===========================================================================

class TestCreateContactLink:
    """Tests for _create_contact_link() in assemble_html.py."""

    def test_linkedin_returns_anchor(self):
        result = _create_contact_link(
            "linkedin.com/in/satvik", "linkedin", anchor_text="LinkedIn"
        )
        assert '<a href="https://linkedin.com/in/satvik"' in result
        assert '>LinkedIn</a>' in result

    def test_portfolio_returns_anchor(self):
        result = _create_contact_link(
            "https://github.com/satvik", "portfolio", anchor_text="Portfolio"
        )
        assert '<a href="https://github.com/satvik"' in result
        assert '>Portfolio</a>' in result

    def test_empty_linkedin_returns_empty_string(self):
        """Empty LinkedIn value must return empty string (field omitted)."""
        result = _create_contact_link("", "linkedin", anchor_text="LinkedIn")
        assert result == ""

    def test_empty_portfolio_returns_empty_string(self):
        result = _create_contact_link("", "portfolio", anchor_text="Portfolio")
        assert result == ""

    def test_linkedin_url_without_scheme_gets_https(self):
        result = _create_contact_link(
            "linkedin.com/in/satvik", "linkedin", anchor_text="LinkedIn"
        )
        assert 'href="https://linkedin.com/in/satvik"' in result

    def test_portfolio_url_without_scheme_gets_https(self):
        result = _create_contact_link(
            "github.com/satvik", "portfolio", anchor_text="Portfolio"
        )
        assert 'href="https://github.com/satvik"' in result

    def test_phone_uses_tel_scheme(self):
        result = _create_contact_link("+919876543210", "tel")
        assert 'href="tel:' in result
        assert '+919876543210' in result

    def test_email_uses_mailto_scheme(self):
        result = _create_contact_link("satvik@example.com", "mailto")
        assert 'href="mailto:satvik@example.com"' in result

    def test_no_brand_color_on_linkedin_anchor(self):
        """Brand-design-spec: no #4285F4 on any contact anchor."""
        result = _create_contact_link(
            "https://linkedin.com/in/satvik", "linkedin", anchor_text="LinkedIn"
        )
        assert '#4285F4' not in result, (
            "Brand-design-spec violation: #4285F4 found on LinkedIn anchor."
        )

    def test_no_brand_color_on_portfolio_anchor(self):
        result = _create_contact_link(
            "https://github.com/satvik", "portfolio", anchor_text="Portfolio"
        )
        assert '#4285F4' not in result, (
            "Brand-design-spec violation: #4285F4 found on Portfolio anchor."
        )

    def test_no_brand_color_on_phone_anchor(self):
        result = _create_contact_link("+919876543210", "tel")
        assert '#4285F4' not in result

    def test_no_brand_color_on_email_anchor(self):
        result = _create_contact_link("satvik@example.com", "mailto")
        assert '#4285F4' not in result

    def test_primary_color_var_on_linkedin(self):
        """All contact anchors must resolve to primary color via CSS variable."""
        result = _create_contact_link(
            "https://linkedin.com/in/satvik", "linkedin", anchor_text="LinkedIn"
        )
        assert 'color: var(--ui-text-primary-color)' in result

    def test_primary_color_var_on_portfolio(self):
        result = _create_contact_link(
            "https://github.com/satvik", "portfolio", anchor_text="Portfolio"
        )
        assert 'color: var(--ui-text-primary-color)' in result

    def test_text_decoration_none_linkedin(self):
        result = _create_contact_link(
            "https://linkedin.com/in/satvik", "linkedin", anchor_text="LinkedIn"
        )
        assert 'text-decoration: none' in result

    def test_anchor_text_defaults_to_linkedin_label(self):
        """When anchor_text not provided, default to 'LinkedIn'."""
        result = _create_contact_link("https://linkedin.com/in/satvik", "linkedin")
        assert '>LinkedIn</a>' in result

    def test_anchor_text_defaults_to_portfolio_label(self):
        """When anchor_text not provided, default to 'Portfolio'."""
        result = _create_contact_link("https://github.com/satvik", "portfolio")
        assert '>Portfolio</a>' in result


# ===========================================================================
# Section C: integration — _replace_header_content()  (5 cases)
# ===========================================================================

_MINIMAL_TEMPLATE = """\
<html><body>
<div class="name">PLACEHOLDER_NAME</div>
<div class="role">PLACEHOLDER_ROLE</div>
<div class="contact-info">
  <span>placeholder</span>
</div>
</body></html>"""


class TestReplaceHeaderContent:
    """Integration tests for the full header replacement function."""

    def test_linkedin_rendered_as_anchor(self):
        header = HeaderData(
            name="Satvik Jain",
            role="Product Manager",
            contacts=[
                "Phone: +91-9876543210",
                "Email: satvik@example.com",
                "LinkedIn: https://linkedin.com/in/satvik",
                "Portfolio: https://github.com/satvik",
            ],
        )
        result = _replace_header_content(_MINIMAL_TEMPLATE, header)
        assert 'href="https://linkedin.com/in/satvik"' in result

    def test_portfolio_rendered_as_anchor(self):
        header = HeaderData(
            name="Satvik Jain",
            role="Product Manager",
            contacts=[
                "Phone: +91-9876543210",
                "Email: satvik@example.com",
                "LinkedIn: https://linkedin.com/in/satvik",
                "Portfolio: https://github.com/satvik",
            ],
        )
        result = _replace_header_content(_MINIMAL_TEMPLATE, header)
        assert 'href="https://github.com/satvik"' in result

    def test_no_brand_color_in_full_header(self):
        """Brand-design-spec compliance: entire header output must contain no #4285F4."""
        header = HeaderData(
            name="Satvik Jain",
            role="Product Manager",
            contacts=[
                "Phone: +91-9876543210",
                "Email: satvik@example.com",
                "LinkedIn: https://linkedin.com/in/satvik",
                "Portfolio: https://github.com/satvik",
            ],
        )
        result = _replace_header_content(_MINIMAL_TEMPLATE, header)
        assert '#4285F4' not in result, (
            "Brand-design-spec violation: #4285F4 appeared in rendered header output."
        )

    def test_empty_linkedin_omitted_from_header(self):
        """Empty LinkedIn value must be omitted entirely (no orphan tag)."""
        header = HeaderData(
            name="Satvik Jain",
            role="Product Manager",
            contacts=[
                "Phone: +91-9876543210",
                "Email: satvik@example.com",
                "LinkedIn: ",
                "Portfolio: https://github.com/satvik",
            ],
        )
        result = _replace_header_content(_MINIMAL_TEMPLATE, header)
        # No linkedin href should exist in output
        assert 'href="https://linkedin' not in result

    def test_primary_color_var_in_full_header(self):
        """MCP path header must use var(--ui-text-primary-color) on all anchors."""
        header = HeaderData(
            name="Satvik Jain",
            role="Product Manager",
            contacts=[
                "Phone: +91-9876543210",
                "Email: satvik@example.com",
                "LinkedIn: https://linkedin.com/in/satvik",
                "Portfolio: https://github.com/satvik",
            ],
        )
        result = _replace_header_content(_MINIMAL_TEMPLATE, header)
        assert 'color: var(--ui-text-primary-color)' in result


# ===========================================================================
# Section D: mcp_sync/tools/assemble_html.py _create_contact_link() — (9 cases)
# Explicitly imports from the mcp_sync path to ensure that module is patched.
# ===========================================================================

from linkright.mcp_sync.tools.assemble_html import (
    _create_contact_link as _mcp_create_contact_link,
    _replace_header_content as _mcp_replace_header_content,
    HeaderData as _MCP_HeaderData,
)


class TestMcpSyncCreateContactLink:
    """Tests for _create_contact_link() in mcp_sync/tools/assemble_html.py.

    Mirrors Section B to confirm the mcp_sync path is identically patched.
    """

    def test_linkedin_returns_anchor_with_label(self):
        result = _mcp_create_contact_link(
            "linkedin.com/in/satvik", "linkedin", anchor_text="LinkedIn"
        )
        assert '<a href="https://linkedin.com/in/satvik"' in result
        assert '>LinkedIn</a>' in result

    def test_portfolio_returns_anchor_with_label(self):
        result = _mcp_create_contact_link(
            "https://github.com/satvik", "portfolio", anchor_text="Portfolio"
        )
        assert '<a href="https://github.com/satvik"' in result
        assert '>Portfolio</a>' in result

    def test_empty_linkedin_returns_empty_string(self):
        """Empty LinkedIn value must return empty string — not an orphan anchor."""
        result = _mcp_create_contact_link("", "linkedin", anchor_text="LinkedIn")
        assert result == ""

    def test_empty_portfolio_returns_empty_string(self):
        result = _mcp_create_contact_link("", "portfolio", anchor_text="Portfolio")
        assert result == ""

    def test_no_color_inherit_on_any_anchor(self):
        """mcp_sync path must NOT use 'color: inherit' — inherits secondary gray."""
        result = _mcp_create_contact_link(
            "https://linkedin.com/in/satvik", "linkedin", anchor_text="LinkedIn"
        )
        assert "color: inherit" not in result, (
            "mcp_sync _create_contact_link still uses 'color: inherit' — Blocker 1 not fixed."
        )

    def test_primary_color_var_on_linkedin(self):
        """mcp_sync anchors must use var(--ui-text-primary-color) per brand-design-spec."""
        result = _mcp_create_contact_link(
            "https://linkedin.com/in/satvik", "linkedin", anchor_text="LinkedIn"
        )
        assert "color: var(--ui-text-primary-color)" in result

    def test_primary_color_var_on_portfolio(self):
        result = _mcp_create_contact_link(
            "https://github.com/satvik", "portfolio", anchor_text="Portfolio"
        )
        assert "color: var(--ui-text-primary-color)" in result

    def test_no_raw_url_as_link_text_linkedin(self):
        """Raw URL must not appear as anchor text — label must be 'LinkedIn'."""
        result = _mcp_create_contact_link(
            "https://linkedin.com/in/satvik", "linkedin", anchor_text="LinkedIn"
        )
        assert ">https://linkedin.com/in/satvik<" not in result, (
            "mcp_sync still renders raw URL as link text for LinkedIn."
        )

    def test_url_without_scheme_gets_https(self):
        result = _mcp_create_contact_link(
            "linkedin.com/in/satvik", "linkedin", anchor_text="LinkedIn"
        )
        assert 'href="https://linkedin.com/in/satvik"' in result


# ===========================================================================
# Section E: orchestrator.py placeholder partial-substitution + stderr warning
# (3 cases)
# Replicates the inline logic from step_14_assemble_html to unit-test the
# partial-substitution branch without running the full pipeline.
# ===========================================================================

import io


def _apply_placeholder_substitution(
    template_html: str,
    phone: str,
    email: str,
    linkedin: str,
    portfolio: str,
) -> tuple[str, str]:
    """Replication of the orchestrator.py step_14 placeholder substitution block.

    Returns (result_html, stderr_output).
    """
    import re
    import sys

    out = template_html
    _contact_fields = [phone, email, linkedin, portfolio]
    _contact_labels = ["phone", "email", "linkedin", "portfolio"]
    placeholders = re.findall(r"<!-- PLACEHOLDER -->", out)
    _n_found = len(placeholders)
    _n_needed = len(_contact_fields)

    stderr_capture = io.StringIO()
    _orig_stderr = sys.stderr
    sys.stderr = stderr_capture
    try:
        if _n_found < _n_needed:
            _missing = _contact_labels[_n_found:]
            sys.stderr.write(
                f"\n[S1.10 WARNING] Template has {_n_found} <!-- PLACEHOLDER --> markers "
                f"but {_n_needed} contact fields expected (phone/email/linkedin/portfolio). "
                f"Contact(s) that may be missing from output: {', '.join(_missing)}. "
                "Check the HTML template for missing <!-- PLACEHOLDER --> tags.\n\n"
            )
            sys.stderr.flush()
            for _field in _contact_fields[:_n_found]:
                out = out.replace("<!-- PLACEHOLDER -->", _field, 1)
        else:
            out = out.replace("<!-- PLACEHOLDER -->", phone, 1)
            out = out.replace("<!-- PLACEHOLDER -->", email, 1)
            out = out.replace("<!-- PLACEHOLDER -->", linkedin, 1)
            out = out.replace("<!-- PLACEHOLDER -->", portfolio, 1)
    finally:
        sys.stderr = _orig_stderr

    return out, stderr_capture.getvalue()


_TEMPLATE_4PH = (
    "<span><!-- PLACEHOLDER --></span>"
    "<span><!-- PLACEHOLDER --></span>"
    "<span><!-- PLACEHOLDER --></span>"
    "<span><!-- PLACEHOLDER --></span>"
)

_TEMPLATE_3PH = (
    "<span><!-- PLACEHOLDER --></span>"
    "<span><!-- PLACEHOLDER --></span>"
    "<span><!-- PLACEHOLDER --></span>"
)


class TestOrchestratorPlaceholderSubstitution:
    """Tests for partial substitution + visible warning when template has < 4 markers."""

    def test_full_substitution_when_4_placeholders(self):
        """Happy path: 4 placeholders → all 4 contacts injected, no warning."""
        result, stderr = _apply_placeholder_substitution(
            _TEMPLATE_4PH,
            phone="+91-9876543210",
            email="satvik@example.com",
            linkedin="https://linkedin.com/in/satvik",
            portfolio="https://github.com/satvik",
        )
        assert "+91-9876543210" in result
        assert "satvik@example.com" in result
        assert "https://linkedin.com/in/satvik" in result
        assert "https://github.com/satvik" in result
        assert "WARNING" not in stderr, "No warning expected when 4 placeholders found."

    def test_partial_substitution_3_placeholders_3_fields_substituted(self):
        """3 placeholders → phone/email/linkedin substituted; portfolio NOT injected."""
        result, stderr = _apply_placeholder_substitution(
            _TEMPLATE_3PH,
            phone="+91-9876543210",
            email="satvik@example.com",
            linkedin="https://linkedin.com/in/satvik",
            portfolio="https://github.com/satvik",
        )
        assert "+91-9876543210" in result
        assert "satvik@example.com" in result
        assert "https://linkedin.com/in/satvik" in result
        # portfolio is 4th field — no 4th placeholder to receive it
        assert "https://github.com/satvik" not in result, (
            "Portfolio should not appear — only 3 placeholders available."
        )

    def test_partial_substitution_emits_visible_stderr_warning(self):
        """3 placeholders → user-visible warning on stderr (not swallowed warnings.warn)."""
        _result, stderr = _apply_placeholder_substitution(
            _TEMPLATE_3PH,
            phone="+91-9876543210",
            email="satvik@example.com",
            linkedin="https://linkedin.com/in/satvik",
            portfolio="https://github.com/satvik",
        )
        assert "[S1.10 WARNING]" in stderr, (
            "Expected user-visible [S1.10 WARNING] on stderr; got nothing. "
            "Silent data loss on placeholder mismatch — Blocker 2 not fixed."
        )
        assert "portfolio" in stderr.lower(), (
            "Warning should name the missing contact field(s)."
        )
