"""Enrich a nugget with 3 LLM-generated follow-ups → user answers → new nuggets.

Two LLM calls per enrich session:
  1. ``generate_followups(nugget)`` — returns 3 sharp follow-up questions.
  2. ``add_from_answer(parent, question, answer)`` — extracts a structured
     nugget from the user's free-text answer.

Both prompts vendored inline; small enough to live alongside callers. Sourced
from website routes (``/api/nuggets/follow-ups`` and ``/api/nuggets/add-from-answer``)
as of 2026-05-01.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from .pipeline import (
    _profile_dir,
    _update_metadata,
    load_embeddings,
    load_nuggets,
    nugget_key,
)


# ── Prompts ─────────────────────────────────────────────────────────────────

FOLLOWUP_SYSTEM = """You are an interviewer helping a candidate articulate the depth of one career achievement. Output strict JSON only — no preamble, no markdown fences."""

FOLLOWUP_USER = """Below is one career nugget. Generate exactly 3 short, sharp follow-up questions that — when answered — would reveal:
  1. The METRIC of impact (size, $, %, time saved, users, revenue, etc.)
  2. The METHOD or technique used (technical, process, leadership pattern)
  3. The HARDER thing this proves about the candidate (cross-functional credibility, depth, range)

Each question:
  - 1 sentence, no preamble
  - Specific to THIS nugget (NOT generic "tell me more")
  - Targets a fact the candidate likely knows but didn't write down

Output JSON exactly:
{{"questions": ["...", "...", "..."]}}

Nugget context:
  Company: {company}
  Role: {role}
  Nugget: {nugget_text}"""


EXTRACT_SYSTEM = """You extract ONE structured career nugget from a Q&A pair. Output strict JSON only — no preamble, no markdown fences."""

EXTRACT_USER = """The candidate was asked a follow-up question about their existing nugget. Their answer is below. Convert it into a fresh nugget that:
  - Is atomic (one achievement / fact, not a list)
  - Names the metric / method / proof concretely
  - Inherits company + role from the parent nugget
  - importance: "P0" if a numeric metric is named; "P1" if a method or proof is named but no metric; "P2" otherwise

Parent nugget (for context, do not repeat its text):
{parent_text}

Question asked:
{question}

User's answer:
{answer}

