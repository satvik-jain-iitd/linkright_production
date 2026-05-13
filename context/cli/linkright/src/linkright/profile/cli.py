"""`linkright profile {create,show,delete-nugget,enrich,refresh,rebuild}`.

Day 1 ships `create` (auto-lock-all `--yes` mode, no truth-engine UI yet)
and the read-only `show`/`status` commands. Day 2 fills in the interactive
truth-engine flow + management mutations.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import click

from ..cli_aliases import AliasedGroup
from .pipeline import (
    PROFILE_DIR,
    _profile_dir,
    _wipe,
    parse_and_extract,
    persist,
    load_metadata,
    load_nuggets,
    truth_engine_loop,
    delete_nugget_interactive,
    contact_verify_loop,
    load_contact,
    ingest_from_markdown,
    print_privacy_audit,
)


@click.group(cls=AliasedGroup, name="profile")
def profile_group() -> None:
    """User profile — one-time creation, persistent reuse across runs.

    \b
    Quick aliases:
      ec  → edit-contact      n  → delete-nugget
      e   → enrich            r  → refresh

    Tip: prefix matching works. `linkright profile sh` → show, `cr` → create.
    """


def _is_interactive() -> bool:
    """True when stdin appears to be an interactive TTY.

    Wrapped so tests (and CliRunner-driven flows) can stub the answer
    without monkey-patching sys.stdin (which click.testing.CliRunner
    forcibly replaces during invoke()).
    """
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


# ── UAT bug #6 — resume sanity heuristic ───────────────────────────────────

# Resume-shaped keyword stems. Cycle 2 reviewer noted that some short stems
# (e.g. "intern") were substring-matching against unrelated words
# ("international", "internal"), giving free hits on cover letters that
# mentioned "international team". Matches are now word-boundary regex
# (see `_keyword_hits()` below) — the stems below are bare tokens, no
# trailing space hack needed.
_RESUME_KEYWORDS = (
    # Sections / structural keywords found in essentially every resume.
    "experience", "employment", "education", "skills", "summary",
    "objective", "achievements", "projects", "certifications",
    "work history", "professional experience", "career history",
    "technical skills", "publications", "languages", "training",
    # Date / role-cue stems that scream "resume" without being section labels.
    "intern", "responsible for", "led", "managed", "designed",
    "developed", "built", "shipped", "engineered",
)

# Cover-letter giveaway phrases. Cycle 2 reviewer B3: the old heuristic gave a
# cover letter with contact info in the header an easy pass (email + phone hit
# automatically; keyword density got over the bar via "international",
# "managed", etc.). These phrases NEVER appear in a real resume but are
# essentially universal in cover letters. Each hit short-circuits to "not a
# resume" — no override budget, no escape via 3/4 signals.
_COVER_LETTER_SIGNALS = (
    "dear hiring",
    "dear sir",
    "dear madam",
    "dear recruiter",
    "to whom it may concern",
    "i am writing to",
    "i am writing in",
    "please find attached",
    "please find enclosed",
    "my qualifications",
    "sincerely,",
    "yours truly",
    "yours sincerely",
    "yours faithfully",
    "best regards,",
    "kind regards,",
)

# Email / phone regex — repeated here instead of importing from
# profile.pipeline because that module imports orchestrator (heavy);
# we want the sanity check to stay zero-cost on import.
import re as _re_uat6
_EMAIL_RE_UAT6 = _re_uat6.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
_PHONE_RE_UAT6 = _re_uat6.compile(r"(?:\+?\d[\d\s().\-]{8,16}\d)")


def _keyword_hits(low: str) -> int:
    """Count distinct word-boundary keyword matches.

    `re.search(r"\\bX\\b", low)` rather than substring `X in low` —
    "intern" no longer matches "international", "internal", "internet",
    and "led" no longer matches "schedule", "scheduled".
    """
    n = 0
    for kw in _RESUME_KEYWORDS:
        # `\b` only treats `\w`+ as word boundaries; multi-word keywords like
        # "work history" naturally bracket on the outer letters.
        if _re_uat6.search(rf"\b{_re_uat6.escape(kw)}\b", low):
            n += 1
    return n


def _cover_letter_signal_count(low: str) -> int:
    """Count distinct cover-letter giveaway phrases present in the text.

    Cycle 3 / MED false-reject fix: cycle 2 treated ANY single hit as a
    hard veto. Realistic false-rejects observed:
      - Resumes with a quoted testimonial: "Best regards, John — VP at X"
      - Summary sections that say "my qualifications include …"
      - Recommendation-letter excerpts pasted inline
    Returning a count (not a boolean) lets the caller distinguish a stray
    quote from a real cover letter (which always has 2+ distinct
    giveaways — opener + closer at minimum).
    """
    return sum(1 for sig in _COVER_LETTER_SIGNALS if sig in low)


def _looks_like_cover_letter(low: str) -> bool:
    """Backwards-compat shim: kept for any caller that imported the old name.

    Cycle 3: cover-letter detection is no longer a binary veto inside
    `_looks_like_resume`; new callers should use `_cover_letter_signal_count`.
    """
    return _cover_letter_signal_count(low) >= 2


def _read_text_for_sanity(path: Path) -> str:
    """Return up to ~30 KB of plain text from the resume file for keyword
    matching. PDF: use pypdf (already a required dep); MD: read directly.
    Best-effort — any extraction failure returns "" and the caller treats
    that as inconclusive (passes the heuristic to avoid false-rejecting
    files we can't peek at).
    """
    suffix = path.suffix.lower()
    try:
        if suffix in (".md", ".markdown", ".txt"):
            return path.read_text(encoding="utf-8", errors="replace")[:30000]
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError:
                return ""
            reader = PdfReader(str(path))
            # Limit to first 5 pages — a real resume has its keyword density
            # there; certificate PDFs that DO leak some text on page 6 won't
            # game the check.
            pages_text: list[str] = []
            for p in reader.pages[:5]:
                try:
                    pages_text.append(p.extract_text() or "")
                except Exception:
                    continue
            return "\n".join(pages_text)[:30000]
    except Exception:
        return ""
    return ""


def _looks_like_resume(path: Path) -> tuple[bool, list[str]]:
    """Return (is_resume_like, missing_signals).

    Heuristic — scores 4 positive signals: keyword presence (≥3 distinct
    hits, word-boundary), email regex, phone regex, minimum length
    (≥400 chars). Cover-letter giveaway phrases ("Dear Hiring Manager",
    "Sincerely,", "I am writing to", "please find attached", etc.) are
    tracked as a *soft* missing-signal (subtracts one from the pass
    count). A real resume must pass ≥3 of 4 signals after the
    cover-letter penalty.

    Cycle 3 / MED false-reject fix: cycle 2 treated ANY single
    cover-letter phrase as a hard veto. Realistic false-rejects:
      - Resumes with quoted testimonials ("Best regards, John — VP at X")
      - Summary sections that say "my qualifications include …"
      - Recommendation-letter excerpts pasted inline
    The hard veto is gone; instead:

      - 1 cover-letter phrase  → no penalty (likely a stray quote)
      - 2+ distinct phrases    → counts as ONE missing signal (the
                                 ≥3-of-4 threshold then catches the
                                 realistic cover-letter case via low
                                 keyword density)

    A real cover letter typically has BOTH an opener ("Dear …" / "To
    whom it may concern") AND a closer ("Sincerely," / "Yours truly,"),
    so the ≥2 threshold catches the realistic case while leaving room
    for an embedded quote on a resume. The override prompt remains the
    escape hatch when users disagree.
    """
    text = _read_text_for_sanity(path)
    if not text:
        # Couldn't extract anything → don't block; the downstream PDF
        # readability guard already catches truly corrupt files.
        return (True, [])
    low = text.lower()

    keyword_hits = _keyword_hits(low)
    has_email = bool(_EMAIL_RE_UAT6.search(text))
    has_phone = bool(_PHONE_RE_UAT6.search(text))
    long_enough = len(text) >= 400
    cover_hits = _cover_letter_signal_count(low)
    cover_letter_like = cover_hits >= 2

    positive_signals = sum([
        keyword_hits >= 3,
        has_email,
        has_phone,
        long_enough,
    ])
    # Cover-letter detection is now a SOFT missing-signal — subtract one
    # from the pass count when 2+ giveaway phrases are present. Realistic
    # cover letters: header contact (+email +phone +length) → 3/4 raw,
    # minus 1 for cover-letter signal → 2/4 → fails ≥3 threshold. Real
    # resume with one embedded "Best regards, John" testimonial quote:
    # cover_hits == 1 → no penalty, full 4/4 pass.
    effective_signals = max(0, positive_signals - (1 if cover_letter_like else 0))

    missing: list[str] = []
    if keyword_hits < 3:
        missing.append(
            f"only {keyword_hits} resume-shaped keyword(s) "
            f"(expected ≥3 like 'experience', 'education', 'skills')"
        )
    if not has_email:
        missing.append("no email address detected")
    if not has_phone:
        missing.append("no phone number detected")
    if not long_enough:
        missing.append(f"very short ({len(text)} chars — most resumes are ≥400)")
    if cover_letter_like:
        # Surface the actual hits so the override prompt is informative
        # ("missing: looks like a cover letter (sincerely + dear hiring)").
        _hit_phrases = [sig for sig in _COVER_LETTER_SIGNALS if sig in low]
        missing.append(
            "looks like a cover letter — multiple cover-letter phrases "
            f"present ({', '.join(_hit_phrases[:4])}"
            f"{', …' if len(_hit_phrases) > 4 else ''})"
        )

    return (effective_signals >= 3, missing)


def _prompt_resume_lookalike_override(path: Path, reasons: list[str]) -> bool:
    """Interactive warning when the file doesn't pass the resume heuristic.

    Returns True if the user wants to continue anyway, False to cancel.
    Power users get override; non-resume files (certificates, cover
    letters pasted by mistake) get caught before 30-90s of pipeline work.
    """
    try:
        from linkright.ui import lr_confirm, console as _con, TEAL
    except Exception:
        # UI primitives missing (e.g. truncated install) — fall back to
        # click.confirm so we still gate the bad path.
        click.echo(
            f"⚠ The file '{path.name}' does not look like a resume:", err=True
        )
        for r in reasons:
            click.echo(f"  • {r}", err=True)
        return click.confirm("Continue anyway?", default=False)

    _con.print()
    _con.print(
        f"[step.warn]⚠[/]  [bold]'{path.name}' does not look like a resume.[/]"
    )
    for r in reasons:
        _con.print(f"     [text.secondary]→[/]  {r}")
    _con.print(
        "     [text.secondary]A certificate PDF / cover letter / random doc "
        "will produce a garbage profile.[/]"
    )
    return bool(lr_confirm("Continue anyway?", default=False, accent=TEAL))


# ── UAT bug #9 — interactive overwrite picker ──────────────────────────────

def _prompt_overwrite_existing(profile_dir: Path) -> str:
    """Show an overwrite picker when a profile already exists.

    Returns one of: "keep" | "overwrite" | "view".
    Power users still have `--force` for non-interactive overwrite.

    Paste-to-existing-profile routes through this same picker (keep /
    overwrite / view). Appending paste content to an existing profile
    is deferred to a future cluster — adding a 4th picker option here
    was a cycle-2 scope creep that introduced regressions; the UX
    surprise risk of an additive option that silently mutates an
    otherwise-trusted profile is non-trivial and needs its own design
    pass.
    """
    try:
        from linkright.ui import lr_select, console as _con, TEAL
        import questionary

        _con.print()
        _con.print(
            f"[step.warn]⚠[/]  [bold]A profile already exists at[/] "
            f"[text.secondary]{profile_dir}[/]"
        )

        choices = [
            questionary.Choice(
                "Keep existing (cancel) — leave my profile untouched",
                value="keep",
            ),
            questionary.Choice(
                "Overwrite — wipe and re-ingest from this resume "
                "(existing data backed up to .backup-<ts>)",
                value="overwrite",
            ),
            questionary.Choice(
                "View existing first — show my current profile, then exit so I can decide",
                value="view",
            ),
        ]
        picked = lr_select(
            "What would you like to do?",
            choices=choices,
            accent=TEAL,
            hint="Enter to select  ·  ↑↓ to navigate  ·  Esc to cancel",
        )
        valid = {"keep", "overwrite", "view"}
        # Esc / Ctrl+C / cancellation defaults to the safe option (keep).
        return picked if picked in valid else "keep"
    except Exception:
        # UI helpers unavailable — fall back to click prompt.
        click.echo(f"Profile already exists at {profile_dir}.")
        click.echo("  [1] Keep existing (cancel)")
        click.echo("  [2] Overwrite (wipe + re-ingest)")
        click.echo("  [3] View existing first")
        choice = click.prompt(
            "Choose [1/2/3]", type=click.Choice(["1", "2", "3"]), default="1"
        )
        return {"1": "keep", "2": "overwrite", "3": "view"}[choice]


def _write_markdown_only_metadata(profile_dir: Path, ingest_result, *, source_hint: str) -> None:
    """Write / update metadata.yaml for the markdown-only / paste / augment paths.

    Cycle 2 / B1: prior to this commit, the `--from-paste` (and picker-paste)
    branches called `ingest_from_markdown` to append nuggets but NEVER wrote
    `metadata.yaml`. Every downstream guard (`profile show` / `status` /
    `tailor` / `enrich` / `graph` / `delete-nugget` / `edit-contact`)
    short-circuits on `(profile_dir / "metadata.yaml").exists()` and reports
    "No profile found." Result: user pastes resume → ingestion runs 30-90s
    → user is stuck with an unusable half-built profile.

    Cycle 3 / HIGH regression fix: the augment-of-existing-PDF-profile path
    (`--from-markdown` against an existing profile) was clobbering the
    existing profile's `embedder_tier`, `embedder_model`, `dim`, and
    `created_at` with live-detected values. Concrete failure mode: a
    profile created on Oracle (`tier=oracle, model=nomic-embed-text,
    dim=768`) gets augmented in an env without Oracle env vars — live
    detection returns fastembed (`dim=384`) — metadata flips to fastembed
    BUT the existing `embeddings.npz` still holds 768-dim vectors. The
    next `resume tailor` reads the (wrong) tier label and either fails
    the cache-tier check or silently runs the wrong embedder.

    Branching is mandatory:

    - **New profile** (`metadata.yaml` does not exist): write all fields
      fresh, including live-detected `embedder_tier` / `embedder_model`
      / `dim`. `created_at = now`, `n_nuggets = n_added`,
      `source = source_hint`.

    - **Augment / append** (`metadata.yaml` exists): only ever bump
      `n_nuggets` (additive) and stamp `last_updated`. `source` is left
      alone if already set; only filled in if absent (preserves PDF-side
      `source_pdf_sha256` semantics). NEVER touch `embedder_tier`,
      `embedder_model`, `dim`, `created_at`, or `profile_version` —
      those describe the underlying vector store, not the augment event.
    """
    from datetime import datetime, timezone
    import yaml as _yaml

    n_added = int(getattr(ingest_result, "nuggets_added", 0) or 0)
    meta_path = profile_dir / "metadata.yaml"

    if meta_path.exists():
        # ── Augment / append on existing profile ────────────────────────
        # Preserve everything the original `persist()` / first-create
        # wrote. Only bump counts + stamp last_updated.
        try:
            existing = _yaml.safe_load(meta_path.read_text()) or {}
        except Exception:
            existing = {}

        meta = dict(existing)
        meta["n_nuggets"] = int(existing.get("n_nuggets", 0) or 0) + n_added
        meta["last_updated"] = datetime.now(timezone.utc).isoformat()
        # Backfill `source` ONLY if missing (don't overwrite PDF-created
        # profiles' `source_pdf_sha256`-equivalent provenance).
        if "source" not in existing or not existing.get("source"):
            meta["source"] = source_hint
        # NEVER mutate: embedder_tier, embedder_model, dim, created_at,
        # profile_version. They describe the vector store on disk.

        profile_dir.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            _yaml.safe_dump(meta, f, sort_keys=False)
        return

    # ── New profile (no prior metadata.yaml) ────────────────────────────
    # Safe to live-detect everything; nothing on disk to contradict.
    from .pipeline import _embedder_model_for_tier
    try:
        from ..resume.lib.embedder import _detect_tier
        _tier = _detect_tier()
    except Exception:
        _tier = "unknown"
    try:
        _model = _embedder_model_for_tier(_tier)
    except Exception:
        _model = "unknown"

    now = datetime.now(timezone.utc).isoformat()
    meta = {
        "created_at": now,
        "embedder_tier": _tier,
        "embedder_model": _model,
        # Markdown ingest skips embeddings — embedder_tier is captured for
        # downstream `tailor` code that resolves which model to compare
        # against, but `dim` defaults to the conventional 384 when no
        # vector exists.
        "dim": 384,
        "n_nuggets": n_added,
        "n_embedded": 0,           # markdown_ingest doesn't embed
        "n_highlights": 0,
        "profile_version": 1,
        "source": source_hint,     # "paste" | "markdown-file"
        "last_updated": now,
    }
    profile_dir.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        _yaml.safe_dump(meta, f, sort_keys=False)


def _offer_enrich(profile_dir: Path) -> None:
    """Offer one round of deep enrichment after truth-engine completes.

    Non-blocking: Ctrl+C or "Skip" exits cleanly. Any nuggets added are
    persisted immediately inside enrich_session. Caller does not need to
    re-run persist().
    """
    import questionary
    from rich.console import Console
    from rich.panel import Panel
    from linkright.ui.theme import LR_THEME

    _TEAL = "#0FBEAF"
    console = Console(theme=LR_THEME)

    nuggets = load_nuggets(profile_dir)
    if not nuggets:
        return

    console.print()
    console.print(Panel(
        f"[{_TEAL}]Deep Enrichment[/] — pick one achievement and answer 3 follow-up questions.\n"
        "Each answer becomes a new nugget with richer detail → better resume tailoring.\n"
        "[dim]Takes ~30–60 sec per nugget. You can run more later: `linkright profile enrich`[/]",
        title="[bold]Optional: Deepen an Achievement[/]",
        border_style=_TEAL,
        expand=False,
    ))

    try:
        from linkright.ui import lr_confirm, TEAL
        do_enrich = lr_confirm("Add depth to a nugget now?", default=False, accent=TEAL)
    except KeyboardInterrupt:
        console.print("[dim]Enrichment skipped (Ctrl+C).[/]")
        return
    if not do_enrich:
        return

    try:
        from .enrich import enrich_session
        enrich_session(profile_dir)
    except KeyboardInterrupt:
        console.print("[dim]Enrichment cancelled — profile saved as-is.[/]")
    except Exception as e:
        console.print(f"[dim]Enrichment failed: {e} — profile saved as-is.[/]")


# ── create ──────────────────────────────────────────────────────────────────

@profile_group.command("create")
@click.option("--resume", "-r", "resume_path", type=click.Path(exists=True, path_type=Path),
              required=False, help="(optional) Path to resume PDF — prompted if omitted.")
@click.option("--paste", "paste", is_flag=True,
              help="(legacy) Interactive paste mode flag — alias for --from-paste.")
@click.option("--from-paste", "from_paste", is_flag=True,
              help="Drop into a paste editor (Esc+Enter to submit) and ingest the text as a markdown resume.")
@click.option("--from-folder", "from_folder", type=click.Path(exists=True, file_okay=False, path_type=Path),
              required=False, help="(optional) Folder to auto-detect first PDF.")
@click.option("--from-markdown", "from_markdown", type=click.Path(exists=True, path_type=Path),
              required=False, help="Path to a Markdown career narrative to ingest into the profile.")
@click.option("--include-personal", "include_personal", is_flag=True,
              help="Include personal-life sections (skipped by default for privacy).")
@click.option("--yes", is_flag=True, help="Skip truth-engine confirmation; auto-lock all extracted nuggets.")
@click.option("--force", is_flag=True, help="Overwrite existing profile without confirmation.")
def create_cmd(resume_path, paste, from_paste, from_folder, from_markdown, include_personal, yes, force) -> None:
    """One-time: parse resume, extract nuggets, embed, persist to ~/.linkright/profile/.

    Run with no flags to be prompted for the resume source (file or paste).
    Pass -r / --from-paste / --from-folder / --from-markdown to skip the prompt.
    """
    if not yes and sys.stdout.isatty():
        from linkright.ui import lr_banner
        from linkright import __version__ as _ver
        lr_banner(version=_ver)
    profile_dir = _profile_dir()

    # Treat legacy --paste as alias for --from-paste (UAT bug #11).
    # The flag previously dead-ended at "Day 2 — coming soon"; now it routes
    # through the same paste-editor path as the interactive picker.
    if paste:
        from_paste = True

    # Determine whether a PDF resume pipeline is needed.
    # --from-markdown alone is valid (markdown-only ingest, no PDF required).
    _markdown_only = (
        from_markdown
        and not resume_path
        and not from_folder
        and not from_paste
    )

    # If no source flag given, prompt interactively (file / paste).
    # UAT bug #11: paste is now a first-class third option in the picker;
    # the legacy "Day 2 coming soon" stub is gone. Folder mode stays
    # available via --from-folder (power-user flag, hidden from picker).
    if (
        not resume_path
        and not from_paste
        and not from_folder
        and not _markdown_only
    ):
        from linkright.prompts import prompt_for_resume_source
        kind, value = prompt_for_resume_source()
        if kind == "file":
            resume_path = value
        elif kind == "paste":
            from_paste = True
            _paste_text = value  # captured here, materialised below
        else:
            # Cycle 2 / LOW-10: previous dead branch (`from_folder = value`)
            # is unreachable — prompt_for_resume_source only returns
            # "file" or "paste". A future picker change that adds a third
            # kind would silently route here; fail loudly instead.
            raise RuntimeError(
                f"prompt_for_resume_source returned unexpected kind {kind!r}; "
                "update create_cmd to handle the new branch."
            )

    # Paste-text collection (B1+B2 cycle 2 refactor)
    # ===========================================================
    # Earlier cycle materialised the paste text into a temp .md file IMMEDIATELY
    # — before the existing-profile / overwrite-picker guard. Two consequences:
    #
    #   1. PII leak (B2): the tempfile dir was never cleaned up. Users who
    #      cancelled at the overwrite picker still left their full resume
    #      text on disk indefinitely.
    #   2. Wasted work: even when the user picked "Keep" we'd already
    #      written the file.
    #
    # Cycle 2 deferral: only collect + materialise the text AFTER the
    # overwrite picker has been resolved (or there's no existing profile to
    # worry about). The materialised file lives inside a try/finally that
    # cleans up on every exit path.
    #
    # We capture the raw paste text NOW (the prompt is synchronous and the
    # user's input is gone if we defer the prompt), but we DO NOT yet
    # write it to disk. The materialise+ingest happens later, gated by
    # the overwrite decision.
    if from_paste:
        if "_paste_text" not in locals():
            # `--from-paste` flag path — picker didn't run; collect text now.
            from linkright.prompts import prompt_for_paste_block
            _paste_text = prompt_for_paste_block(
                "Paste your resume text below (Esc + Enter when done):",
                flag_hint="--from-paste",
            )
        if not (_paste_text and _paste_text.strip()):
            click.echo("✗ Paste was empty — nothing to ingest.", err=True)
            sys.exit(1)
        # Mark `_markdown_only` so the rest of create_cmd's pipeline
        # routing treats this as a markdown-source run. `from_markdown`
        # stays None for now — assigned once we've decided to proceed
        # (after the overwrite picker).
        _markdown_only = True

    if from_folder:
        pdfs = sorted(Path(from_folder).glob("*.pdf"))
        if not pdfs:
            click.echo(f"No PDFs found in {from_folder}", err=True)
            sys.exit(1)
        resume_path = pdfs[0]
        click.echo(f"Detected resume: {resume_path}")
    if not resume_path and not _markdown_only:
        click.echo("Need --resume PATH, --from-paste, --from-folder DIR, or --from-markdown PATH.", err=True)
        sys.exit(2)

    # Auto-route .md / .markdown files to the markdown-ingest path (UAT bug #4).
    # Previously a .md file passed via `-r` fell through to the PDF readability
    # guard below and errored with "invalid pdf header" — even though
    # `--from-markdown` was a supported flag. Auto-detect by extension so
    # users don't need to remember which flag matches which extension.
    if resume_path and resume_path.suffix.lower() in (".md", ".markdown"):
        from_markdown = resume_path
        resume_path = None
        _markdown_only = True

    # PDF readability guard — catch corrupt/empty/password-protected files
    # before running the 30-90 sec pipeline. pypdf raises on empty files.
    if resume_path and not _markdown_only:
        try:
            from pypdf import PdfReader
        except ImportError:
            click.echo("pypdf is not installed — run `pip install pypdf`.", err=True)
            sys.exit(1)
        try:
            reader = PdfReader(str(resume_path))
            if len(reader.pages) == 0:
                raise ValueError("empty PDF")
        except Exception:
            click.echo(f"✗ Cannot read PDF: {resume_path.name}", err=True)
            click.echo(
                "  Check the file is not password-protected, corrupt, or empty.",
                err=True,
            )
            sys.exit(1)

    # UAT bug #6 — resume sanity-check: skim the file for resume-shaped
    # signals BEFORE running the 30-90 sec extract pipeline. Lightweight
    # keyword + email heuristic (deterministic, no LLM call). Low-confidence
    # files prompt the user to confirm "really proceed?" — no hard reject,
    # so power users can still force-run on unusual layouts. Skipped for
    # markdown-only augment mode (user already has a profile they trust).
    #
    # Cycle 2 / MED-5: previously `--yes` silently disabled the resume
    # sanity check. `--yes` should mean "accept defaults," not "skip safety
    # nets." Now under `--yes` we still RUN the heuristic and print a
    # stderr warning if the file looks off, but continue (no interactive
    # prompt — scripted automation must not block). User can still see
    # what tripped the heuristic and re-run with a real resume.
    def _warn_yes(p, reasons):
        click.echo(
            f"⚠ '{p.name}' did not pass the resume sanity heuristic "
            f"(--yes bypasses the prompt; continuing anyway):",
            err=True,
        )
        for r in reasons:
            click.echo(f"    • {r}", err=True)

    if resume_path and not _markdown_only:
        _looks, _reasons = _looks_like_resume(resume_path)
        if not _looks:
            if yes:
                _warn_yes(resume_path, _reasons)
            else:
                _proceed = _prompt_resume_lookalike_override(resume_path, _reasons)
                if not _proceed:
                    click.echo("Cancelled — file did not look like a resume.")
                    sys.exit(0)

    # Same heuristic for markdown source — catches the obvious "I pasted my
    # cover letter" mistake before truth-engine wastes user time.
    if from_markdown and _markdown_only and not from_paste:
        _looks_md, _reasons_md = _looks_like_resume(Path(from_markdown))
        if not _looks_md:
            if yes:
                _warn_yes(Path(from_markdown), _reasons_md)
            else:
                _proceed_md = _prompt_resume_lookalike_override(Path(from_markdown), _reasons_md)
                if not _proceed_md:
                    click.echo("Cancelled — file did not look like a resume.")
                    sys.exit(0)

    # Paste heuristic — run BEFORE materialising the tempfile (so a dud
    # paste never even hits disk). We have `_paste_text` in scope; write
    # it to a throwaway file for the heuristic, scrub it after.
    if from_paste:
        import tempfile as _tmp_for_check
        _check_dir = _tmp_for_check.mkdtemp(prefix="linkright-paste-check-")
        _check_path = Path(_check_dir) / "resume.md"
        try:
            _check_path.write_text(_paste_text, encoding="utf-8")
            _looks_p, _reasons_p = _looks_like_resume(_check_path)
            if not _looks_p:
                if yes:
                    # Use the human-readable label ("pasted-text") in the
                    # warning instead of the throwaway tempfile path
                    # (avoids "'resume.md' did not pass …" referring to a
                    # filename the user never named).
                    _warn_yes(Path("pasted-text"), _reasons_p)
                else:
                    _proceed_p = _prompt_resume_lookalike_override(
                        Path("pasted-text"), _reasons_p
                    )
                    if not _proceed_p:
                        click.echo("Cancelled — paste did not look like a resume.")
                        sys.exit(0)
        finally:
            shutil.rmtree(_check_dir, ignore_errors=True)

    # Existing profile guard — check metadata.yaml specifically (same signal
    # as `profile show`/`status`). Avoids false-positive on empty scaffold dirs
    # (artifacts/ inputs/ logs/ from a prior failed run with no actual data).
    #
    # Exception: --from-markdown augment mode. If only --from-markdown is passed
    # (no PDF source), the user is ADDING to an existing profile, not replacing it.
    # The guard must not block in this case — markdown ingest appends to nuggets.jsonl.
    #
    # Paste-to-existing-profile deliberately routes through the standard
    # 3-option picker (keep / overwrite / view). Appending paste content to
    # an existing profile is a future-cluster feature — the UX surprise of
    # an additive option that silently mutates a trusted profile needs its
    # own design pass, and cycle-2's attempt at it introduced regressions.
    _augment_only = bool(from_markdown and _markdown_only and not from_paste)
    if (profile_dir / "metadata.yaml").exists() and not _augment_only:
        if not force:
            # UAT bug #9 — interactive overwrite. Non-technical users do not
            # know to pass --force; previously the CLI dead-ended with a
            # flag suggestion. Show a 3-option picker: keep (cancel),
            # overwrite (wipe + re-ingest), or view first. Power users
            # can still pass --force on the CLI for scripted runs.
            #
            # Non-TTY (CI / piped) sticks with the original error so
            # automation behavior is unchanged — `--force` remains the
            # explicit opt-in for unattended overwrite.
            if not _is_interactive():
                click.echo(f"Profile already exists at {profile_dir}.")
                click.echo(
                    "Run `linkright profile show` to inspect, "
                    "`linkright profile rebuild` to start over,"
                )
                click.echo(
                    "or pass `--force` to overwrite "
                    "(existing data backed up to .backup-<timestamp>)."
                )
                sys.exit(1)
            choice = _prompt_overwrite_existing(profile_dir)
            if choice == "keep":
                click.echo("Kept existing profile. Nothing changed.")
                sys.exit(0)
            if choice == "view":
                # Show the profile inline, then bail out so the user can
                # decide their next move (rebuild, edit-contact, etc.).
                from .render import show_profile
                show_profile(profile_dir, full=False)
                click.echo(
                    "\nViewed existing profile. Re-run `linkright profile create` "
                    "and pick Overwrite, or `linkright profile rebuild` to replace with a new resume."
                )
                sys.exit(0)
            # choice == "overwrite" — fall through to wipe + re-ingest.
        _wipe(profile_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)

    if _markdown_only:
        # Markdown-only mode: skip PDF pipeline, just ensure profile dir exists.
        profile_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"Creating profile from Markdown → {profile_dir}")
        click.echo("Markdown-only mode: PDF pipeline skipped.\n")
    else:
        click.echo(f"Creating profile from {resume_path} → {profile_dir}")
        click.echo("This runs steps 0-3 of the resume pipeline (parse → extract nuggets → embed).")
        click.echo("Expected wall-time: 30-90 sec depending on LLM backend.\n")

        result = parse_and_extract(resume_path, profile_dir)
        persist(profile_dir, resume_path, result)

    if not _markdown_only:
        meta = load_metadata(profile_dir) or {}
        click.echo("")
        click.echo(f"✓ Profile created at {profile_dir}")
        click.echo(f"  Nuggets:     {meta.get('n_nuggets', 0)} extracted")
        click.echo(f"  Embedded:    {meta.get('n_embedded', 0)} vectors stored")
        click.echo(f"  Highlights:  {meta.get('n_highlights', 0)} (P0/P1 importance)")
        click.echo(f"  Embedder:    {meta.get('embedder_tier')} ({meta.get('embedder_model')})")
        click.echo(f"  Dim:         {meta.get('dim')}")

    if not _markdown_only:
        # PC-4: Eagerly warm up the embedding model before interactive prompts.
        # step_03 may have used a cached artifact (cache-hit path skips embed() calls),
        # leaving the model uninitialised. Any model download triggered mid-questionary
        # (e.g. when user edits a highlight in truth_engine_loop) interleaves tqdm
        # progress with interactive text — visible race condition. Warming here
        # guarantees download + init happens in this "Indexing" phase, not mid-prompt.
        try:
            from ..resume.lib.embedder import _detect_tier, _fastembed_init, _st_init
            _tier = _detect_tier()
            click.echo("Indexing achievements semantically…")
            if _tier == "fastembed":
                _fastembed_init()
            elif _tier == "sentence_transformers":
                _st_init()
            # oracle + stub tiers require no local model init
        except Exception:
            pass  # never block the flow on warm-up failure

        # Truth-engine Layer 1: contact-info verification — runs FIRST (before
        # highlights loop). Per Jane 2026-05-02
        # (memory feedback_personal_details_verify_at_start): wrong contact info =
        # silent failure (recruiter can't reach candidate). Verify always; only
        # `--yes` skips (batch flows / scripted profile creation).
        if not yes:
            contact_verify_loop(profile_dir)

        # Truth-engine Layer 2: highlights confirmation loop — Lock/Skip/Edit per
        # nugget. --yes auto-locks all.
        if not yes:
            truth_engine_loop(profile_dir)
            meta = load_metadata(profile_dir) or {}
            click.echo(
                f"\nFinal counts: {meta.get('n_nuggets', 0)} nuggets, "
                f"{meta.get('n_highlights', 0)} highlights locked."
            )

        # Truth-engine Layer 3: optional deep enrichment.
        # After truth engine, user has verified all highlights. Offer to deepen
        # specific achievements via 3 follow-up Q&A → new nuggets persisted.
        # --yes skips (batch/scripted). Ctrl+C cancels gracefully without loss.
        if not yes:
            _offer_enrich(profile_dir)

    # ── S3.4: Markdown profile ingestion ────────────────────────────────────
    # Append nuggets from a long-form career narrative (Obsidian export, etc.)
    # Can be combined with resume-based create (both sources merged) or used
    # standalone on a new profile (profile_dir may have no metadata.yaml yet).
    #
    # Cycle 2 / B1+B2 paste path: if `from_paste`, materialise the paste text
    # NOW (after all guards have passed) inside a try/finally so the tempfile
    # dir is removed on every exit path. Then write a minimal metadata.yaml
    # so downstream commands (`profile show` / `status` / `tailor`) recognise
    # the profile as valid.
    _paste_tmpdir: Path | None = None
    try:
        if from_paste:
            import tempfile
            _paste_tmpdir = Path(tempfile.mkdtemp(prefix="linkright-paste-"))
            _tmp_md = _paste_tmpdir / "resume.md"
            _tmp_md.write_text(_paste_text, encoding="utf-8")
            from_markdown = _tmp_md

        if from_markdown:
            md_path = Path(from_markdown)
            profile_dir.mkdir(parents=True, exist_ok=True)
            click.echo(f"\nIngesting Markdown profile: {md_path}")
            if include_personal:
                click.echo("  (--include-personal: processing all sections including personal-life)")
            else:
                click.echo("  (personal-life sections will be skipped — use --include-personal to opt in)")

            ingest_result = ingest_from_markdown(
                md_path=md_path,
                profile_dir=profile_dir,
                include_personal=include_personal,
            )
            print_privacy_audit(ingest_result)

            # Cycle 2 / B1: write metadata.yaml so the profile is recognised
            # by downstream commands. Without this, paste flow leaves the
            # user with an unusable half-built profile.
            #
            # Skip metadata write when the PDF path already wrote a
            # complete metadata.yaml (PDF + markdown-augment combo). In
            # that case `_markdown_only` is False and `persist()` already
            # ran. For paste / markdown-only / paste-append paths there
            # is NO PDF-side metadata, so we synthesise minimal fields.
            if _markdown_only:
                _src = "paste" if from_paste else "markdown-file"
                _write_markdown_only_metadata(
                    profile_dir, ingest_result, source_hint=_src
                )
                # Reflect counts to the user.
                meta = load_metadata(profile_dir) or {}
                click.echo("")
                click.echo(f"✓ Profile created at {profile_dir}")
                click.echo(f"  Nuggets:     {meta.get('n_nuggets', 0)} (markdown ingest)")
                click.echo(f"  Embedder:    {meta.get('embedder_tier')} ({meta.get('embedder_model')})")
                click.echo(f"  Source:      {meta.get('source')}")
    finally:
        # Cycle 2 / B2: tempfile cleanup. Even when ingest_from_markdown
        # crashes mid-run we MUST remove the PII-bearing temp dir. Without
        # ignore_errors=True, a partial-write race could leave the dir
        # around — paranoid cleanup is the safer default for a file
        # holding the user's full resume text.
        if _paste_tmpdir is not None:
            shutil.rmtree(_paste_tmpdir, ignore_errors=True)

    click.echo("")
    click.echo("Next: `linkright profile show` to review, "
               "or `linkright tailor -j jd.md` to use it.")


# ── show ────────────────────────────────────────────────────────────────────

@profile_group.command("show")
@click.option("--full", "show_full", is_flag=True,
              help="Show full bullet text (disable 120-char truncation).")
def show_cmd(show_full: bool) -> None:
    """Render the profile outline (resume sections → companies → roles → bullets) using rich."""
    from .render import show_profile
    profile_dir = _profile_dir()
    if not (profile_dir / "metadata.yaml").exists():
        click.echo("No profile found. Run `linkright profile create -r resume.pdf --yes` first.", err=True)
        sys.exit(1)
    show_profile(profile_dir, full=show_full)


# ── status (cheap non-render check) ─────────────────────────────────────────

@profile_group.command("status")
@click.option("--debug", is_flag=True, help="Show raw metadata including SHA256 checksums.")
def status_cmd(debug: bool) -> None:
    """Print metadata.yaml + counts. Fast, no rich rendering."""
    from datetime import datetime as _dt
    profile_dir = _profile_dir()
    meta = load_metadata(profile_dir)
    if not meta:
        click.echo("No profile found. Run `linkright profile create -r resume.pdf --yes` first.", err=True)
        sys.exit(1)
    click.echo(f"Profile dir:  {profile_dir}")
    click.echo(f"Created:      {meta.get('created_at')}")

    # Show resume source as filename + modified date instead of raw SHA256.
    resume_input = profile_dir / "inputs" / "resume.pdf"
    if not resume_input.exists():
        resume_input = profile_dir / "inputs" / "resume.md"
    if resume_input.exists():
        mtime = _dt.fromtimestamp(resume_input.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        click.echo(f"Resume:       {resume_input.name} (modified {mtime})")
    else:
        click.echo("Resume:       (not set — markdown-only profile)")
    if debug and meta.get("source_pdf_sha256"):
        click.echo(f"  sha256:     {meta.get('source_pdf_sha256')}")

    click.echo(f"Embedder:     {meta.get('embedder_tier')} ({meta.get('embedder_model')}, dim={meta.get('dim')})")
    click.echo(f"Nuggets:      {meta.get('n_nuggets')}")
    click.echo(f"  embedded:   {meta.get('n_embedded')}")
    click.echo(f"  highlights: {meta.get('n_highlights')}")

    # Surface confirmed contact summary if present
    contact = load_contact(profile_dir)
    if contact:
        _NONE_STRINGS = {"none", "null", "n/a", ""}
        click.echo(f"Contact:")
        for k in ("name", "phone", "email", "linkedin", "portfolio"):
            raw = contact.get(k)
            v = raw if raw and str(raw).strip().lower() not in _NONE_STRINGS else None
            display = v if v else "(not set)"
            line = f"  {k:<10}: {display}"
            # AR walkthrough A.6 fix: surface the action when a field is blank
            # so the user knows the next move (don't make them search docs).
            if not v and k == "portfolio":
                line += "  (set with: linkright contact)"
            click.echo(line)


# ── edit-contact ────────────────────────────────────────────────────────────

@profile_group.command("edit-contact")
def edit_contact_cmd() -> None:
    """Re-verify / edit personal contact details (phone, email, LinkedIn, etc.).

    Use this when your phone changes, LinkedIn URL updates, or you add
    a portfolio. Wrong contact info is the worst kind of resume bug —
    the recruiter can't reach you, and you'll never know.
    """
    profile_dir = _profile_dir()
    if not (profile_dir / "metadata.yaml").exists():
        click.echo("No profile found. Run `linkright profile create -r resume.pdf` first.", err=True)
        sys.exit(1)
    from .pipeline import contact_verify_loop
    contact_verify_loop(profile_dir)


# ── delete-nugget ───────────────────────────────────────────────────────────

@profile_group.command("delete-nugget")
def delete_nugget_cmd() -> None:
    """Interactive picker — select a nugget, confirm, remove from jsonl + npz."""
    profile_dir = _profile_dir()
    if not (profile_dir / "metadata.yaml").exists():
        click.echo("No profile found. Run `linkright profile create -r resume.pdf` first.", err=True)
        sys.exit(1)
    delete_nugget_interactive(profile_dir)


# ── enrich ──────────────────────────────────────────────────────────────────

@profile_group.command("enrich")
@click.argument("nugget_id", required=False)
def enrich_cmd(nugget_id: str | None) -> None:
    """Generate 3 follow-up questions for a nugget; user answers → new nuggets persisted.

    NUGGET_ID is optional — pass an integer index or nugget_index field to skip
    the picker. With no arg, an interactive picker lists all nuggets.
    """
    from .enrich import enrich_session
    profile_dir = _profile_dir()
    if not (profile_dir / "metadata.yaml").exists():
        click.echo("No profile found. Run `linkright profile create -r resume.pdf` first.", err=True)
        sys.exit(1)
    enrich_session(profile_dir, nugget_id=nugget_id)


# ── refresh ─────────────────────────────────────────────────────────────────

@profile_group.command("refresh")
@click.option("--yes", is_flag=True, help="Auto-lock-all (skip truth engine).")
def refresh_cmd(yes) -> None:
    """Re-parse the existing inputs/resume.pdf without changing the source."""
    profile_dir = _profile_dir()
    pdf = profile_dir / "inputs" / "resume.pdf"
    if not pdf.exists():
        click.echo(f"No staged resume.pdf at {pdf}. Use `linkright profile create -r ...` first.", err=True)
        sys.exit(1)
    click.echo(f"Refreshing profile from {pdf}")
    result = parse_and_extract(pdf, profile_dir)
    persist(profile_dir, pdf, result)
    if not yes:
        truth_engine_loop(profile_dir)
    click.echo(f"✓ Profile refreshed.")


# ── rebuild ─────────────────────────────────────────────────────────────────

@profile_group.command("rebuild")
@click.option("--resume", "-r", "resume_path", type=click.Path(exists=True, path_type=Path),
              required=False, help="(optional) Path to NEW resume PDF — prompted if omitted.")
@click.option("--yes", is_flag=True, help="Skip confirmation (destructive).")
def rebuild_cmd(resume_path, yes) -> None:
    """Wipe existing profile (backed up) and start over from a new resume.

    Run with no flags to be prompted for the path. Pass -r to skip the prompt.
    """
    if resume_path is None:
        from linkright.prompts import prompt_for_existing_path
        resume_path = prompt_for_existing_path(
            "Path to your NEW resume PDF:",
            must_be_file=True,
            flag_hint="-r/--resume",
        )

    profile_dir = _profile_dir()
    if profile_dir.exists() and any(profile_dir.iterdir()):
        if not yes:
            confirm = click.confirm(
                f"This will wipe {profile_dir} (backed up to .backup-<ts>). Continue?", default=False)
            if not confirm:
                click.echo("Aborted.")
                sys.exit(0)
        _wipe(profile_dir)

    profile_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"Rebuilding profile from {resume_path}")
    result = parse_and_extract(resume_path, profile_dir)
    persist(profile_dir, resume_path, result)
    click.echo(f"✓ Profile rebuilt at {profile_dir}")


# ── delete (entire profile) ─────────────────────────────────────────────────

@profile_group.command("delete")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
def delete_cmd(yes) -> None:
    """Wipe ~/.linkright/profile/ entirely (backed up to .backup-<ts>)."""
    profile_dir = _profile_dir()
    if not profile_dir.exists():
        click.echo("No profile to delete.", err=True)
        sys.exit(0)
    if not yes and not click.confirm(f"Wipe {profile_dir}?", default=False):
        click.echo("Aborted.")
        return
    _wipe(profile_dir)
    click.echo(f"✓ Profile wiped (backup retained alongside).")


# ── Subcommand aliases (registered after all commands are defined) ──────────

profile_group.add_aliases({
    # edit-contact / contact / ec
    "ec":      "edit-contact",
    "contact": "edit-contact",
    # delete-nugget / dn / n
    "dn":      "delete-nugget",
    "n":       "delete-nugget",
    # enrich / e
    "e":       "enrich",
    # refresh / r
    "r":       "refresh",
    # rebuild / rb
    "rb":      "rebuild",
    # status / st (avoid clash with `s`→show prefix-match)
    "st":      "status",
    # graph / g
    "g":       "graph",
})


# ── graph ────────────────────────────────────────────────────────────────────

@profile_group.command("graph")
@click.option("--force", is_flag=True, help="Rebuild graph even if graph.json already exists.")
def graph_cmd(force: bool) -> None:
    """Build an interactive career knowledge graph from profile nuggets.

    Saves graph.json + graph.html to ~/.linkright/profile/ and opens the
    HTML visualization in the default browser.

    Requires: pip install graphifyy networkx
    """
    import webbrowser

    profile_dir = _profile_dir()
    if not (profile_dir / "metadata.yaml").exists():
        click.echo(
            "No profile found. Run `linkright profile create -r resume.pdf` first.",
            err=True,
        )
        sys.exit(1)

    graph_path = profile_dir / "graph.json"
    html_path = profile_dir / "graph.html"

    if graph_path.exists() and not force:
        click.echo(f"Graph already exists at {graph_path}")
        click.echo("Opening existing graph. Pass --force to rebuild.")
        webbrowser.open(html_path.as_uri())
        click.echo(f"Graph HTML: {html_path}")
        return

    # ── Load nuggets ──────────────────────────────────────────────────────────
    nuggets_path = profile_dir / "nuggets.jsonl"
    if not nuggets_path.exists():
        click.echo("No nuggets.jsonl found. Profile may be incomplete.", err=True)
        sys.exit(1)

    nuggets = []
    with nuggets_path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    nuggets.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not nuggets:
        click.echo("No nuggets found in profile. Profile may be empty.", err=True)
        sys.exit(1)

    click.echo(f"Building career graph from {len(nuggets)} nuggets…")

    # ── Build extraction dict for graphify.build.build_from_json ─────────────
    # Nodes: one per nugget. Each nugget has id, company, role, answer fields.
    # Edges: connect nuggets that share the same company.
    nodes = []
    edges = []
    seen_edges: set[tuple[str, str]] = set()

    # Group nugget IDs by company for edge construction
    company_to_ids: dict[str, list[str]] = {}

    for nug in nuggets:
        nid = str(nug.get("id", nug.get("nugget_index", "")))
        if not nid:
            continue
        company = nug.get("company", "Unknown")
        role = nug.get("role", nug.get("title", ""))
        label = nug.get("question", nug.get("answer", ""))[:80]
        nodes.append({
            "id": nid,
            "label": label,
            "type": "nugget",
            "company": company,
            "role": role,
        })
        company_to_ids.setdefault(company, []).append(nid)

    # Add company hub nodes + edges to their nuggets
    for company, ids in company_to_ids.items():
        hub_id = f"company:{company}"
        nodes.append({
            "id": hub_id,
            "label": company,
            "type": "company",
            "company": company,
        })
        for nid in ids:
            key = (hub_id, nid)
            if key not in seen_edges:
                edges.append({"source": hub_id, "target": nid, "type": "EXTRACTED"})
                seen_edges.add(key)

    extraction = {"nodes": nodes, "edges": edges}

    # ── Import graphify pipeline pieces ──────────────────────────────────────
    try:
        from graphify.build import build_from_json
        from graphify.cluster import cluster
        from graphify.export import to_json, to_html
    except ImportError:
        click.echo(
            "graphify not installed. Run: pip install graphifyy networkx",
            err=True,
        )
        sys.exit(1)

    # ── Build + cluster ───────────────────────────────────────────────────────
    G = build_from_json(extraction)
    click.echo(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    communities = cluster(G)
    click.echo(f"Communities detected: {len(communities)}")

    # Build community_labels: {community_id: str} from hub node labels
    community_labels: dict[int, str] = {}
    for cid, member_ids in communities.items():
        # Find a company-hub node in this community (cleaner label)
        hub_labels = [
            G.nodes[nid].get("label", nid)
            for nid in member_ids
            if G.nodes[nid].get("type") == "company"
        ]
        if hub_labels:
            community_labels[cid] = " / ".join(sorted(set(hub_labels)))
        elif member_ids:
            community_labels[cid] = G.nodes[member_ids[0]].get("label", str(cid))
        else:
            community_labels[cid] = str(cid)

    member_counts = {cid: len(members) for cid, members in communities.items()}

    # ── Export ────────────────────────────────────────────────────────────────
    to_json(G, communities, str(graph_path), force=True)

    # Patch community_labels into graph.json — to_json doesn't write them,
    # but graph_context.py reads data.get("community_labels", {}) to resolve
    # community cluster names for subliminal context injection.
    raw = json.loads(graph_path.read_text())
    raw["community_labels"] = {str(k): v for k, v in community_labels.items()}
    graph_path.write_text(json.dumps(raw))

    to_html(G, communities, str(html_path),
            community_labels=community_labels,
            member_counts=member_counts)

    click.echo(f"✓ Graph saved: {graph_path}")
    click.echo(f"✓ Visualization: {html_path}")

    webbrowser.open(html_path.as_uri())
    click.echo("Opened in browser.")
