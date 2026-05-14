"""End-to-end ingest tests using a fake embedder + tmp evidence dir.

Verifies:
  - memo .md → chunk_memo → atoms persisted + embeddings stored
  - resume .pdf path skipped (needs real PDF) — covered by chunking tests
  - unstructured fallback emits warning
  - multiple evidence ingestions accumulate atoms + extend embeddings.npz
  - delete_evidence wipes atoms + file copy + rebuild embeddings drops vectors
  - tier inference from frontmatter (diary, additional_info, reflection)
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from linkright.evidence.ingest import ingest_file
from linkright.evidence.schemas import EvidenceTier, EvidenceType
from linkright.evidence.store import EvidenceStore


def fake_embed(text: str):
    """Deterministic 384-dim hash-based vector. Fast, no model load."""
    import hashlib
    import math
    h = hashlib.sha256(text.encode()).digest()
    raw = list(h) * (384 // len(h) + 1)
    raw = raw[:384]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw], {"tier": "fake", "model": "fake_sha256", "dim": 384}


def _write_memo(tmp_path: Path, name: str, source_type: str = "diary") -> Path:
    content = textwrap.dedent(f"""\
        ---
        source_type: {source_type}
        date: 2026-05-15
        author_role: "Test Role"
        default_tags: [test]
        ---

        ## Atom: First topic
        date: 2026-05-15
        role: "Test Role"
        company: TestCo
        tags: [first]

        Body of the first atom — needs to be substantial enough to look real.
        Lorem ipsum dolor sit amet, consectetur adipiscing elit.

        ## Atom: Second topic
        date: 2026-05-16
        role: "Test Role"
        company: TestCo
        tags: [second]

        Body of the second atom — also substantial enough to look real.
        Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
    """)
    p = tmp_path / name
    p.write_text(content)
    return p


def test_ingest_memo_basic(tmp_path: Path):
    src = _write_memo(tmp_path, "test.md")
    ev_dir = tmp_path / "evidence_store"
    store = EvidenceStore(ev_dir)

    result = ingest_file(src, store=store, embed_fn=fake_embed)

    assert result.evidence.id == "ev_001"
    assert result.evidence.type == EvidenceType.DIARY  # source_type=diary → DIARY type
    assert result.evidence.tier == EvidenceTier.DIARY
    assert result.atom_count == 2
    assert result.embedding_dim == 384
    assert result.warnings == []

    # Source file copied
    copied = ev_dir / "files" / "ev_001.md"
    assert copied.exists()

    # Atoms persisted
    atoms = store.list_atoms("ev_001")
    assert len(atoms) == 2
    assert atoms[0].atom_title == "First topic"

    # Embeddings persisted
    ids, vecs = store.load_embeddings()
    assert len(ids) == 2
    assert vecs.shape == (2, 384)


def test_ingest_memo_additional_info_default(tmp_path: Path):
    src = _write_memo(tmp_path, "notes.md", source_type="additional_info")
    ev_dir = tmp_path / "ev"
    store = EvidenceStore(ev_dir)
    result = ingest_file(src, store=store, embed_fn=fake_embed)
    assert result.evidence.tier == EvidenceTier.ADDITIONAL_INFO
    assert result.evidence.type == EvidenceType.MEMO


def test_ingest_memo_reflection(tmp_path: Path):
    src = _write_memo(tmp_path, "ref.md", source_type="reflection")
    store = EvidenceStore(tmp_path / "ev")
    result = ingest_file(src, store=store, embed_fn=fake_embed)
    assert result.evidence.tier == EvidenceTier.REFLECTION


def test_ingest_unstructured_emits_warning(tmp_path: Path):
    src = tmp_path / "raw.txt"
    src.write_text("Just unstructured text. No memo format. " * 30)
    store = EvidenceStore(tmp_path / "ev")
    result = ingest_file(src, store=store, embed_fn=fake_embed)
    assert result.evidence.type == EvidenceType.OTHER
    assert any("lower" in w for w in result.warnings)
    assert result.atom_count >= 1


def test_ingest_multiple_evidence_accumulates(tmp_path: Path):
    src1 = _write_memo(tmp_path, "a.md")
    src2 = _write_memo(tmp_path, "b.md")
    store = EvidenceStore(tmp_path / "ev")

    r1 = ingest_file(src1, store=store, embed_fn=fake_embed)
    r2 = ingest_file(src2, store=store, embed_fn=fake_embed)

    assert r1.evidence.id == "ev_001"
    assert r2.evidence.id == "ev_002"

    all_evidence = store.list_evidence()
    assert len(all_evidence) == 2

    all_atoms = store.list_atoms()
    assert len(all_atoms) == 4  # 2 atoms per memo

    ids, vecs = store.load_embeddings()
    assert len(ids) == 4
    assert vecs.shape == (4, 384)


def test_delete_evidence_removes_atoms_and_file(tmp_path: Path):
    src = _write_memo(tmp_path, "x.md")
    store = EvidenceStore(tmp_path / "ev")
    ingest_file(src, store=store, embed_fn=fake_embed)

    assert (tmp_path / "ev" / "files" / "ev_001.md").exists()
    assert len(store.list_atoms("ev_001")) == 2

    assert store.delete_evidence("ev_001") is True
    assert store.list_evidence() == []
    assert store.list_atoms("ev_001") == []
    assert not (tmp_path / "ev" / "files" / "ev_001.md").exists()


def test_delete_then_rebuild_embeddings(tmp_path: Path):
    src1 = _write_memo(tmp_path, "a.md")
    src2 = _write_memo(tmp_path, "b.md")
    store = EvidenceStore(tmp_path / "ev")
    ingest_file(src1, store=store, embed_fn=fake_embed)
    ingest_file(src2, store=store, embed_fn=fake_embed)

    store.delete_evidence("ev_001")
    n, dim = store.rebuild_embeddings(fake_embed)
    assert n == 2  # only ev_002's 2 atoms remain
    assert dim == 384

    ids, vecs = store.load_embeddings()
    assert len(ids) == 2
    # All remaining ids must belong to ev_002
    assert all(i.startswith("ev_002_") for i in ids)


def test_tier_override_wins(tmp_path: Path):
    src = _write_memo(tmp_path, "x.md", source_type="diary")
    store = EvidenceStore(tmp_path / "ev")
    result = ingest_file(
        src, tier=EvidenceTier.RESUME_CANONICAL, store=store, embed_fn=fake_embed
    )
    assert result.evidence.tier == EvidenceTier.RESUME_CANONICAL


def test_ingest_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        ingest_file(tmp_path / "nonexistent.md")


def test_next_evidence_id_handles_gaps(tmp_path: Path):
    store = EvidenceStore(tmp_path / "ev")
    src = _write_memo(tmp_path, "a.md")

    ingest_file(src, store=store, embed_fn=fake_embed)
    ingest_file(_write_memo(tmp_path, "b.md"), store=store, embed_fn=fake_embed)
    ingest_file(_write_memo(tmp_path, "c.md"), store=store, embed_fn=fake_embed)

    # Delete middle one
    store.delete_evidence("ev_002")
    # Next should be ev_004 (max + 1, not refilling gap)
    assert store.next_evidence_id() == "ev_004"
