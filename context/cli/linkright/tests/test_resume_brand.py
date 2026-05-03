"""Tests for `linkright resume brand` — Phase 1 brand-color feature.

Per Satvik design spec 2026-05-03 (memory: feedback_brand_design_spec_2026_05_03):
- Default = pure black-and-white
- User opt-in via 1-3 hex codes
- Color lands in EXACTLY 2 places: bolded metrics + section dividers
- Hex regex: ^#?[0-9A-Fa-f]{6}$ (auto-prepend # if missing)
- Empty secondary → solid primary line (no gradient)
- Empty accent → 2-stop gradient (primary→secondary)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

_ROOT = Path(__file__).parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Avoid loading the full `resume.cli` (which imports orchestrator with all its
# heavy dependencies). Test the brand module directly.
from linkright.resume.brand import (  # noqa: E402
    apply_brand_to_html,
    brand_cmd,
    markdown_to_branded_html,
    normalize_hex,
)


# ── normalize_hex ───────────────────────────────────────────────────────────

class TestNormalizeHex:
    def test_valid_with_hash(self):
        assert normalize_hex("#635BFF") == "#635BFF"

    def test_valid_without_hash_auto_prepends(self):
        assert normalize_hex("635BFF") == "#635BFF"

    def test_lowercase_normalized_to_uppercase(self):
        assert normalize_hex("#635bff") == "#635BFF"
        assert normalize_hex("635bff") == "#635BFF"

    def test_mixed_case_normalized(self):
        assert normalize_hex("#635BfF") == "#635BFF"

    def test_whitespace_stripped(self):
        assert normalize_hex("  #635BFF  ") == "#635BFF"

    def test_none_returns_none(self):
        assert normalize_hex(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_hex("") is None
        assert normalize_hex("   ") is None

    def test_3_char_hex_rejected(self):
        # Spec mandates 6-char hex only — no shorthand
        assert normalize_hex("#fff") is None
        assert normalize_hex("#abc") is None

    def test_invalid_chars_rejected(self):
        assert normalize_hex("#GGGGGG") is None
        assert normalize_hex("#12345Z") is None

    def test_too_long_rejected(self):
        assert normalize_hex("#1234567") is None

    def test_too_short_rejected(self):
        assert normalize_hex("#12345") is None

    def test_named_color_rejected(self):
        assert normalize_hex("red") is None
        assert normalize_hex("blue") is None


# ── apply_brand_to_html ─────────────────────────────────────────────────────

ROOT_OVERRIDE_HTML = """<html><head>
<style>
:root {
  --brand-primary-color: #000000;
  --brand-secondary-color: #000000;
  --brand-tertiary-color: #000000;
  --font-size-name: 18.5pt !important;
}
</style>
</head><body>
<div class="page">
  <div class="section-title">Experience<div class="section-divider"></div></div>
  <span class="li-content">Cut latency by <b>70%</b></span>
