"""v2 storage — Fact, Signal, CareerProfile JSON/JSONL/npz I/O.

Layout:
  ~/.linkright/profile/
    canonical_profile.json     # CareerProfile root (single source of truth)
    facts.jsonl                # Fact entities, one per line
    facts_embeddings.npz       # ids + vectors (fact-level)
    signals.jsonl              # Signal entities
    signals_embeddings.npz     # ids + vectors (signal-level)
    profile_history/           # versioned snapshots (v001.json, v002.json…)
    metadata.yaml              # schema_version, embedder, identity_version

Embeddings dim follows the same tier as evidence/embeddings.npz (sticky
fastembed 384 by default). Cosine over facts gives RAG attribution at the
fact granularity; cosine over signals gives signal-first retrieval.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import yaml

from .v2_schemas import CareerProfile, Fact, Signal


def _profile_dir() -> Path:
    home = os.environ.get("LINKRIGHT_HOME")
    base = Path(home) if home else Path.home() / ".linkright"
    return base / "profile"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ════════════════════════════════════════════════════════════════════════════
# Profile dir + metadata
# ════════════════════════════════════════════════════════════════════════════

def ensure_profile_dirs(profile_dir: Optional[Path] = None) -> Path:
    p = profile_dir or _profile_dir()
    p.mkdir(parents=True, exist_ok=True)
    (p / "profile_history").mkdir(exist_ok=True)
    return p


def write_metadata(profile_dir: Path, **kwargs) -> None:
    """Merge new metadata fields into metadata.yaml without losing existing keys."""
    path = profile_dir / "metadata.yaml"
    existing = {}
    if path.exists():
        try:
            existing = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError:
            existing = {}
    existing.update(kwargs)
    path.write_text(yaml.safe_dump(existing, sort_keys=False))


def read_metadata(profile_dir: Path) -> dict:
    path = profile_dir / "metadata.yaml"
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError:
        return {}


# ════════════════════════════════════════════════════════════════════════════
# CareerProfile (canonical_profile.json)
# ════════════════════════════════════════════════════════════════════════════

def load_canonical_profile(profile_dir: Optional[Path] = None) -> Optional[CareerProfile]:
    p = (profile_dir or _profile_dir()) / "canonical_profile.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return CareerProfile.from_dict(d)
    except (json.JSONDecodeError, KeyError):
        return None


def save_canonical_profile(
    profile: CareerProfile,
    profile_dir: Optional[Path] = None,
    *,
    snapshot: bool = True,
) -> Path:
    """Atomic write canonical_profile.json. Optionally snapshot to history."""
    p = ensure_profile_dirs(profile_dir)
    profile.updated_at = _now_iso()
    target = p / "canonical_profile.json"
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(profile.to_json(), encoding="utf-8")
    tmp.replace(target)

    if snapshot:
        snap_dir = p / "profile_history"
        snap_dir.mkdir(exist_ok=True)
        n = sum(1 for _ in snap_dir.glob("v*.json")) + 1
        snap = snap_dir / f"v{n:03d}.json"
        snap.write_text(profile.to_json(), encoding="utf-8")
    return target


# ════════════════════════════════════════════════════════════════════════════
# Facts
# ════════════════════════════════════════════════════════════════════════════

def facts_path(profile_dir: Optional[Path] = None) -> Path:
    return (profile_dir or _profile_dir()) / "facts.jsonl"


def load_facts(profile_dir: Optional[Path] = None) -> list[Fact]:
    p = facts_path(profile_dir)
    if not p.exists():
        return []
    out: list[Fact] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Fact.from_dict(json.loads(line)))
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def write_facts(facts: Iterable[Fact], profile_dir: Optional[Path] = None) -> None:
    p = facts_path(profile_dir)
    ensure_profile_dirs(profile_dir)
    tmp = p.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for fact in facts:
            f.write(fact.to_jsonl() + "\n")
    tmp.replace(p)


def append_facts(facts: Iterable[Fact], profile_dir: Optional[Path] = None) -> int:
    p = facts_path(profile_dir)
    ensure_profile_dirs(profile_dir)
    n = 0
    with p.open("a", encoding="utf-8") as f:
        for fact in facts:
            f.write(fact.to_jsonl() + "\n")
            n += 1
    return n


def next_fact_id(profile_dir: Optional[Path] = None) -> str:
    facts = load_facts(profile_dir)
    if not facts:
        return "fact_001"
    max_n = 0
    for f in facts:
        try:
            n = int(f.id.removeprefix("fact_"))
            max_n = max(max_n, n)
        except ValueError:
            continue
    return f"fact_{max_n + 1:03d}"


# ════════════════════════════════════════════════════════════════════════════
# Signals
# ════════════════════════════════════════════════════════════════════════════

def signals_path(profile_dir: Optional[Path] = None) -> Path:
    return (profile_dir or _profile_dir()) / "signals.jsonl"


def load_signals(profile_dir: Optional[Path] = None) -> list[Signal]:
    p = signals_path(profile_dir)
    if not p.exists():
        return []
    out: list[Signal] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Signal.from_dict(json.loads(line)))
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def write_signals(signals: Iterable[Signal], profile_dir: Optional[Path] = None) -> None:
    p = signals_path(profile_dir)
    ensure_profile_dirs(profile_dir)
    tmp = p.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for sig in signals:
            f.write(sig.to_jsonl() + "\n")
    tmp.replace(p)


# ════════════════════════════════════════════════════════════════════════════
# Embeddings (facts + signals share npz format)
# ════════════════════════════════════════════════════════════════════════════

def _embeddings_path(profile_dir: Optional[Path], kind: str) -> Path:
    return (profile_dir or _profile_dir()) / f"{kind}_embeddings.npz"


def load_embeddings(profile_dir: Optional[Path], kind: str) -> tuple[np.ndarray, np.ndarray]:
    """Read {facts|signals}_embeddings.npz. Returns (ids, vectors)."""
    p = _embeddings_path(profile_dir, kind)
    if not p.exists():
        return np.array([], dtype=object), np.zeros((0, 384), dtype=np.float32)
    data = np.load(p, allow_pickle=True)
    return data["ids"], data["vectors"]


def save_embeddings(
    profile_dir: Optional[Path],
    kind: str,
    ids: list[str],
    vectors: list[list[float]],
) -> None:
    ensure_profile_dirs(profile_dir)
    p = _embeddings_path(profile_dir, kind)
    ids_arr = np.array(ids, dtype=object)
    if vectors:
        vecs_arr = np.array(vectors, dtype=np.float32)
    else:
        vecs_arr = np.zeros((0, 384), dtype=np.float32)
    np.savez(p, ids=ids_arr, vectors=vecs_arr)


def rebuild_facts_embeddings(profile_dir: Optional[Path], embed_fn) -> tuple[int, int]:
    facts = load_facts(profile_dir)
    if not facts:
        save_embeddings(profile_dir, "facts", [], [])
        return 0, 0
    ids: list[str] = []
    vecs: list[list[float]] = []
    for f in facts:
        vec, _meta = embed_fn(f.text)
        if vec is None:
            continue
        ids.append(f.id)
        vecs.append(vec)
    save_embeddings(profile_dir, "facts", ids, vecs)
    return len(ids), (len(vecs[0]) if vecs else 0)


def rebuild_signals_embeddings(profile_dir: Optional[Path], embed_fn) -> tuple[int, int]:
    signals = load_signals(profile_dir)
    if not signals:
        save_embeddings(profile_dir, "signals", [], [])
        return 0, 0
    ids: list[str] = []
    vecs: list[list[float]] = []
    for s in signals:
        # Embed canonical_name + definition together — captures both lexical
        # and semantic match surfaces for retrieval.
        text = f"{s.canonical_name}: {s.definition}"
        vec, _meta = embed_fn(text)
        if vec is None:
            continue
        ids.append(s.id)
        vecs.append(vec)
    save_embeddings(profile_dir, "signals", ids, vecs)
    return len(ids), (len(vecs[0]) if vecs else 0)
