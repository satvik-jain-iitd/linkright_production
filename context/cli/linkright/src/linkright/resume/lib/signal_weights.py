"""signal_weights.py — S3.1: 13-signal × 5-career-level multiplier matrix.

Pre-stores a 65-cell weight matrix so step_11 bullet ranking scores the same
set of nuggets differently depending on the candidate's career level.

Public API:
    load_signal_weights() -> dict[str, dict[str, float]]
        Returns {signal: {career_level: multiplier}} — module-cached.

    apply_signal_weights(
        bullets: list[dict],
        career_level: str,
        weight_matrix: dict[str, dict[str, float]],
    ) -> list[dict]
        Applies in-place _brs multiplication by the per-signal, per-level
        weight. Returns the same list (mutated) for chaining.

        Each bullet dict must have:
          "_brs"  — float base BRS score (already computed by step_11)
          "signal" — str signal name (one of the 13 _VALID_SIGNALS)

        After this call each bullet has "_weighted_brs" added.

S3.1 — 2026-05-11
"""

from __future__ import annotations

from pathlib import Path

import yaml

# ── Module-level cache ─────────────────────────────────────────────────────────

_WEIGHTS_CACHE: dict[str, dict[str, float]] | None = None

_YAML_PATH = Path(__file__).parent.parent / "data" / "signal_weights.yaml"

# Default multiplier when signal or career_level is absent from the matrix.
_DEFAULT_MULTIPLIER: float = 1.0

# Valid career levels (mirrors _CAREER_LEVEL_MIN_YEARS in orchestrator.py)
_VALID_CAREER_LEVELS = frozenset(
    {"fresher", "early_career", "mid", "senior", "executive"}
)
# "entry" is aliased below so _VALID_CAREER_LEVELS stays a pure YAML-key enum


# ── Public API ─────────────────────────────────────────────────────────────────

def load_signal_weights() -> dict[str, dict[str, float]]:
    """Load the signal weights YAML, module-cached.

    Returns:
        {signal_name: {career_level: multiplier_float}}

    All 65 cells guaranteed to be floats in [0.5, 2.5].
    """
    global _WEIGHTS_CACHE
    if _WEIGHTS_CACHE is not None:
        return _WEIGHTS_CACHE
    raw = yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(
            f"signal_weights.yaml must be a mapping at top level, got {type(raw)}"
        )
    # Validate all cells are numeric and in range
    for signal, level_map in raw.items():
        if not isinstance(level_map, dict):
            raise ValueError(
                f"signal_weights.yaml: signal '{signal}' must map to a dict of "
                f"career_level → multiplier, got {type(level_map)}"
            )
        for level, val in level_map.items():
            val_f = float(val)
            if not (0.5 <= val_f <= 2.5):
                raise ValueError(
                    f"signal_weights.yaml: [{signal}][{level}] = {val_f} is outside "
                    f"[0.5, 2.5] range"
                )
            level_map[level] = val_f
        raw[signal] = level_map
    _WEIGHTS_CACHE = raw
    return _WEIGHTS_CACHE


def apply_signal_weights(
    bullets: list[dict],
    career_level: str,
    weight_matrix: dict[str, dict[str, float]],
) -> list[dict]:
    """Apply signal × career-level multipliers to pre-computed _brs scores.

    Mutates each bullet dict in-place by adding "_weighted_brs".
    Sorting by "_weighted_brs" DESC in step_11 surfaces the most relevant
    bullets for the given career level.

    Args:
        bullets:       List of paragraph dicts from step_10; each must have
                       "_brs" (float) and "signal" (str).
        career_level:  One of {fresher, early_career, mid, senior, executive}.
                       Falls back to "mid" if unrecognised.
        weight_matrix: Output of load_signal_weights().

    Returns:
        The same list (mutated) — caller should sort by "_weighted_brs" DESC.
    """
    cl = (career_level or "").strip().lower()
    if cl == "entry":
        cl = "early_career"
    if cl not in _VALID_CAREER_LEVELS:
        cl = "mid"

    for bullet in bullets:
        base = float(bullet.get("_brs") or 0.0)
        signal = (bullet.get("signal") or "").strip().lower()
        # Look up multiplier; fall back to 1.0 if signal or level not in matrix
        level_map = weight_matrix.get(signal, {})
        multiplier = level_map.get(cl, _DEFAULT_MULTIPLIER)
        bullet["_weighted_brs"] = round(base * multiplier, 4)

    return bullets
