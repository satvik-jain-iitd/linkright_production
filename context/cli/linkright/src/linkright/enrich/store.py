"""Pending-proposal + run-log persistence under ~/.linkright/enrichment/.

Layout:
  ~/.linkright/enrichment/
    pending_facts.jsonl           # current unresolved proposals (overwritten per run)
    enrichment_runs/<ts>/
      gaps.json                   # gap analysis snapshot
      queries.json                # generated queries
      retrieval_log.jsonl         # per-query retrieved atoms
      proposals.jsonl             # all LLM-proposed facts
      decisions.jsonl             # final accept/reject log
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


def _enrichment_dir() -> Path:
    home = os.environ.get("LINKRIGHT_HOME")
    base = Path(home) if home else Path.home() / ".linkright"
    return base / "enrichment"


def ensure_dirs() -> Path:
    p = _enrichment_dir()
    p.mkdir(parents=True, exist_ok=True)
    (p / "enrichment_runs").mkdir(exist_ok=True)
    return p


def new_run_dir() -> Path:
    p = ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = p / "enrichment_runs" / ts
    run.mkdir(parents=True, exist_ok=True)
    return run


# ── Pending facts ──────────────────────────────────────────────────────────

def write_pending_facts(proposals: Iterable[dict[str, Any]]) -> Path:
    """Atomic full rewrite of pending_facts.jsonl."""
    p = ensure_dirs() / "pending_facts.jsonl"
    tmp = p.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for prop in proposals:
            f.write(json.dumps(prop, ensure_ascii=False, default=str) + "\n")
    tmp.replace(p)
    return p


def load_pending_facts() -> list[dict[str, Any]]:
    p = _enrichment_dir() / "pending_facts.jsonl"
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def clear_pending_facts() -> None:
    p = _enrichment_dir() / "pending_facts.jsonl"
    p.unlink(missing_ok=True)


# ── Run log artifacts ──────────────────────────────────────────────────────

def write_run_artifact(
    run_dir: Path,
    name: str,
    payload: Any,
) -> Path:
    """Write JSON or JSONL artifact to a run directory.

    JSONL when `payload` is iterable of dicts AND name endswith .jsonl.
    JSON otherwise.
    """
    target = run_dir / name
    if name.endswith(".jsonl") and isinstance(payload, list):
        with target.open("w", encoding="utf-8") as f:
            for row in payload:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    else:
        target.write_text(
            json.dumps(payload, ensure_ascii=False, default=str, indent=2),
            encoding="utf-8",
        )
    return target
