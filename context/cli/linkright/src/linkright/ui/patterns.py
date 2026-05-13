"""LinkRight CLI rendering primitives — reusable building blocks.

Cluster E1 (PR #158) shipped 6 primitives: picker, status_event, insight_block,
code_block, progress_indicator, tree_branch.

Cluster E3 (this file) adds 5 more — strictly additive, no E1 signatures
changed:
  7.  TYPE_SOMETHING + lr_select_with_custom — "Type something…" sentinel in
      numbered selection lists (UAT bug #19)
  8.  user_input_echo — high-contrast white '●' echo for previously-submitted
      user inputs (UAT bug #20)
  9.  progress_verb — coral working verb + muted grey telemetry tail, mirroring
      Claude Code's "* Smooshing… (0.3s · 12 toks)" style (UAT bug #21)
  10. muted_detail — '· label: value' sub-context line for metadata /
      timestamps / paths (UAT bug #30)

The Priority Legend definitions (UAT bug #29) live in
`linkright.profile.priority_legend` so they can be imported by both the
profile renderer and the enrichment LLM prompts.

All primitives accept an optional `console` kwarg so callers can pass a
pre-configured or recording console (useful for tests). When omitted they
use the module-level themed console from linkright.ui.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from rich.console import Console


# Sentinel returned by lr_select_with_custom() when the user picks the
# "Type something…" option. Distinct, opaque, and quoted-only so it cannot
# collide with a real choice label even if a caller types "Type something…"
# as a legitimate option.
TYPE_SOMETHING: str = "__lr_custom_input__"
TYPE_SOMETHING_LABEL: str = "Type something…"


def _con(console: "Console | None") -> "Console":
    if console is not None:
        return console
    from linkright.ui import console as _default
    return _default


# ── 1. picker ────────────────────────────────────────────────────────────────

def picker(
    items: list[str],
    *,
    title: str = "",
    indent: int = 2,
    console: "Console | None" = None,
) -> None:
    """Numbered choice list — display-only (no interaction).

    Use alongside lr_select() when you want to show options before prompting.
    """
    con = _con(console)
    if title:
        con.print(f"\n{' ' * indent}[step.gold]◆[/]  [bold]{title}[/]")
    for i, item in enumerate(items, 1):
        con.print(f"{' ' * indent}  [brand.primary]{i}.[/]  {item}")


# ── 2. status_event ───────────────────────────────────────────────────────────

def status_event(
    label: str,
    ok: bool,
    detail: str = "",
    *,
    indent: int = 2,
    label_width: int = 0,
    console: "Console | None" = None,
) -> None:
    """Single status row: ✓/✗ + label + grey detail.

    Used by `linkright doctor`, `setup --check`, and any checklist surface.
    `label_width` pads labels to a fixed column for tabular alignment.
    """
    con = _con(console)
    mark = "[metric.positive]✓[/]" if ok else "[error]✗[/]"
    padded = f"{label:<{label_width}}" if label_width else label
    detail_str = f"  [text.secondary]{detail}[/]" if detail else ""
    con.print(f"{' ' * indent}{mark}  {padded}{detail_str}")


# ── 3. insight_block ─────────────────────────────────────────────────────────

def insight_block(
    lines: list[str],
    *,
    indent: int = 0,
    console: "Console | None" = None,
) -> None:
    """★ Insight block with horizontal rules — mirrors Claude Code style."""
    con = _con(console)
    rule = "─" * 49
    con.print(f"\n[step.accent]★ Insight {rule[:40]}[/]")
    for line in lines:
        con.print(f"{' ' * indent}{line}")
    con.print(f"[step.accent]{rule}[/]\n")


# ── 4. code_block ─────────────────────────────────────────────────────────────

def code_block(
    code: str,
    language: str = "",
    *,
    title: str = "",
    console: "Console | None" = None,
) -> None:
    """Formatted code snippet using Rich Syntax or plain markup."""
    con = _con(console)
    try:
        from rich.syntax import Syntax
        syn = Syntax(code, language or "text", theme="monokai", line_numbers=False)
        if title:
            con.print(f"[text.secondary]{title}[/]")
        con.print(syn)
    except Exception:
        if title:
            con.print(f"[text.secondary]{title}[/]")
        con.print(f"[dim]{code}[/]")


# ── 5. progress_indicator ─────────────────────────────────────────────────────

def progress_indicator(
    label: str,
    elapsed_s: float | None = None,
    *,
    indent: int = 6,
    console: "Console | None" = None,
) -> None:
    """Elapsed-time progress line — printed inline during long operations."""
    con = _con(console)
    if elapsed_s is not None:
        time_str = f"  [text.secondary]{elapsed_s:.1f}s[/]"
    else:
        time_str = ""
    con.print(f"{' ' * indent}[step.accent]●[/]  {label}{time_str}")


# ── 6. tree_branch ────────────────────────────────────────────────────────────

def tree_branch(
    label: str,
    children: list[str] | None = None,
    *,
    indent: int = 2,
    accent: str = "step.accent",
    console: "Console | None" = None,
) -> None:
    """Tree-indented status block — root label + optional child lines."""
    con = _con(console)
    con.print(f"\n{' ' * indent}[{accent}]◆[/]  [bold]{label}[/]")
    if children:
        for child in children:
            con.print(f"{' ' * (indent + 4)}[text.secondary]→[/]  {child}")


# ── 7. lr_select_with_custom — "Type something" entry (UAT bug #19) ───────────

def append_type_something(choices: Sequence[Any]) -> list[Any]:
    """Return a new choice list with a "Type something…" entry appended.

    Use when callers want to render a picker that exposes a free-text entry
    alongside the suggested options. The sentinel value ``TYPE_SOMETHING`` is
    what the caller will receive back when the user picks it; the displayed
    label is ``TYPE_SOMETHING_LABEL``.

    Callers that build questionary Choice objects directly (rather than plain
    strings) can compose the sentinel themselves:

        from questionary import Choice
        choices = [Choice("Resume PDF", value="pdf"),
                   Choice(TYPE_SOMETHING_LABEL, value=TYPE_SOMETHING)]

    For plain string lists this helper preserves order: existing choices
    first, custom-entry last. We deliberately never re-order existing options
    so muscle memory ("1. Resume PDF") stays stable as the list grows.
    """
    # Defensive copy — never mutate caller's list. Also de-dupe if caller has
    # already appended the sentinel (idempotent).
    out = list(choices)

    # Plain-string idempotency check.
    if TYPE_SOMETHING in out or TYPE_SOMETHING_LABEL in out:
        return out

    # questionary.Choice idempotency check — Choice objects don't compare equal
    # to plain strings, so the `in` check above misses them. Walk the list and
    # detect by `.value` / `.title` attributes (duck-typed; safe for any object
    # exposing those attrs). Without this, a caller that pre-composed a Choice
    # with value=TYPE_SOMETHING would have a plain-string sentinel appended on
    # top → questionary chokes on the mixed list.
    for c in out:
        title = getattr(c, "title", None)
        value = getattr(c, "value", None)
        if title == TYPE_SOMETHING_LABEL or value == TYPE_SOMETHING:
            return out

    # Detect whether the caller is using Choice objects so we append a matching
    # Choice (not a bare string, which would break the homogeneous-type
    # invariant questionary expects).
    has_choice_objects = any(
        hasattr(c, "title") and hasattr(c, "value") for c in out
    )
    if has_choice_objects:
        try:
            from questionary import Choice
            out.append(Choice(title=TYPE_SOMETHING_LABEL, value=TYPE_SOMETHING))
        except ImportError:
            # Fallback — questionary unavailable in test contexts.
            out.append(TYPE_SOMETHING_LABEL)
    else:
        out.append(TYPE_SOMETHING_LABEL)
    return out


def lr_select_with_custom(
    question: str,
    choices: Sequence[Any],
    *,
    accent: str | None = None,
    custom_prompt: str = "Type your answer:",
    custom_default: str = "",
    hint: str = "Enter to select  ·  ↑↓ to navigate  ·  Esc to cancel",
) -> str | None:
    """Numbered single-select that also offers a free-text "Type something…" entry.

    Returns the selected choice's underlying value (string), or the user's
    typed string when they pick "Type something…". Returns ``None`` on
    cancel/ESC so callers can detect the abort path explicitly.

    Implementation note: this thin wrapper sits on top of ``lr_select`` +
    ``lr_text`` from ``linkright.ui.__init__``. Kept here so the sentinel
    constant + helper live next to the rest of the picker primitives without
    creating a circular import (we import inside the function body).
    """
    from linkright.ui import lr_select, lr_text, TEAL
    use_accent = accent or TEAL
    augmented = append_type_something(choices)
    pick = lr_select(question, choices=augmented, accent=use_accent, hint=hint)
    if pick is None:
        return None
    # Match against label OR sentinel — supports plain-string lists AND
    # questionary.Choice objects whose `.value` was set to TYPE_SOMETHING.
    if pick == TYPE_SOMETHING_LABEL or pick == TYPE_SOMETHING:
        typed = lr_text(custom_prompt, default=custom_default, accent=use_accent)
        # Empty/cancelled type-something falls through as None — callers
        # should re-prompt or treat as cancellation.
        if typed is None or not str(typed).strip():
            return None
        return str(typed).strip()
    return pick


# ── 8. user_input_echo — '●' echo for prior user inputs (UAT bug #20) ────────

def user_input_echo(
    text: str,
    *,
    label: str = "",
    indent: int = 2,
    console: "Console | None" = None,
) -> None:
    """Echo a previously-submitted user input with a high-contrast white '●'.

    Mirrors Claude Code's pattern of bubbling the user's last answer back to
    them before continuing — gives the user visual confirmation of what the
    tool *thinks* they said. The bullet uses ``tui.hi_white`` which is now
    aliased to ``bold bright_white`` (was ``#F5F5F7`` before UAT cluster E3
    cycle 2 — that hex had ΔE ≈ 3.5% vs #FFFFFF, effectively invisible on
    Apple Terminal default, iTerm light, and GNOME Tango Light themes).
    Rich auto-inverts ``bright_white`` against the detected terminal
    background, so the bullet stays legible on BOTH light and dark themes
    without us reading $COLORFGBG. The body text is rendered in default
    foreground for maximum readability.

    Example output (with label):

        ●  Name: Satvik Jain

    Example output (no label):

        ●  Increased revenue by 30% in Q4
    """
    con = _con(console)
    body = f"{label}: {text}" if label else text
    con.print(f"{' ' * indent}[tui.hi_white]●[/]  {body}")


# ── 9. progress_verb — coral working verb + muted telemetry (UAT bug #21) ────

def progress_verb(
    verb: str,
    *,
    telemetry: str = "",
    icon: str = "*",
    indent: int = 6,
    console: "Console | None" = None,
) -> None:
    """Coral working verb with optional muted-grey telemetry tail.

    Renders like::

        *  Smooshing nuggets…  (0.3s · 12 toks)
        \\__/\\__________________/\\______________/
         |          |                   |
         coral      coral               muted grey

    Pairs with ``progress_indicator`` (which uses ``●`` and is for *completed*
    progress lines). Use ``progress_verb`` for *in-flight* working states.

    The default icon ``*`` matches ``ICON.working`` from
    ``linkright.ui.icons``; callers wanting the green "thinking" variant can
    pass ``icon="+"`` and the colour will switch to ``tui.green`` automatically.

    Telemetry payload should be a short "·"-separated metadata string
    (latency, token counts, batch index) — never user-facing copy.
    """
    con = _con(console)
    # Pick colour based on icon semantics: '*' = working (coral), '+' = thinking (green).
    icon_color = "tui.green" if icon.strip() == "+" else "tui.coral"
    tail = f"  [tui.muted]{telemetry}[/]" if telemetry else ""
    con.print(f"{' ' * indent}[{icon_color}]{icon}[/]  [tui.coral]{verb}[/]{tail}")


# ── 10. muted_detail — Claude Code sub-context line (UAT bug #30) ────────────

def muted_detail(
    text: str,
    *,
    label: str = "",
    indent: int = 4,
    prefix: str = "·",
    console: "Console | None" = None,
) -> None:
    """Render a secondary metadata / timestamp line in muted grey.

    Used for sub-context details the user *might* want to scan but does not
    need to read — paths, run IDs, model names, timestamps. Always rendered
    in ``tui.muted`` (#8E8E93) so it visually recedes behind the primary
    surface text.

    Example output (with label)::

          · Run ID: 2026-05-13-a3f2

    Example output (no label)::

          · ~/.linkright/outputs/run-a3f2/resume.pdf
    """
    con = _con(console)
    body = f"{label}: {text}" if label else text
    con.print(f"{' ' * indent}[tui.muted]{prefix} {body}[/]")


def claude_metadata(
    pairs: Sequence[tuple[str, str]],
    *,
    indent: int = 4,
    sep: str = "  ·  ",
    console: "Console | None" = None,
) -> None:
    """Render a compact muted-grey metadata footer: ``key: value · key: value``.

    Common shape for run summaries::

          · Run: a3f2  ·  Model: gemma3:1b  ·  Tokens: 1.2k

    Use ``muted_detail`` for a single-line sub-context, ``claude_metadata``
    for the multi-key footer that ends a step.
    """
    con = _con(console)
    parts = [f"{k}: {v}" for k, v in pairs]
    line = sep.join(parts)
    con.print(f"{' ' * indent}[tui.muted]· {line}[/]")
