"""Nugget audit / cleanup phase — UAT bug #32.

Standalone re-analysis loop the user runs after multiple `profile enrich`
sessions accumulate noise. It:

  1. Re-classifies any nugget missing `nugget_class` (#25 backfill for
     legacy profiles created before that field existed).
  2. Re-resolves "unknown" / "none" company + role using parsed-resume
     headers (#27).
  3. Detects fluff-metric nuggets and demotes them to P3 with an
     `_audit_flags: ["fluff_metric"]` tag (#31).
  4. Re-sorts the on-disk jsonl + highlights files by priority (#26).

Idempotent: re-running on a clean profile is a no-op. NEVER deletes a
nugget — only mutates fields. User retains control via `profile
delete-nugget` and the truth-engine edit loop.

Why a separate file vs. inlining in pipeline.py: the audit phase is
user-invoked from a dedicated CLI subcommand, has its own evaluation
output, and reads BOTH nuggets.jsonl AND artifacts/01_resume_parsed.json
+ artifacts/00_resume_raw_text.txt — a noticeably wider read surface
than the create-pipeline's persist() helper. Keeping it in its own
module makes the dependency surface explicit and the testing scope
narrow.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .pipeline import (
    _profile_dir,
    _update_metadata,
    load_nuggets,
)
from .nugget_utils import audit_nuggets, sort_by_priority


def _read_parsed(profile_dir: Path) -> dict:
    """Best-effort load of `artifacts/01_resume_parsed.json` for entity hints.
    Returns empty dict on any error — audit must work on minimal data."""
    p = profile_dir / "artifacts" / "01_resume_parsed.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("parsed", {}) or {}
    except Exception:
        return {}


def _read_raw_text(profile_dir: Path) -> str:
    """Best-effort load of `artifacts/00_resume_raw_text.txt`. Returns empty
    string when absent (audit then skips raw-text-pattern entity resolution
    but still runs the other audit passes)."""
    p = profile_dir / "artifacts" / "00_resume_raw_text.txt"
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def run_audit(profile_dir: Optional[Path] = None) -> dict:
    """Run the audit pass over the given profile. Writes back to
    nuggets.jsonl + highlights.jsonl + metadata.yaml.

    Returns the counts dict from `audit_nuggets` plus a `wrote_files`
    bool flag indicating whether anything was rewritten (false when
    audit found zero changes — a clean re-run).
    """
    profile_dir = profile_dir or _profile_dir()
    nuggets = load_nuggets(profile_dir)
    if not nuggets:
        return {
            "classified": 0,
            "entity_resolved": 0,
            "fluff_demoted": 0,
            "reprioritised": 0,
            "total": 0,
            "wrote_files": False,
        }

    parsed = _read_parsed(profile_dir)
    raw_text = _read_raw_text(profile_dir)
    counts = audit_nuggets(nuggets, parsed=parsed, raw_text=raw_text)

    # Decide whether to rewrite. If nothing changed, skip disk I/O.
    any_change = any(
        counts.get(k, 0) > 0
        for k in ("classified", "entity_resolved", "fluff_demoted", "reprioritised")
    )
    if not any_change:
        counts["wrote_files"] = False
        return counts

    # Re-sort and rewrite nuggets.jsonl.
    # LOW fix (cycle-2): mirror persist()'s transient-key strip so
    # `_entity_resolved_by` (in-memory audit-trail flag from #27) is
    # never persisted. The flag re-appears on the next audit run if
    # the resolver still fires.
    _TRANSIENT_KEYS = {"_entity_resolved_by"}

    def _strip(n: dict) -> dict:
        return {k: v for k, v in n.items() if k not in _TRANSIENT_KEYS}

    sorted_nuggets = sort_by_priority(nuggets)
    with open(profile_dir / "nuggets.jsonl", "w", encoding="utf-8") as f:
        for n in sorted_nuggets:
            f.write(json.dumps(_strip(n), ensure_ascii=False) + "\n")

    # Rewrite highlights.jsonl: subset = P0/P1 from the sorted set, in priority order.
    # Demoted-to-P3 fluff nuggets correctly drop out of highlights here.
    highlights_path = profile_dir / "highlights.jsonl"
    highlights = [
        n for n in sorted_nuggets
        if str(n.get("importance", "")).upper() in ("P0", "P1")
    ]
    with open(highlights_path, "w", encoding="utf-8") as f:
        for n in highlights:
            f.write(json.dumps(_strip(n), ensure_ascii=False) + "\n")

    _update_metadata(profile_dir, {"n_highlights": len(highlights)})

    counts["wrote_files"] = True
    return counts
