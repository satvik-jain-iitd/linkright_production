"""Thin shim over the resume orchestrator's first three steps.

Why a shim and not a refactor: the orchestrator is 4400+ lines, mature, and
already supports module-level path repointing (resume/cli.py:tailor uses this
exact pattern). We re-point ``orchestrator.RUN_DIR / ARTIFACTS / INPUTS / LOG_PATH``
to the profile dir, call ``step_00..03`` as functions, and inherit all the
LLM-fallback / retry / telemetry plumbing for free.

After step_03 runs, ``persist()`` canonicalises the per-step artifacts into
profile-level files (``nuggets.jsonl``, ``embeddings.npz``, ``highlights.jsonl``,
``metadata.yaml``) plus copies the original PDF.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import yaml


PROFILE_DIR = Path.home() / ".linkright" / "profile"


def _profile_dir() -> Path:
    """Honour LINKRIGHT_HOME override (config.py respects it too)."""
    home = os.environ.get("LINKRIGHT_HOME")
    if home:
        return Path(home) / "profile"
    return PROFILE_DIR


def _stage_pdf(profile_dir: Path, src_pdf: Path) -> Path:
    """Copy resume.pdf into <profile>/inputs/. Returns the staged path."""
    inputs = profile_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    dst = inputs / "resume.pdf"
    if src_pdf.resolve() != dst.resolve():
        shutil.copy(src_pdf, dst)
    return dst


def _wipe(profile_dir: Path) -> None:
    """Move existing profile to a timestamped backup, then start fresh.

    Cleaner than rm -rf — gives the user a 7-day rollback window. The cli
    layer is responsible for asking for confirmation before calling this.
    """
    if not profile_dir.exists():
        return
    backup = profile_dir.with_name(
        profile_dir.name + ".backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    profile_dir.rename(backup)


def _sha256_of_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def nugget_key(n: dict) -> str:
    """Stable id for embeddings.npz lookup. Single canonical rule across the
    profile module so persist/refresh/delete/append all agree on the same key.

    Order: nugget_index (most stable, present in step_02 output) → nugget_text
    → answer (fallback for nuggets that came from website's narration flow,
    where the text field is named differently) → empty string (last resort).
    """
    if n.get("nugget_index") is not None:
        return str(n["nugget_index"])
    text = (n.get("nugget_text") or n.get("answer") or "").strip()
    return text[:200]


def parse_and_extract(resume_pdf: Path, profile_dir: Optional[Path] = None) -> dict:
    """Run orchestrator step_00 → step_01 → step_02 → step_03 against the PDF.

    Returns a dict with the artefact paths and the in-memory results — but
    the canonical write site is the artefacts/ directory (created by the
    orchestrator itself). Caller follows up with persist().
    """
    profile_dir = profile_dir or _profile_dir()
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Stage the PDF where step_00 will look for it.
    _stage_pdf(profile_dir, resume_pdf)

    # Re-point the orchestrator's module-level paths. Same pattern as
    # resume/cli.py:tailor (lines ~75-83). Must do this BEFORE importing
    # any step functions so they capture the new paths if needed — but in
    # the orchestrator the steps reference the module globals at call-time,
    # so import-then-reassign also works.
    from ..resume import orchestrator
    orchestrator.RUN_DIR = profile_dir
    orchestrator.ARTIFACTS = profile_dir / "artifacts"
    orchestrator.INPUTS = profile_dir / "inputs"
    orchestrator.LOG_PATH = profile_dir / "logs" / "pipeline.log"
    orchestrator.ARTIFACTS.mkdir(parents=True, exist_ok=True)
    orchestrator.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # step_00 reads orchestrator.INPUTS / "resume.pdf" and returns text.
    raw_text = orchestrator.step_00_ingest_pdf()
    parsed = orchestrator.step_01_parse_resume(raw_text)
    nuggets = orchestrator.step_02_extract_nuggets(raw_text, parsed)
    nuggets_with_emb = orchestrator.step_03_embed_nuggets(nuggets)

    return {
        "raw_text": raw_text,
        "parsed": parsed,
        "nuggets": nuggets_with_emb,  # list of dicts including 'emb' field
        "n_nuggets": len(nuggets_with_emb),
        "n_embedded": sum(1 for n in nuggets_with_emb if n.get("emb")),
    }


def persist(profile_dir: Path, source_pdf: Path, result: dict) -> None:
    """Write the four canonical files: nuggets.jsonl, embeddings.npz,
    highlights.jsonl, metadata.yaml.

    Only writes nuggets that have an embedding. Failed-embed nuggets are
    skipped from embeddings.npz but kept in nuggets.jsonl with `emb: null`
    so the user can still see them via ``profile show`` and re-embed later.
    """
    profile_dir = profile_dir or _profile_dir()
    nuggets = result.get("nuggets") or []

    # 1. nuggets.jsonl — strip embeddings, keep all other fields.
    with open(profile_dir / "nuggets.jsonl", "w", encoding="utf-8") as f:
        for n in nuggets:
            row = {k: v for k, v in n.items() if k != "emb"}
            row["has_embedding"] = bool(n.get("emb"))
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # 2. embeddings.npz — numpy file with parallel ids + vectors arrays.
    embedded = [n for n in nuggets if n.get("emb")]
    if embedded:
        ids = np.array([nugget_key(n) for n in embedded], dtype=object)
        vecs = np.array([n["emb"] for n in embedded], dtype=np.float32)
        np.savez(profile_dir / "embeddings.npz", ids=ids, vectors=vecs)
    else:
        # Empty placeholder — keeps consumers from crashing on .npz absence.
        np.savez(profile_dir / "embeddings.npz",
                 ids=np.array([], dtype=object), vectors=np.zeros((0, 384), dtype=np.float32))

    # 3. highlights.jsonl — P0/P1 importance subset (truth-engine-locked).
    # Day 1 (--yes mode): we treat all nuggets as locked. Day 2's truth-engine
    # loop will filter this set based on user Lock decisions.
    highlights = [n for n in nuggets if str(n.get("importance", "")).upper() in ("P0", "P1")]
    with open(profile_dir / "highlights.jsonl", "w", encoding="utf-8") as f:
        for n in highlights:
            row = {k: v for k, v in n.items() if k != "emb"}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # 4. metadata.yaml — embedder tier + dim + provenance.
    from ..resume.lib.embedder import _detect_tier
    tier = _detect_tier()
    dim = int(vecs.shape[1]) if embedded else 384
    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedder_tier": tier,
        "embedder_model": _embedder_model_for_tier(tier),
        "dim": dim,
        "source_pdf_sha256": _sha256_of_file(source_pdf),
        "n_nuggets": len(nuggets),
        "n_embedded": len(embedded),
        "n_highlights": len(highlights),
        "profile_version": 1,
    }
    with open(profile_dir / "metadata.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(meta, f, sort_keys=False)


def _embedder_model_for_tier(tier: str) -> str:
    """Reverse-lookup the model name for a given tier (best-effort string)."""
    return {
        "oracle": "nomic-embed-text",
        "fastembed": "BAAI/bge-small-en-v1.5",
        "sentence_transformers": os.environ.get("LR_ST_MODEL", "all-mpnet-base-v2"),
        "stub": "stub_sha256",
    }.get(tier, "unknown")


def load_metadata(profile_dir: Optional[Path] = None) -> Optional[dict]:
    """Read metadata.yaml. Returns None if profile doesn't exist."""
    profile_dir = profile_dir or _profile_dir()
    meta_path = profile_dir / "metadata.yaml"
    if not meta_path.exists():
        return None
    return yaml.safe_load(meta_path.read_text()) or {}


