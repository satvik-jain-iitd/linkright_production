"""domain_verbs.py — S2.2: Industry-domain strong-verb prefix maps.

Provides deterministic weak-verb replacement for step_10 bullets.
No LLM retry loop — pure lookup from a pre-stored YAML file.

Public API:
    load_domain_verbs()           → dict[str, list[str]]
    get_strong_verb(industry, used_verbs) → str | None
    replace_weak_verb(text, industry, used_verbs) → tuple[str, str | None]

The substitution helper ``replace_weak_verb`` is extracted here (not inline in
orchestrator) so it is unit-testable — lesson from S2.1 round 2.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

# ── Constants ──────────────────────────────────────────────────────────────────

_WEAK_VERBS: frozenset[str] = frozenset({
    "worked",
    "helped",
    "assisted",
    "supported",
    "participated",
    "contributed",
    "involved",
    "utilized",
    "leveraged",
})

_DEFAULT_INDUSTRY = "tech"

# ── Module-level cache ─────────────────────────────────────────────────────────

_VERB_CACHE: dict[str, list[str]] | None = None

_YAML_PATH = Path(__file__).parent.parent / "data" / "domain_verbs.yaml"


def load_domain_verbs() -> dict[str, list[str]]:
    """Load the domain-verb YAML, module-cached.

    Returns a dict mapping industry slug → list[str] of strong past-tense verbs.
    Raises FileNotFoundError if the YAML is missing (never silently returns empty).
    """
    global _VERB_CACHE
    if _VERB_CACHE is None:
        with open(_YAML_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"domain_verbs.yaml must be a YAML mapping, got {type(data)}")
        _VERB_CACHE = {k: list(v) for k, v in data.items()}
    return _VERB_CACHE


# Ordered priority list: (keyword, industry) — first match wins.
# Ordered so more specific domain terms (longer / more distinctive) appear
# earlier than generic ones that could collide (e.g. "analyst" alone maps to
# data, but "finance analyst" should resolve to finance because "finance" is
# listed before "analyst" here).
_CAREER_LEVEL_PRIORITY: list[tuple[str, str]] = [
    # Finance domain — check before generic "analyst"
    ("finance",     "finance"),
    ("financial",   "finance"),
    ("accounting",  "finance"),
    ("cfo",         "finance"),
    # Legal domain
    ("attorney",    "legal"),
    ("counsel",     "legal"),
    ("litigation",  "legal"),
    ("legal",       "legal"),
    # Data domain
    ("scientist",   "data"),
    ("ml ",         "data"),
    ("machine learn", "data"),
    ("data engin",  "data"),
    ("data ",       "data"),
    # Sales domain
    ("account exec","sales"),
    ("account mana","sales"),
    ("sales",       "sales"),
    # Marketing domain
    ("marketing",   "marketing"),
    ("growth",      "marketing"),
    # Operations domain
    ("logistics",   "operations"),
    ("supply chain","operations"),
    ("operations",  "operations"),
    ("oper",        "operations"),
    # Tech domain
    ("engineer",    "tech"),
    ("developer",   "tech"),
    ("sde",         "tech"),
    ("software",    "tech"),
    ("eng ",        "tech"),
    ("dev ",        "tech"),
    # PM domain
    ("director",    "pm"),
    ("vp ",         "pm"),
    ("product mana","pm"),
    ("senior pm",   "pm"),
    (" pm",         "pm"),
    ("product",     "pm"),
    # Fallback for generic "analyst" → data
    ("analyst",     "data"),
    # Generic exec → pm
    ("exec",        "pm"),
]


def infer_industry(career_level: str) -> str:
    """Infer the best industry slug from a career_level string.

    Uses an ordered priority list so more specific terms take precedence over
    generic ones (e.g. "finance analyst" → finance, not data). Falls back to
    ``_DEFAULT_INDUSTRY`` when no keyword matches.
    """
    if not career_level:
        return _DEFAULT_INDUSTRY
    cl_lower = career_level.lower()
    for keyword, industry in _CAREER_LEVEL_PRIORITY:
        if keyword in cl_lower:
            return industry
    return _DEFAULT_INDUSTRY


def get_strong_verb(industry: str, used_verbs: set[str]) -> Optional[str]:
    """Return the first unused strong verb for *industry*.

    Parameters
    ----------
    industry:   Industry slug (e.g. "tech", "pm"). Unknown slugs fall back to
                "tech".  Case-insensitive.
    used_verbs: Set of verb strings already used in this resume (case-insensitive
                comparison against entries in the YAML).

    Returns the first verb from the industry list that is not in ``used_verbs``,
    or ``None`` if every verb is exhausted.
    """
    verbs = load_domain_verbs()
    key = industry.lower() if industry else _DEFAULT_INDUSTRY
    if key not in verbs:
        key = _DEFAULT_INDUSTRY
    used_lower = {v.lower() for v in used_verbs}
    for verb in verbs[key]:
        if verb.lower() not in used_lower:
            return verb
    return None


def _opening_verb(text: str) -> Optional[str]:
    """Extract the first word of *text* if it is a weak verb (case-insensitive).

    Returns the matched weak verb string, or None.
    """
    if not text:
        return None
    # Strip leading HTML tags (e.g. <b>, <strong>)
    stripped = re.sub(r"^(<[^>]+>)+", "", text).strip()
    first_word = re.split(r"[\s,;]", stripped)[0].rstrip(".,;:!?").lower()
    return first_word if first_word in _WEAK_VERBS else None


def replace_weak_verb(
    text: str,
    industry: str,
    used_verbs: set[str],
) -> tuple[str, Optional[str]]:
    """Replace a leading weak verb in *text* with a strong domain verb.

    Parameters
    ----------
    text:       Raw bullet text (may contain leading HTML tags like ``<b>``).
    industry:   Industry slug for verb lookup.
    used_verbs: Mutable set of verbs already consumed — updated in-place on success.

    Returns
    -------
    (new_text, new_verb) where ``new_verb`` is the replacement verb used (or
    ``None`` if no replacement was made — either no weak verb found, or all
    strong verbs exhausted).
    """
    weak = _opening_verb(text)
    if weak is None:
        return text, None

    strong = get_strong_verb(industry, used_verbs)
    if strong is None:
        # All verbs exhausted — graceful degradation
        return text, None

    # Replace the weak verb at the start of text (case-insensitive, preserve HTML lead)
    # Pattern: optional leading HTML tags, then the weak verb word
    pattern = re.compile(
        r"^((?:<[^>]+>)*\s*)(" + re.escape(weak) + r")\b",
        re.IGNORECASE,
    )
    new_text, n_subs = pattern.subn(r"\g<1>" + strong, text, count=1)
    if n_subs == 0:
        # Fallback: simple word replacement at start (no HTML prefix)
        new_text = re.sub(
            r"(?i)^" + re.escape(weak) + r"\b",
            strong,
            text,
            count=1,
        )

    used_verbs.add(strong)
    return new_text, strong
