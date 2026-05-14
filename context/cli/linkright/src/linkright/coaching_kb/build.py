"""Build the coaching playbook RAG index from source markdown research docs.

Heading-based chunking: each H2 (## ...) section becomes one chunk. If a
section is too large it sub-splits at H3 (###). Sub-100-char fragments
are merged into the previous chunk to avoid embedding noise.

Each chunk records:
  id              str   stable identifier — `{doc_stem}__{section_slug}__{idx:03d}`
  doc_name        str   filename (e.g. interview_intro_positioning_guide.md)
  doc_stem        str   filename without extension
  chunk_idx       int   per-doc chunk index
  headings_path   list  ["H1 title", "H2 section", ...]
  text            str   the chunk body (markdown preserved)
  char_count      int
  phases          list  resolved from routing (which phase keys reference doc)

Storage:
  ~/.linkright/coaching_kb/
    playbook.npz             ids + vectors (fastembed 384-dim)
    playbook_chunks.jsonl    per-chunk metadata + text
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from .routing import phases_for_doc


# Default research source location (Satvik's machine).
DEFAULT_SOURCE_DIR = Path("/Users/satvikjain/Downloads/Procol_AI/Research_Linkright")

# Chunking tunables
TARGET_CHUNK_CHARS = 1800
MIN_CHUNK_CHARS = 100
SUB_SPLIT_AT_HEADING_LEVEL = 3  # split H2 sections at H3 if they exceed target


_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_H3_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)


def _kb_dir() -> Path:
    home = os.environ.get("LINKRIGHT_HOME")
    base = Path(home) if home else Path.home() / ".linkright"
    return base / "coaching_kb"


@dataclass
class PlaybookChunk:
    id: str
    doc_name: str
    doc_stem: str
    chunk_idx: int
    headings_path: list[str] = field(default_factory=list)
    text: str = ""
    char_count: int = 0
    phases: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.char_count:
            self.char_count = len(self.text)

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, default=str)


# ════════════════════════════════════════════════════════════════════════════
# Chunker
# ════════════════════════════════════════════════════════════════════════════

def chunk_doc(content: str, doc_name: str) -> Iterator[PlaybookChunk]:
    """Split a research doc into heading-bounded chunks.

    Strategy:
      1. Find H1 (if present) — used as document title for headings_path
      2. Split at H2 boundaries
      3. For each H2 section: if > TARGET_CHUNK_CHARS, sub-split at H3
      4. Merge sub-MIN-CHUNK fragments into the previous chunk
    """
    doc_stem = doc_name.removesuffix(".md").removesuffix(".markdown")
    referenced_phases = phases_for_doc(doc_name)

    # Document title from H1 (first match) — fall back to filename stem
    h1_match = _H1_RE.search(content)
    doc_title = h1_match.group(1).strip() if h1_match else doc_stem.replace("_", " ").title()

    # Build H2 spans: (start, end, title)
    h2_matches = list(_H2_RE.finditer(content))
    if not h2_matches:
        # No H2 headings — single chunk for whole doc
        text = content.strip()
        if len(text) >= MIN_CHUNK_CHARS:
            yield PlaybookChunk(
                id=_chunk_id(doc_stem, doc_title, 0),
                doc_name=doc_name,
                doc_stem=doc_stem,
                chunk_idx=0,
                headings_path=[doc_title],
                text=text,
                phases=referenced_phases,
            )
        return

    h2_spans: list[tuple[int, int, str]] = []
    # Pre-section preamble (text before first H2)
    if h2_matches[0].start() > 0:
        preamble_end = h2_matches[0].start()
        preamble_text = content[:preamble_end].strip()
        # Strip the H1 line (already captured as doc_title)
        if h1_match and h1_match.end() < preamble_end:
            preamble_text = content[h1_match.end():preamble_end].strip()
        if len(preamble_text) >= MIN_CHUNK_CHARS:
            h2_spans.append((0, preamble_end, "Preamble"))

    for i, m in enumerate(h2_matches):
        start = m.end()
        end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(content)
        h2_spans.append((start, end, m.group(1).strip()))

    chunk_idx = 0
    pending_merge: Optional[PlaybookChunk] = None

    for span_start, span_end, h2_title in h2_spans:
        body = content[span_start:span_end].strip()
        if not body:
            continue

        section_chunks = list(_split_h2_section(
            body, doc_title, h2_title, doc_stem, doc_name, referenced_phases,
        ))

        for sc in section_chunks:
            sc.chunk_idx = chunk_idx
            sc.id = _chunk_id(doc_stem, sc.headings_path[-1], chunk_idx)

            # Merge tiny fragments back into the prev chunk
            if sc.char_count < MIN_CHUNK_CHARS and pending_merge is not None:
                pending_merge.text = (pending_merge.text + "\n\n" + sc.text).strip()
                pending_merge.char_count = len(pending_merge.text)
                continue

            if pending_merge is not None:
                yield pending_merge
                chunk_idx += 1
                # re-mint the just-yielded chunk's chunk_idx (already set)

            pending_merge = sc

    if pending_merge is not None:
        pending_merge.chunk_idx = chunk_idx
        pending_merge.id = _chunk_id(doc_stem, pending_merge.headings_path[-1], chunk_idx)
        yield pending_merge


def _split_h2_section(
    body: str,
    doc_title: str,
    h2_title: str,
    doc_stem: str,
    doc_name: str,
    phases: list[str],
) -> Iterator[PlaybookChunk]:
    """If H2 section > target, sub-split at H3 boundaries; else emit as one."""
    if len(body) <= TARGET_CHUNK_CHARS:
        yield PlaybookChunk(
            id="",  # filled by caller
            doc_name=doc_name,
            doc_stem=doc_stem,
            chunk_idx=0,  # filled by caller
            headings_path=[doc_title, h2_title],
            text=body,
            phases=phases,
        )
        return

    h3_matches = list(_H3_RE.finditer(body))
    if not h3_matches:
        # Too large but no H3 sub-structure — split at TARGET char boundary
        for sub_text in _hard_split(body, TARGET_CHUNK_CHARS):
            yield PlaybookChunk(
                id="",
                doc_name=doc_name,
                doc_stem=doc_stem,
                chunk_idx=0,
                headings_path=[doc_title, h2_title],
                text=sub_text,
                phases=phases,
            )
        return

    # Pre-H3 preamble of the H2 section
    if h3_matches[0].start() > 0:
        pre = body[:h3_matches[0].start()].strip()
        if len(pre) >= MIN_CHUNK_CHARS:
            yield PlaybookChunk(
                id="",
                doc_name=doc_name,
                doc_stem=doc_stem,
                chunk_idx=0,
                headings_path=[doc_title, h2_title],
                text=pre,
                phases=phases,
            )

    for i, m in enumerate(h3_matches):
        start = m.end()
        end = h3_matches[i + 1].start() if i + 1 < len(h3_matches) else len(body)
        sub_body = body[start:end].strip()
        if not sub_body:
            continue
        yield PlaybookChunk(
            id="",
            doc_name=doc_name,
            doc_stem=doc_stem,
            chunk_idx=0,
            headings_path=[doc_title, h2_title, m.group(1).strip()],
            text=sub_body,
            phases=phases,
        )


def _hard_split(text: str, max_chars: int) -> list[str]:
    """Last-resort character split for sections without sub-headings."""
    out: list[str] = []
    pos = 0
    while pos < len(text):
        out.append(text[pos:pos + max_chars])
        pos += max_chars
    return out


def _chunk_id(doc_stem: str, section_title: str, idx: int) -> str:
    s = section_title.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")[:30] or "x"
    return f"{doc_stem}__{s}__{idx:03d}"


# ════════════════════════════════════════════════════════════════════════════
# Builder
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class BuildReport:
    docs_scanned: int = 0
    docs_chunked: int = 0
    chunks_total: int = 0
    chunks_embedded: int = 0
    embedding_dim: int = 0
    skipped: list[str] = field(default_factory=list)
    output_dir: Path = field(default_factory=Path)


def ensure_kb_dir() -> Path:
    p = _kb_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_playbook(
    *,
    source_dir: Optional[Path] = None,
    embed_fn=None,
) -> BuildReport:
    """One-shot index build over a source directory of research markdown files.

    Args:
      source_dir: location of .md research docs. Defaults to
                  /Users/satvikjain/Downloads/Procol_AI/Research_Linkright.
      embed_fn:   ``embed(text) -> (vec, meta)`` from resume.lib.embedder.
                  If None, imported lazily.

    Returns BuildReport summary; persists to ~/.linkright/coaching_kb/.
    """
    source = source_dir or DEFAULT_SOURCE_DIR
    if not source.exists():
        raise FileNotFoundError(
            f"Coaching playbook source not found: {source}. "
            f"Pass --source <path> or place research docs at {DEFAULT_SOURCE_DIR}."
        )

    if embed_fn is None:
        from linkright.resume.lib.embedder import embed as _embed
        embed_fn = _embed

    out_dir = ensure_kb_dir()
    chunks_path = out_dir / "playbook_chunks.jsonl"
    npz_path = out_dir / "playbook.npz"

    # Find all .md files in source
    md_files = sorted(p for p in source.glob("*.md") if p.is_file())
    report = BuildReport(output_dir=out_dir)
    report.docs_scanned = len(md_files)

    all_chunks: list[PlaybookChunk] = []
    for md in md_files:
        try:
            content = md.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            report.skipped.append(f"{md.name}: {e}")
            continue

        if not content.strip():
            report.skipped.append(f"{md.name}: empty file")
            continue

        chunks = list(chunk_doc(content, md.name))
        if not chunks:
            report.skipped.append(f"{md.name}: no chunks produced")
            continue

        all_chunks.extend(chunks)
        report.docs_chunked += 1

    report.chunks_total = len(all_chunks)

    if not all_chunks:
        # Persist empty index files so callers can detect "built but empty"
        with chunks_path.open("w") as f:
            pass
        np.savez(npz_path, ids=np.array([], dtype=object),
                 vectors=np.zeros((0, 384), dtype=np.float32))
        return report

    # Embed each chunk
    ids: list[str] = []
    vecs: list[list[float]] = []
    for c in all_chunks:
        vec, _meta = embed_fn(c.text)
        if vec is None:
            report.skipped.append(f"{c.id}: embedding failed")
            continue
        ids.append(c.id)
        vecs.append(vec)

    report.chunks_embedded = len(ids)
    report.embedding_dim = len(vecs[0]) if vecs else 0

    # Persist chunks JSONL (atomic via tmp + replace)
    tmp_chunks = chunks_path.with_suffix(".jsonl.tmp")
    with tmp_chunks.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(c.to_jsonl() + "\n")
    tmp_chunks.replace(chunks_path)

    # Persist embeddings
    ids_arr = np.array(ids, dtype=object)
    vecs_arr = np.array(vecs, dtype=np.float32) if vecs else np.zeros((0, 384), dtype=np.float32)
    np.savez(npz_path, ids=ids_arr, vectors=vecs_arr)

    return report


# ════════════════════════════════════════════════════════════════════════════
# Loaders for downstream consumers (Phase 6 coach)
# ════════════════════════════════════════════════════════════════════════════

def load_playbook_chunks(kb_dir: Optional[Path] = None) -> list[PlaybookChunk]:
    p = (kb_dir or _kb_dir()) / "playbook_chunks.jsonl"
    if not p.exists():
        return []
    out: list[PlaybookChunk] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            out.append(PlaybookChunk(**d))
        except (json.JSONDecodeError, TypeError):
            continue
    return out


def load_playbook_embeddings(kb_dir: Optional[Path] = None) -> tuple[np.ndarray, np.ndarray]:
    p = (kb_dir or _kb_dir()) / "playbook.npz"
    if not p.exists():
        return np.array([], dtype=object), np.zeros((0, 384), dtype=np.float32)
    data = np.load(p, allow_pickle=True)
    return data["ids"], data["vectors"]


def is_kb_built(kb_dir: Optional[Path] = None) -> bool:
    """True iff both playbook.npz and playbook_chunks.jsonl exist + non-empty."""
    base = kb_dir or _kb_dir()
    chunks_p = base / "playbook_chunks.jsonl"
    npz_p = base / "playbook.npz"
    if not (chunks_p.exists() and npz_p.exists()):
        return False
    try:
        if chunks_p.stat().st_size == 0:
            return False
        ids, _vecs = load_playbook_embeddings(base)
        return len(ids) > 0
    except Exception:
        return False