def load_nuggets(profile_dir: Optional[Path] = None) -> list[dict]:
    """Read nuggets.jsonl. Returns empty list if profile doesn't exist."""
    profile_dir = profile_dir or _profile_dir()
    p = profile_dir / "nuggets.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def load_embeddings(profile_dir: Optional[Path] = None) -> tuple[np.ndarray, np.ndarray]:
    """Read embeddings.npz. Returns (ids, vectors). Empty arrays if absent."""
    profile_dir = profile_dir or _profile_dir()
    p = profile_dir / "embeddings.npz"
    if not p.exists():
        return np.array([], dtype=object), np.zeros((0, 384), dtype=np.float32)
    data = np.load(p, allow_pickle=True)
    return data["ids"], data["vectors"]


# ── Contact info — Truth Engine Layer 1 (start) ────────────────────────────
# Per Jane 2026-05-02 (memory feedback_personal_details_verify_at_start):
# wrong contact info = silent failure (recruiter can't reach candidate).
# Verify each field with user at profile creation; never hallucinate.

_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().\-]{8,16}\d)")
_EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
_LINKEDIN_RE = re.compile(r"(?:linkedin\.com/(?:in|pub)/[\w\-]+)", re.IGNORECASE)
_PORTFOLIO_HINT_RE = re.compile(
    r"https?://(?!linkedin\.com)[\w\-]+(?:\.[\w\-]+)+(?:/[\w\-./?%&=#]*)?",
    re.IGNORECASE,
)