</div>
</body></html>"""


class TestApplyBrandToHtml:
    def test_all_three_colors_swapped(self):
        out = apply_brand_to_html(ROOT_OVERRIDE_HTML, "#635BFF", "#00D4FF", "#FF6B6B")
        assert "--brand-primary-color: #635BFF" in out
        assert "--brand-secondary-color: #00D4FF" in out
        assert "--brand-tertiary-color: #FF6B6B" in out
        # Original black values should be gone
        assert out.count("#000000") == 0

    def test_secondary_empty_falls_back_to_primary(self):
        out = apply_brand_to_html(ROOT_OVERRIDE_HTML, "#635BFF", None, None)
        # All three should equal primary → solid line, no gradient
        assert "--brand-primary-color: #635BFF" in out
        assert "--brand-secondary-color: #635BFF" in out
        assert "--brand-tertiary-color: #635BFF" in out

    def test_accent_empty_falls_back_to_secondary(self):
        out = apply_brand_to_html(ROOT_OVERRIDE_HTML, "#635BFF", "#00D4FF", None)
        # primary stays, secondary set, tertiary falls back to secondary
        assert "--brand-primary-color: #635BFF" in out
        assert "--brand-secondary-color: #00D4FF" in out
        assert "--brand-tertiary-color: #00D4FF" in out

    def test_empty_string_secondary_treated_as_none(self):
        # Defensive: caller might pass "" instead of None
        out = apply_brand_to_html(ROOT_OVERRIDE_HTML, "#635BFF", "", "")
        assert "--brand-primary-color: #635BFF" in out
        assert "--brand-secondary-color: #635BFF" in out
        assert "--brand-tertiary-color: #635BFF" in out

    def test_non_brand_css_untouched(self):
        out = apply_brand_to_html(ROOT_OVERRIDE_HTML, "#635BFF", "#00D4FF", "#FF6B6B")
        # font-size-name var must not be touched
        assert "--font-size-name: 18.5pt !important;" in out

    def test_html_body_text_untouched(self):
        out = apply_brand_to_html(ROOT_OVERRIDE_HTML, "#635BFF", "#00D4FF", "#FF6B6B")
        # Body content is identical
        assert "Cut latency by <b>70%</b>" in out
        assert 'class="section-divider"' in out

    def test_pattern_handles_extra_whitespace(self):
        # Different formatters may use 1 or 2 spaces after the colon
        html_loose = "--brand-primary-color:    #000000;"
        out = apply_brand_to_html(html_loose, "#FF0000", None, None)
        assert "#FF0000" in out
        assert "#000000" not in out

    def test_pattern_preserves_important_suffix(self):
        # Robustness: `!important` after hex must be preserved (AR concern).
        html_important = "--brand-primary-color: #000000 !important;"
        out = apply_brand_to_html(html_important, "#FF0000", None, None)
        assert "#FF0000 !important;" in out
        assert "#000000" not in out

    def test_pattern_preserves_inline_comment(self):
        # Robustness: inline `/* comment */` after hex must be preserved
        html_comment = "--brand-primary-color: #000000 /* user-set */;"
        out = apply_brand_to_html(html_comment, "#FF0000", None, None)
        assert "#FF0000 /* user-set */;" in out
        assert "#000000" not in out


# ── markdown_to_branded_html ────────────────────────────────────────────────

class TestMarkdownToBrandedHtml:
    def test_simple_paragraph(self):
        out = markdown_to_branded_html("Hello world.", "#635BFF")
        assert "<p>Hello world.</p>" in out
        assert "--brand-primary-color: #635BFF" in out

    def test_multiple_paragraphs_split_on_blank_lines(self):
        md = "First paragraph.\n\nSecond paragraph."
        out = markdown_to_branded_html(md, "#635BFF")
        assert "<p>First paragraph.</p>" in out
        assert "<p>Second paragraph.</p>" in out

    def test_bold_metrics_get_brand_color(self):
        # Bold gets <b> tags; CSS rule sets b { color: var(--brand-primary-color) }
        md = "Drove **$1.2M** in savings via **40%** automation."
        out = markdown_to_branded_html(md, "#635BFF")
        assert "<b>$1.2M</b>" in out
        assert "<b>40%</b>" in out
        # Brand var set on body via CSS — bolds inherit
        assert "--brand-primary-color: #635BFF" in out

    def test_html_special_chars_escaped(self):
        # `<script>` must NOT appear unescaped in output (XSS guard)
        md = "Skills: TypeScript & <Sass>. <script>alert(1)</script>"
        out = markdown_to_branded_html(md, "#000000")
        assert "<script>" not in out  # raw script tag must be escaped
        assert "&lt;script&gt;" in out
        assert "&amp;" in out  # `&` escaped to `&amp;`

    def test_soft_newlines_become_br(self):
        md = "Line one\nLine two\n\nNew paragraph"
        out = markdown_to_branded_html(md, "#000000")
        # Within first paragraph, `\n` → `<br>`
        assert "Line one<br>" in out
        assert "Line two" in out
        # New paragraph is its own <p>
        assert "<p>New paragraph</p>" in out

    def test_default_black_when_primary_is_black(self):
        out = markdown_to_branded_html("Test **bold**.", "#000000")
        # When primary is black, bold renders as black bold (still bold weight)
        assert "--brand-primary-color: #000000" in out
        assert "<b>bold</b>" in out

    def test_empty_input_yields_no_paragraphs(self):
        out = markdown_to_branded_html("", "#000000")
        # Should still be valid HTML (no <p> blocks)
        assert "<!DOCTYPE html>" in out
        assert "<p>" not in out

    def test_whitespace_only_input_yields_no_paragraphs(self):
        out = markdown_to_branded_html("   \n\n  \n", "#000000")
        assert "<p>" not in out


# ── CLI: brand_cmd ──────────────────────────────────────────────────────────

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fake_run_dir(tmp_path, monkeypatch):
    """Create a fake `~/.linkright/runs/<run_id>/artifacts/14_final_resume.html`
    and point Config to look at tmp_path instead of $HOME/.linkright/."""
    home = tmp_path / "linkright_home"
    home.mkdir()
    monkeypatch.setenv("LINKRIGHT_HOME", str(home))

    # Reload config module so the patched env var is picked up
    import importlib
    import linkright.config
    importlib.reload(linkright.config)

    run_id = "test-run-001"
    artifacts = home / "runs" / run_id / "artifacts"
    artifacts.mkdir(parents=True)
    html_path = artifacts / "14_final_resume.html"
    html_path.write_text(ROOT_OVERRIDE_HTML, encoding="utf-8")
    return run_id, artifacts


def test_brand_yes_with_all_flags_runs_clean(runner, fake_run_dir):
    run_id, artifacts = fake_run_dir
    with patch("linkright.resume.brand.render_branded_pdf") as mock_render:
        result = runner.invoke(
            brand_cmd,
            ["--run-id", run_id,
             "--primary", "#635BFF",
             "--secondary", "#00D4FF",
             "--accent", "#FF6B6B",
             "--yes"],
        )

    assert result.exit_code == 0, f"unexpected: {result.output}"
    # Branded HTML created
    branded_html = artifacts / "14_final_resume_branded.html"
    assert branded_html.exists()
    content = branded_html.read_text(encoding="utf-8")
    assert "--brand-primary-color: #635BFF" in content
    assert "--brand-secondary-color: #00D4FF" in content
    assert "--brand-tertiary-color: #FF6B6B" in content
    # Playwright was invoked once for resume PDF
    mock_render.assert_called_once()


def test_brand_yes_without_primary_raises(runner, fake_run_dir):
    run_id, _ = fake_run_dir
    result = runner.invoke(
        brand_cmd,
        ["--run-id", run_id, "--yes"],
    )
    assert result.exit_code != 0
    assert "--primary is required" in result.output


def test_brand_missing_run_id_raises(runner, tmp_path, monkeypatch):
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path / "linkright_home"))
    import importlib
    import linkright.config
    importlib.reload(linkright.config)

    result = runner.invoke(
        brand_cmd,
        ["--run-id", "does-not-exist", "--primary", "#635BFF", "--yes"],
    )
    assert result.exit_code != 0
    assert "not found" in result.output


def test_brand_missing_html_raises(runner, tmp_path, monkeypatch):
    home = tmp_path / "linkright_home"
    home.mkdir()
    monkeypatch.setenv("LINKRIGHT_HOME", str(home))
    import importlib
    import linkright.config
    importlib.reload(linkright.config)

    # run_id directory exists but no 14_final_resume.html
    artifacts = home / "runs" / "empty-run" / "artifacts"
    artifacts.mkdir(parents=True)

    result = runner.invoke(
        brand_cmd,
        ["--run-id", "empty-run", "--primary", "#635BFF", "--yes"],
    )
    assert result.exit_code != 0
    assert "14_final_resume.html missing" in result.output


def test_brand_invalid_primary_flag_treated_as_missing(runner, fake_run_dir):
    """Invalid hex via flag → falls through to interactive prompt; with --yes,
    raises 'primary required' since normalize_hex returns None."""
    run_id, _ = fake_run_dir
    result = runner.invoke(
        brand_cmd,
        ["--run-id", run_id, "--primary", "not-a-hex", "--yes"],
    )
    assert result.exit_code != 0
    assert "--primary is required" in result.output


def test_brand_secondary_only_solid_line(runner, fake_run_dir):
    """Primary + no secondary + no accent → both fall back to primary →
    divider renders as solid primary line (no gradient visible)."""
    run_id, artifacts = fake_run_dir
    with patch("linkright.resume.brand.render_branded_pdf"):
        result = runner.invoke(
            brand_cmd,
            ["--run-id", run_id, "--primary", "#FF0000", "--yes"],
        )

    assert result.exit_code == 0, result.output
    content = (artifacts / "14_final_resume_branded.html").read_text()
    # All three CSS vars should be primary (red)
    assert content.count("#FF0000") == 3


def test_brand_interactive_prompt_uses_input(runner, fake_run_dir):
    """Without --yes, the command prompts. CliRunner can pipe input."""
    run_id, artifacts = fake_run_dir
    with patch("linkright.resume.brand.render_branded_pdf"):
        # Three prompts in order: primary (required), secondary (optional), accent (optional)
        # Input: primary=#000FFF, secondary=blank (skip), accent=blank (skip)
        result = runner.invoke(
            brand_cmd,
            ["--run-id", run_id],
            input="#000FFF\n\n\n",
        )

    assert result.exit_code == 0, result.output
    content = (artifacts / "14_final_resume_branded.html").read_text()
    assert content.count("#000FFF") == 3  # primary only → all fall back


# ── Cover letter branding ──────────────────────────────────────────────────

def test_brand_cover_letter_renders_branded_pdf(runner, fake_run_dir, tmp_path):
    """--cover-letter <md-path> renders cover_letter_branded.pdf next to the md."""
    run_id, artifacts = fake_run_dir

    cl_dir = tmp_path / "cl_artifacts"
    cl_dir.mkdir()
    cl_md = cl_dir / "cover_letter.md"
    cl_md.write_text(
        "Dear Hiring Manager,\n\nI led work that drove **$1.2M ARR** in 6 months.\n\nSincerely,\nSatvik",
        encoding="utf-8",
    )

    with patch("linkright.resume.brand.render_branded_pdf") as mock_render:
        result = runner.invoke(
            brand_cmd,
            ["--run-id", run_id, "--primary", "#635BFF",
             "--cover-letter", str(cl_md), "--yes"],
        )

    assert result.exit_code == 0, result.output
    # Branded CL HTML created next to the source md
    cl_html = cl_dir / "cover_letter_branded.html"
    assert cl_html.exists()
    cl_content = cl_html.read_text(encoding="utf-8")
    assert "--brand-primary-color: #635BFF" in cl_content
    assert "<b>$1.2M ARR</b>" in cl_content
    # render_branded_pdf called twice: once for resume, once for CL
    assert mock_render.call_count == 2


def test_brand_cover_letter_missing_path_fails(runner, fake_run_dir, tmp_path):
    """If --cover-letter points to a non-existent file, Click rejects."""
    run_id, _ = fake_run_dir
    nonexistent = tmp_path / "no_such_file.md"

    result = runner.invoke(
        brand_cmd,
        ["--run-id", run_id, "--primary", "#635BFF",
         "--cover-letter", str(nonexistent), "--yes"],
    )
    assert result.exit_code != 0
    # Click's exists=True validator returns "does not exist" or "Invalid value"
    assert "does not exist" in result.output.lower() or "invalid" in result.output.lower()


def test_brand_no_cover_letter_flag_does_not_render_cl(runner, fake_run_dir):
    """Without --cover-letter, only resume PDF gets rendered."""
    run_id, _ = fake_run_dir
    with patch("linkright.resume.brand.render_branded_pdf") as mock_render:
        result = runner.invoke(
            brand_cmd,
            ["--run-id", run_id, "--primary", "#635BFF", "--yes"],
        )

    assert result.exit_code == 0, result.output
    # Only resume rendered (1 call), not CL
    assert mock_render.call_count == 1
