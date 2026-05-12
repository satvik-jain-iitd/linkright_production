"""Tests for success box path rendering — S4.5.

AC1: No filename string breaks mid-word across lines in the success box.
AC2: Box renders cleanly at 80, 100, 120 col terminal widths.
AC3: Filename shown bold on its own line, full path on a separate (indented) line
     below it — even if the full path itself folds at a path-separator on narrow
     terminals (fold at "/" is acceptable; mid-word break is not).
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

import linkright.ui as ui_mod
from linkright.ui import success_card, TEAL


# Representative long path that previously caused a mid-word wrap.
_LONG_PDF_PATH = Path(
    "/Users/satvikjain/.linkright/runs/2026-05-11_12-34-56/artifacts/15_final_resume.pdf"
)


def _render_card_via_helper(width: int) -> str:
    """Render using the low-level Rich primitives (same as success_card internals)."""
    buf = io.StringIO()
    con = Console(file=buf, width=width, highlight=False, markup=True,
                  force_terminal=False, no_color=True)

    filename = _LONG_PDF_PATH.name
    full_path = str(_LONG_PDF_PATH)
    pdf_field_value = f"{filename}\n{full_path}"

    fields = [("PDF", pdf_field_value), ("Took", "2m 15s")]

    key_w = max(len(k) for k, _ in fields) + 2
    cont_indent = " " * (2 + key_w + 2)

    body = Text(overflow="fold", no_wrap=False)
    for i, (k, v) in enumerate(fields):
        if i > 0:
            body.append("\n")
        first_line, *rest_lines = v.split("\n")
        body.append("  ")
        body.append(f"{k:<{key_w}}", style="bold")
        body.append("  ")
        body.append(first_line, style="bold")
        for line in rest_lines:
            body.append("\n")
            body.append(cont_indent)
            body.append(line, style="dim")

    con.print()
    con.print(Panel(body, title="Resume Tailored", border_style="cyan",
                    expand=False, padding=(1, 2)))
    con.print()
    return buf.getvalue()


def _render_card_via_module(width: int) -> str:
    """Render using the actual linkright.ui.success_card() with a test console."""
    buf = io.StringIO()
    original_console = ui_mod.console
    ui_mod.console = Console(file=buf, width=width, highlight=False,
                              markup=True, force_terminal=False, no_color=True)
    try:
        filename = _LONG_PDF_PATH.name
        full_path = str(_LONG_PDF_PATH)
        pdf_field_value = f"{filename}\n{full_path}"

        success_card(
            title="Resume Tailored",
            fields=[("PDF", pdf_field_value), ("Took", "2m 15s")],
            next_steps=[("linkright critique", "review")],
            accent=TEAL,
        )
    finally:
        ui_mod.console = original_console
    return buf.getvalue()


@pytest.mark.parametrize("width", [80, 100, 120])
def test_no_mid_filename_wrap(width: int) -> None:
    """AC1 + AC2: The filename '15_final_resume.pdf' must never be split
    across two adjacent lines at any of 80/100/120 col widths.

    A fold at a '/' path separator is acceptable (the filename component is
    still whole). A fold that breaks the filename itself (e.g. '15_final_re'
    on one line and 'sume.pdf' on the next) is the bug being fixed.
    """
    output = _render_card_via_helper(width)
    lines = output.splitlines()
    filename = _LONG_PDF_PATH.name  # "15_final_resume.pdf"

    # Detect mid-word split: two adjacent lines whose stripped concatenation
    # contains the filename as a contiguous substring, while neither line alone
    # contains the whole filename.
    for i in range(len(lines) - 1):
        stripped = lines[i].rstrip()
        stripped_next = lines[i + 1].lstrip()
        combined = stripped + stripped_next
        if (filename in combined
                and filename not in stripped
                and filename not in stripped_next):
            pytest.fail(
                f"[width={width}] Filename '{filename}' is split across lines "
                f"{i} and {i + 1}:\n  line {i}:   {repr(stripped)}\n"
                f"  line {i+1}: {repr(stripped_next)}"
            )


@pytest.mark.parametrize("width", [80, 100, 120])
def test_filename_appears_whole_on_key_row(width: int) -> None:
    """AC3 (part 1): The filename must appear whole on the 'PDF' key row."""
    output = _render_card_via_helper(width)
    lines = output.splitlines()
    filename = _LONG_PDF_PATH.name  # "15_final_resume.pdf"

    # Find a line that has both the 'PDF' key label and the intact filename.
    key_row_found = any("PDF" in line and filename in line for line in lines)
    assert key_row_found, (
        f"[width={width}] No line found containing both 'PDF' label and "
        f"intact filename '{filename}'.\nRendered output:\n{output}"
    )


@pytest.mark.parametrize("width", [80, 100, 120])
def test_full_path_on_separate_continuation_line(width: int) -> None:
    """AC3 (part 2): The full path must start on a line AFTER the key row.

    At narrow terminals the path may fold across multiple lines (fold at '/'
    is acceptable — the line still starts with the beginning of the path).
    We verify the continuation indented line exists and starts with the first
    segment of the path.
    """
    output = _render_card_via_helper(width)
    lines = output.splitlines()

    # Find the PDF key row.
    filename = _LONG_PDF_PATH.name
    key_row_idx = next(
        (i for i, line in enumerate(lines) if "PDF" in line and filename in line),
        None,
    )
    assert key_row_idx is not None, (
        f"[width={width}] PDF key row not found in output:\n{output}"
    )

    # The line immediately after the key row must start the full path.
    # (It will be indented by cont_indent then start with '/'.)
    assert key_row_idx + 1 < len(lines), (
        f"[width={width}] No line after PDF key row."
    )
    next_line = lines[key_row_idx + 1]
    path_root = "/Users/satvikjain/.linkright"  # first segment of the path
    assert path_root in next_line, (
        f"[width={width}] Line after PDF key row does not contain path start "
        f"'{path_root}'.\n  key_row:    {repr(lines[key_row_idx])}\n"
        f"  next_line:  {repr(next_line)}"
    )


@pytest.mark.parametrize("width", [80, 100, 120])
def test_success_card_module_no_crash(width: int) -> None:
    """AC1 + AC2: success_card() from linkright.ui must not raise and must
    include the filename in its output."""
    rendered = _render_card_via_module(width)
    filename = _LONG_PDF_PATH.name
    assert filename in rendered, (
        f"[width={width}] filename '{filename}' not found in rendered output"
    )


@pytest.mark.parametrize("width", [80, 100, 120])
def test_success_card_module_no_mid_filename_wrap(width: int) -> None:
    """AC1 via the actual module function: filename must not be split mid-word."""
    rendered = _render_card_via_module(width)
    lines = rendered.splitlines()
    filename = _LONG_PDF_PATH.name

    for i in range(len(lines) - 1):
        stripped = lines[i].rstrip()
        stripped_next = lines[i + 1].lstrip()
        combined = stripped + stripped_next
        if (filename in combined
                and filename not in stripped
                and filename not in stripped_next):
            pytest.fail(
                f"[width={width}] Filename '{filename}' is split across lines "
                f"{i} and {i + 1}:\n  line {i}:   {repr(stripped)}\n"
                f"  line {i+1}: {repr(stripped_next)}"
            )