def _extract_contact_from_text(raw_text: str) -> dict:
    """Regex-extract contact fields from PDF raw text. Deterministic — no LLM,
    no fabrication. Returns best-guess dict; user verifies via
    contact_verify_loop. Empty fields ALWAYS empty (never invented).
    """
    text = raw_text or ""
    contact = {"phone": "", "email": "", "linkedin": "", "portfolio": "", "name": ""}

    m = _EMAIL_RE.search(text)
    if m:
        contact["email"] = m.group(0).strip().rstrip(".,;")

    m = _LINKEDIN_RE.search(text)
    if m:
        contact["linkedin"] = m.group(0).strip().rstrip("/")

    # Phone: prefer matches near top of resume (contact line typically header).
    head = text[:1500]
    m = _PHONE_RE.search(head) or _PHONE_RE.search(text)
    if m:
        # Strip trailing non-digit chars that the regex may have captured
        ph = re.sub(r"[\s().\-]+$", "", m.group(0).strip())
        # Avoid matching numbers like "100M+" or year ranges — require ≥9 digits
        if sum(c.isdigit() for c in ph) >= 9:
            contact["phone"] = ph

    # Portfolio: any non-LinkedIn URL in the top of doc
    for pm in _PORTFOLIO_HINT_RE.finditer(head):
        url = pm.group(0).rstrip(".,;)")
        if "linkedin.com" in url.lower() or "@" in url:
            continue
        contact["portfolio"] = url
        break

    # Name: first non-empty line of resume head, often "FirstName LastName"
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Heuristic: looks like a name if 2-4 words, capitalized, no @ or digits
        words = line.split()
        if (2 <= len(words) <= 4
                and not any(ch.isdigit() for ch in line)
                and "@" not in line
                and all(w[0].isupper() for w in words if w)):
            contact["name"] = line
            break

    return contact


def save_contact(profile_dir: Path, contact: dict) -> None:
    """Persist user-confirmed contact to `profile_dir/contact.yaml`."""
    path = profile_dir / "contact.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(contact, f, sort_keys=False)


