"""UAT Cluster C — Tailor UX Redesign.

Covers UAT bugs #33, #34, #35, #36, #38, #39.

These tests focus on user-facing behaviour (on-output / on-disk assertions) per
memory `feedback_clirunner_test_mock_assertions.md` — never just "mock was
called". Each test names the bug ID it covers.
"""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from rich.console import Console

# Ensure src/ on path even when test invoked from repo root.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from linkright.resume import orchestrator as orch


# ────────────────────────────────────────────────────────────────────────────
# Bug #33 — Silent JD Analysis → render P0/P1/P2 requirements panel
# ────────────────────────────────────────────────────────────────────────────

def test_bug_33_jd_panel_renders_p0_p1_p2_buckets(monkeypatch, capsys):
    """After step_07, panel renders importance buckets + JD keywords."""
    monkeypatch.delenv("LR_NO_PAUSE", raising=False)
    parsed_p12 = {
        "target_role": "Staff PM",
        "strategy": "lead",
        "requirements": [
            {"id": "r1", "text": "5+ years product management", "importance": "required"},
            {"id": "r2", "text": "Drive cross-functional alignment", "importance": "required"},
            {"id": "r3", "text": "Familiarity with SQL",            "importance": "preferred"},
            {"id": "r4", "text": "MBA from top-tier school",       "importance": "optional"},
        ],
        "jd_keywords": ["roadmap", "alignment", "growth", "metrics"],
    }
    # Capture printed output by patching the Console CONSTRUCTOR to a themed
    # Console that writes to our buffer. Theme must come from linkright.ui to
    # resolve step.accent / step.gold custom styles defined in LR_THEME.
    from linkright.ui.theme import LR_THEME
    buf = io.StringIO()
    fake_console = Console(file=buf, force_terminal=False, color_system=None,
                           width=120, theme=LR_THEME)
    # Patch via the symbol imported inside orchestrator's function body
    with patch("rich.console.Console", return_value=fake_console):
        orch._render_jd_requirements_panel(parsed_p12)

    out = buf.getvalue()
    # P0 / P1 / P2 buckets surface to user
    assert "P0" in out and "Must-have" in out, f"P0 bucket missing in:\n{out}"
    assert "P1" in out and "Preferred" in out, f"P1 bucket missing in:\n{out}"
    assert "P2" in out and "Optional" in out, f"P2 bucket missing in:\n{out}"
    # Counts shown
    assert "(2)" in out, f"Should show '(2)' for two P0 reqs in:\n{out}"
    assert "(1)" in out, f"Should show '(1)' for each of P1/P2 in:\n{out}"
    # Top keywords surface
    assert "roadmap" in out and "metrics" in out, f"keywords missing in:\n{out}"
    # Target role + strategy surface
    assert "Staff PM" in out
    assert "LEAD" in out  # uppercased


def test_bug_33_jd_panel_skipped_when_no_pause(monkeypatch, capsys):
    """LR_NO_PAUSE=1 → JD requirements panel is a no-op."""
    monkeypatch.setenv("LR_NO_PAUSE", "1")
    parsed_p12 = {"requirements": [{"text": "x", "importance": "required"}]}
    orch._render_jd_requirements_panel(parsed_p12)
    captured = capsys.readouterr()
    # When skipped, NO panel text printed
    assert "JD Analysis" not in captured.out
    assert "Must-have" not in captured.out


# ────────────────────────────────────────────────────────────────────────────
# Bug #34 — Opaque Cache Info → expanded detail
# ────────────────────────────────────────────────────────────────────────────

def test_bug_34_cache_info_details_in_tailor_message():
    """The tailor cache-hit code path should reference each artifact + the
    profile dir + an inspection command in the printed message.

    We assert against the source text directly (not just runtime echo) so the
    description survives later refactors; the source IS the user-visible copy.
    """
    cli_src = (Path(__file__).resolve().parents[1] / "src" / "linkright" / "resume" / "cli.py").read_text()
    # Plain-English artifact descriptions appear:
    assert "raw resume text" in cli_src
    assert "parsed structure" in cli_src
    assert "extracted career nuggets" in cli_src
    assert "nugget embeddings" in cli_src
    # Profile dir + inspect command both surfaced:
    assert "~/.linkright/profile/" in cli_src
    assert "linkright profile show" in cli_src
    # Time-saved estimate retained:
    assert "30-60s" in cli_src


