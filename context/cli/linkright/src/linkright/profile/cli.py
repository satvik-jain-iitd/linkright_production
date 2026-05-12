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
@click.option("--paste", is_flag=True, help="Interactive paste mode — type/paste resume text. (Day 2+)")
@click.option("--from-folder", "from_folder", type=click.Path(exists=True, file_okay=False, path_type=Path),
              required=False, help="(optional) Folder to auto-detect first PDF.")
@click.option("--from-markdown", "from_markdown", type=click.Path(exists=True, path_type=Path),
              required=False, help="Path to a Markdown career narrative to ingest into the profile.")
@click.option("--include-personal", "include_personal", is_flag=True,
              help="Include personal-life sections (skipped by default for privacy).")
@click.option("--yes", is_flag=True, help="Skip truth-engine confirmation; auto-lock all extracted nuggets.")
@click.option("--force", is_flag=True, help="Overwrite existing profile without confirmation.")
def create_cmd(resume_path, paste, from_folder, from_markdown, include_personal, yes, force) -> None:
    """One-time: parse resume, extract nuggets, embed, persist to ~/.linkright/profile/.

    Run with no flags to be prompted for the resume source. Pass -r / --paste /
    --from-folder to skip the prompt.
    """
    if not yes and sys.stdout.isatty():
        from linkright.ui import lr_banner
        from linkright import __version__ as _ver
        lr_banner(version=_ver)
    profile_dir = _profile_dir()

    # Determine whether a PDF resume pipeline is needed.
    # --from-markdown alone is valid (markdown-only ingest, no PDF required).
    _markdown_only = from_markdown and not resume_path and not paste and not from_folder

    # If no source flag given (and not markdown-only), prompt interactively (file / folder).
    # The `--paste` flag still exists as a stub but is NOT surfaced in
    # the prompt — the downstream parser is not wired yet, so offering
    # paste interactively would dead-end the user. When the text-only
    # parser ships, add the paste branch back to prompt_for_resume_source.
    if not resume_path and not paste and not from_folder and not _markdown_only:
        from linkright.prompts import prompt_for_resume_source
        kind, value = prompt_for_resume_source()
        if kind == "file":
            resume_path = value
        else:  # folder
            from_folder = value

    # Resolve resume source
    if paste:
        click.echo("[paste mode] Day 2 feature — coming soon.", err=True)
        sys.exit(2)
    if from_folder:
        pdfs = sorted(Path(from_folder).glob("*.pdf"))
        if not pdfs:
            click.echo(f"No PDFs found in {from_folder}", err=True)
            sys.exit(1)
        resume_path = pdfs[0]
        click.echo(f"Detected resume: {resume_path}")
    if not resume_path and not _markdown_only:
        click.echo("Need --resume PATH or --paste or --from-folder DIR.", err=True)
        sys.exit(2)

    # Existing profile guard — check metadata.yaml specifically (same signal
    # as `profile show`/`status`). Avoids false-positive on empty scaffold dirs
    # (artifacts/ inputs/ logs/ from a prior failed run with no actual data).
    #
    # Exception: --from-markdown augment mode. If only --from-markdown is passed
    # (no PDF source), the user is ADDING to an existing profile, not replacing it.
    # The guard must not block in this case — markdown ingest appends to nuggets.jsonl.
    _augment_only = bool(from_markdown and _markdown_only)
    if (profile_dir / "metadata.yaml").exists() and not _augment_only:
        if not force:
            click.echo(f"Profile already exists at {profile_dir}.")
            click.echo("Run `linkright profile show` to inspect, `linkright profile rebuild` to start over,")
            click.echo("or pass `--force` to overwrite (existing data backed up to .backup-<timestamp>).")
            sys.exit(1)
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
def status_cmd() -> None:
    """Print metadata.yaml + counts. Fast, no rich rendering."""
    profile_dir = _profile_dir()
    meta = load_metadata(profile_dir)
    if not meta:
        click.echo("No profile found. Run `linkright profile create -r resume.pdf --yes` first.", err=True)
        sys.exit(1)
    click.echo(f"Profile dir:  {profile_dir}")
    click.echo(f"Created:      {meta.get('created_at')}")
    click.echo(f"Embedder:     {meta.get('embedder_tier')} ({meta.get('embedder_model')}, dim={meta.get('dim')})")
    click.echo(f"Nuggets:      {meta.get('n_nuggets')}")
    click.echo(f"  embedded:   {meta.get('n_embedded')}")
    click.echo(f"  highlights: {meta.get('n_highlights')}")

    # Surface confirmed contact summary if present
    contact = load_contact(profile_dir)
    if contact:
        click.echo(f"Contact:")
        for k in ("name", "phone", "email", "linkedin", "portfolio"):
            v = contact.get(k) or "(blank)"
            line = f"  {k:<10}: {v}"
            # AR walkthrough A.6 fix: surface the action when a field is blank
            # so the user knows the next move (don't make them search docs).
            if v == "(blank)" and k == "portfolio":
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
