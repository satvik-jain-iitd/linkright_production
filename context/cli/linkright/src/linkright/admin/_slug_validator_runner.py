"""Fallback slug validator — used when worker package is not on path."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationReport:
    validated: int = 0
    healed: int = 0
    marked_zero: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


async def validate_and_heal_slugs(batch_size: int = 100) -> ValidationReport:
    """Attempt to import from worker, raise informative error if not available."""
    import sys
    from pathlib import Path
    this_file = Path(__file__).resolve()
    for depth in (7, 8, 9):
        candidate = this_file.parents[depth] / "worker"
        if candidate.exists():
            sys.path.insert(0, str(candidate))
            try:
                from app.oracle.slug_validator import validate_and_heal_slugs as _real
                return await _real(batch_size=batch_size)
            except ImportError:
                sys.path.pop(0)
    raise RuntimeError(
        "Could not import slug_validator from worker. "
        "Ensure you're running from the repo root or that worker/ is on PYTHONPATH."
    )
