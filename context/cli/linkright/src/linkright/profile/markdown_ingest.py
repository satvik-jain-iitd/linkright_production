"""Markdown profile ingestion — S3.4.

Ingests long-form career narrative documents (Obsidian exports, diary-style
prose, 95KB career profiles) into the nugget store without manual copy-paste.

Public API:
    ingest_from_markdown(md_path, profile_dir, include_personal, llm_call_fn)
        → IngestResult

Privacy model:
    - Sections classified as personal-life are SKIPPED by default.
    - Pass include_personal=True to include them.
    - Privacy audit log summarises what was skipped.

LLM usage:
    - One call per chunk (per ## section, never the whole document at once).
    - Uses chat_with_fallback in direct mode (NEVER agent mode — see AC6 note).
    - Caller can inject a mock llm_call_fn for tests (no real LLM needed).

Dedup:
    - Jaccard token-overlap >= 0.8 against existing nuggets.
    - Deterministic, no vectors, no external deps.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# ── Section classification ────────────────────────────────────────────────────

_PERSONAL_KEYWORDS = frozenset({
    "family", "personal", "health", "diary", "private",
    "journal", "relationships", "feelings", "mental", "spiritual",
    "religion", "romance", "grief", "illness", "therapy",
})

_CAREER_KEYWORDS = frozenset({
    "work", "job", "project", "achievement", "role", "company",
    "team", "client", "career", "professional", "experience",
    "product", "engineering", "sales", "marketing", "leadership",
    "startup", "intern", "promotion", "raise", "goal", "okr",
})

# ATX heading pattern: captures optional depth + title
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def classify_section(title: str, body: str) -> str:
    """Return 'career-relevant', 'personal-life', or 'mixed'.

    Classification logic (heading-first):
    1. Normalise title to lowercase word-tokens.
    2. Check for keyword hits in title AND body.
    3. career hits > 0 AND personal hits == 0  → career-relevant
       personal hits > 0 AND career hits == 0  → personal-life
       both > 0                                 → mixed
       neither                                  → career-relevant (default)
    """
    combined = (title + " " + body).lower()
    tokens = set(re.findall(r"[a-z]+", combined))

    personal_hits = len(tokens & _PERSONAL_KEYWORDS)
    career_hits = len(tokens & _CAREER_KEYWORDS)

    if career_hits > 0 and personal_hits == 0:
        return "career-relevant"
    if personal_hits > 0 and career_hits == 0:
        return "personal-life"
    if personal_hits > 0 and career_hits > 0:
        return "mixed"
    # neither keyword found — treat as career-relevant (conservative, don't drop)
    return "career-relevant"


# ── Chunking ──────────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    """A single ## (or deeper) section of a Markdown document."""
    title: str
    body: str
    depth: int            # 1 = #, 2 = ##, etc.
    classification: str   # career-relevant / personal-life / mixed


def split_into_chunks(md_text: str) -> list[Chunk]:
    """Split Markdown at ## heading boundaries.

    Strategy:
    - Find all ATX headings via regex.
    - Body of each section = text between current heading and next heading.
    - Content before first heading = a synthetic "Introduction" chunk at depth 0.
    - Minimum body length 20 chars to skip empty/trivial sections.
    """
    headings = list(_HEADING_RE.finditer(md_text))
    chunks: list[Chunk] = []

    # Pre-heading content
    first_start = headings[0].start() if headings else len(md_text)
    preamble = md_text[:first_start].strip()
    if len(preamble) >= 20:
        chunks.append(Chunk(
            title="Introduction",
            body=preamble,
            depth=0,
            classification=classify_section("introduction", preamble),
        ))

    for i, m in enumerate(headings):
        depth = len(m.group(1))  # number of # chars
        title = m.group(2).strip()
        body_start = m.end()
        body_end = headings[i + 1].start() if i + 1 < len(headings) else len(md_text)
        body = md_text[body_start:body_end].strip()

        if len(body) < 20:
            continue  # skip headings with trivial bodies

        chunks.append(Chunk(
            title=title,
            body=body,
            depth=depth,
            classification=classify_section(title, body),
        ))

    return chunks


# ── Dedup ─────────────────────────────────────────────────────────────────────