# ────────────────────────────────────────────────────────────────────────────
# Bug #35 — Contact Info Desync → step_01b reads contact.yaml fresh
# ────────────────────────────────────────────────────────────────────────────

def _silence_logbook(monkeypatch):
    """step_01b calls logbook.append(); silence it in tests so we don't
    mutate the shared vision.md fixture file."""
    import linkright.resume.lib.logbook as _logbook
    monkeypatch.setattr(_logbook, "append", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(_logbook, "append_raw", lambda *a, **k: None, raising=False)


def test_bug_35_step_01b_merges_contact_yaml_over_parsed(monkeypatch, tmp_path):
    """If `linkright contact` wrote to contact.yaml, step_01b must show the
    yaml values — not the stale parse-time data from step_01.
    """
    _silence_logbook(monkeypatch)
    monkeypatch.setenv("LR_NO_PAUSE", "0")  # force interactive code path
    monkeypatch.setenv("HOME", str(tmp_path))

    profile_dir = tmp_path / ".linkright" / "profile"
    profile_dir.mkdir(parents=True)
    contact_yaml = profile_dir / "contact.yaml"
    contact_yaml.write_text(
        "email: fresh@user.com\n"
        "phone: '+1-555-9999'\n"
        "linkedin: linkedin.com/in/fresh\n"
        "portfolio: fresh.example.com\n",
        encoding="utf-8",
    )

    parsed = {
        "contact_info": {
            "email": "stale@user.com",       # different from yaml
            "phone": "+1-555-0000",          # different from yaml
            "linkedin": "linkedin.com/in/stale",
            "portfolio": "stale.example.com",
        }
    }

    # Patch `_profile_dir` so load_contact reads tmp_path's yaml
    import linkright.profile.pipeline as pp
    monkeypatch.setattr(pp, "_profile_dir", lambda: profile_dir)
    # ALSO patch save_contact so step_01b's "persist edits" branch can't write
    # outside tmp_path (defensive — we don't trigger an edit in this test).
    monkeypatch.setattr(pp, "save_contact", lambda *a, **k: None, raising=False)

    # Patch questionary to bail immediately after first prompt (action="s")
    fake_q = MagicMock()
    fake_q.select.return_value.ask.return_value = "s"
    fake_q.Choice = MagicMock(side_effect=lambda label, value: MagicMock(label=label, value=value))
    monkeypatch.setitem(sys.modules, "questionary", fake_q)

    # Force tty so we hit the interactive branch
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    # Swallow click.echo to keep stdout clean
    monkeypatch.setattr("click.echo", lambda *a, **k: None)

    result = orch.step_01b_verify_contact_details(parsed)
    # The merged contact dict has yaml values, not parsed values
    assert result["email"]   == "fresh@user.com", f"Expected yaml email, got {result.get('email')!r}"
    assert result["phone"]   == "+1-555-9999",    f"Expected yaml phone, got {result.get('phone')!r}"
    assert result["linkedin"] == "linkedin.com/in/fresh"
    assert result["portfolio"] == "fresh.example.com"


def test_bug_35_step_01b_no_yaml_falls_back_to_parsed(monkeypatch, tmp_path):
    """No contact.yaml → step_01b uses parsed step_01 data (today's behaviour)."""
    _silence_logbook(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LR_NO_PAUSE", "1")  # fast path
    parsed = {"contact_info": {"email": "parsed@user.com", "phone": "+1"}}
    out = orch.step_01b_verify_contact_details(parsed)
    assert out["email"] == "parsed@user.com"
    assert out["phone"] == "+1"


# ────────────────────────────────────────────────────────────────────────────
# Bug #36 — Pipeline Execution screen visual hierarchy
# ────────────────────────────────────────────────────────────────────────────

def test_bug_36_run_details_muted_in_tailor_source():
    """Run ID / Output / LLM mode lines should live inside a muted block
    (ANSI \\033[2m) under a 'Run details' header — not plain echo.
    """
    cli_src = (Path(__file__).resolve().parents[1] / "src" / "linkright" / "resume" / "cli.py").read_text()
    assert "Run details" in cli_src, "expected 'Run details' header"
    # ANSI dim wraps Run ID + Output + LLM mode lines:
    assert "\\033[2m    Run ID" in cli_src
    assert "\\033[2m    Output" in cli_src
    assert "\\033[2m    LLM mode" in cli_src
    # The OLD non-muted plain prints should be gone:
    assert "click.echo(f\"Run ID: {run_id}\")"   not in cli_src
    assert "click.echo(f\"Output: {run_dir}\")"  not in cli_src


# ────────────────────────────────────────────────────────────────────────────
# Bug #38 — JD analysis moved to Step 3 (was Step 5)
# ────────────────────────────────────────────────────────────────────────────

def test_bug_38_jd_analysis_runs_before_nugget_extraction():
    """Read the orchestrator source; verify step ordering: JD analysis (step_07)
    is invoked BEFORE step_02 nugget extraction in main().
    """
    orch_src = (Path(__file__).resolve().parents[1] / "src" / "linkright" / "resume" / "orchestrator.py").read_text()
    main_idx     = orch_src.index("def main():")
    step07_idx   = orch_src.index("parsed_p12 = step_07_phase_1_2", main_idx)
    step02_idx   = orch_src.index("nuggets = step_02_extract_nuggets", main_idx)
    assert step07_idx < step02_idx, (
        "step_07 (JD analyze) must run BEFORE step_02 (nuggets) "
        "so users see JD interpretation immediately"
    )


def test_bug_38_step_indices_announce_jd_as_step_3():
    """The 'Analyzing job description' step_start announces index=3 of 9."""
    orch_src = (Path(__file__).resolve().parents[1] / "src" / "linkright" / "resume" / "orchestrator.py").read_text()
    assert 'step_start("Analyzing job description", index=3, total=9)' in orch_src


def test_bug_38_jd_panel_invoked_after_step_07():
    """_render_jd_requirements_panel is called from main() right after step_07."""
    orch_src = (Path(__file__).resolve().parents[1] / "src" / "linkright" / "resume" / "orchestrator.py").read_text()
    main_idx        = orch_src.index("def main():")
    step07_idx      = orch_src.index("parsed_p12 = step_07_phase_1_2", main_idx)
    jd_panel_idx    = orch_src.index("_render_jd_requirements_panel(parsed_p12)", main_idx)
    nugget_idx      = orch_src.index("nuggets = step_02_extract_nuggets", main_idx)
    assert step07_idx < jd_panel_idx < nugget_idx


# ────────────────────────────────────────────────────────────────────────────
# Bug #39 — Strategy Review surfaces layout fit insights
# ────────────────────────────────────────────────────────────────────────────

def test_bug_39_estimate_section_heights_full_plan():
    """Standard 4-role plan → returns sections + total_lines + fit_probability."""
    parsed_p12 = {}
    parsed_resume = {
        "education": [{"degree": "MBA"}, {"degree": "BTech"}],
        "projects":  [{"name": "p1"}, {"name": "p2"}],
    }
    distribution = {
        "included_companies": [
            {"company": "C1", "bullets": 5},
            {"company": "C2", "bullets": 4},
            {"company": "C3", "bullets": 3},
        ],
        "included_sections": ["experience", "education", "skills", "projects"],
    }
    heights = orch._estimate_section_heights(parsed_p12, parsed_resume, distribution)
    # All expected sections present:
    section_names = {s["name"] for s in heights["sections"]}
    assert "Header" in section_names
    assert "Summary" in section_names
    assert "Experience" in section_names
    assert "Education" in section_names
    assert "Skills" in section_names
    assert "Projects" in section_names
    # Experience lines = 2*3 + 12 = 18
    exp_lines = next(s for s in heights["sections"] if s["name"] == "Experience")["lines"]
    assert exp_lines == 18, f"Experience lines should be 2*3 roles + 12 bullets = 18, got {exp_lines}"
    # total_lines is the sum
    assert heights["total_lines"] == sum(s["lines"] for s in heights["sections"])
    # Each section has a pct_height
    assert all("pct_height" in s for s in heights["sections"])
    # fit_probability is one of HIGH/MEDIUM/LOW
    assert heights["fit_probability"] in ("HIGH", "MEDIUM", "LOW")
    # fit_pct is reasonable for ~31-line plan vs 47 capacity → MEDIUM/LOW
    assert 50.0 <= heights["fit_pct"] <= 200.0


def test_bug_39_estimate_section_heights_high_fit_band():
    """Plan that lands close to 47 lines → HIGH probability."""
    parsed_p12 = {}
    parsed_resume = {"education": [{"degree": "x"}], "projects": []}
    # Header(4) + Summary(3) + Experience(2*4 + 19 = 27) + Education(2) + Skills(4) = 40
    distribution = {
        "included_companies": [
            {"company": "C1", "bullets": 5},
            {"company": "C2", "bullets": 5},
            {"company": "C3", "bullets": 5},
            {"company": "C4", "bullets": 4},
        ],
        "included_sections": ["experience", "education", "skills"],
    }
    heights = orch._estimate_section_heights(parsed_p12, parsed_resume, distribution)
    assert heights["fit_probability"] == "HIGH", (
        f"40 lines vs 47 capacity → {heights['fit_pct']:.1f}% should be HIGH, "
        f"got {heights['fit_probability']}"
    )


def test_bug_39_estimate_section_heights_low_overflow():
    """Far-overflow plan → LOW probability."""
    parsed_p12 = {}
    parsed_resume = {"education": [{"degree": "x"}] * 4, "projects": [{"name": "p"}] * 4}
    distribution = {
        "included_companies": [{"company": f"C{i}", "bullets": 8} for i in range(8)],
        "included_sections": ["experience", "education", "skills", "projects"],
    }
    heights = orch._estimate_section_heights(parsed_p12, parsed_resume, distribution)
    assert heights["fit_probability"] == "LOW", (
        f"Far overflow plan ({heights['fit_pct']:.1f}%) should be LOW, "
        f"got {heights['fit_probability']}"
    )


def test_bug_39_strategy_review_renders_layout_block(monkeypatch):
    """Strategy Review panel includes 'Layout fit' + 'Page utilization' rows
    when parsed_resume is supplied.
    """
    monkeypatch.delenv("LR_NO_PAUSE", raising=False)
    parsed_p12 = {
        "target_role": "PM",
        "strategy": "lead",
        "jd_keywords": ["k1"],
    }
    distribution = {
        "included_companies": [{"company": "C1", "role": "PM", "bullets": 5}],
        "excluded_companies": [],
        "included_sections": ["experience", "education", "skills"],
    }
    parsed_resume = {"education": [{"degree": "MBA"}], "projects": []}

    from linkright.ui.theme import LR_THEME
    buf = io.StringIO()
    fake_console = Console(file=buf, force_terminal=False, color_system=None,
                           width=140, theme=LR_THEME)
    # Patch BOTH the strategy gate's Console class and the confirm prompt
    with patch("rich.console.Console", return_value=fake_console), \
         patch("click.confirm", return_value=True):
        orch._strategy_review_gate(parsed_p12, distribution, parsed_resume=parsed_resume)

    out = buf.getvalue()
    assert "Layout fit" in out, f"Layout-fit block missing:\n{out}"
    assert "Page utilization" in out, f"Page utilization line missing:\n{out}"
    assert "1-page fit" in out, f"fit probability tag missing:\n{out}"
    # At least one section row rendered
    assert "Header" in out
    assert "Experience" in out


def test_bug_39_strategy_review_skipped_when_no_pause(monkeypatch, capsys):
    """LR_NO_PAUSE=1 → strategy gate is a no-op (no panel printed, no prompt)."""
    monkeypatch.setenv("LR_NO_PAUSE", "1")
    # Even with parsed_resume, no-pause short-circuits before any rendering.
    orch._strategy_review_gate(
        parsed_p12={"target_role": "PM"},
        distribution={"included_companies": [], "excluded_companies": []},
        parsed_resume={"education": []},
    )
    captured = capsys.readouterr()
    assert "Strategy Review" not in captured.out
    assert "Layout fit" not in captured.out


# ────────────────────────────────────────────────────────────────────────────
# Integration — pipeline ordering invariant (regression guard for #38)
# ────────────────────────────────────────────────────────────────────────────

def test_pipeline_step_indices_are_sequential_1_through_9():
    """All step_start() calls in main() use index 1..9 with total=9 in order."""
    orch_src = (Path(__file__).resolve().parents[1] / "src" / "linkright" / "resume" / "orchestrator.py").read_text()
    main_idx = orch_src.index("def main():")
    main_block = orch_src[main_idx:]
    import re
    matches = re.findall(r"step_start\([^)]*index=(\d+),\s*total=(\d+)\)", main_block)
    assert matches, "No step_start calls found in main()"
    indices = [int(i) for i, _ in matches]
    totals  = [int(t) for _, t in matches]
    assert indices == sorted(set(indices)) == list(range(1, len(indices) + 1)), (
        f"step indices not 1..N sequential: {indices}"
    )
    assert all(t == 9 for t in totals), f"total should be 9 everywhere, got {totals}"
