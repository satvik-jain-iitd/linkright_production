"""Profile renderer using rich — resume-section-grouped outline.

Renders the user's profile in the same section taxonomy a real resume uses
(Professional Experience → Education → Skills → Projects → Awards), so the
inspection tool feels like a preview of the resume rather than a developer
view of the underlying nuggets table. Dates are loaded lazily from the
parsed-resume artifact so users can see role timelines at a glance. A
`--full` flag disables the 120-char truncation when the user wants to read
a full bullet that was clipped in the default view.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

from linkright.ui.theme import LR_THEME
from .pipeline import _profile_dir, load_metadata, load_nuggets


# Resume-conventional section ordering for mid-career resumes. Add new tuples
# as the nugget extractor learns to emit new types (certificates, languages,
# voluntary, etc.). Anything not in this list falls through to "Other".
SECTION_ORDER: list[tuple[str, str]] = [
    ("work_experience",     "Professional Experience"),
    ("education",           "Education"),
    ("skill",               "Skills"),
    ("independent_project", "Projects"),
    ("award",               "Awards"),
]
SECTION_LABELS = dict(SECTION_ORDER)

# Future-proofing: when nugget extractor starts emitting these types, surface
# them as "Not yet populated: X" hints. Order follows FlowCV's content panel.
FUTURE_SECTION_LABELS: list[tuple[str, str]] = [
    ("summary",      "Summary"),
    ("language",     "Languages"),
    ("certificate",  "Certificates"),
    ("interest",     "Interests"),
    ("course",       "Courses"),
    ("organisation", "Organisations"),
    ("publication",  "Publications"),
    ("voluntary",    "Voluntary Work"),
]


def _normalize(s: Optional[str]) -> str:
    """Treat literal 'none'/'null'/'n/a' as empty (some upstream LLMs emit
    these strings instead of leaving the field blank)."""
    s = (s or "").strip()
    return "" if s.lower() in ("", "none", "null", "n/a") else s


_MONTH_NUMS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _date_sort_key(date_str: str) -> tuple[int, int]:
    """Parse a freeform resume date into a sortable (year, month) tuple.

    Handles these inputs the wild produces:
      'Nov 2024'    → (2024, 11)
      'Jul 2024'    → (2024, 7)
      '2021'        → (2021, 0)        # year-only education entries
      'Present'     → (9999, 12)       # defensive fallback: should not occur
                                       # for `start_date` in valid data, but
                                       # if it does, sort it to top in DESC.
                                       # NOTE: 'current-role-first' boost for
                                       # Professional Experience is implemented
                                       # at the COMPANY-sort level via
                                       # `_co_key`'s `is_active` flag, NOT
                                       # via this function's `Present` branch.
      '' / unknown  → (0, 0)           # sorts last in DESC

    Without this helper, string-comparison on 'Nov 2024' vs 'Jan 2025' would
    yield reverse-chronological order ('N' > 'J' alphabetically), causing a
    November-2024 role to appear above a January-2025 role despite being
    older.
    """
    if not date_str:
        return (0, 0)
    s = date_str.strip().lower()
    if s == "present":
        return (9999, 12)
    year = 0
    month = 0
    for tok in s.replace(",", " ").replace("-", " ").split():
        if tok.isdigit():
            n = int(tok)
            if 1900 <= n <= 2100:
                year = n
        elif tok[:3] in _MONTH_NUMS:
            month = _MONTH_NUMS[tok[:3]]
    return (year, month)


def _load_date_lookups(profile_dir: Path) -> tuple[dict[tuple[str, str], str], dict[str, str], dict[tuple[str, str], str], dict[tuple[str, str], str]]:
    """Lazy-load `01_resume_parsed.json` for date hints.

    Returns four dicts (all empty if the artifact is missing or corrupt):
      * work_dates:  (company.lower(), role.lower()) → "start – end"
      * edu_dates:   institution.lower()             → "year" (or "y1 / y2"
                     if multiple degrees from the same institution — common
                     for IIT-style 5-year integrated programs)
      * work_starts: (company.lower(), role.lower()) → start_date string
                     (used to sort Professional Experience by recency)
      * work_ends:   (company.lower(), role.lower()) → end_date string
                     (used to detect 'Present' = currently-active roles, so
                     they sort to the top of Professional Experience —
                     resume-convention "current job first")

    Failure to load is non-fatal — the tree still renders, just without
    date chips. We never crash `profile show` over a missing artifact.
    """
    work_dates: dict[tuple[str, str], str] = {}
    edu_dates: dict[str, str] = {}
    work_starts: dict[tuple[str, str], str] = {}
    work_ends: dict[tuple[str, str], str] = {}

    parsed_path = profile_dir / "artifacts" / "01_resume_parsed.json"
    if not parsed_path.exists():
        return work_dates, edu_dates, work_starts, work_ends

    try:
        parsed = json.loads(parsed_path.read_text()).get("parsed", {})
        for exp in parsed.get("experiences", []) or []:
            co = (exp.get("company") or "").strip().lower()
            role = (exp.get("role") or "").strip().lower()
            start = (exp.get("start_date") or "").strip()
            end = (exp.get("end_date") or "").strip() or "Present"
            if co and start:
                work_dates[(co, role)] = f"{start} – {end}"
                work_starts[(co, role)] = start
                work_ends[(co, role)] = end
        # Accumulate education years per institution into a list, then join
        # with ' / ' for display. This preserves dual-degree history (e.g.
        # IIT integrated 5-year programs) instead of silently overwriting.
        edu_years_acc: dict[str, list[str]] = defaultdict(list)
        for edu in parsed.get("education", []) or []:
            inst = (edu.get("institution") or "").strip().lower()
            year = (edu.get("year") or "")
            if inst and year:
                edu_years_acc[inst].append(str(year))
        for inst, years in edu_years_acc.items():
            # Sort DESC so the most recent year leads ('2021 / 2019').
            try:
                years_sorted = sorted(set(years), key=lambda y: int(y) if y.isdigit() else 0, reverse=True)
            except Exception:
                years_sorted = list(dict.fromkeys(years))
            edu_dates[inst] = " / ".join(years_sorted)
    except Exception:
        pass  # corrupt JSON / missing keys / etc. → no dates; tree still renders.

    return work_dates, edu_dates, work_starts, work_ends


def show_profile(profile_dir: Optional[Path] = None, full: bool = False) -> None:
    """Render the profile outline as a rich Tree, grouped by resume sections.

    Args:
        profile_dir: Optional override; defaults to ~/.linkright/profile/.
        full:        When True, bullet text is rendered untruncated. Default
                     truncates at 120 chars with an ellipsis (avoids mid-word
                     terminal wrap on small windows).
    """
    profile_dir = profile_dir or _profile_dir()
    console = Console(theme=LR_THEME)
    meta = load_metadata(profile_dir)
    nuggets = load_nuggets(profile_dir)

    # UAT bug #7: header previously exposed internal metadata (full profile
    # path, embedder tier+model+dim, embed counts). Users don't need these to
    # read their profile. Default header now shows only meaningful counts +
    # creation date; pass --full to see internal metadata.
    if full:
        header_lines = [
            f"[bold]Profile dir:[/]  {profile_dir}",
            f"[bold]Created:[/]      {meta.get('created_at')}" if meta else "",
            f"[bold]Embedder:[/]     {meta.get('embedder_tier')} ({meta.get('embedder_model')}, dim={meta.get('dim')})" if meta else "",
            f"[bold]Nuggets:[/]      {meta.get('n_nuggets')} (embedded: {meta.get('n_embedded')}, highlights: {meta.get('n_highlights')})" if meta else "",
        ]
    else:
        n_nuggets = meta.get("n_nuggets") if meta else None
        n_highlights = meta.get("n_highlights") if meta else None
        created = meta.get("created_at") if meta else None
        header_lines = [
            f"[bold]Created:[/]      {created}" if created else "",
            f"[bold]Nuggets:[/]      {n_nuggets}" if n_nuggets is not None else "",
            f"[bold]Highlights:[/]   {n_highlights}" if n_highlights is not None else "",
        ]
    console.print(Panel("\n".join(l for l in header_lines if l), title="LinkRight Profile", expand=False))

    if not nuggets:
        console.print("[yellow]No nuggets in this profile.[/]")
        return

    work_dates, edu_dates, work_starts, work_ends = _load_date_lookups(profile_dir)

    # Group: type → company → role → [nuggets]. A second per-type bucket holds
    # nuggets without a company (common for skills, awards, projects).
    sections: dict[str, dict[str, dict[str, list[dict]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    section_untagged: dict[str, list[dict]] = defaultdict(list)

    # UAT #26 — render in priority order (P0 → P1 → P2 → P3 → unknown).
    # Stable sort means the LLM's extraction order is preserved within
    # each priority bucket, but newly-enriched P0 nuggets no longer
    # render below pre-existing P2s under the same company.
    from .nugget_utils import sort_by_priority
    nuggets_sorted = sort_by_priority(nuggets)

    for n in nuggets_sorted:
        n_type = (n.get("type") or "").strip().lower() or "other"
        company = _normalize(n.get("company"))
        role = _normalize(n.get("role"))
        if company:
            sections[n_type][company][role or "(role unspecified)"].append(n)
        else:
            section_untagged[n_type].append(n)

    # Priority-badge legend — quantified definitions (UAT bug #29).
    # Single source of truth lives in `priority_legend.py` so the legend
    # users see here matches the criteria the LLM uses to assign importance.
    from linkright.profile.priority_legend import format_legend_inline
    console.print(format_legend_inline())
    # UAT bug #8: 120-char default was too aggressive — bullets like
    # "Drove 20+ UX research sessions at American Express with compliance
    # analysts across 6 regions, designing 3 AML capability UIs end-to-end"
    # (191 chars) got cut mid-sentence, hiding the user's own data. Default
    # bumped to 240 (sentence-length); --full still disables truncation entirely.
    _TRUNCATE_LIMIT = 240
    has_long_bullet = any(
        len((n.get("nugget_text") or n.get("answer", "") or "").strip()) > _TRUNCATE_LIMIT
        for n in nuggets
    )
    if not full and has_long_bullet:
        console.print(f"[dim]Tip:  bullets >{_TRUNCATE_LIMIT} chars are truncated. Run `linkright profile show --full` for full text.[/]")

    def _truncate_title(s: str, limit: int = _TRUNCATE_LIMIT) -> str:
        s = s.strip()
        if full or len(s) <= limit:
            return s
        cut = s[:limit].rsplit(" ", 1)[0]
        return f"{cut}…"

    def _render_nugget_leaf(parent_node, n: dict) -> None:
        # Badge style comes from priority_legend (single source of truth).
        from linkright.profile.priority_legend import priority_badge
        imp = (n.get("importance") or "").upper()
        badge = priority_badge(imp)
        raw_title = _normalize(n.get("nugget_text")) or _normalize(n.get("answer", "")) or "(untitled)"
        parent_node.add(f"{badge} {_truncate_title(raw_title)}")

    tree = Tree("[bold cyan]Career outline[/]")
    rendered_section_types: set[str] = set()

    for n_type, label in SECTION_ORDER:
        companies = sections.get(n_type, {})
        loose = section_untagged.get(n_type, [])
        if not companies and not loose:
            continue
        rendered_section_types.add(n_type)

        section_node = tree.add(f"[bold cyan]{label}[/]")

        # Sort companies: work_experience puts CURRENT employer (any role
        # with end_date == "Present") at the top — universal resume convention,
        # so users see their primary current role first. Among inactive
        # companies, sort by latest start_date DESC. Within work, also
        # break ties on start_date DESC so a current AND-recently-started
        # role still beats a current-but-older-started role.
        # Education by year DESC; everything else alphabetical for stability.
        if n_type == "work_experience":
            def _co_key(item):
                co_lower = item[0].lower()
                roles_dict = item[1]
                # is_active = 1 if ANY role at this company is still ongoing
                # (its end_date string parses to (9999, 12) — i.e. literal
                # "Present" or empty). Active beats inactive; ties broken
                # by latest start_date.
                ends = [
                    work_ends.get((co_lower, r.lower()), "")
                    for r in roles_dict.keys()
                ]
                is_active = 1 if any(_date_sort_key(e) == (9999, 12) for e in ends) else 0
                starts = [
                    work_starts.get((co_lower, r.lower()), "")
                    for r in roles_dict.keys()
                ]
                latest_start = max((_date_sort_key(s) for s in starts), default=(0, 0))
                return (is_active, latest_start)
            sorted_companies = sorted(companies.items(), key=_co_key, reverse=True)
        elif n_type == "education":
            def _edu_key(item):
                return _date_sort_key(edu_dates.get(item[0].lower(), ""))
            sorted_companies = sorted(companies.items(), key=_edu_key, reverse=True)
        else:
            sorted_companies = sorted(companies.items(), key=lambda kv: kv[0].lower())

        for company, roles in sorted_companies:
            if not any(roles.values()):
                continue
            co_node = section_node.add(f"[bold]{company}[/]")
            for role, items in roles.items():
                # Date chip: work uses work_dates lookup; education uses edu_dates
                # (keyed by institution, since "role" for education = degree).
                date_str = ""
                if n_type == "work_experience":
                    date_str = work_dates.get((company.lower(), role.lower()), "")
                elif n_type == "education":
                    date_str = edu_dates.get(company.lower(), "")
                date_chip = f"  [dim]({date_str})[/]" if date_str else ""
                role_node = co_node.add(
                    f"[italic]{role}[/]{date_chip}  [dim]({len(items)} nugget{'s' if len(items)!=1 else ''})[/]"
                )
                for n in items:
                    _render_nugget_leaf(role_node, n)

        # Skills / Projects / Awards typically have no company. Render those
        # nuggets as a flat list under the section header (no fake company
        # node), so the tree reads naturally.
        if loose:
            if companies:
                loose_node = section_node.add(f"[dim italic](Other)[/]  [dim]({len(loose)} item{'s' if len(loose)!=1 else ''})[/]")
            else:
                loose_node = section_node
            for n in loose:
                _render_nugget_leaf(loose_node, n)

    # Catch-all for nugget types we don't recognize (so nothing is silently
    # dropped). Future types end up here until SECTION_ORDER is updated.
    other_types = (set(sections.keys()) | set(section_untagged.keys())) - rendered_section_types
    if other_types:
        other_section = tree.add(f"[bold cyan]Other[/]")
        for n_type in sorted(other_types):
            sub_label = n_type.replace("_", " ").title()
            sub_node = other_section.add(f"[italic]{sub_label}[/]")
            for company, roles in sorted(sections.get(n_type, {}).items(), key=lambda kv: kv[0].lower()):
                co_node = sub_node.add(f"[bold]{company}[/]")
                for role, items in roles.items():
                    role_node = co_node.add(f"[italic]{role}[/]  [dim]({len(items)} nugget{'s' if len(items)!=1 else ''})[/]")
                    for n in items:
                        _render_nugget_leaf(role_node, n)
            for n in section_untagged.get(n_type, []):
                _render_nugget_leaf(sub_node, n)
            rendered_section_types.add(n_type)

    console.print(tree)

    # Gentle footer: list resume sections that exist in the FlowCV taxonomy
    # but aren't yet populated in this profile, plus a one-line how-to-fill.
    # User-friendly awareness without cluttering the populated tree above.
    expected_types = [t for t, _ in SECTION_ORDER]
    missing_known = [SECTION_LABELS[t] for t in expected_types if t not in rendered_section_types]
    missing_future = [label for t, label in FUTURE_SECTION_LABELS if t not in rendered_section_types]
    missing_all = missing_known + missing_future
    if missing_all:
        # UAT #14: horizontal divider separates the tree (populated content)
        # from the "not yet populated" advisory block — same role-boundary
        # semantics as user-prompt → assistant-response in the chat surfaces.
        try:
            from linkright.ui import horizontal_divider
            horizontal_divider(console=console)
        except Exception:
            pass
        console.print(
            f"[dim italic]Not yet populated:[/] [dim]{', '.join(missing_all)}.[/]"
        )
        # UAT #22: secondary info follows the L-shaped muted-gray branch pattern.
        try:
            from linkright.ui import l_branch_tip
            l_branch_tip(
                "add these sections to your resume PDF + run "
                "`linkright profile rebuild -r resume.pdf` to refresh.",
                console=console,
            )
        except Exception:
            console.print(
                "[dim italic]Tip:[/] [dim]add these sections to your resume PDF + run "
                "`linkright profile rebuild -r resume.pdf` to refresh.[/]"
            )

    # UAT #16: sticky footer summarising the `profile show` surface — tier =
    # CLI version (gold), mode = "profile" (mint/teal), status = nugget count
    # (muted). Rendered once at the bottom so the user always sees orientation
    # info regardless of how long the tree is.
    try:
        from linkright.ui import sticky_footer
        from linkright import __version__ as _lr_ver
    except Exception:
        _lr_ver = ""
        sticky_footer = None  # type: ignore[assignment]
    if sticky_footer is not None:
        n_total = len(nuggets) if nuggets else 0
        console.print()
        sticky_footer(
            tier=f"v{_lr_ver}" if _lr_ver else None,
            mode="profile",
            status=f"{n_total} nugget{'s' if n_total != 1 else ''}",
            console=console,
        )
