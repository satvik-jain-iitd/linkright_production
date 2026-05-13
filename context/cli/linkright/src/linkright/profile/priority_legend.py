"""Quantified Priority-Legend definitions (UAT bug #29).

The old in-line legend in `profile/render.py` used qualitative terms
("core / strong / supporting / context-only") that didn't tell the user
*what makes* a nugget a P0 vs a P1. This module replaces it with
evidence-shape definitions that are reproducible by both the LLM that
assigns the importance and the user inspecting the result.

Design rules (cross-checked against memory):

  * Definitions describe the SHAPE of the evidence in the nugget, not an
    absolute revenue/headcount threshold. Why: cross-domain resumes
    (designer, scientist, marketer) do NOT all have $-denominated metrics.
    A scoped, well-grounded one-tier system works for all.
  * Per memory `feedback_metric_placeholders_not_fabrication.md` we never
    invent metrics — the legend asks the LLM (and user) to FIND quantified
    evidence already in the source text, not to make some up.
  * Per memory `feedback_brand_design_spec_2026_05_03.md` Rule 2: the legend
    body stays text-default colour; only the P-badge tokens carry colour.
  * Per memory `feedback_cli_ui_patterns.md`: red = #EA4335 brand.secondary
    for P0, gold = #F4B400 for P1, muted #5F6368 for P2/P3.

Single source of truth — importable by both `profile/render.py` (header
legend) and `profile/enrich.py` (LLM prompts that assign importance).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriorityTier:
    code: str                   # "P0", "P1", "P2", "P3"
    headline: str               # 1-3 word descriptor for the legend chip
    evidence_shape: str         # measurable criterion for assignment
    example: str                # one canonical example bullet
    badge_style: str            # Rich markup style (theme alias)


# ── Tiers ────────────────────────────────────────────────────────────────────
# Order matters — they are P0 → P3 strongest → weakest. Anything above the
# floor of P3 (i.e. context-free generic statements) should not enter the
# nugget pool at all; P3 exists as a transient bucket so the audit/cleanup
# loop (#32, deferred) has a category to demote ambiguous extractions into.

P0 = PriorityTier(
    code="P0",
    headline="Quantified outcome",
    evidence_shape=(
        "Contains a named outcome AND at least one quantified metric "
        "(number with unit or %/$/x/+ symbol)."
    ),
    example=(
        "Cut customer-onboarding time from 14 days to 4 days "
        "(-71%) for 1,200 enterprise accounts in Q3."
    ),
    badge_style="bold red",
)

P1 = PriorityTier(
    code="P1",
    headline="Named proof, no metric",
    evidence_shape=(
        "Names a specific method, decision, deliverable, or stakeholder "
        "outcome, but contains no quantified number."
    ),
    example=(
        "Re-architected the dunning emails to use Stripe's grace-period "
        "windows, eliminating involuntary churn for annual plans."
    ),
    badge_style="bold yellow",
)

P2 = PriorityTier(
    code="P2",
    headline="Contextual activity",
    evidence_shape=(
        "Describes activity with specific context (company, role, team, "
        "or tech) but no named outcome or metric."
    ),
    example=(
        "Owned the iOS onboarding flow for the growth pod at Stripe, "
        "partnering with design and PMM."
    ),
    badge_style="dim",
)

P3 = PriorityTier(
    code="P3",
    headline="Generic / unverifiable",
    evidence_shape=(
        "Generic statement with no specific context, outcome, or metric. "
        "Candidates for audit/cleanup or merge into a parent nugget."
    ),
    example=(
        "Collaborated with cross-functional teams to deliver business value."
    ),
    badge_style="dim italic",
)

ALL_TIERS: tuple[PriorityTier, ...] = (P0, P1, P2, P3)
TIER_BY_CODE: dict[str, PriorityTier] = {t.code: t for t in ALL_TIERS}


# ── Renderers ────────────────────────────────────────────────────────────────


def format_legend_inline() -> str:
    """One-line Rich markup string for the in-tree header legend.

    Used by `profile/render.py` immediately above the career-outline tree.
    Keeps the legend compact (single terminal row) while still conveying
    the evidence-shape via the headline.
    """
    chips = []
    for t in ALL_TIERS:
        chips.append(f"[{t.badge_style}]{t.code}[/]={t.headline}")
    return "[dim]Priority:[/] " + "  ".join(chips)


def format_legend_detailed() -> list[str]:
    """Multi-line legend with full evidence-shape definitions.

    Returned as a list of Rich-markup-ready strings so callers can plug them
    into a panel, an `insight_block`, or stream them through `console.print`.
    """
    lines: list[str] = []
    for t in ALL_TIERS:
        lines.append(
            f"[{t.badge_style}]{t.code}[/]  [bold]{t.headline}[/]  "
            f"— {t.evidence_shape}"
        )
    return lines


def priority_badge(code: str) -> str:
    """Return the Rich-markup badge for a P-tier code, or '' if unknown."""
    tier = TIER_BY_CODE.get((code or "").upper().strip())
    if not tier:
        return ""
    return f"[{tier.badge_style}]{tier.code}[/]"


def llm_prompt_instructions() -> str:
    """Block of text suitable for embedding into an LLM extraction prompt.

    Mirrors `format_legend_detailed` but stripped of Rich markup so the LLM
    sees just the evidence-shape rules. Use in `profile/enrich.py` to keep
    importance-assignment behaviour consistent with the user-facing legend.
    """
    lines = ["Importance levels:"]
    for t in ALL_TIERS:
        lines.append(f"  - {t.code}: {t.evidence_shape}")
    return "\n".join(lines)


__all__ = [
    "PriorityTier",
    "P0", "P1", "P2", "P3", "ALL_TIERS", "TIER_BY_CODE",
    "format_legend_inline",
    "format_legend_detailed",
    "priority_badge",
    "llm_prompt_instructions",
]