def _tokenise(text: str) -> frozenset[str]:
    """Lowercase word tokens for Jaccard comparison."""
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard token-overlap. Returns 0.0 when both are empty."""
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def is_duplicate(candidate_text: str, existing_texts: list[str],
                 threshold: float = 0.8) -> bool:
    """Return True if candidate_text is Jaccard >= threshold with any existing text."""
    cand_tokens = _tokenise(candidate_text)
    for existing in existing_texts:
        if jaccard(cand_tokens, _tokenise(existing)) >= threshold:
            return True
    return False


# ── LLM extraction ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are a career data extractor. Given a section of someone's career narrative, "
    "extract career nuggets (roles, achievements, measurable impacts). "
    "Return a JSON array of objects with these fields: "
    '{"role": "...", "company": "...", "achievement": "...", "impact": "..."}. '
    "If no career information is present, return an empty array []. "
    "Return ONLY the JSON array, no commentary."
)


def _extract_nuggets_from_chunk(
    chunk: Chunk,
    llm_call_fn: Callable[[str, str], tuple[str, dict]],
) -> list[dict]:
    """Call LLM to extract nuggets from a single chunk. Returns list of dicts.

    On parse failure or empty result, returns []. Never raises — failures
    are logged to stderr and the chunk is skipped gracefully.
    """
    user_prompt = f"Section title: {chunk.title}\n\n{chunk.body}"
    try:
        text, _usage = llm_call_fn(_SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        print(f"  [markdown_ingest] LLM error for chunk '{chunk.title}': {e}",
              file=sys.stderr)
        return []

    # Strip markdown fences if LLM wrapped the JSON
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:])
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        if not isinstance(result, list):
            return []
        # Keep only dicts with at least one non-empty field
        nuggets = []
        for item in result:
            if isinstance(item, dict) and any(
                (item.get(k) or "").strip()
                for k in ("role", "company", "achievement", "impact")
            ):
                nuggets.append(item)
        return nuggets
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  [markdown_ingest] JSON parse failed for chunk '{chunk.title}': {e}",
              file=sys.stderr)
        return []


# ── Token budget guard (AC6) ──────────────────────────────────────────────────

# Conservative estimate: 1 token ≈ 4 chars.
# Groq free tier ≈ 14,400 RPD for llama-3.1-8b → effective ~6,000 calls/day budget.
# AC6: never exceed 50% of provider rate limit at any window.
# We enforce this by limiting chunk count per invocation.

_MAX_CHUNKS_PER_RUN = int(50)  # 50 LLM calls max per ingest run (~25% of hourly Groq limit)


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class IngestResult:
    """Summary of a single markdown ingest run."""
    chunks_total: int = 0
    chunks_career: int = 0
    chunks_personal_skipped: int = 0
    chunks_mixed: int = 0
    chunks_budget_truncated: int = 0  # chunks skipped because token budget was reached
    nuggets_extracted: int = 0
    nuggets_deduped: int = 0
    nuggets_added: int = 0
    llm_calls: int = 0
    new_nuggets: list[dict] = field(default_factory=list)


# ── Main entry point ──────────────────────────────────────────────────────────

def ingest_from_markdown(
    md_path: Path,
    profile_dir: Path,
    *,
    include_personal: bool = False,
    llm_call_fn: Optional[Callable[[str, str], tuple[str, dict]]] = None,
) -> IngestResult:
    """Parse a Markdown file and append new nuggets to the profile nugget store.

    Args:
        md_path:          Path to the .md file.
        profile_dir:      Profile directory (contains nuggets.jsonl etc.).
        include_personal: When True, personal-life sections are processed.
                          Default False (skip personal-life sections).
        llm_call_fn:      Optional LLM callable (system, user) → (text, usage).
                          Defaults to chat_with_fallback in DIRECT mode.
                          Inject a mock for tests — no real LLM calls.

    Returns:
        IngestResult with audit counts.
    """
    if llm_call_fn is None:
        # Import here to allow tests to bypass without LLM keys
        from ..llm.direct import chat_with_fallback as _fallback
        llm_call_fn = lambda sys_, usr: _fallback(  # noqa: E731
            sys_, usr, temperature=0.2, max_tokens=2000
        )

    md_text = md_path.read_text(encoding="utf-8", errors="replace")
    chunks = split_into_chunks(md_text)

    # Load existing nugget texts for dedup
    nuggets_path = profile_dir / "nuggets.jsonl"
    existing_texts: list[str] = []
    if nuggets_path.exists():
        for line in nuggets_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                n = json.loads(line)
                t = (n.get("nugget_text") or n.get("achievement") or
                     n.get("answer") or "").strip()
                if t:
                    existing_texts.append(t)
            except json.JSONDecodeError:
                pass

    result = IngestResult(chunks_total=len(chunks))
    llm_calls_this_run = 0
    new_nuggets: list[dict] = []

    for chunk in chunks:
        # Privacy gate
        if chunk.classification == "personal-life" and not include_personal:
            result.chunks_personal_skipped += 1
            continue

        # Token budget guard — check BEFORE counting as career/mixed so audit counts are accurate.
        # When budget is reached, all remaining non-personal chunks go to chunks_budget_truncated.
        if llm_calls_this_run >= _MAX_CHUNKS_PER_RUN:
            if result.chunks_budget_truncated == 0:
                # Print once — first time budget is hit
                print(
                    f"  [markdown_ingest] Token budget reached ({_MAX_CHUNKS_PER_RUN} LLM calls). "
                    "Remaining chunks skipped. Re-run to continue.",
                    file=sys.stderr,
                )
            result.chunks_budget_truncated += 1
            continue

        if chunk.classification == "career-relevant":
            result.chunks_career += 1
        else:  # mixed
            result.chunks_mixed += 1

        extracted = _extract_nuggets_from_chunk(chunk, llm_call_fn)
        llm_calls_this_run += 1
        result.llm_calls += 1
        result.nuggets_extracted += len(extracted)

        for nugget in extracted:
            candidate_text = (
                nugget.get("achievement") or
                nugget.get("impact") or
                nugget.get("role") or ""
            ).strip()

            if is_duplicate(candidate_text, existing_texts):
                result.nuggets_deduped += 1
                continue

            # Enrich with source provenance
            nugget["source"] = "markdown_ingest"
            nugget["source_file"] = str(md_path)
            nugget["source_section"] = chunk.title
            nugget["section_classification"] = chunk.classification
            # Normalise to nugget_text for compatibility with pipeline.py's nugget_key()
            nugget["nugget_text"] = candidate_text or (
                nugget.get("role") or nugget.get("company") or ""
            )

            new_nuggets.append(nugget)
            existing_texts.append(candidate_text)  # prevent intra-run dupes
            result.nuggets_added += 1

    result.new_nuggets = new_nuggets

    # Append new nuggets to nuggets.jsonl
    if new_nuggets:
        profile_dir.mkdir(parents=True, exist_ok=True)
        with open(nuggets_path, "a", encoding="utf-8") as f:
            for n in new_nuggets:
                row = {k: v for k, v in n.items()}
                row["has_embedding"] = False  # embeddings added by a separate step
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return result


def print_privacy_audit(result: IngestResult) -> None:
    """Print the end-of-run privacy audit log (AC7)."""
    print(f"\n{'─' * 56}")
    print(f"  Markdown Ingest — Privacy Audit")
    print(f"{'─' * 56}")
    print(f"  Sections total:          {result.chunks_total:>4}")
    print(f"  Sections processed:")
    print(f"    career-relevant:       {result.chunks_career:>4}")
    print(f"    mixed:                 {result.chunks_mixed:>4}")
    print(f"  Sections skipped (personal-life): {result.chunks_personal_skipped:>4}")
    if result.chunks_budget_truncated:
        print(f"  Sections skipped (budget limit): {result.chunks_budget_truncated:>4}")
    print(f"  LLM calls made:          {result.llm_calls:>4}")
    print(f"  Nuggets extracted:       {result.nuggets_extracted:>4}")
    print(f"  Nuggets deduped:         {result.nuggets_deduped:>4}")
    print(f"  Nuggets added to store:  {result.nuggets_added:>4}")
    print(f"{'─' * 56}\n")
