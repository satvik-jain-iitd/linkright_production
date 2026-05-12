"""`linkright cover-letter` CLI subcommand group.

Commands:
  linkright cover-letter -j jd.md              Generate cover letter from JD file
  linkright cover-letter --from-discovery <id>  Fetch JD from Pillar 2 API, then generate
  linkright cl -j jd.md                         (alias: cl)
"""
from __future__ import annotations

import sys
from pathlib import Path

import click


@click.group(name="cover-letter", invoke_without_command=True)
@click.option("-j", "--jd", "jd_path",
              type=click.Path(exists=True, path_type=Path),
              default=None,
              help="Path to JD file (markdown or plain text)")
@click.option("--from-discovery", "discovery_id",
              default=None,
              help="Fetch JD from Pillar 2 API by discovery ID (requires auth)")
@click.option("--tone",
              type=click.Choice(["formal", "conversational", "enthusiastic"], case_sensitive=False),
              default="conversational",
              show_default=True,
              help="Tone style for the cover letter")
@click.option("--output", "-o",
              type=click.Path(path_type=Path),
              default=None,
              help="Output path for the cover letter markdown (default: ~/.linkright/runs/<id>/artifacts/cover_letter.md)")
@click.option("--pdf", "render_pdf",
              is_flag=True, default=False,
              help="Also render a PDF version (requires playwright or weasyprint)")
@click.option("--json", "output_json",
              is_flag=True, default=False,
              help="Output machine-readable JSON result to stdout")
@click.pass_context
def coverletter_group(
    ctx: click.Context,
    jd_path: Path | None,
    discovery_id: str | None,
    tone: str,
    output: Path | None,
    render_pdf: bool,
    output_json: bool,
) -> None:
    """Pillar 1 — Generate a personalized cover letter from a JD.

    Run with no flags to be prompted for the JD (file path or paste).

    \b
    Quick start:
      linkright cl                              (prompts for JD)
      linkright cl -j jd.md                     (power-user: skip prompts)
      linkright cl -j jd.md --tone formal
      linkright cl --from-discovery abc123

    \b
    The pipeline:
      1. Parses JD into structured requirements (LLM, free tier)
      2. Retrieves matching career nuggets from your profile (no LLM)
      3. Generates 3-paragraph draft (LLM, free tier)
      4. Validates metrics vs your actual experience (no LLM)
      5. Formats and saves markdown + optional PDF

    Requires: `linkright profile create -r resume.pdf` (one-time setup).
    """
    if ctx.invoked_subcommand:
        return

    # Bare-command UX: if neither -j nor --from-discovery, prompt
    # interactively (file path first, paste fallback).
    pasted_jd_text: str = ""
    if not jd_path and not discovery_id:
        from linkright.prompts import prompt_for_jd_input
        kind, value = prompt_for_jd_input(flag_hint="-j/--jd")
        if kind == "file":
            jd_path = value
        else:  # paste — pasted text used directly, no need to write tempfile
            pasted_jd_text = value

    import time as _time
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn

    console = Console()
    jd_text: str = ""

    # ── Source JD text ──────────────────────────────────────────────────────
    if jd_path:
        jd_text = jd_path.read_text(encoding="utf-8", errors="replace")
    elif discovery_id:
        jd_text = _fetch_discovery_jd(discovery_id)
    elif pasted_jd_text:
        jd_text = pasted_jd_text

    if not jd_text.strip():
        raise click.ClickException("JD text is empty — cannot generate cover letter.")

    # ── Run pipeline ────────────────────────────────────────────────────────
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task("Parsing JD…", total=None)

        from linkright.coverletter.pipeline import run_cover_letter_pipeline

        progress.update(task, description="Running cover letter pipeline…")
        try:
            result = run_cover_letter_pipeline(
                jd_text=jd_text,
                tone=tone,
                output_path=output,
                render_pdf=render_pdf,
            )
        except RuntimeError as e:
            raise click.ClickException(str(e))

        progress.update(task, description="Done.")

    # ── Post-generation: optional Pillar 2 status update ───────────────────
    if discovery_id:
        _maybe_update_discovery_status(discovery_id)

    # ── Output ──────────────────────────────────────────────────────────────
    if output_json:
        import json
        telemetry = result["telemetry"]
        out = {
            "run_id": result["run_id"],
            "letter_path": str(result["letter_path"]),
            "pdf_path": str(result["pdf_path"]) if result["pdf_path"] else None,
            "violations": result["violations"],
            "telemetry": {
                "api_calls": telemetry["api_calls"],
                "tokens": telemetry["tokens"],
                "wall_time_s": telemetry["wall_time_s"],
                "cost": telemetry["cost"],
                "validator_failures": telemetry["validator_failures"],
                "nuggets_retrieved": telemetry["nuggets_retrieved"],
            },
        }
        click.echo(json.dumps(out, indent=2))
        return

    # Human-readable output
    console.print()
    console.print("[bold green]Cover letter generated![/]")
    console.print()
    console.rule("Cover Letter")
    console.print(result["letter_md"])
    console.rule()
    console.print()

    tel = result["telemetry"]
    console.print(
        f"[dim]Saved to: {result['letter_path']}[/]"
    )
    if result["pdf_path"]:
        console.print(f"[dim]PDF: {result['pdf_path']}[/]")
    console.print(
        f"[dim]Run ID: {result['run_id']}  |  "
        f"API calls: {tel['api_calls']}  |  "
        f"Tokens: {tel['tokens']:,}  |  "
        f"Time: {tel['wall_time_s']}s  |  "
        f"Nuggets used: {tel['nuggets_retrieved']}[/]"
    )
    if result["violations"]:
        console.print(
            f"[yellow]Truth-engine dropped {len(result['violations'])} fabricated claim(s).[/]"
        )

    jd_parsed = result.get("jd_parsed") or {}
    if jd_parsed.get("company_name") or jd_parsed.get("role_title"):
        console.print()
        console.print(
            f"[bold]Role:[/] {jd_parsed.get('role_title') or '?'}  |  "
            f"[bold]Company:[/] {jd_parsed.get('company_name') or '?'}"
        )