def load_contact(profile_dir: Optional[Path] = None) -> dict:
    """Read user-confirmed contact. Returns empty dict if not present."""
    profile_dir = profile_dir or _profile_dir()
    path = profile_dir / "contact.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def contact_verify_loop(profile_dir: Optional[Path] = None,
                        raw_text_fallback: str = "") -> dict:
    """Interactive contact verification — Truth Engine Layer 1.

    Per Jane 2026-05-02 (memory feedback_personal_details_verify_at_start):
    Surface phone/email/LinkedIn/portfolio/name to user. User confirms each
    or types correction. Tool MUST NOT invent any value. Empty fields stay
    empty unless user types a value.

    Reads existing `contact.yaml` (if previously saved) — pre-fills defaults.
    Otherwise extracts via regex from raw resume text.
    """
    import questionary
    from rich.console import Console
    profile_dir = profile_dir or _profile_dir()
    console = Console()

    existing = load_contact(profile_dir)
    if not existing and raw_text_fallback:
        existing = _extract_contact_from_text(raw_text_fallback)
    elif not existing:
        # Try to read from cached step_01 raw text in profile/artifacts
        raw_path = profile_dir / "artifacts" / "00_resume_raw_text.txt"
        if raw_path.exists():
            existing = _extract_contact_from_text(raw_path.read_text(encoding="utf-8", errors="ignore"))
        else:
            existing = {"phone": "", "email": "", "linkedin": "", "portfolio": "", "name": ""}

    console.print()
    console.print("[bold cyan]📇 Contact Verification — Truth Engine Layer 1[/]")
    console.print("[dim]Confirm or correct each field. Wrong contact = recruiter can't reach you.[/]")
    console.print("[dim]Press Enter to accept current value; type a new value to override; type a single space + Enter to clear.[/]")
    console.print()

    confirmed: dict = {}
    fields = [
        ("name", "Full name"),
        ("phone", "Phone (with country code)"),
        ("email", "Email"),
        ("linkedin", "LinkedIn URL (e.g., linkedin.com/in/...)"),
        ("portfolio", "Portfolio URL (leave blank if none)"),
    ]
    for key, label in fields:
        default = (existing.get(key) or "").strip()
        try:
            ans = questionary.text(
                f"{label}:",
                default=default,
            ).ask()
        except KeyboardInterrupt:
            console.print("[red]Aborted by user (Ctrl+C). No changes saved.[/]")
            sys.exit(130)
        if ans is None:
            console.print("[red]Aborted. No changes saved.[/]")
            sys.exit(130)
        ans = ans.strip()
        # Single space = explicit clear
        if ans == "":
            confirmed[key] = ""
        else:
            confirmed[key] = ans

    save_contact(profile_dir, confirmed)
    console.print()
    console.print(f"[green]✓ Contact confirmed and saved to {profile_dir}/contact.yaml[/]")
    return confirmed


def _update_metadata(profile_dir: Path, patch: dict) -> None:
    meta_path = profile_dir / "metadata.yaml"
    if not meta_path.exists():
        return
    meta = yaml.safe_load(meta_path.read_text()) or {}
    meta.update(patch)
    with open(meta_path, "w") as f:
        yaml.safe_dump(meta, f, sort_keys=False)


def _patch_embeddings_for_edits(profile_dir: Path, nuggets: list[dict]) -> int:
    """Surgical update: replace vectors for nuggets carrying ``_new_emb``,
    preserving every other row in embeddings.npz.

    Why surgical: ``load_nuggets()`` returns rows from nuggets.jsonl which
    INTENTIONALLY strip the `emb` field (embeddings live in the .npz, not
    the jsonl). A naive "rebuild from in-memory nuggets" would lose all
    pre-existing vectors except the edited one.

    Returns count of rows actually patched.
    """
    ids, vectors = load_embeddings(profile_dir)
    if len(ids) == 0:
        return 0
    str_ids = np.array([str(x) for x in ids])
    patched = 0
    new_vectors = np.array(vectors, copy=True)
    for n in nuggets:
        new_emb = n.get("_new_emb")
        if not new_emb:
            continue
        key = nugget_key(n)
        mask = str_ids == key
        if mask.any():
            idx = int(np.where(mask)[0][0])
            new_vectors[idx] = np.array(new_emb, dtype=np.float32)
            patched += 1
    if patched:
        np.savez(
            profile_dir / "embeddings.npz",
            ids=np.array([str(x) for x in ids], dtype=object),
            vectors=new_vectors,
        )
    return patched


