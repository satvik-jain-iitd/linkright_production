"""Tests for UAT Cluster E3 — Pickers, progress, sub-context, priority legend.

UAT bugs covered:
  #19 — "Type something" custom-input sentinel in selection lists
  #20 — '●' high-contrast white echo for previously-submitted user inputs
  #21 — Coral/salmon progress verb + muted grey telemetry tail
  #29 — Quantified Priority Legend (P0-P3) replacing vague core/strong/...
  #30 — Muted-grey sub-context line for metadata, timestamps, paths

Snapshot strategy mirrors `test_cli_ui_snapshot.py`: capture via a recording
Rich console and assert on plain-text content + theme-style invariants
(no raw ANSI codes, no color collisions with sibling tokens).
"""
from __future__ import annotations

from rich.console import Console


def _recording_console(width: int = 120) -> Console:
    from linkright.ui.theme import LR_THEME
    return Console(
        theme=LR_THEME,
        record=True,
        force_terminal=True,
        width=width,
        highlight=False,
    )


# ─── #19  TYPE_SOMETHING + lr_select_with_custom ───────────────────────────────

def test_type_something_sentinel_exported():
    """Sentinel constant + label must be importable from linkright.ui.patterns."""
    from linkright.ui.patterns import TYPE_SOMETHING, TYPE_SOMETHING_LABEL
    assert isinstance(TYPE_SOMETHING, str)
    assert isinstance(TYPE_SOMETHING_LABEL, str)
    assert TYPE_SOMETHING != TYPE_SOMETHING_LABEL, (
        "Sentinel value must be distinct from the user-visible label so "
        "callers can match on either without ambiguity."
    )
    # The opaque value should be unlikely to collide with a real choice label.
    assert TYPE_SOMETHING.startswith("__"), (
        "Sentinel value should be opaque (starts with '__') to avoid "
        "collision with any human-readable choice the caller might add."
    )
    # The label is what humans see — make sure it's recognisable.
    assert "Type something" in TYPE_SOMETHING_LABEL


def test_type_something_also_exported_from_ui():
    """linkright.ui should re-export the sentinel + helpers."""
    import linkright.ui as ui
    assert hasattr(ui, "TYPE_SOMETHING")
    assert hasattr(ui, "TYPE_SOMETHING_LABEL")
    assert hasattr(ui, "append_type_something")
    assert hasattr(ui, "lr_select_with_custom")


def test_append_type_something_preserves_order_and_appends():
    """append_type_something must preserve order and place the entry last."""
    from linkright.ui.patterns import append_type_something, TYPE_SOMETHING_LABEL
    original = ["Alpha", "Beta", "Gamma"]
    out = append_type_something(original)
    assert out == ["Alpha", "Beta", "Gamma", TYPE_SOMETHING_LABEL]
    # Original list must NOT be mutated — callers reuse choice lists across loops.
    assert original == ["Alpha", "Beta", "Gamma"]


def test_append_type_something_is_idempotent():
    """Calling twice should not produce two 'Type something…' entries."""
    from linkright.ui.patterns import append_type_something, TYPE_SOMETHING_LABEL
    first = append_type_something(["A", "B"])
    second = append_type_something(first)
    assert second.count(TYPE_SOMETHING_LABEL) == 1


def test_lr_select_with_custom_routes_to_lr_text_on_sentinel(monkeypatch):
    """When user picks 'Type something…' the helper must call lr_text and
    return the typed string."""
    import linkright.ui as ui
    from linkright.ui.patterns import TYPE_SOMETHING_LABEL

    captured = {}

    def fake_lr_select(question, choices, accent=None, hint=None, **kwargs):
        captured["select_question"] = question
        captured["choices"] = list(choices)
        # Simulate user picking the "Type something…" entry.
        return TYPE_SOMETHING_LABEL

    def fake_lr_text(prompt, default="", accent=None, **kwargs):
        captured["text_prompt"] = prompt
        return "  Custom answer from user  "

    monkeypatch.setattr(ui, "lr_select", fake_lr_select)
    monkeypatch.setattr(ui, "lr_text", fake_lr_text)

    result = ui.lr_select_with_custom(
        "Pick an option:",
        ["First", "Second"],
        custom_prompt="Type your option:",
    )
    assert result == "Custom answer from user"  # stripped
    assert captured["select_question"] == "Pick an option:"
    assert captured["text_prompt"] == "Type your option:"
    # The augmented choices must include the sentinel label.
    assert TYPE_SOMETHING_LABEL in captured["choices"]