def _fetch_discovery_jd(discovery_id: str) -> str:
    """Fetch JD text from Pillar 2 API using saved session JWT."""
    import httpx
    from linkright.auth import require_session, api_headers, LINKRIGHT_API

    sess = require_session()
    headers = api_headers(sess)

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(
                f"{LINKRIGHT_API}/api/discoveries/{discovery_id}",
                headers=headers,
            )
        if resp.status_code == 404:
            raise click.ClickException(
                f"Discovery '{discovery_id}' not found. "
                f"Run `linkright jobs find` to list available discoveries."
            )
        if resp.status_code == 401:
            raise click.ClickException(
                "Session expired. Run `linkright auth login` to refresh."
            )
        if resp.status_code != 200:
            raise click.ClickException(
                f"API error {resp.status_code}: {resp.text[:200]}"
            )
        data = resp.json()
        # Try common JD body fields in priority order
        jd_text = (
            data.get("jd_text")
            or data.get("description")
            or data.get("body")
            or data.get("content")
            or ""
        )
        if not jd_text:
            raise click.ClickException(
                f"Discovery '{discovery_id}' returned no JD text. "
                "Check the discovery ID or use -j jd.md instead."
            )
        return jd_text
    except click.ClickException:
        raise
    except httpx.HTTPError as e:
        raise click.ClickException(f"Network error fetching discovery: {e}")


def _maybe_update_discovery_status(discovery_id: str) -> None:
    """Ask user if they want to mark the discovery's cover_letter_status = 'generated'.

    Silent on API error or if the field/endpoint doesn't exist — graceful degradation.
    """
    import httpx
    from linkright.auth import load_session, api_headers, LINKRIGHT_API

    try:
        ans = click.confirm(
            "Mark this job's cover letter status as 'generated'?",
            default=True,
        )
        if not ans:
            return

        sess = load_session()
        if not sess:
            return

        with httpx.Client(timeout=10.0) as client:
            resp = client.put(
                f"{LINKRIGHT_API}/api/discoveries/{discovery_id}",
                headers=api_headers(sess),
                json={"cover_letter_status": "generated"},
            )
        # 404 or 422 (field doesn't exist) → skip silently
        if resp.status_code in (200, 204):
            click.echo(f"  Marked discovery {discovery_id} cover_letter_status=generated")
        else:
            click.echo(f"  (Note: could not update discovery status — endpoint returned {resp.status_code})", err=True)
    except Exception:
        pass  # always silent on failure