# ── Truth-engine interactive loop (Day 2) ────────────────────────────────────

def truth_engine_loop(profile_dir: Optional[Path] = None) -> dict:
    """Walk highlights interactively. User Locks, Skips, or Edits each.

    Mutates: highlights.jsonl (rewritten with locked-only), nuggets.jsonl +
    embeddings.npz (only if edits happened). Returns counts.

    Aborts with exit 130 on Ctrl+C (no partial state saved).
    """
    import questionary  # imported here so non-interactive paths don't pay the cost
    from rich.console import Console
    from rich.panel import Panel

    profile_dir = profile_dir or _profile_dir()
    highlights_path = profile_dir / "highlights.jsonl"
    if not highlights_path.exists():
        return {"locked": 0, "skipped": 0, "edited": 0}

    highlights = [json.loads(l) for l in highlights_path.read_text().splitlines() if l.strip()]
    if not highlights:
        return {"locked": 0, "skipped": 0, "edited": 0}

    console = Console()
    console.print()
    console.print(Panel(
        f"[bold]Truth engine[/] — {len(highlights)} highlights to confirm.\n\n"
        f"For each: [bold green]Lock[/] (keep as-is), "
        f"[bold yellow]Skip[/] (drop from highlights), or "
        f"[bold cyan]Edit[/] (correct text, re-embed).",
        title="Confirm what your career profile says about you",
        expand=False,
    ))

    nuggets = load_nuggets(profile_dir)

    locked: list[dict] = []
    n_skipped = 0
    n_edited = 0
    edits: dict[str, str] = {}

    for i, h in enumerate(highlights, 1):
        company = (h.get("company") or "").strip() or "(no company)"
        role = (h.get("role") or "").strip() or "(no role)"
        importance = (h.get("importance") or "").upper()
        text = (h.get("nugget_text") or h.get("answer") or "(empty)").strip()

        console.print()
        console.print(Panel(
            f"[bold]{company}[/]  |  [italic]{role}[/]  |  [yellow]{importance}[/]\n\n{text}",
            title=f"Highlight {i}/{len(highlights)}",
            expand=False,
        ))

        action = questionary.select(
            "Action?",
            choices=["Lock", "Skip", "Edit"],
            default="Lock",
        ).ask()

        if action is None:
            console.print("[yellow]Aborted — partial state NOT saved.[/]")
            import sys
            sys.exit(130)

        if action == "Lock":
            locked.append(h)
            continue

        if action == "Skip":
            n_skipped += 1
            continue

        new_text = questionary.text(
            "Corrected version:",
            default=text,
        ).ask()
        if not new_text or not new_text.strip():
            console.print("[yellow]Empty — treating as skip.[/]")
            n_skipped += 1
            continue

        new_text = new_text.strip()
        if new_text == text:
            locked.append(h)
            continue

        # Re-embed the corrected nugget. If embed fails, keep edit anyway —
        # has_embedding=False on the row; user can `profile refresh` later.
        from ..resume.lib.embedder import embed
        try:
            new_vec, _ = embed(new_text)
        except Exception:
            new_vec = None

        h_new = dict(h)
        h_new["nugget_text"] = new_text
        h_new["edited"] = True
        locked.append(h_new)
        edits[text] = new_text
        n_edited += 1

        for n in nuggets:
            if (n.get("nugget_text") or n.get("answer", "")).strip() == text:
                n["nugget_text"] = new_text
                if new_vec:
                    n["_new_emb"] = new_vec
                break

    # Rewrite highlights.jsonl
    with open(highlights_path, "w", encoding="utf-8") as f:
        for h in locked:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")

    # If edits, refresh nuggets.jsonl + surgical-patch embeddings.npz
    if edits:
        with open(profile_dir / "nuggets.jsonl", "w", encoding="utf-8") as f:
            for n in nuggets:
                row = {k: v for k, v in n.items() if k not in ("emb", "_new_emb")}
                row["has_embedding"] = bool(n.get("emb") or n.get("_new_emb"))
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        _patch_embeddings_for_edits(profile_dir, nuggets)

    _update_metadata(profile_dir, {"n_highlights": len(locked)})

    console.print()
    console.print(
        f"[green]✓[/] Truth engine done: "
        f"[green]{len(locked)} locked[/], "
        f"[yellow]{n_skipped} skipped[/], "
        f"[cyan]{n_edited} edited[/]"
    )
    return {"locked": len(locked), "skipped": n_skipped, "edited": n_edited}


