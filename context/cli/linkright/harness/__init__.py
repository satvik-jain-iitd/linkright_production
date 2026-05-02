"""LinkRight quality harness — scorecard + RCA loop + cross-pillar aggregation.

Per plan §12 (CRITICAL): every run emits a scorecard; every iteration appends
to CONTINUOUS_RCA_LOG.md; regression checks run on every PR. Non-negotiable.
"""
from .scorecard import Dimension, Scorecard, grade_from_score

__all__ = ["Dimension", "Scorecard", "grade_from_score"]