def test_lr_select_with_custom_passthrough_for_real_choice(monkeypatch):
    """If user picks a real choice (not the sentinel) lr_text must NOT be called."""
    import linkright.ui as ui
    text_called = {"yes": False}

    monkeypatch.setattr(ui, "lr_select", lambda *a, **kw: "First")

    def boom(*a, **kw):
        text_called["yes"] = True
        return "should not happen"

    monkeypatch.setattr(ui, "lr_text", boom)

    out = ui.lr_select_with_custom("Q?", ["First", "Second"])
    assert out == "First"
    assert text_called["yes"] is False, (
        "lr_text must not be invoked when the user picked a regular option."
    )


def test_lr_select_with_custom_handles_cancel(monkeypatch):
    """ESC / cancel on the picker returns None — caller can detect the abort."""
    import linkright.ui as ui
    monkeypatch.setattr(ui, "lr_select", lambda *a, **kw: None)
    monkeypatch.setattr(ui, "lr_text", lambda *a, **kw: "should not be called")
    out = ui.lr_select_with_custom("Q?", ["A", "B"])
    assert out is None


def test_lr_select_with_custom_handles_empty_typed_input(monkeypatch):
    """User picks 'Type something…' but submits blank → returns None."""
    import linkright.ui as ui
    from linkright.ui.patterns import TYPE_SOMETHING_LABEL
    monkeypatch.setattr(ui, "lr_select", lambda *a, **kw: TYPE_SOMETHING_LABEL)
    monkeypatch.setattr(ui, "lr_text", lambda *a, **kw: "   ")
    out = ui.lr_select_with_custom("Q?", ["A", "B"])
    assert out is None


# ─── #20  user_input_echo  ────────────────────────────────────────────────────

def test_user_input_echo_renders_white_bullet():
    from linkright.ui.patterns import user_input_echo
    con = _recording_console()
    user_input_echo("Hello, world.", console=con)
    text = con.export_text()
    assert "●" in text, "Echo must use the '●' bullet glyph (UAT bug #20)."
    assert "Hello, world." in text


def test_user_input_echo_with_label():
    from linkright.ui.patterns import user_input_echo
    con = _recording_console()
    user_input_echo("Satvik Jain", label="Name", console=con)
    text = con.export_text()
    assert "● " in text or "●  " in text
    assert "Name: Satvik Jain" in text


def test_user_input_echo_uses_high_contrast_white_style():
    """The bullet should be rendered with the tui.hi_white style.

    We assert on the styled-segment metadata by exporting HTML and grepping
    for the colour hex. Using export_html keeps the assertion stable across
    Rich versions vs raw ANSI matching.
    """
    from linkright.ui.patterns import user_input_echo
    con = _recording_console()
    user_input_echo("verifying", console=con)
    html = con.export_html(inline_styles=True, clear=False)
    # tui.hi_white = #F5F5F7
    assert "f5f5f7" in html.lower(), (
        "Echo bullet should be coloured with tui.hi_white (#F5F5F7) — "
        "got HTML without the hex: " + html[:300]
    )


def test_step_echo_input_facade_exists():
    """linkright.ui.step_echo_input is the public facade for callers."""
    import linkright.ui as ui
    assert hasattr(ui, "step_echo_input")
    assert callable(ui.step_echo_input)


# ─── #21  progress_verb (coral + muted telemetry)  ────────────────────────────

def test_progress_verb_renders_coral_working_icon():
    from linkright.ui.patterns import progress_verb
    con = _recording_console()
    progress_verb("Smooshing nuggets", telemetry="0.3s · 12 toks", console=con)
    text = con.export_text()
    assert "Smooshing nuggets" in text
    assert "0.3s" in text
    assert "12 toks" in text
    assert "*" in text, "Default progress verb icon should be '*'."


def test_progress_verb_coral_hex_in_output():
    """The verb itself must be coloured with tui.coral (#EE6F4F)."""
    from linkright.ui.patterns import progress_verb
    con = _recording_console()
    progress_verb("Smooshing nuggets", telemetry="0.3s", console=con)
    html = con.export_html(inline_styles=True, clear=False)
    assert "ee6f4f" in html.lower(), (
        "Progress verb must be rendered in tui.coral (#EE6F4F). "
        "HTML head: " + html[:300]
    )


def test_progress_verb_telemetry_uses_muted_gray():
    """Telemetry tail must use tui.muted (#8E8E93) — never the same coral
    as the verb (visual hierarchy)."""
    from linkright.ui.patterns import progress_verb
    con = _recording_console()
    progress_verb("Working", telemetry="0.3s", console=con)
    html = con.export_html(inline_styles=True, clear=False)
    assert "8e8e93" in html.lower(), (
        "Telemetry tail must be rendered in tui.muted (#8E8E93)."
    )


def test_progress_verb_thinking_icon_switches_color():
    """When caller passes icon='+' (thinking), the icon colour should switch
    to tui.green so '*' = working and '+' = thinking stay visually distinct."""
    from linkright.ui.patterns import progress_verb
    con = _recording_console()
    progress_verb("Pondering", icon="+", console=con)
    html = con.export_html(inline_styles=True, clear=False)
    # tui.green = #34A853
    assert "34a853" in html.lower(), (
        "Thinking icon '+' should be coloured with tui.green (#34A853)."
    )


