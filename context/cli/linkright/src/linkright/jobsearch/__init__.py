"""LinkRight Pillar 2 — Job Search.

Public surface:
  evaluator.evaluate_jd(jd_text, profile, *, persist=True) -> dict
  scorecard.JobSearchScorecard — 10-dim A-F scorecard
  cli.jobsearch_group — Click group, wired into linkright.cli
"""
from __future__ import annotations

from . import evaluator, scorecard  # noqa: F401
from .cli import jobsearch_group  # noqa: F401

__all__ = ["evaluator", "scorecard", "jobsearch_group"]
