"""Acronym expansion bank loader — S2.1.

Loads the pre-built acronym expansion bank from
``resume/data/acronyms.yaml`` and returns a flat
``dict[str, str]`` mapping acronym → expansion phrase.

Priority model (highest to lowest):
  1. Per-run learned expansions (from resume text / JD text)
  2. Persistent learned_corpus (cross-run learning)
  3. **This bank** — fills gaps for the ~350 common domain acronyms
     so LLM lookup is never needed for them.

Handles missing file / bad YAML gracefully: returns empty dict so that
a corrupted or missing install never crashes step_14.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_DATA_FILE = Path(__file__).parent.parent / "data" / "acronyms.yaml"
_CACHE: dict[str, str] | None = None


def load_acronym_bank(*, _force_reload: bool = False) -> dict[str, str]:
    """Return a flat ``{acronym: expansion}`` dict from the bundled YAML bank.

    The result is module-level cached after the first load; subsequent calls
    within the same process are O(1) dict lookups.

    Args:
        _force_reload: Internal / test hook — bypass module cache.

    Returns:
        Mapping of acronym strings to their full expansion phrases.
        Empty dict if the bank file is missing or unparseable.
    """
    global _CACHE
    if _CACHE is not None and not _force_reload:
        return _CACHE

    result: dict[str, str] = {}
    try:
        # PyYAML is already a transitive dep (Kubernetes / Helm configs, etc.)
        # but we guard the import so a missing install falls back gracefully.
        import yaml  # type: ignore[import]

        raw: Any = yaml.safe_load(_DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for acronym, meta in raw.items():
                if isinstance(meta, dict):
                    expansion = meta.get("expansion")
                    if expansion and isinstance(expansion, str):
                        result[str(acronym)] = expansion
    except FileNotFoundError:
        # Bank file absent — bad install or editable dev install without data/.
        pass
    except Exception:
        # YAML parse error, encoding issue, etc. — never crash the pipeline.
        pass

    _CACHE = result
    return result


def bank_size() -> int:
    """Return the number of entries currently in the cached bank (for telemetry)."""
    return len(load_acronym_bank())


def _merge_bank_into_expansions(
    bank: dict[str, str],
    learned: dict[str, str],
    no_expand_upper: frozenset[str],
) -> dict[str, str]:
    """Merge bank entries into *learned* dict, applying the same guard as
    orchestrator.py step_14 (lines 4664-4680).

    Rules (mirroring the inline wire-in block exactly):
    - Skip entry if its key is already in *learned* (per-run learned has priority).
    - Skip entry if ``key.upper()`` is in *no_expand_upper* (silently suppressed
      at step_14 to prevent expanding universally-known tokens like API/ML/LLM).
    - Otherwise add to *learned* in place.

    Args:
        bank:            Output of :func:`load_acronym_bank`.
        learned:         The ``_LEARNED_EXPANSIONS`` dict accumulating all known
                         expansions for this step_14 run.  Mutated in place.
        no_expand_upper: The ``_UNIVERSAL_NO_EXPAND_UPPER`` frozenset.

    Returns:
        The same *learned* dict (mutated in place) for convenience.

    Extracted for testability (S2.1 Blocker 3 — AC4 coverage).
    """
    for key, expansion in bank.items():
        if key not in learned and key.upper() not in no_expand_upper:
            learned[key] = expansion
    return learned
