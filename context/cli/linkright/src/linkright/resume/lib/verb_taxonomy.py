"""verb_taxonomy.py — S2.3: 2D impact-category × industry verb matrix.

Provides deterministic taxonomy-based verb selection for step_10 bullets.
Selection uses two axes:
  1. Impact category — classified from bullet text (9 categories from FlowCV)
  2. Industry domain — inferred from candidate's job title (same 8 as S2.2)

Public API:
    load_verb_taxonomy() -> dict[str, dict[str, list[str]]]
    classify_impact_category(bullet_text: str) -> str
    get_taxonomy_verb(category: str, industry: str, used_verbs: set[str]) -> str | None
    replace_with_taxonomy_verb(text: str, industry: str, used_verbs: set[str]) -> tuple[str, str | None]

S2.3 — 2026-05-11
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

# ── Constants ──────────────────────────────────────────────────────────────────

_CATEGORIES = (
    "Achievement",
    "Communication",
    "Initiative",
    "Research",
    "OrgPlanning",
    "Leadership",
    "Managing",
    "ProblemSolving",
    "Interpersonal",
)

_DEFAULT_CATEGORY = "Achievement"
_DEFAULT_INDUSTRY = "tech"

# ── Priority-ordered keyword classifier ──────────────────────────────────────
# Each tuple: (keyword_set_as_frozenset_or_str, category)
# Earlier entries take priority. Match on first found keyword.
# All keywords lowercased for comparison.

_CATEGORY_RULES: list[tuple[tuple[str, ...], str]] = [
    # Leadership: led/managed team / oversaw / directed / mentored
    (("led", "managed team", "oversaw", "directed", "mentored", "coached", "built team"), "Leadership"),
    # Managing: managed / coordinated / supervised / ran / owned end-to-end
    (("managed", "coordinated", "supervised", "ran", "owned end-to-end"), "Managing"),
    # Initiative: initiated / proposed / pioneered / introduced
    (("initiated", "proposed", "pioneered", "introduced", "started", "founded", "established"), "Initiative"),
    # Communication: presented / wrote / published / authored
    (("presented", "wrote", "published", "authored", "communicated", "evangelized", "documented"), "Communication"),
    # Research: analyzed / researched / investigated / studied
    (("analyzed", "researched", "investigated", "studied", "evaluated", "assessed", "benchmarked"), "Research"),
    # OrgPlanning: planned / roadmapped / prioritized / organized
    (("planned", "roadmapped", "prioritized", "organized", "structured", "scoped", "scheduled"), "OrgPlanning"),
    # ProblemSolving: fixed / resolved / debugged / diagnosed
    (("fixed", "resolved", "debugged", "diagnosed", "improved", "optimized", "reduced"), "ProblemSolving"),
    # Interpersonal: collaborated / partnered / worked with / aligned
    (("collaborated", "partnered", "worked with", "aligned", "supported"), "Interpersonal"),
    # Achievement: shipped / delivered / launched / built / created
    (("shipped", "delivered", "launched", "built", "created", "implemented", "released", "completed", "hit", "exceeded"), "Achievement"),
]


# ── Module-level cache ─────────────────────────────────────────────────────────

_TAXONOMY_CACHE: dict[str, dict[str, list[str]]] | None = None

_YAML_PATH = Path(__file__).parent.parent / "data" / "verb_taxonomy.yaml"


# ── Public API ─────────────────────────────────────────────────────────────────

def load_verb_taxonomy() -> dict[str, dict[str, list[str]]]:
    """Load the verb taxonomy YAML, module-cached.

    Returns a nested dict: category → industry → list[str] of past-tense verbs.
    Raises FileNotFoundError if the YAML is missing (never silently returns empty).
    """
    global _TAXONOMY_CACHE
    if _TAXONOMY_CACHE is None:
        with open(_YAML_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"verb_taxonomy.yaml must be a YAML mapping, got {type(data)}")
        _TAXONOMY_CACHE = {
            cat: {ind: list(verbs) for ind, verbs in ind_map.items()}
            for cat, ind_map in data.items()
        }
    return _TAXONOMY_CACHE


def classify_impact_category(bullet_text: str) -> str:
    """Classify a bullet's impact category from its text.

    Uses a priority-ordered keyword match — first match wins.
    Returns one of the 9 category strings or ``"Achievement"`` as default.

    Parameters
    ----------
    bullet_text: Raw bullet text (HTML tags stripped before matching).
    """
    if not bullet_text:
        return _DEFAULT_CATEGORY

    # Strip leading HTML tags for keyword matching
    clean = re.sub(r"<[^>]+>", " ", bullet_text).lower()

    for keywords, category in _CATEGORY_RULES:
        for kw in keywords:
            if kw in clean:
                return category

    return _DEFAULT_CATEGORY


def get_taxonomy_verb(
    category: str,
    industry: str,
    used_verbs: set[str],
) -> Optional[str]:
    """Return the first unused taxonomy verb for (category, industry).

    Parameters
    ----------
    category:   Impact category (e.g. "Achievement"). Unknown categories return
                None (caller should fall back to S2.2).
    industry:   Industry slug (e.g. "tech"). Unknown slugs fall back to "tech".
    used_verbs: Set of verb strings already used in this resume (case-insensitive
                comparison). NOT mutated here — caller manages the set.

    Returns the first verb from taxonomy[category][industry] not in used_verbs.
    Falls back to "tech" if primary industry list is exhausted.
    Returns None if fully exhausted (caller should fall back to S2.2).
    """
    taxonomy = load_verb_taxonomy()

    cat_map = taxonomy.get(category)
    if cat_map is None:
        return None

    used_lower = {v.lower() for v in used_verbs}

    def _first_unused(verb_list: list[str]) -> Optional[str]:
        for verb in verb_list:
            if verb.lower() not in used_lower:
                return verb
        return None

    # Try primary industry
    ind_key = industry.lower() if industry else _DEFAULT_INDUSTRY
    primary_list = cat_map.get(ind_key, [])
    result = _first_unused(primary_list)
    if result is not None:
        return result

    # Fallback to "tech" if primary exhausted or unknown
    if ind_key != _DEFAULT_INDUSTRY:
        fallback_list = cat_map.get(_DEFAULT_INDUSTRY, [])
        result = _first_unused(fallback_list)
        if result is not None:
            return result

    return None


def replace_with_taxonomy_verb(
    text: str,
    industry: str,
    used_verbs: set[str],
) -> tuple[str, Optional[str]]:
    """Classify bullet's impact category and replace its opening verb.

    This is the S2.3 main entry point for orchestrator.step_10.

    Flow:
      1. Classify impact category from bullet text.
      2. Call get_taxonomy_verb(category, industry, used_verbs).
      3. If taxonomy verb found AND it differs from current opening verb → replace.
      4. Update used_verbs in-place with the new verb.
      5. If taxonomy returns None → return (text, None) so caller can fall back to S2.2.

    Parameters
    ----------
    text:       Raw bullet text (may contain leading HTML tags like ``<b>``).
    industry:   Industry slug for verb lookup.
    used_verbs: Mutable set of verbs already consumed — updated in-place on success.

    Returns
    -------
    (new_text, new_verb) where ``new_verb`` is the verb used (or ``None`` if
    no taxonomy replacement was made).
    """
    if not text:
        return text, None

    category = classify_impact_category(text)
    taxonomy_verb = get_taxonomy_verb(category, industry, used_verbs)

    if taxonomy_verb is None:
        return text, None

    # Extract current opening verb (strip leading HTML)
    clean_start = re.sub(r"^(<[^>]+>)+", "", text).strip()
    current_verb = re.split(r"[\s,;]", clean_start)[0].rstrip(".,;:!?")

    # If taxonomy verb is the same as current opening verb (case-insensitive):
    # mark the verb as used so subsequent bullets don't duplicate it, but return
    # None to signal "no text replacement needed" (bullet already has the right verb).
    if current_verb.lower() == taxonomy_verb.lower():
        used_verbs.add(taxonomy_verb)
        return text, None

    # Replace the opening verb (preserve any leading HTML tags)
    pattern = re.compile(
        r"^((?:<[^>]+>)*\s*)(" + re.escape(current_verb) + r")\b",
        re.IGNORECASE,
    )
    new_text, n_subs = pattern.subn(r"\g<1>" + taxonomy_verb, text, count=1)
    if n_subs == 0:
        # Fallback: simple replacement at start (no HTML prefix)
        new_text = re.sub(
            r"(?i)^" + re.escape(current_verb) + r"\b",
            taxonomy_verb,
            text,
            count=1,
        )
        if new_text == text:
            # Could not replace — return unchanged
            return text, None

    used_verbs.add(taxonomy_verb)
    return new_text, taxonomy_verb
