"""Atom-level chunking — three strategies, deterministic dispatch.

Strategy table:
  Memo-formatted .md  → chunk_memo()         best — atom-bounded, zero LLM cost
  Resume PDF          → chunk_resume_pdf()   high — heading-bounded
  Plain text / .md    → chunk_unstructured() lower — recursive char split, warning shown

The architectural insight: by giving the user a Memo Helper Prompt for free
LLM tools, we offload chunking discipline to ChatGPT once-per-doc and get
perfect topic coherence at retrieval time. See memo_prompt.py.
"""
from __future__ import annotations

import re
from typing import Iterator, Optional

import yaml

from .schemas import Atom

# ── Memo format constants ────────────────────────────────────────────────────

ATOM_HEADER_RE = re.compile(r"^## Atom: (.+)$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# ── Resume PDF section heuristics ────────────────────────────────────────────

# Common resume section headers (case-insensitive, line-anchored).
_RESUME_SECTION_RE = re.compile(
    r"^\s*("
    r"professional\s+experience|work\s+experience|experience|"
    r"education|skills|technical\s+skills|certifications|"
    r"projects|publications|awards|achievements|"
    r"summary|profile|objective|"
    r"volunteer|interests"
    r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Role-boundary heuristic within Experience section: lines that look like
# "<Company> | <Title>" or "<Title>, <Company>" or "<Title> @ <Company>".
_ROLE_BOUNDARY_RE = re.compile(
    r"^[A-Z][A-Za-z0-9 .&'\-]+\s*[\|@\-]\s*[A-Z][A-Za-z0-9 .&'\-]+",
    re.MULTILINE,
)

# ── Unstructured fallback constants ──────────────────────────────────────────

UNSTRUCTURED_TARGET_CHARS = 600
UNSTRUCTURED_OVERLAP_CHARS = 100
UNSTRUCTURED_MIN_CHARS = 200


# ════════════════════════════════════════════════════════════════════════════
# Memo chunker — best path
# ════════════════════════════════════════════════════════════════════════════

def split_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter dict + remaining body. Returns ({}, content)
    when no frontmatter present.
    """
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    try:
        meta = yaml.safe_load(m.group(1)) or {}
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError:
        meta = {}
    return meta, content[m.end():]


def _parse_atom_metadata(atom_block: str) -> tuple[dict, str]:
    """Parse the leading ``key: value`` lines of an atom into a dict, return
    (metadata, narrative_body). Stops at the first blank line OR first
    non-metadata line. If the atom is metadata-only (no body), returns
    (meta, "") rather than treating the metadata text as body.
    """
    lines = atom_block.splitlines()
    meta_lines: list[str] = []
    body_start: Optional[int] = None
    for i, line in enumerate(lines):
        if not line.strip():
            body_start = i + 1
            break
        if re.match(r"^\s*[a-z_][a-z0-9_]*\s*:", line):
            meta_lines.append(line)
            continue
        body_start = i
        break

    # If we exhausted the loop without a body marker, the entire block was
    # metadata — body is empty.
    if body_start is None:
        body_start = len(lines)

    meta: dict = {}
    if meta_lines:
        try:
            parsed = yaml.safe_load("\n".join(meta_lines)) or {}
            if isinstance(parsed, dict):
                meta = parsed
        except yaml.YAMLError:
            pass
    body = "\n".join(lines[body_start:]).strip()
    return meta, body


def is_memo_format(content: str) -> bool:
    """True if content has frontmatter with ``source_type`` AND at least one
    ``## Atom:`` header. Used by ingest dispatch.
    """
    meta, body = split_frontmatter(content)
    if "source_type" not in meta:
        return False
    return bool(ATOM_HEADER_RE.search(body))


def chunk_memo(content: str, evidence_id: str) -> Iterator[Atom]:
    """Best-quality chunker: split at ``## Atom:`` headers.

    Each Atom becomes one chunk. Per-atom metadata (date, role, company, tags,
    metric_keys) is parsed from the leading ``key: value`` lines and merged
    onto doc-level frontmatter (atom-level wins on conflict).
    """
    doc_metadata, body = split_frontmatter(content)

    matches = list(ATOM_HEADER_RE.finditer(body))
    if not matches:
        return

    # Compute (start, end, title) for each atom
    spans: list[tuple[int, int, str]] = []
    for i, m in enumerate(matches):
        start = m.end()  # body of atom starts after the header line
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        spans.append((start, end, m.group(1).strip()))

    for idx, (start, end, title) in enumerate(spans):
        atom_block = body[start:end].strip()
        atom_meta, atom_body = _parse_atom_metadata(atom_block)

        merged_meta = {**doc_metadata, **atom_meta}
        # Strip non-content frontmatter keys we don't want in atom.metadata
        merged_meta.pop("source_type", None)
        # author_role is a doc-level default; keep it under role if atom didn't
        # provide its own
        if "role" not in merged_meta and "author_role" in merged_meta:
            merged_meta["role"] = merged_meta["author_role"]
        merged_meta.pop("author_role", None)
        # default_tags merge with atom-level tags
        default_tags = merged_meta.pop("default_tags", []) or []
        atom_tags = merged_meta.get("tags") or []
        if default_tags:
            merged_meta["tags"] = list(dict.fromkeys([*default_tags, *atom_tags]))

        if not atom_body:
            continue

        yield Atom(
            id=f"{evidence_id}_a{idx:03d}",
            evidence_id=evidence_id,
            chunk_idx=idx,
            atom_title=title,
            text=atom_body,
            metadata=merged_meta,
        )


# ════════════════════════════════════════════════════════════════════════════
# Resume PDF chunker — high quality (heading-bounded)
# ════════════════════════════════════════════════════════════════════════════

def chunk_resume_pdf(content: str, evidence_id: str) -> Iterator[Atom]:
    """Chunk an extracted-resume text by section headings.

    Strategy:
      1. Locate canonical section headings (Experience, Education, Skills, …).
      2. Split text into per-section blocks.
      3. For Experience section, sub-split at role boundaries
         (``Company | Title`` or ``Title, Company``).
      4. Each chunk gets ``headings_path`` metadata for retrieval context.
    """
    if not content.strip():
        return

    # Find section boundaries
    section_matches = list(_RESUME_SECTION_RE.finditer(content))
    if not section_matches:
        # No section structure found — treat whole resume as one block
        yield Atom(
            id=f"{evidence_id}_a000",
            evidence_id=evidence_id,
            chunk_idx=0,
            atom_title="Resume (full text)",
            text=content.strip(),
            metadata={"headings_path": ["Resume"]},
        )
        return

    # Pre-section preamble (contact info, name, summary above first heading)
    chunk_idx = 0
    if section_matches[0].start() > 0:
        preamble = content[: section_matches[0].start()].strip()
        if preamble:
            yield Atom(
                id=f"{evidence_id}_a{chunk_idx:03d}",
                evidence_id=evidence_id,
                chunk_idx=chunk_idx,
                atom_title="Header / Contact",
                text=preamble,
                metadata={"headings_path": ["Header"]},
            )
            chunk_idx += 1

    # Per-section chunks
    for i, m in enumerate(section_matches):
        section_name = m.group(1).strip().title()
        start = m.end()
        end = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(content)
        section_body = content[start:end].strip()
        if not section_body:
            continue

        # Sub-split Experience section by role boundaries
        if "experience" in section_name.lower():
            for role_chunk_idx, role_atom in enumerate(
                _split_experience_by_role(section_body)
            ):
                yield Atom(
                    id=f"{evidence_id}_a{chunk_idx:03d}",
                    evidence_id=evidence_id,
                    chunk_idx=chunk_idx,
                    atom_title=role_atom["title"],
                    text=role_atom["text"],
                    metadata={"headings_path": [section_name, role_atom["title"]]},
                )
                chunk_idx += 1
        else:
            yield Atom(
                id=f"{evidence_id}_a{chunk_idx:03d}",
                evidence_id=evidence_id,
                chunk_idx=chunk_idx,
                atom_title=section_name,
                text=section_body,
                metadata={"headings_path": [section_name]},
            )
            chunk_idx += 1


def _split_experience_by_role(body: str) -> Iterator[dict]:
    """Split an experience-section body into per-role atoms."""
    boundary_matches = list(_ROLE_BOUNDARY_RE.finditer(body))
    if not boundary_matches:
        # No role boundaries detected — emit the whole section
        yield {"title": "Experience (combined)", "text": body}
        return

    for i, m in enumerate(boundary_matches):
        start = m.start()
        end = boundary_matches[i + 1].start() if i + 1 < len(boundary_matches) else len(body)
        role_text = body[start:end].strip()
        if not role_text:
            continue
        # First line is the role title
        title_line = role_text.splitlines()[0].strip()
        yield {"title": title_line[:80], "text": role_text}


# ════════════════════════════════════════════════════════════════════════════
# Unstructured fallback chunker — last resort
# ════════════════════════════════════════════════════════════════════════════

def chunk_unstructured(content: str, evidence_id: str) -> Iterator[Atom]:
    """Recursive character splitting with paragraph-preference + overlap.

    Used only when the document is neither memo-formatted nor a resume PDF.
    The CLI shows a warning when this chunker fires, suggesting the user
    reformat via ``linkright evidence add --from-raw``.
    """
    if not content.strip():
        return

    # Prefer paragraph breaks
    paragraphs = re.split(r"\n\s*\n", content.strip())
    chunks: list[str] = []
    buf = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(buf) + len(para) + 2 <= UNSTRUCTURED_TARGET_CHARS:
            buf = f"{buf}\n\n{para}".strip()
        else:
            if buf:
                chunks.append(buf)
            # If a single paragraph itself exceeds target, hard-split
            if len(para) > UNSTRUCTURED_TARGET_CHARS:
                chunks.extend(
                    _hard_split(para, UNSTRUCTURED_TARGET_CHARS, UNSTRUCTURED_OVERLAP_CHARS)
                )
                buf = ""
            else:
                buf = para

    if buf:
        chunks.append(buf)

    # Drop chunks too small to embed meaningfully (drift noise)
    chunks = [c for c in chunks if len(c) >= UNSTRUCTURED_MIN_CHARS] or chunks

    for idx, chunk_text in enumerate(chunks):
        yield Atom(
            id=f"{evidence_id}_a{idx:03d}",
            evidence_id=evidence_id,
            chunk_idx=idx,
            atom_title=f"Chunk {idx + 1} (unstructured)",
            text=chunk_text,
            metadata={"chunker": "unstructured"},
        )


def _hard_split(text: str, target: int, overlap: int) -> list[str]:
    """Sliding-window split when a single paragraph is too large."""
    out: list[str] = []
    step = max(1, target - overlap)
    i = 0
    while i < len(text):
        out.append(text[i : i + target])
        i += step
    return out