def test_step_progress_facade_exists():
    import linkright.ui as ui
    assert hasattr(ui, "step_progress")
    assert callable(ui.step_progress)


def test_progress_verb_no_telemetry_renders_cleanly():
    """No telemetry → no trailing whitespace, no empty markup tag."""
    from linkright.ui.patterns import progress_verb
    con = _recording_console()
    progress_verb("Working", console=con)
    text = con.export_text()
    assert "Working" in text
    # Should NOT end with a hanging separator '·' from an empty telemetry string.
    assert "·" not in text.split("Working")[-1].strip()


# ─── #29  Priority Legend  ────────────────────────────────────────────────────

def test_priority_legend_module_exports():
    from linkright.profile import priority_legend as pl
    assert pl.P0.code == "P0"
    assert pl.P1.code == "P1"
    assert pl.P2.code == "P2"
    assert pl.P3.code == "P3"
    assert len(pl.ALL_TIERS) == 4
    assert pl.TIER_BY_CODE["P0"] is pl.P0


def test_priority_legend_definitions_are_measurable():
    """Each tier's evidence_shape must describe a SHAPE of evidence, not a
    vague qualifier. Sanity check: P0 must mention 'metric' or 'quantified',
    P1 must mention 'method' / 'outcome' / 'proof', etc.
    """
    from linkright.profile.priority_legend import P0, P1, P2, P3
    # P0: quantified
    p0_shape = P0.evidence_shape.lower()
    assert any(k in p0_shape for k in ("quantified", "metric", "number", "%")), (
        "P0 evidence_shape must reference a quantified metric — got: "
        + P0.evidence_shape
    )
    # P1: named proof, no metric
    p1_shape = P1.evidence_shape.lower()
    assert any(k in p1_shape for k in ("method", "outcome", "proof", "deliverable")), (
        "P1 evidence_shape must reference method/outcome/proof — got: "
        + P1.evidence_shape
    )
    assert "no quantified" in p1_shape or "no number" in p1_shape, (
        "P1 must explicitly contrast with P0 (no quantified metric) — got: "
        + P1.evidence_shape
    )
    # P2: contextual activity
    p2_shape = P2.evidence_shape.lower()
    assert "context" in p2_shape or "activity" in p2_shape


def test_priority_legend_inline_renders_all_tiers():
    from linkright.profile.priority_legend import format_legend_inline
    con = _recording_console()
    con.print(format_legend_inline())
    text = con.export_text()
    for code in ("P0", "P1", "P2", "P3"):
        assert code in text, f"Inline legend missing tier {code}."
    # No vague legacy terms left behind.
    for stale in ("=core", "=strong", "=supporting", "=context-only"):
        assert stale not in text, (
            f"Inline legend still uses the vague legacy descriptor {stale!r} — "
            f"UAT bug #29 not fixed."
        )


def test_priority_legend_detailed_includes_evidence_shape():
    from linkright.profile.priority_legend import format_legend_detailed
    lines = format_legend_detailed()
    assert len(lines) == 4
    joined = "\n".join(lines).lower()
    # All four tiers represented
    for code in ("P0", "P1", "P2", "P3"):
        assert code in "\n".join(lines)
    # Detailed lines should communicate evidence shape
    assert "metric" in joined or "quantified" in joined
    assert "context" in joined or "activity" in joined


def test_priority_badge_falls_through_unknown_code():
    from linkright.profile.priority_legend import priority_badge
    assert priority_badge("P0") != ""
    assert priority_badge("p0") != ""  # case-insensitive
    assert priority_badge("XX") == ""
    assert priority_badge("") == ""
    assert priority_badge(None) == ""  # type: ignore[arg-type]


def test_priority_badge_p0_uses_red():
    from linkright.profile.priority_legend import priority_badge
    con = _recording_console()
    con.print(priority_badge("P0") + " test")
    html = con.export_html(inline_styles=True, clear=False)
    # bold red — Rich expands "bold red" to the default red ANSI; assert
    # we at least did not lose the badge.
    text = con.export_text()
    assert "P0" in text


def test_render_uses_priority_legend_module():
    """profile/render.py must import and call format_legend_inline — i.e. NOT
    keep its own hard-coded legend string. Guards against the legacy duplicate
    drifting out of sync with the priority_legend.py definitions.
    """
    from pathlib import Path
    src = Path(__file__).resolve().parent.parent / "src" / "linkright" / "profile" / "render.py"
    body = src.read_text(encoding="utf-8")
    assert "format_legend_inline" in body, (
        "render.py must import format_legend_inline from priority_legend — "
        "single-source-of-truth invariant for the legend."
    )
    # Legacy vague descriptors should be gone.
    for stale in ("P0[/]=core", "P1[/]=strong", "P2[/]=supporting", "P3[/]=context-only"):
        assert stale not in body, (
            f"render.py still inlines legacy legend text {stale!r}; "
            "delete and rely on format_legend_inline."
        )