Output JSON exactly:
{{"nugget_text": "...", "company": "{company}", "role": "{role}", "importance": "P0|P1|P2", "type": "work_experience"}}"""


# ── Helpers ─────────────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """LLMs sometimes wrap JSON in ```json fences despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def generate_followups(nugget: dict) -> list[str]:
    """LLM call → 3 follow-up questions. Returns [] on failure."""
    from ..llm.direct import tier_chat
    company = (nugget.get("company") or "").strip() or "(no company)"
    role = (nugget.get("role") or "").strip() or "(no role)"
    nugget_text = (nugget.get("nugget_text") or nugget.get("answer", "")).strip()

    user_prompt = FOLLOWUP_USER.format(
        company=company, role=role, nugget_text=nugget_text,
    )
    try:
        text, _usage = tier_chat(
            system=FOLLOWUP_SYSTEM,
            user=user_prompt,
            klass="C",
            intent="enrich_generate_followups",
            temperature=0.5,
            max_tokens=400,
        )
    except Exception:
        return []

    try:
        data = json.loads(_strip_fences(text))
    except json.JSONDecodeError:
        return []

    qs = data.get("questions") or []
    return [str(q).strip() for q in qs if str(q).strip()][:3]


def extract_from_answer(parent: dict, question: str, answer: str) -> Optional[dict]:
    """LLM call → one structured nugget. Returns None on failure."""
    from ..llm.direct import tier_chat
    company = (parent.get("company") or "").strip()
    role = (parent.get("role") or "").strip()
    parent_text = (parent.get("nugget_text") or parent.get("answer", "")).strip()

    user_prompt = EXTRACT_USER.format(
        parent_text=parent_text,
        question=question,
        answer=answer,
        company=company,
        role=role,
    )
    try:
        text, _usage = tier_chat(
            system=EXTRACT_SYSTEM,
            user=user_prompt,
            klass="A",
            intent="enrich_extract_from_answer",
            temperature=0.3,
            max_tokens=300,
        )
    except Exception:
        return None

    try:
        data = json.loads(_strip_fences(text))
    except json.JSONDecodeError:
        return None

    if not data.get("nugget_text"):
        return None

    data.setdefault("company", company)
    data.setdefault("role", role)
    data.setdefault("importance", "P2")
    data.setdefault("type", "work_experience")
    return data


def append_nuggets(profile_dir: Path, new_nuggets: list[dict]) -> int:
    """Embed each new nugget, append to nuggets.jsonl, embeddings.npz,
    and highlights.jsonl (when P0/P1). Updates metadata counts.

    Each new nugget gets a fresh ``nugget_index`` (max-existing + 1, +2, ...)
    so it stays addressable by the same canonical key the rest of the module
    uses (see ``pipeline.nugget_key``).

    Returns count of nuggets that received an embedding.
    """
    from ..resume.lib.embedder import embed

    existing = load_nuggets(profile_dir)
    existing_max = 0
    for n in existing:
        try:
            existing_max = max(existing_max, int(n.get("nugget_index", 0)))
        except (TypeError, ValueError):
            continue

    embedded_count = 0
    rows_to_write: list[dict] = []
    for offset, new in enumerate(new_nuggets, 1):
        text = (new.get("nugget_text") or "").strip()
        if not text:
            continue
        rec = dict(new)
        rec.setdefault("nugget_index", existing_max + offset)
        try:
            vec, _meta = embed(text)
        except Exception:
            vec = None
        if vec:
            rec["_emb"] = vec
            embedded_count += 1
        rows_to_write.append(rec)

    if not rows_to_write:
        return 0

    with open(profile_dir / "nuggets.jsonl", "a", encoding="utf-8") as f:
        for rec in rows_to_write:
            row = {k: v for k, v in rec.items() if k != "_emb"}
            row["has_embedding"] = bool(rec.get("_emb"))
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    new_ids = [nugget_key(r) for r in rows_to_write if r.get("_emb")]
    new_vecs = [r["_emb"] for r in rows_to_write if r.get("_emb")]
    if new_vecs:
        ids, vectors = load_embeddings(profile_dir)
        combined_ids = (
            np.concatenate([ids, np.array(new_ids, dtype=object)])
            if len(ids) > 0 else np.array(new_ids, dtype=object)
        )
        combined_vecs = (
            np.vstack([vectors, np.array(new_vecs, dtype=np.float32)])
            if len(vectors) > 0 else np.array(new_vecs, dtype=np.float32)
        )
        np.savez(profile_dir / "embeddings.npz", ids=combined_ids, vectors=combined_vecs)

    new_highlights = [
        r for r in rows_to_write
        if str(r.get("importance", "")).upper() in ("P0", "P1")
    ]
    if new_highlights:
        highlights_path = profile_dir / "highlights.jsonl"
        with open(highlights_path, "a", encoding="utf-8") as f:
            for h in new_highlights:
                row = {k: v for k, v in h.items() if k != "_emb"}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    final_nuggets = load_nuggets(profile_dir)
    final_ids, _ = load_embeddings(profile_dir)
    # Count from highlights.jsonl directly — that file is the truth
    # post-truth-engine (Skipped P0/P1 nuggets aren't in there). Importance
    # field alone over-counts skipped highlights.
    highlights_path = profile_dir / "highlights.jsonl"
    n_high_total = 0
    if highlights_path.exists():
        n_high_total = sum(
            1 for line in highlights_path.read_text().splitlines() if line.strip()
        )
    _update_metadata(profile_dir, {
        "n_nuggets": len(final_nuggets),
        "n_embedded": len(final_ids),
        "n_highlights": n_high_total,
    })
    return embedded_count


# ── End-to-end enrich session ───────────────────────────────────────────────

def enrich_session(profile_dir: Optional[Path] = None, nugget_id: Optional[str] = None) -> dict:
    """Pick a nugget (or use given id), generate 3 follow-ups, accept user
    answers, extract one new nugget per answered question, persist.

    Returns counts dict.
    """
    import questionary
    from rich.console import Console
    from rich.panel import Panel
    from linkright.ui import step_start, step_done, step_error, step_warn, step_detail, section_header, lr_text, TEAL

    profile_dir = profile_dir or _profile_dir()
    nuggets = load_nuggets(profile_dir)
    console = Console()

    if not nuggets:
        console.print("[yellow]No nuggets to enrich. Run `linkright profile create` first.[/]")
        return {"questions": 0, "answers": 0, "new_nuggets": 0}

    target = _resolve_target_nugget(nuggets, nugget_id, console)
    if target is None:
        return {"questions": 0, "answers": 0, "new_nuggets": 0}

    target_text = (target.get("nugget_text") or target.get("answer", "")).strip()
    company = (target.get("company") or "").strip()
    role = (target.get("role") or "").strip()

    console.print()
    console.print(Panel(
        f"[bold]{company or '(no company)'}[/]  |  "
        f"[italic]{role or '(no role)'}[/]\n\n{target_text}",
        title="Enriching this nugget",
        expand=False,
    ))

    step_start("Generating follow-up questions", accent=TEAL)
    questions = generate_followups(target)
    if not questions:
        step_error("LLM failed to generate follow-up questions.")
        return {"questions": 0, "answers": 0, "new_nuggets": 0}

    step_done(f"{len(questions)} follow-up(s) generated")

    new_nuggets_to_add: list[dict] = []
    answered = 0
    for q_idx, q in enumerate(questions, 1):
        section_header(f"Q{q_idx}", accent=TEAL)
        console.print(f"  {q}\n")
        answer = lr_text("Your answer (blank = skip):", accent=TEAL)
        if answer is None:
            console.print("[yellow]Aborted.[/]")
            break
        if not answer.strip():
            continue
        answered += 1
        new = extract_from_answer(target, q, answer.strip())
        if new:
            new["parent_nugget_text"] = target_text
            new_nuggets_to_add.append(new)
            step_detail(f"extracted: {new.get('nugget_text', '')[:120]}")
        else:
            step_warn("extraction failed — answer not added")

    if not new_nuggets_to_add:
        console.print("\n[yellow]No new nuggets added.[/]")
        return {"questions": len(questions), "answers": answered, "new_nuggets": 0}

    embedded_count = append_nuggets(profile_dir, new_nuggets_to_add)
    console.print(
        f"\n[green]✓[/] Added {len(new_nuggets_to_add)} new nugget(s) "
        f"({embedded_count} embedded)."
    )
    return {
        "questions": len(questions),
        "answers": answered,
        "new_nuggets": len(new_nuggets_to_add),
    }


def _resolve_target_nugget(nuggets: list[dict], nugget_id: Optional[str], console) -> Optional[dict]:
    """Either by id (numeric index OR nugget_index field) or via questionary picker."""
    import questionary

    if nugget_id is not None:
        # Try integer index first
        try:
            idx = int(nugget_id)
            if 0 <= idx < len(nuggets):
                return nuggets[idx]
        except ValueError:
            pass
        # Try nugget_index field match
        for n in nuggets:
            if str(n.get("nugget_index")) == str(nugget_id):
                return n
        console.print(f"[red]No nugget found for id={nugget_id}.[/]")
        return None

    # Interactive picker
    from linkright.ui import lr_select, TEAL
    choices = []
    for i, n in enumerate(nuggets):
        company = (n.get("company") or "").strip()[:22] or "(no co)"
        text = (n.get("nugget_text") or n.get("answer", "")).strip()[:80]
        importance = (n.get("importance") or "??").upper()
        label = f"[{importance:>2s}] {company:<22} | {text}"
        choices.append(questionary.Choice(title=label, value=i))
    choices.append(questionary.Choice(title="(cancel)", value=-1))

    pick = lr_select(f"Pick a nugget to enrich ({len(nuggets)} total):", choices=choices, accent=TEAL)
    if pick is None or pick == -1:
        console.print("Cancelled.")
        return None
    return nuggets[pick]
