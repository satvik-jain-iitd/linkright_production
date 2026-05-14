"""Diary subcommand — daily journaling that compounds into Evidence Layer.

Diary entries are first-class evidence with ``tier=diary``. Every entry the
user writes today becomes RAG-able context for tomorrow's `linkright profile
enrich`, the interview coach, and resume tailoring.

Two write paths:
  - `linkright diary add` — opens $EDITOR with a pre-filled memo template
  - `linkright diary add --auto <raw>` — Groq formats raw thoughts → memo

Read paths:
  - `linkright diary today / week / month` — recent atoms by date filter

See plan: ~/.claude/plans/okay-what-i-want-elegant-cook.md (Part B.4)
"""
from __future__ import annotations

from .templates import build_diary_template

__all__ = ["build_diary_template"]