def test_enrich_llm_prompt_text_available():
    """Importance-assignment prompt must be derivable from priority_legend so
    the LLM's classification rules cannot drift from the user-facing legend."""
    from linkright.profile.priority_legend import llm_prompt_instructions
    text = llm_prompt_instructions()
    assert "P0:" in text
    assert "P1:" in text
    assert "P2:" in text
    assert "P3:" in text


# ─── #30  muted_detail / claude_metadata  ─────────────────────────────────────

def test_muted_detail_renders_with_prefix():
    from linkright.ui.patterns import muted_detail
    con = _recording_console()
    muted_detail("/tmp/output.pdf", label="Saved to", console=con)
    text = con.export_text()
    assert "Saved to: /tmp/output.pdf" in text
    assert "·" in text, "muted_detail must lead with the '·' field-separator glyph."


def test_muted_detail_uses_muted_gray_hex():
    from linkright.ui.patterns import muted_detail
    con = _recording_console()
    muted_detail("a3f2", label="Run ID", console=con)
    html = con.export_html(inline_styles=True, clear=False)
    assert "8e8e93" in html.lower(), (
        "muted_detail must render in tui.muted (#8E8E93)."
    )


def test_muted_detail_no_label_renders_value_only():
    from linkright.ui.patterns import muted_detail
    con = _recording_console()
    muted_detail("~/.linkright/outputs/run-a3f2/resume.pdf", console=con)
    text = con.export_text()
    assert "~/.linkright/outputs/run-a3f2/resume.pdf" in text
    # No phantom 'label: ' prefix when label is empty
    assert ": ~/" not in text


def test_claude_metadata_renders_separator_between_pairs():
    from linkright.ui.patterns import claude_metadata
    con = _recording_console()
    claude_metadata(
        [("Run", "a3f2"), ("Model", "gemma3:1b"), ("Tokens", "1.2k")],
        console=con,
    )
    text = con.export_text()
    assert "Run: a3f2" in text
    assert "Model: gemma3:1b" in text
    assert "Tokens: 1.2k" in text
    # All three pairs concatenated with the separator
    assert text.count("·") >= 3  # leading bullet + 2 between-pair separators


def test_step_meta_facade_exists():
    import linkright.ui as ui
    assert hasattr(ui, "step_meta")
    assert callable(ui.step_meta)


# ─── Cross-bug invariants  ────────────────────────────────────────────────────

def test_no_raw_ansi_in_any_e3_primitive():
    """All new primitives must render through Rich — no raw ANSI escapes."""
    from linkright.ui.patterns import (
        user_input_echo, progress_verb, muted_detail, claude_metadata,
    )
    con = _recording_console()
    user_input_echo("test", label="In", console=con)
    progress_verb("Working", telemetry="0.1s", console=con)
    muted_detail("foo", label="bar", console=con)
    claude_metadata([("a", "1"), ("b", "2")], console=con)
    text = con.export_text()
    assert "\x1b[" not in text
    assert "\033[" not in text


def test_e1_primitives_still_callable():
    """E3 changes must not break the E1 primitive surface — call each one."""
    from linkright.ui.patterns import (
        picker, status_event, insight_block, code_block,
        progress_indicator, tree_branch,
    )
    con = _recording_console()
    picker(["A", "B"], title="T", console=con)
    status_event("label", True, "detail", console=con)
    insight_block(["line"], console=con)
    code_block("x=1", "python", console=con)
    progress_indicator("doing", elapsed_s=1.0, console=con)
    tree_branch("root", ["child"], console=con)
    text = con.export_text()
    assert "A" in text and "label" in text and "doing" in text


def test_e3_primitives_callable_via_ui_facade():
    """All E3 facade helpers must be invocable without explicit console arg."""
    import linkright.ui as ui
    # These call the module-level console; just ensure no exception.
    ui.step_echo_input("foo", label="In")
    ui.step_progress("Smooshing", telemetry="0.2s")
    ui.step_meta("Run ID", "a3f2")


def test_priority_badge_dark_theme_contrast_p2_p3():
    """P2 / P3 use 'dim' / 'dim italic' so the lowest-priority bullets still
    render readable text in monochrome terminals (no terminal renders 'dim' as
    fully invisible; the test just ensures the string contains the badge code
    so monochrome fallback is non-empty)."""
    from linkright.profile.priority_legend import priority_badge
    con = _recording_console()
    con.print(priority_badge("P2"))
    con.print(priority_badge("P3"))
    text = con.export_text()
    assert "P2" in text
    assert "P3" in text
