"""Top-level evidence ingestion — auto-detect type, route to chunker, embed.

Public API: ``ingest_file(path, tier=None) -> IngestResult``

Type detection cascade:
  1. ``.pdf`` → resume_pdf → chunk_resume_pdf
  2. ``.md`` / ``.markdown`` with frontmatter ``source_type`` AND ``## Atom:``
     headers → memo → chunk_memo
  3. anything else → other → chunk_unstructured (warning emitted)

Tier defaults:
  - resume_pdf → resume_canonical
  - memo with source_type=diary → diary
  - memo with source_type=reflection → reflection
  - everything else → additional_info
"""
from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .chunking import (
    chunk_memo,
    chunk_resume_pdf,
    chunk_unstructured,
    is_memo_format,
    split_frontmatter,
)
from .schemas import Atom, Evidence, EvidenceTier, EvidenceType
from .store import EvidenceStore


@dataclass
class IngestResult:
    evidence: Evidence
    atom_count: int
    embedding_dim: int
    warnings: list[str]


def _extract_pdf_text(path: Path) -> str:
    """PDF → plain text. Reuses the resume pipeline's parser if available."""
    try:
        from linkright.resume.lib.pdf_parse import extract_text  # type: ignore
        return extract_text(path)
    except Exception:
        # Last-resort minimal pypdf path
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            return "\n\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:
            raise RuntimeError(f"PDF parse failed for {path}: {e}") from e


def _detect_type_and_tier(
    path: Path, content: str, tier_override: Optional[EvidenceTier]
) -> tuple[EvidenceType, EvidenceTier, dict, str]:
    """Returns (type, tier, doc_metadata, chunker_name).

    Memo doc-metadata is pulled from the frontmatter here so the Evidence row
    can store it without re-parsing.
    """
    suffix = path.suffix.lower()
    warns: list[str] = []

    # Resume PDF
    if suffix == ".pdf":
        ev_type = EvidenceType.RESUME_PDF
        tier = tier_override or EvidenceTier.RESUME_CANONICAL
        return ev_type, tier, {}, "resume_pdf"

    # Memo-formatted markdown
    if suffix in (".md", ".markdown") and is_memo_format(content):
        meta, _body = split_frontmatter(content)
        source_type = (meta.get("source_type") or "").lower()
        ev_type = EvidenceType.MEMO
        if tier_override:
            tier = tier_override
        elif source_type == "diary":
            tier = EvidenceTier.DIARY
            ev_type = EvidenceType.DIARY
        elif source_type == "reflection":
            tier = EvidenceTier.REFLECTION
        else:
            tier = EvidenceTier.ADDITIONAL_INFO
        return ev_type, tier, meta, "memo"

    # Anything else → unstructured fallback
    ev_type = EvidenceType.OTHER
    tier = tier_override or EvidenceTier.ADDITIONAL_INFO
    return ev_type, tier, {}, "unstructured"


def ingest_file(
    path: Path,
    *,
    tier: Optional[EvidenceTier] = None,
    store: Optional[EvidenceStore] = None,
    embed_fn=None,
) -> IngestResult:
    """Ingest one document end-to-end: parse, route, chunk, embed, persist.

    Args:
        path: source document.
        tier: optional override; otherwise inferred from doc type/frontmatter.
        store: optional pre-built ``EvidenceStore`` (used in tests).
        embed_fn: ``embed(text) -> (vec, meta)``. If None, imported lazily.

    Returns ``IngestResult`` with the persisted ``Evidence`` row + counts.
    """
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    store = store or EvidenceStore()
    if embed_fn is None:
        from linkright.resume.lib.embedder import embed as _embed
        embed_fn = _embed

    warns: list[str] = []

    # 1. Read content
    if path.suffix.lower() == ".pdf":
        content = _extract_pdf_text(path)
    else:
        content = path.read_text(encoding="utf-8", errors="ignore")

    # 2. Type + tier detection
    ev_type, tier_resolved, doc_metadata, chunker_name = _detect_type_and_tier(
        path, content, tier
    )

    if chunker_name == "unstructured":
        warns.append(
            f"{path.name} has no Memo or resume structure — embed quality will "
            "be lower. Try: linkright evidence add --from-raw <file>"
        )

    # 3. Mint evidence id + copy file
    evidence_id = store.next_evidence_id()
    copied_path = store.copy_source_file(path, evidence_id)

    # 4. Chunk
    if chunker_name == "memo":
        atoms = list(chunk_memo(content, evidence_id))
    elif chunker_name == "resume_pdf":
        atoms = list(chunk_resume_pdf(content, evidence_id))
    else:
        atoms = list(chunk_unstructured(content, evidence_id))

    if not atoms:
        raise ValueError(f"No atoms produced from {path}; document may be empty")

    # 5. Embed + persist atoms
    new_ids: list[str] = []
    new_vecs: list[list[float]] = []
    for a in atoms:
        vec, _meta = embed_fn(a.text)
        if vec is None:
            warns.append(f"Embedding failed for atom {a.id} — skipping")
            continue
        new_ids.append(a.id)
        new_vecs.append(vec)
    store.append_atoms(atoms)

    # 6. Merge embeddings (append new vectors to existing)
    existing_ids, existing_vecs = store.load_embeddings()
    combined_ids = [*list(existing_ids), *new_ids]
    combined_vecs = [*existing_vecs.tolist(), *new_vecs] if existing_vecs.size else new_vecs
    store.save_embeddings(combined_ids, combined_vecs)

    # 7. Build + persist Evidence row
    evidence = Evidence(
        id=evidence_id,
        type=ev_type,
        source_path=str(copied_path),
        tier=tier_resolved,
        doc_metadata=doc_metadata,
        atom_count=len(atoms),
    )
    store.append_evidence(evidence)

    dim = len(new_vecs[0]) if new_vecs else 0
    return IngestResult(
        evidence=evidence,
        atom_count=len(atoms),
        embedding_dim=dim,
        warnings=warns,
    )
