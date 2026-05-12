"""Persistent self-improving corpus — acronym expansions learned across pipeline runs.

Sourced from:
1. Inline pairs auto-learned in step_14 (when user's resume has "Anti-Money Laundering (AML)")
2. Oracle gemma3:1b enrichment script (offline, manual or weekly cron)
3. (future) Pipeline-detected vocabulary candidates

Schema (JSON file at LINKRIGHT_CORPUS_PATH or default ~/.linkright/learned_corpus.json):
{
  "acronyms": {"AML": "Anti-Money Laundering", "K8s": "Kubernetes", ...},
  "vocab_candidates": ["spearheaded", "uncovered", ...],
  "last_enriched_at": "2026-04-26T10:00:00Z",
  "schema_version": 1
}

Used by:
- orchestrator.step_14 — load at start, contribute new pairs, save at end
- scripts/enrich_synonym_bank.py — read vocab_candidates, write enriched dict

Atomic: file is rewritten via tmp + rename. Concurrent-safe under typical use.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1


def _corpus_path() -> Path:
    custom = os.environ.get("LINKRIGHT_CORPUS_PATH")
    if custom:
        return Path(custom)
    home = Path.home() / ".linkright"
    home.mkdir(parents=True, exist_ok=True)
    return home / "learned_corpus.json"


def load_corpus() -> dict[str, Any]:
    """Load the persistent corpus. Returns empty shape if file missing/invalid."""
    p = _corpus_path()
    if not p.exists():
        return {"acronyms": {}, "vocab_candidates": [], "last_enriched_at": None, "schema_version": SCHEMA_VERSION}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("corpus root must be dict")
        data.setdefault("acronyms", {})
        data.setdefault("vocab_candidates", [])
        data.setdefault("schema_version", SCHEMA_VERSION)
        return data
    except Exception:
        # Corrupt corpus — start fresh (don't crash pipeline)
        return {"acronyms": {}, "vocab_candidates": [], "last_enriched_at": None, "schema_version": SCHEMA_VERSION}


def save_corpus(corpus: dict[str, Any]) -> None:
    """Atomic write: tmp file + rename."""
    p = _corpus_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(corpus, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, p)
    except Exception:
        # Best-effort cleanup
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def merge_acronyms(corpus: dict[str, Any], new_pairs: dict[str, str]) -> int:
    """Merge new acronym pairs into corpus. Returns count of NEW additions.

    Conflict policy: existing entries win (don't overwrite — first source of truth wins).
    """
    if not isinstance(corpus.get("acronyms"), dict):
        corpus["acronyms"] = {}
    added = 0
    for ac, expansion in (new_pairs or {}).items():
        if not ac or not expansion:
            continue
        if ac not in corpus["acronyms"]:
            corpus["acronyms"][ac] = expansion
            added += 1
    return added


def add_vocab_candidates(corpus: dict[str, Any], words: set | list) -> int:
    """Add unique vocabulary words to candidate list. Returns count of NEW additions."""
    if not isinstance(corpus.get("vocab_candidates"), list):
        corpus["vocab_candidates"] = []
    existing = set(corpus["vocab_candidates"])
    added = 0
    for w in (words or []):
        w_norm = (w or "").strip().lower()
        if w_norm and len(w_norm) > 3 and w_norm not in existing:
            corpus["vocab_candidates"].append(w_norm)
            existing.add(w_norm)
            added += 1
    return added


def stamp_enriched(corpus: dict[str, Any]) -> None:
    """Update the last_enriched_at timestamp (called by enrichment script)."""
    corpus["last_enriched_at"] = datetime.now(timezone.utc).isoformat()