# ── Delete-nugget interactive picker (Day 2) ────────────────────────────────

def delete_nugget_interactive(profile_dir: Optional[Path] = None) -> bool:
    """Interactive picker for deleting a single nugget. Mutates nuggets.jsonl,
    embeddings.npz, highlights.jsonl, metadata.yaml. Returns True on delete,
    False on cancel.
    """
    import questionary
    from rich.console import Console

    profile_dir = profile_dir or _profile_dir()
    nuggets = load_nuggets(profile_dir)
    console = Console()

    if not nuggets:
        console.print("[yellow]No nuggets in this profile.[/]")
        return False

    choices = []
    for i, n in enumerate(nuggets):
        company = (n.get("company") or "").strip()[:22] or "(no co)"
        role = (n.get("role") or "").strip()[:20]
        text = (n.get("nugget_text") or n.get("answer", "")).strip()[:80]
        importance = (n.get("importance") or "??").upper()
        label = f"[{importance:>2s}] {company:<22} | {role:<20} | {text}"
        choices.append(questionary.Choice(title=label, value=i))
    choices.append(questionary.Choice(title="(cancel)", value=-1))

    pick = questionary.select(
        f"Select nugget to delete (out of {len(nuggets)}):",
        choices=choices,
    ).ask()

    if pick is None or pick == -1:
        console.print("Cancelled.")
        return False

    target = nuggets[pick]
    target_key = nugget_key(target)
    target_preview = (
        target.get("nugget_text") or target.get("answer") or "(empty)"
    ).strip()[:120]

    if not questionary.confirm(
        f"Delete this nugget?\n   {target_preview}",
        default=False,
    ).ask():
        console.print("Cancelled.")
        return False

    new_nuggets = nuggets[:pick] + nuggets[pick + 1:]

    with open(profile_dir / "nuggets.jsonl", "w", encoding="utf-8") as f:
        for n in new_nuggets:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")

    ids, vectors = load_embeddings(profile_dir)
    if len(ids) > 0:
        # Coerce ids to str — older profiles persisted ids as int (1,2,3,...)
        # while nugget_key returns str. np ids != "1" would never match an int 1.
        keep_mask = np.array([str(x) != target_key for x in ids])
        new_ids_arr = np.array([str(x) for x in ids[keep_mask]], dtype=object)
        np.savez(
            profile_dir / "embeddings.npz",
            ids=new_ids_arr,
            vectors=vectors[keep_mask],
        )

    highlights_path = profile_dir / "highlights.jsonl"
    if highlights_path.exists():
        kept = []
        for line in highlights_path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if nugget_key(row) != target_key:
                kept.append(row)
        with open(highlights_path, "w") as f:
            for h in kept:
                f.write(json.dumps(h, ensure_ascii=False) + "\n")

    new_ids, _ = load_embeddings(profile_dir)
    # Count from highlights.jsonl (truth post-truth-engine), not from importance.
    n_high = 0
    if highlights_path.exists():
        n_high = sum(
            1 for line in highlights_path.read_text().splitlines() if line.strip()
        )
    _update_metadata(profile_dir, {
        "n_nuggets": len(new_nuggets),
        "n_embedded": len(new_ids),
        "n_highlights": n_high,
    })

    console.print(f"[green]✓[/] Deleted: {target_preview}")
    return True
