"""Evidence + Atom + embeddings storage on local disk.

Layout (per plan Part C):
  ~/.linkright/evidence/
    ├── store.jsonl        # Evidence entities, one per line
    ├── atoms.jsonl        # Atom entities, one per line
    ├── embeddings.npz     # ids + vectors (atom-level, fastembed 384-dim)
    └── files/             # original docs preserved

All writes are append-friendly. ``rebuild_embeddings()`` is the only
operation that fully rewrites embeddings.npz — called after any add/remove.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

from .schemas import Atom, Evidence


def _evidence_dir() -> Path:
    home = os.environ.get("LINKRIGHT_HOME")
    base = Path(home) if home else Path.home() / ".linkright"
    return base / "evidence"


class EvidenceStore:
    """Disk-backed evidence + atoms + embeddings store.

    Single-process semantics — no locking. Concurrent CLI invocations on the
    same evidence dir are not supported (matches existing profile pattern).
    """

    def __init__(self, evidence_dir: Optional[Path] = None) -> None:
        self.dir = evidence_dir or _evidence_dir()
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "files").mkdir(exist_ok=True)
        self.store_path = self.dir / "store.jsonl"
        self.atoms_path = self.dir / "atoms.jsonl"
        self.embeddings_path = self.dir / "embeddings.npz"

    # ── Evidence I/O ────────────────────────────────────────────────────────

    def list_evidence(self) -> list[Evidence]:
        if not self.store_path.exists():
            return []
        out: list[Evidence] = []
        for line in self.store_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                out.append(Evidence.from_dict(d))
            except (json.JSONDecodeError, KeyError):
                continue
        return out

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        for ev in self.list_evidence():
            if ev.id == evidence_id:
                return ev
        return None

    def write_evidence(self, evidences: Iterable[Evidence]) -> None:
        """Atomic full rewrite of store.jsonl. Used after add or remove."""
        tmp = self.store_path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for ev in evidences:
                f.write(ev.to_jsonl() + "\n")
        tmp.replace(self.store_path)

    def append_evidence(self, ev: Evidence) -> None:
        with self.store_path.open("a", encoding="utf-8") as f:
            f.write(ev.to_jsonl() + "\n")

    def delete_evidence(self, evidence_id: str) -> bool:
        """Remove evidence + its atoms + its file copy. Rebuilds embeddings.
        Returns True if anything was removed.
        """
        all_ev = self.list_evidence()
        kept = [e for e in all_ev if e.id != evidence_id]
        if len(kept) == len(all_ev):
            return False

        # Wipe associated atoms
        kept_atoms = [a for a in self.list_atoms() if a.evidence_id != evidence_id]
        self.write_atoms(kept_atoms)

        # Remove file copy
        for fp in (self.dir / "files").glob(f"{evidence_id}.*"):
            fp.unlink(missing_ok=True)

        # Persist evidence list
        self.write_evidence(kept)
        return True

    # ── Atom I/O ────────────────────────────────────────────────────────────

    def list_atoms(self, evidence_id: Optional[str] = None) -> list[Atom]:
        if not self.atoms_path.exists():
            return []
        out: list[Atom] = []
        for line in self.atoms_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                a = Atom.from_dict(d)
                if evidence_id and a.evidence_id != evidence_id:
                    continue
                out.append(a)
            except (json.JSONDecodeError, KeyError):
                continue
        return out

    def write_atoms(self, atoms: Iterable[Atom]) -> None:
        tmp = self.atoms_path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for atom in atoms:
                f.write(atom.to_jsonl() + "\n")
        tmp.replace(self.atoms_path)

    def append_atoms(self, atoms: Iterable[Atom]) -> int:
        n = 0
        with self.atoms_path.open("a", encoding="utf-8") as f:
            for atom in atoms:
                f.write(atom.to_jsonl() + "\n")
                n += 1
        return n

    # ── File copy ───────────────────────────────────────────────────────────

    def copy_source_file(self, src: Path, evidence_id: str) -> Path:
        """Copy original doc to evidence/files/<id>.<ext> for replayability."""
        suffix = src.suffix or ".txt"
        dest = self.dir / "files" / f"{evidence_id}{suffix}"
        shutil.copy2(src, dest)
        return dest

    # ── Embeddings ──────────────────────────────────────────────────────────

    def load_embeddings(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (ids, vectors). Empty arrays if no embeddings file yet."""
        if not self.embeddings_path.exists():
            return np.array([], dtype=object), np.zeros((0, 384), dtype=np.float32)
        data = np.load(self.embeddings_path, allow_pickle=True)
        return data["ids"], data["vectors"]

    def save_embeddings(self, ids: list[str], vectors: list[list[float]]) -> None:
        ids_arr = np.array(ids, dtype=object)
        if vectors:
            vecs_arr = np.array(vectors, dtype=np.float32)
        else:
            vecs_arr = np.zeros((0, 384), dtype=np.float32)
        np.savez(self.embeddings_path, ids=ids_arr, vectors=vecs_arr)

    def rebuild_embeddings(self, embed_fn) -> tuple[int, int]:
        """Re-embed every atom currently in atoms.jsonl. Returns (n_atoms, dim).

        ``embed_fn`` is the embedder ``embed(text) -> (vec, meta)`` from
        ``resume.lib.embedder``. Sticky-tier: must match the profile tier.
        """
        atoms = self.list_atoms()
        if not atoms:
            self.save_embeddings([], [])
            return 0, 0

        ids: list[str] = []
        vecs: list[list[float]] = []
        for a in atoms:
            vec, _meta = embed_fn(a.text)
            if vec is None:
                continue
            ids.append(a.id)
            vecs.append(vec)
        self.save_embeddings(ids, vecs)
        dim = len(vecs[0]) if vecs else 0
        return len(ids), dim

    # ── Helpers ─────────────────────────────────────────────────────────────

    def next_evidence_id(self) -> str:
        existing = self.list_evidence()
        if not existing:
            return "ev_001"
        max_n = 0
        for ev in existing:
            try:
                n = int(ev.id.removeprefix("ev_"))
                max_n = max(max_n, n)
            except ValueError:
                continue
        return f"ev_{max_n + 1:03d}"
