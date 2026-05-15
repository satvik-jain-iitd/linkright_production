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

    # Bug #12 — long-document safety net: warn if raw text is very long.
    # Does NOT truncate or refuse — user can self-remediate. 15000 chars ≈ 3750
    # tokens (conservative estimate), which approaches LLM context limits for
    # small free-tier models. Warn early so the user knows why extraction may
    # be incomplete if the LLM drops trailing content silently.
    _RAW_TEXT_WARN_CHARS = 15000
    if raw_text and len(raw_text) > _RAW_TEXT_WARN_CHARS:
        print(
            f"⚠ Document is long ({len(raw_text)} chars). If extraction is incomplete, "
            "consider shortening your resume or using a trimmed plain-text version.",
            file=sys.stderr,
        )

    parsed = orchestrator.step_01_parse_resume(raw_text)
    nuggets = orchestrator.step_02_extract_nuggets(raw_text, parsed)

    # PC-9: Post-extraction fabrication guard — flag nuggets whose company name
    # does NOT appear anywhere in the raw resume text (simple string containment).
    # LLMs occasionally hallucinate company names from few-shot examples; this
    # catches the symptom without blocking the pipeline.
    _raw_lower = (raw_text or "").lower()
    for _i, _n in enumerate(nuggets):
        _co = (_n.get("company") or "").strip()
        if _co and _co.lower() not in ("none", "null", ""):
            if _co.lower() not in _raw_lower:
                print(
                    f"⚠ Possible fabrication detected in nugget {_i} — "
                    f"company '{_co}' not found in resume text. Review carefully.",
                    file=sys.stderr,
                )

    nuggets_with_emb = orchestrator.step_03_embed_nuggets(nuggets)

    # UAT Cluster D — pre-persist hardening on the freshly extracted batch.
    # Order matters:
    #   1. Entity resolution first (#27) — fills "unknown" company/role
    #      using parsed-resume headers, so the classification step (#25)
    #      can correctly bucket work_experience nuggets that the LLM left
    #      ambiguous.
    #   2. Classification (#25) — stamps nugget_class on every row.
    #   3. Gap flag (#28) — surfaces missing fields for the CLI to prompt
    #      the user (when interactive); attaches a non-persisted list to
    #      the result dict.
    # These steps NEVER delete a nugget — only enrich existing rows.
    from .nugget_utils import (
        resolve_entity,
        classify_in_place,
        gap_filling_targets,
        _is_missing,
    )
    for nug in nuggets_with_emb:
        # resolve_entity returns a copy; copy back ONLY the entity fields
        # that started missing on the input. Preserves the orchestrator's
        # "emb" field and never overwrites an LLM-set company/role.
        if _is_missing(nug.get("company")) or _is_missing(nug.get("role")):
            resolved = resolve_entity(nug, parsed=parsed, raw_text=raw_text)
            if _is_missing(nug.get("company")) and resolved.get("company"):
                nug["company"] = resolved["company"]
            if _is_missing(nug.get("role")) and resolved.get("role"):
                nug["role"] = resolved["role"]
            if resolved.get("_entity_resolved_by"):
                nug["_entity_resolved_by"] = resolved["_entity_resolved_by"]
    classify_in_place(nuggets_with_emb)
    gaps = gap_filling_targets(nuggets_with_emb)

    return {
        "raw_text": raw_text,
        "parsed": parsed,
        "nuggets": nuggets_with_emb,  # list of dicts including 'emb' field
        "n_nuggets": len(nuggets_with_emb),
        "n_embedded": sum(1 for n in nuggets_with_emb if n.get("emb")),
        "gaps": gaps,  # UAT #28 — caller (CLI) decides whether to prompt user
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

    # UAT #26 — write nuggets ordered by priority (P0 → P1 → P2 → P3 →
    # unknown). Stable sort preserves LLM-output order within each
    # bucket, so the user sees their most-recent-extraction's strongest
    # achievements at the top of `profile show`. Note: highlights.jsonl
    # gets the same treatment below.
    # UAT #25 — also ensure nugget_class is stamped on the persisted row;
    # parse_and_extract() runs classify_in_place(), but a defensive second
    # pass here means load_nuggets() always sees a populated class field
    # even if a future caller bypasses parse_and_extract().
    from .nugget_utils import sort_by_priority, classify_in_place
    classify_in_place(nuggets)
    nuggets = sort_by_priority(nuggets)

    # 1. nuggets.jsonl — strip embeddings + transient audit-trail fields.
    # LOW fix (cycle-2): `_entity_resolved_by` is an in-memory debugging
    # signal from #27 fallback resolution; persisting it bloats every
    # nugget row with a permanent diagnostic flag. Keep it in-memory
    # only — re-running audit will re-set it when needed.
    _TRANSIENT_KEYS = {"emb", "_entity_resolved_by"}
    with open(profile_dir / "nuggets.jsonl", "w", encoding="utf-8") as f:
        for n in nuggets:
            row = {k: v for k, v in n.items() if k not in _TRANSIENT_KEYS}
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
    #
    # UAT #26 — highlights are already in priority order because the
    # parent `nuggets` list was sorted above. sort_by_priority is stable,
    # so within the P0 bucket we preserve LLM extraction order.
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
    """Return nugget-shaped dicts for legacy consumers.

    Phase 4 (Memory v2): facts.jsonl is the canonical source. When present,
    return Facts converted to legacy nugget shape via the adapter
    (profile/legacy_adapter.py). Falls back to nuggets.jsonl only when v2
    facts are absent — preserves any pre-onboard dev profile that was
    created via the old `profile create` flow.

    Existing consumers (orchestrator.py, coverletter/pipeline.py,
    jd_matcher.py, profile_facts.py) keep working without code changes.
    """
    profile_dir = profile_dir or _profile_dir()

    # v2 path: derive nuggets from facts.jsonl
    from .legacy_adapter import facts_as_nuggets, has_v2_facts
    if has_v2_facts(profile_dir):
        return facts_as_nuggets(profile_dir)

    # Legacy fallback: read nuggets.jsonl directly
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

from .regex_extract import (
    extract_email as _regex_extract_email,
    extract_phone as _regex_extract_phone,
)

_LINKEDIN_RE = re.compile(r"(?:linkedin\.com/(?:in|pub)/[\w\-]+)", re.IGNORECASE)
_PORTFOLIO_HINT_RE = re.compile(
    r"https?://(?!linkedin\.com)[\w\-]+(?:\.[\w\-]+)+(?:/[\w\-./?%&=#]*)?",
    re.IGNORECASE,
)


def _extract_contact_from_text(raw_text: str) -> dict:
    """Regex-extract contact fields from PDF raw text. Deterministic — no LLM,
    no fabrication. Returns best-guess dict; user verifies via
    contact_verify_loop. Empty fields ALWAYS empty (never invented).

    Email / phone regex live in ``regex_extract.py`` (single source of truth,
    shared with the orchestrator's truth-engine reconciliation step for
    UAT bug #13). LinkedIn / portfolio / name heuristics remain local
    because they are profile-create-specific.
    """
    text = raw_text or ""
    contact = {"phone": "", "email": "", "linkedin": "", "portfolio": "", "name": ""}

    contact["email"] = _regex_extract_email(text)
    contact["phone"] = _regex_extract_phone(text)

    m = _LINKEDIN_RE.search(text)
    if m:
        contact["linkedin"] = m.group(0).strip().rstrip("/")

    # Portfolio: any non-LinkedIn URL in the top of doc (header region).
    head = text[:1500]
    for pm in _PORTFOLIO_HINT_RE.finditer(head):
        url = pm.group(0).rstrip(".,;)")
        if "linkedin.com" in url.lower() or "@" in url:
            continue
        contact["portfolio"] = url
        break

    # Name: first non-empty line of resume head, often "FirstName LastName"
    # UAT bug #5: lines like "Dear Satvik Jain" or "Mr. John Doe" passed the
    # name heuristic (capitalized, 2-4 words, no digits/@) and got stored as
    # the candidate's name. Strip common greeting/honorific prefixes before
    # the heuristic check.
    # Polish PR: extended with regional honorifics (Thiru — Tamil Mr.) and
    # religious / honour titles (Rev., Fr., Sis., Hon., Late). These all
    # modify the SAME PERSON named on the line, so stripping is safe.
    _GREETING_PREFIXES = (
        "dear ", "hi ", "hello ", "greetings ",
        "mr. ", "mr ", "mrs. ", "mrs ", "ms. ", "ms ",
        "dr. ", "dr ", "prof. ", "prof ",
        "sir ", "madam ", "to: ", "to ", "respected ",
        "shri ", "shrimati ", "smt. ", "smt ",
        "thiru ", "thiruvalar ",
        "rev. ", "rev ", "fr. ", "fr ", "sis. ", "sis ",
        "hon. ", "hon ", "honorable ", "honourable ",
        "late ",
    )

    # Polish PR adversarial review (AR-1, blocker fix): relationship-marker
    # lines name a DIFFERENT person (father/mother/husband of the candidate),
    # not the candidate themselves. Stripping the prefix and storing the
    # remainder would store the wrong person's name (data integrity bug).
    # These lines must be SKIPPED entirely during candidate-name extraction.
    _REJECT_LINE_PREFIXES = (
        "s/o ", "s/o.", "son of ",
        "d/o ", "d/o.", "daughter of ",
        "w/o ", "w/o.", "wife of ",
        "h/o ", "h/o.", "husband of ",
        "father's name", "father name",
        "mother's name", "mother name",
        "spouse's name", "spouse name",
    )

    def _is_relationship_line(s: str) -> bool:
        low = s.lower()
        return any(low.startswith(p) for p in _REJECT_LINE_PREFIXES)

    def _strip_greeting(s: str) -> str:
        low = s.lower()
        for pref in _GREETING_PREFIXES:
            if low.startswith(pref):
                return s[len(pref):].strip()
        return s

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip relationship-marker lines (S/o, D/o, W/o, etc.) — these name
        # a relative of the candidate, not the candidate themselves.
        if _is_relationship_line(line):
            continue
        candidate = _strip_greeting(line)
        # Heuristic: looks like a name if 2-4 words, capitalized, no @ or digits
        words = candidate.split()
        if (2 <= len(words) <= 4
                and not any(ch.isdigit() for ch in candidate)
                and "@" not in candidate
                and all(w[0].isupper() for w in words if w)):
            contact["name"] = candidate
            break

    return contact


def save_contact(profile_dir: Path, contact: dict) -> None:
    """Persist user-confirmed contact to `profile_dir/contact.yaml`."""
    path = profile_dir / "contact.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
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

    Per feedback_personal_details_verify_at_start: surface phone/email/LinkedIn/
    portfolio/name to user. User confirms each or types correction. Tool MUST NOT
    invent any value. Empty fields stay empty unless user types a value.

    UI pattern (mirrors Claude Code AskUserQuestion style):
    - Phase 1: collect all fields with pre-filled defaults
    - Phase 2: review panel → select-to-edit any single field → back to review
    This gives true per-field forward/backward navigation without questionary
    back-nav (which questionary does not natively support).

    Reads existing `contact.yaml` (if previously saved) — pre-fills defaults.
    Otherwise extracts via regex from raw resume text.
    """
    from InquirerPy.base.control import Choice as IQChoice
    from rich.console import Console
    from rich.panel import Panel
    from linkright.ui import (
        lr_text, lr_select, step_done, section_header,
        TEAL as _TEAL, GOLD as _GOLD, CORAL as _CORAL,
    )
    from linkright.ui.theme import LR_THEME
    _DIM = "dim"
    profile_dir = profile_dir or _profile_dir()
    console = Console(theme=LR_THEME)

    existing = load_contact(profile_dir)
    if not existing and raw_text_fallback:
        existing = _extract_contact_from_text(raw_text_fallback)
    elif not existing:
        raw_path = profile_dir / "artifacts" / "00_resume_raw_text.txt"
        if raw_path.exists():
            existing = _extract_contact_from_text(raw_path.read_text(encoding="utf-8", errors="ignore"))
        else:
            existing = {"phone": "", "email": "", "linkedin": "", "portfolio": "", "name": ""}

    fields = [
        ("name",      "Full name"),
        ("phone",     "Phone (with country code)"),
        ("email",     "Email"),
        ("linkedin",  "LinkedIn URL"),
        ("portfolio", "Portfolio URL (blank if none)"),
    ]
    _label = dict(fields)

    console.print()
    console.print(Panel(
        f"[{_TEAL}]Wrong contact → recruiter can't reach you.[/]\n"
        f"[{_DIM}]Press Enter to accept • type to override • space+Enter to clear[/]",
        title="[bold]📇 Contact Details[/]",
        border_style=_TEAL,
        expand=False,
    ))
    console.print()

    # ── Phase 1: initial collection with pre-filled defaults ─────────────────
    confirmed: dict = {}
    for key, label in fields:
        default = (existing.get(key) or "").strip()
        try:
            ans = lr_text(f"{label}:", default=default, accent=_TEAL)
        except KeyboardInterrupt:
            console.print(f"[{_CORAL}]Aborted (Ctrl+C). No changes saved.[/]")
            sys.exit(130)
        if ans is None:
            console.print(f"[{_CORAL}]Aborted. No changes saved.[/]")
            sys.exit(130)
        confirmed[key] = ans.strip()

    # ── Phase 2: review + per-field select-to-edit loop ─────────────────────
    # Mirrors Claude Code AskUserQuestion: numbered panel → pick field to edit
    # → single text prompt → back to review. "✓ All correct" = confirm.
    while True:
        console.print()
        rows = []
        for i, (key, label) in enumerate(fields, 1):
            val = confirmed.get(key) or ""
            display = val if val else f"[{_DIM}](blank)[/]"
            rows.append(f"  [{_GOLD}]{i}.[/]  {label:<30} [{_TEAL}]{display}[/]")
        console.print(Panel(
            "\n".join(rows),
            title="[bold]Review — select a field to edit or confirm[/]",
            border_style=_TEAL,
            expand=False,
        ))

        _CONFIRM = "__confirm__"
        choices = [IQChoice(name="✓  All correct — save and continue", value=_CONFIRM)]
        for key, label in fields:
            val = confirmed.get(key) or "(blank)"
            choices.append(IQChoice(name=f"   Edit: {label}  [{val}]", value=key))

        try:
            # NOTE (UAT cluster-E3 cycle 2, HIGH #1): this picker INTENTIONALLY
            # keeps `lr_select` (not `lr_select_with_custom`). Every field
            # (name / phone / email / linkedin / portfolio) is already
            # addressable as its own "Edit: …" row — adding a "Type something…"
            # row would be redundant and ambiguous (which field would the
            # free-text apply to?). Fixed numbered list also preserves muscle
            # memory across sessions.
            action = lr_select("Action:", choices=choices, accent=_TEAL)
        except KeyboardInterrupt:
            console.print(f"[{_CORAL}]Aborted (Ctrl+C). No changes saved.[/]")
            sys.exit(130)
        if action is None or action == _CONFIRM:
            break

        # Edit exactly one field → back to review panel
        label = _label[action]
        current = confirmed.get(action) or ""
        try:
            new_val = lr_text(f"{label}:", default=current, accent=_TEAL)
        except KeyboardInterrupt:
            # Ctrl+C on edit → cancel the edit, return to review (don't exit)
            console.print(f"[{_DIM}]Edit cancelled — back to review.[/]")
            continue
        if new_val is not None:
            confirmed[action] = new_val.strip()

    save_contact(profile_dir, confirmed)
    console.print()
    step_done("Contact saved")
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
    from rich.console import Console
    from rich.panel import Panel
    from linkright.ui import lr_select, lr_text, step_done, step_warn, TEAL as _TEAL, CORAL as _CORAL
    from linkright.ui.theme import LR_THEME

    profile_dir = profile_dir or _profile_dir()
    highlights_path = profile_dir / "highlights.jsonl"
    if not highlights_path.exists():
        return {"locked": 0, "skipped": 0, "edited": 0}

    highlights = [json.loads(l) for l in highlights_path.read_text().splitlines() if l.strip()]
    if not highlights:
        return {"locked": 0, "skipped": 0, "edited": 0}

    console = Console(theme=LR_THEME)
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

        # UAT cluster-E3 cycle 2 (HIGH #1): use lr_select_with_custom so the
        # user can press "Type something…" to jump straight into the corrected
        # text without first navigating to the Edit option. We distinguish
        # picker-cancel (Esc on the menu — should abort the whole session) from
        # a blank type-something (just re-prompt the same highlight) by using
        # the lower-level lr_select first and only invoking the custom branch
        # explicitly. This preserves the Esc-aborts-session contract.
        from linkright.ui import (
            lr_select as _lr_select,
            TYPE_SOMETHING,
            TYPE_SOMETHING_LABEL,
        )
        action = _lr_select(
            "Action?",
            choices=["Lock", "Skip", "Edit", TYPE_SOMETHING_LABEL],
            accent=_TEAL,
        )

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

        if action == TYPE_SOMETHING_LABEL:
            # Type-something fast-path → user types correction immediately.
            typed = lr_text("Type your correction:", default=text, accent=_TEAL)
            if typed is None or not str(typed).strip():
                # Blank → treat as Skip-and-keep-as-is rather than session abort
                locked.append(h)
                continue
            new_text = str(typed).strip()
        else:
            # action == "Edit"
            new_text = lr_text("Corrected version:", default=text, accent=_TEAL)
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
    from InquirerPy.base.control import Choice as IQChoice
    from rich.console import Console
    from linkright.ui.theme import LR_THEME

    profile_dir = profile_dir or _profile_dir()
    nuggets = load_nuggets(profile_dir)
    console = Console(theme=LR_THEME)

    if not nuggets:
        console.print("[yellow]No nuggets in this profile.[/]")
        return False

    # UAT cluster-E3 cycle 2 (HIGH #1): wired through lr_select_with_custom
    # so the user can type a free-text query to filter nuggets when the list
    # is too long to scroll. Mirrors the enrich-nugget picker pattern.
    from linkright.ui import lr_select_with_custom, lr_confirm, TEAL
    _CANCEL_SENTINEL = "__delete_cancel__"

    def _build_delete_choices(pool: list[dict]) -> list:
        c = []
        for i, n in enumerate(pool):
            company = (n.get("company") or "").strip()[:22] or "(no co)"
            role = (n.get("role") or "").strip()[:20]
            text = (n.get("nugget_text") or n.get("answer", "")).strip()[:80]
            importance = (n.get("importance") or "??").upper()
            label = f"[{importance:>2s}] {company:<22} | {role:<20} | {text}"
            c.append(IQChoice(name=label, value=f"idx:{i}"))
        c.append(IQChoice(name="(cancel)", value=_CANCEL_SENTINEL))
        return c

    pool = list(nuggets)
    target = None
    while target is None:
        pick = lr_select_with_custom(
            f"Select nugget to delete ({len(pool)} total):",
            choices=_build_delete_choices(pool),
            accent=TEAL,
            custom_prompt="Search nuggets by company / role / text:",
        )
        if pick is None or pick == _CANCEL_SENTINEL:
            console.print("Cancelled.")
            return False
        if isinstance(pick, str) and pick.startswith("idx:"):
            try:
                idx = int(pick[4:])
            except ValueError:
                idx = -1
            if 0 <= idx < len(pool):
                target = pool[idx]
                break
            pool = list(nuggets)
            continue
        # Free-text search → filter and re-prompt
        q = pick.strip().lower()
        filtered = [
            n for n in nuggets
            if q in (n.get("company") or "").lower()
            or q in (n.get("role") or "").lower()
            or q in (n.get("nugget_text") or n.get("answer") or "").lower()
        ]
        if not filtered:
            console.print(f"[yellow]No nuggets match '{pick.strip()}'. Showing full list.[/]")
            pool = list(nuggets)
        else:
            pool = filtered
    # The legacy `pick` variable downstream expected an int index into the
    # original `nuggets` list — recover it from `target` so the slice ops
    # below stay correct without further refactoring.
    pick = nuggets.index(target)
    target_key = nugget_key(target)
    target_preview = (
        target.get("nugget_text") or target.get("answer") or "(empty)"
    ).strip()[:120]

    if not lr_confirm(
        f"Delete this nugget?\n   {target_preview}",
        default=False,
        accent=TEAL,
    ):
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


# ── Batch review loop (Phase 2) ──────────────────────────────────────────────

def batch_review_loop(nuggets: list[dict]) -> tuple[list[dict], list[dict]]:
    """Walk ALL nuggets interactively for pre-persist human review.

    For each nugget the user chooses:
      [K]eep    — accept as-is
      [E]dit    — type a correction (free text)
      [D]rop    — mark for removal
      [S]kip    — accept all remaining nuggets without review

    Corrections and drops are collected in memory; NO LLM call per correction.
    After the loop (or user skip), a summary is shown and the user must
    confirm "Finalize?" before the function returns.

    Returns:
        (original_nuggets, corrections_list)

    where ``corrections_list`` is a list of dicts::

        {"nugget_id": str, "action": "edit"|"drop", "correction_text": str|None}

    ``nugget_id`` is the stable nugget_key() for the row.
    """
    from rich.console import Console
    from rich.panel import Panel
    from linkright.ui import lr_text, lr_select, step_done, TEAL as _TEAL, CORAL as _CORAL
    from linkright.ui.theme import LR_THEME

    console = Console(theme=LR_THEME)

    if not nuggets:
        return nuggets, []

    console.print()
    console.print(Panel(
        f"[bold]Batch Review[/] — {len(nuggets)} nugget(s) extracted.\n\n"
        f"For each: [bold green]Keep[/] (accept), "
        f"[bold cyan]Edit[/] (correct text), "
        f"[bold red]Drop[/] (remove), or "
        f"[bold yellow]Skip all[/] (accept remaining as-is).",
        title="[bold]Review Extracted Nuggets[/]",
        border_style=_TEAL,
        expand=False,
    ))

    corrections: list[dict] = []
    skip_remaining = False

    for i, nugget in enumerate(nuggets, 1):
        if skip_remaining:
            break

        company = (nugget.get("company") or "").strip() or "(no company)"
        role = (nugget.get("role") or "").strip() or "(no role)"
        importance = (nugget.get("importance") or "??").upper()
        # Handle both `answer` (PDF pipeline) and `nugget_text` (markdown ingest)
        text = (nugget.get("answer") or nugget.get("nugget_text") or "(empty)").strip()
        section = (nugget.get("source_section") or "").strip()

        body_lines = [
            f"[bold]{company}[/]  |  [italic]{role}[/]  |  [yellow]{importance}[/]",
            "",
            text,
        ]
        if section:
            body_lines.append(f"\n[dim]Section: {section}[/]")

        console.print()
        console.print(Panel(
            "\n".join(body_lines),
            title=f"[bold]Nugget {i}/{len(nuggets)}[/]",
            border_style=_TEAL,
            expand=False,
        ))

        action = lr_select(
            "Action?",
            choices=["Keep", "Edit", "Drop", "Skip all remaining"],
            accent=_TEAL,
        )

        if action is None:
            console.print(f"[{_CORAL}]Aborted (Ctrl+C). No changes applied.[/]")
            import sys
            sys.exit(130)

        nid = nugget_key(nugget)

        if action == "Keep":
            continue
        elif action == "Drop":
            corrections.append({"nugget_id": nid, "action": "drop", "correction_text": None})
        elif action == "Edit":
            new_text = lr_text("Corrected version:", default=text, accent=_TEAL)
            if new_text is None:
                console.print(f"[{_CORAL}]Aborted (Ctrl+C). No changes applied.[/]")
                import sys
                sys.exit(130)
            new_text = new_text.strip()
            if not new_text:
                console.print("[dim]Empty text — keeping original.[/]")
            elif new_text != text:
                corrections.append({"nugget_id": nid, "action": "edit", "correction_text": new_text})
        elif action == "Skip all remaining":
            skip_remaining = True

    # Summary
    n_keep = len(nuggets) - sum(1 for c in corrections if c["action"] == "edit") - sum(1 for c in corrections if c["action"] == "drop")
    n_edit = sum(1 for c in corrections if c["action"] == "edit")
    n_drop = sum(1 for c in corrections if c["action"] == "drop")

    console.print()
    console.print(Panel(
        f"  [green]Kept:[/]    {n_keep}\n"
        f"  [cyan]Edited:[/]  {n_edit}\n"
        f"  [red]Dropped:[/] {n_drop}",
        title="[bold]Review Summary[/]",
        border_style=_TEAL,
        expand=False,
    ))

    from linkright.ui import lr_confirm
    confirmed = lr_confirm("Finalize?", default=True, accent=_TEAL)
    if not confirmed:
        console.print("[dim]Review cancelled — no changes applied.[/]")
        return nuggets, []

    step_done("Review complete")
    return nuggets, corrections


# ── Apply corrections via LLM (Phase 3) ──────────────────────────────────────

def apply_corrections_llm(nuggets: list[dict], corrections: list[dict]) -> list[dict]:
    """Apply batch corrections via ONE LLM call.

    Called only when ``corrections`` is non-empty (caller's responsibility).

    The LLM receives:
    - All original nuggets serialised as JSON
    - All corrections from Phase 2 (edit text or drop)
    - Instructions to: apply edits, apply drops, normalise company names
      globally (if user edited "Amex" → "American Express", apply globally),
      extract structured start_date/end_date from source_section strings like
      "(April 2022 -- April 2023)", and ALWAYS output the `answer` field
      (never `nugget_text`).

    Returns the corrected nugget list in standard schema (``answer`` field).
    Falls back to a deterministic apply (no LLM) if the LLM call fails,
    so the pipeline is never blocked by an LLM outage.
    """
    import json as _json

    # Build system + user prompts
    _SYSTEM = (
        "You are a career-data editor. You receive a JSON list of career nuggets and a list "
        "of corrections requested by the user. Apply EVERY correction exactly as specified. "
        "Rules:\n"
        "1. For action='edit': replace the nugget's answer text with correction_text.\n"
        "2. For action='drop': remove the nugget from the output list entirely.\n"
        "3. Company normalisation: if the user edited a company name (e.g. 'Amex' → "
        "'American Express') in ANY nugget, apply that same normalisation to ALL nuggets "
        "that share the original company name.\n"
        "4. Date extraction: if source_section contains a date range like "
        "'(April 2022 -- April 2023)' or '(Jan 2020 - Dec 2021)', extract start_date and "
        "end_date fields (format: YYYY-MM) and add them to the nugget.\n"
        "5. Field normalisation: ALWAYS output 'answer' (never 'nugget_text'). "
        "Preserve all other fields (company, role, importance, type, id, nugget_index, etc.).\n"
        "6. Output ONLY a valid JSON array of corrected nuggets. No commentary, no markdown "
        "fences, no explanation."
    )

    # Strip embeddings (large, not needed by LLM) before serialising
    _TRANSIENT = {"emb", "_entity_resolved_by", "_new_emb"}
    nuggets_for_llm = [
        {k: v for k, v in n.items() if k not in _TRANSIENT}
        for n in nuggets
    ]

    _user = (
        f"NUGGETS:\n{_json.dumps(nuggets_for_llm, ensure_ascii=False, indent=2)}\n\n"
        f"CORRECTIONS:\n{_json.dumps(corrections, ensure_ascii=False, indent=2)}\n\n"
        "Apply all corrections and return the corrected nuggets as a JSON array."
    )

    try:
        from ..llm.direct import tier_chat, extract_json, LLMError
        raw, _usage = tier_chat(
            system=_SYSTEM,
            user=_user,
            klass="B",
            intent="profile_apply_corrections",
            temperature=0.1,
            max_tokens=8000,
        )
        cleaned = extract_json(raw)
        result = _json.loads(cleaned)
        if not isinstance(result, list):
            raise ValueError(f"LLM returned {type(result).__name__}, expected list")

        # Post-process: normalise nugget_text → answer for any row the LLM
        # accidentally left with the old field name.
        for n in result:
            if "nugget_text" in n and "answer" not in n:
                n["answer"] = n.pop("nugget_text")
            elif "nugget_text" in n:
                # Both present — keep answer, drop nugget_text
                del n["nugget_text"]

        return result

    except Exception as e:
        import sys as _sys
        print(
            f"⚠ LLM correction call failed ({e}); "
            "applying corrections deterministically instead.",
            file=_sys.stderr,
        )
        return _apply_corrections_deterministic(nuggets, corrections)


def _apply_corrections_deterministic(
    nuggets: list[dict], corrections: list[dict]
) -> list[dict]:
    """Deterministic fallback: apply edits/drops without LLM.

    Used when apply_corrections_llm()'s LLM call fails. Also handles
    company-name normalisation heuristically (exact string match on original
    company field).

    Always outputs `answer` field (never `nugget_text`).
    """
    # Build a lookup by nugget_key → correction
    correction_map: dict[str, dict] = {c["nugget_id"]: c for c in corrections}

    # First pass: identify company renames (action='edit' that also changed company)
    # We detect this by comparing the original company in the nugget vs what the
    # user may have typed. Since deterministic mode doesn't parse semantic intent
    # from free text, we look for edits that are PURELY a company-name change
    # (answer text unchanged). This is a best-effort heuristic only.
    # Full normalisation lives in the LLM path; here we just apply the edit text.
    company_renames: dict[str, str] = {}
    for nid, corr in correction_map.items():
        if corr["action"] != "edit":
            continue
        # Find the original nugget
        orig = next((n for n in nuggets if nugget_key(n) == nid), None)
        if orig is None:
            continue
        orig_company = (orig.get("company") or "").strip()
        new_text = (corr.get("correction_text") or "").strip()
        # Heuristic: if the correction is exactly a company name (short, no verb),
        # treat it as a company rename. This is intentionally conservative.
        if orig_company and new_text and len(new_text.split()) <= 5:
            orig_answer = (orig.get("answer") or orig.get("nugget_text") or "").strip()
            if new_text != orig_answer:
                # Likely a company rename correction
                company_renames[orig_company] = new_text

    result = []
    for n in nuggets:
        nid = nugget_key(n)
        corr = correction_map.get(nid)

        if corr and corr["action"] == "drop":
            continue  # drop this nugget

        # Start from a copy; normalise answer field
        row = dict(n)
        # Normalise: always use answer, remove nugget_text
        if "nugget_text" in row and "answer" not in row:
            row["answer"] = row.pop("nugget_text")
        elif "nugget_text" in row:
            del row["nugget_text"]

        if corr and corr["action"] == "edit":
            row["answer"] = corr["correction_text"] or row.get("answer", "")

        # Apply any company renames globally
        current_company = (row.get("company") or "").strip()
        if current_company in company_renames:
            row["company"] = company_renames[current_company]

        result.append(row)

    return result


# ── Markdown ingest (S3.4) — re-exported here for CLI import convenience ─────
# Full implementation in markdown_ingest.py. Importing via pipeline.py keeps
# the CLI's import surface consistent with other profile operations.

from .markdown_ingest import (  # noqa: E402,F401
    ingest_from_markdown,
    print_privacy_audit,
    IngestResult,
)
