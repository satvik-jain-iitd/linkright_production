"""`linkright jobs` (jobsearch) subcommand group — Pillar 2 v1.

Commands (old scaffold preserved):
  evaluate --jd <path>          10-dim JD scorecard (local MongoDB)
  recommend [--top N]           list top-N evaluations from MongoDB
  apply <jd_hash>               mark an application in MongoDB

New commands (sync.linkright.in API thin-client):
  find [--top N] [--location L] [--grade A] [--json]   daily job feed
  show <id>                                              full JD detail
  apply <id> [--no-status-update]                        tailor + mark applied
  status <id> <state>                                    update status
  import <csv>                                           import jobs from CSV

Single-letter aliases registered at group level:
  f → find     s → status
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import click

from linkright.cli_aliases import AliasedGroup

_LINKRIGHT_API = "https://sync.linkright.in"


# ── Group ─────────────────────────────────────────────────────────────────────

@click.group(cls=AliasedGroup, name="jobs")
def jobsearch_group() -> None:
    """Pillar 2 — Job feed from sync.linkright.in + local evaluation.

    \b
    Daily workflow:
      linkright auth login           1. Log in once (stores session locally)
      linkright jobs find            2. See today's top-10 scored jobs
      linkright jobs show 1          3. Read full JD for rank #1
      linkright jobs apply 1         4. Tailor resume + mark applied

    \b
    Aliases:
      f   find        s   status
    """


# Register single-letter aliases
jobsearch_group.add_aliases({"f": "find", "s": "status"})


# ── Helper ────────────────────────────────────────────────────────────────────

def _http() -> "httpx.Client":
    import httpx
    return httpx.Client(timeout=20, follow_redirects=True)


def _auth_headers() -> dict:
    from linkright.auth import require_session, api_headers
    return api_headers(require_session())


def _grade_color(grade: str) -> str:
    return {"A": "green", "B": "cyan", "C": "yellow", "D": "red", "F": "red"}.get(grade, "white")


# ── find ──────────────────────────────────────────────────────────────────────

@jobsearch_group.command("find")
@click.option("--top", "top_n", default=10, type=int, show_default=True,
              help="How many results to show")
@click.option("--location", default=None, help="Filter by location (partial match)")
@click.option("--grade", default=None, type=click.Choice(["A", "B", "C", "D", "F"]),
              help="Minimum grade filter")
@click.option("--refresh", is_flag=True, help="Trigger a fresh scan before fetching")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON (pipe-friendly)")
def find(top_n: int, location: str | None, grade: str | None, refresh: bool, as_json: bool) -> None:
    """Show today's top job matches from your sync.linkright.in feed."""
    import httpx
    from rich.console import Console
    from rich.table import Table
    from rich import box

    headers = _auth_headers()

    if refresh:
        click.echo("Triggering scan... ", nl=False)
        try:
            with _http() as client:
                client.post(f"{_LINKRIGHT_API}/api/scan", headers=headers)
            click.echo("done.")
        except Exception:
            click.echo("(scan endpoint unreachable — fetching cached feed)")

    try:
        with _http() as client:
            resp = client.get(
                f"{_LINKRIGHT_API}/api/recommendations/today",
                headers=headers,
                params={"limit": max(top_n * 3, 50)},  # over-fetch to allow client-side filter
            )
    except Exception as e:
        raise click.ClickException(f"Network error: {e}")

    if resp.status_code == 401:
        click.echo(
            "Session expired or invalid.\nRun: linkright auth login",
            err=True,
        )
        sys.exit(1)
    if resp.status_code != 200:
        raise click.ClickException(f"API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    rows = data.get("top20") or []

    # Client-side filters
    if location:
        loc_lower = location.lower()
        rows = [r for r in rows if loc_lower in (r.get("job_discoveries") or {}).get("location", "").lower()]

    grade_order = ["A", "B", "C", "D", "F"]
    if grade:
        allowed = grade_order[: grade_order.index(grade) + 1]
        rows = [r for r in rows if r.get("auto_score_grade") in allowed or
                (r.get("job_discoveries") or {}).get("auto_score_grade") in allowed]

    rows = rows[:top_n]

    if as_json:
        click.echo(json.dumps(rows, indent=2, default=str))
        return

    if not rows:
        click.echo("No jobs match your filters. Try `linkright jobs find` with no filters.")
        return

    console = Console()
    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
    table.add_column("Rank", style="dim", width=4, justify="right")
    table.add_column("Grade", width=5, justify="center")
    table.add_column("Title", min_width=28, max_width=48)
    table.add_column("Company", min_width=18, max_width=28)
    table.add_column("Location", min_width=14, max_width=24)
    table.add_column("Score", width=6, justify="right")
    table.add_column("Action", width=14)

    for i, row in enumerate(rows, 1):
        disc = row.get("job_discoveries") or {}
        rank_val = row.get("rank", i)
        score_val = row.get("final_score") or row.get("auto_score") or 0
        grade_val = (
            row.get("auto_score_grade")
            or disc.get("auto_score_grade")
            or "?"
        )
        title = disc.get("title") or row.get("title") or "-"
        company = disc.get("company_name") or row.get("company_name") or "-"
        loc = disc.get("location") or row.get("location") or "-"
        discovery_id = disc.get("id") or row.get("id") or ""

        grade_styled = f"[{_grade_color(grade_val)}]{grade_val}[/{_grade_color(grade_val)}]"
        action = f"jobs show {discovery_id[:8]}..." if discovery_id else "jobs show <id>"

        table.add_row(
            str(rank_val),
            grade_styled,
            title[:48],
            company[:28],
            loc[:24],
            f"{score_val:.0f}" if isinstance(score_val, (int, float)) else str(score_val),
            action,
        )

    console.print(table)
    click.echo(f"\n{len(rows)} jobs shown. Use 'linkright jobs show <id>' for full detail.")
    click.echo("Use 'linkright jobs apply <id>' to tailor your resume and mark applied.")


# ── show ──────────────────────────────────────────────────────────────────────

@jobsearch_group.command("show")
@click.argument("discovery_id")
def show(discovery_id: str) -> None:
    """Show full JD detail for a discovery (by ID or rank from `find`)."""
    from rich.console import Console
    from rich.panel import Panel
    from rich import box

    # If given a rank integer, fetch today's feed and resolve to ID
    resolved_id = _resolve_id(discovery_id)

    headers = _auth_headers()
    try:
        with _http() as client:
            resp = client.get(f"{_LINKRIGHT_API}/api/discoveries/{resolved_id}", headers=headers)
    except Exception as e:
        raise click.ClickException(f"Network error: {e}")

    if resp.status_code == 404:
        raise click.ClickException(f"Discovery '{resolved_id}' not found.")
    if resp.status_code == 401:
        click.echo("Session expired. Run: linkright auth login", err=True)
        sys.exit(1)
    if resp.status_code != 200:
        raise click.ClickException(f"API error {resp.status_code}: {resp.text[:200]}")

    disc = resp.json().get("discovery") or {}
    if not disc:
        raise click.ClickException("Empty response from API.")

    console = Console()

    title_line = f"{disc.get('title', '(no title)')} — {disc.get('company_name', '?')}"
    location = disc.get("location") or "(location not specified)"
    job_url = disc.get("job_url") or ""
    status = disc.get("status") or "new"
    grade = disc.get("auto_score_grade") or "?"
    score = disc.get("auto_score") or 0
    jd_text = disc.get("jd_text") or "(JD text not available — check the URL)"

    meta_lines = [
        f"[bold]Location:[/bold] {location}",
        f"[bold]Grade:[/bold]    [{_grade_color(grade)}]{grade}[/{_grade_color(grade)}]"
        + (f"  [bold]Score:[/bold] {score:.0f}" if score else ""),
        f"[bold]Status:[/bold]   {status}",
    ]
    if job_url:
        meta_lines.append(f"[bold]URL:[/bold]      {job_url}")
    meta_lines.append(f"[bold]ID:[/bold]       {disc.get('id', resolved_id)}")

    # Scoring breakdown if present
    score_breakdown = disc.get("score_breakdown") or {}
    missing_skills = disc.get("missing_skills") or []

    console.print(Panel("\n".join(meta_lines), title=title_line, box=box.ROUNDED, expand=False))

    if score_breakdown:
        console.print("\n[bold]Scoring breakdown:[/bold]")
        for dim, val in score_breakdown.items():
            console.print(f"  {dim:28s} {val}")

    if missing_skills:
        console.print("\n[bold]Missing skills:[/bold]")
        for sk in missing_skills:
            console.print(f"  • {sk}")

    # JD text (truncated for terminal)
    jd_preview = jd_text[:3000] + ("\n... [truncated — full text available via API]" if len(jd_text) > 3000 else "")
    console.print(Panel(jd_preview, title="Job Description", box=box.SIMPLE))

    click.echo(f"\nApply: linkright jobs apply {disc.get('id', resolved_id)}")


# ── apply (new: website API) ───────────────────────────────────────────────────

@jobsearch_group.command("apply")
@click.argument("discovery_id")
@click.option("--no-status-update", "no_status", is_flag=True,
              help="Run tailor pipeline only — do not mark discovery as applied on the website")
def apply_cmd(discovery_id: str, no_status: bool) -> None:
    """Fetch JD, run Pillar 1 tailor pipeline, and mark as applied.

    \b
    Steps:
      1. Fetch full JD from API
      2. Save JD to ~/.linkright/runs/<run-id>/inputs/jd.md
      3. Run `linkright resume tailor` pipeline against your profile
      4. Mark discovery status='applied' on sync.linkright.in (unless --no-status-update)
    """
    import shutil
    import subprocess
    from datetime import datetime, timezone

    resolved_id = _resolve_id(discovery_id)
    headers = _auth_headers()

    # Fetch JD
    click.echo(f"Fetching JD for discovery {resolved_id[:8]}...", nl=False)
    try:
        with _http() as client:
            resp = client.get(f"{_LINKRIGHT_API}/api/discoveries/{resolved_id}", headers=headers)
    except Exception as e:
        raise click.ClickException(f"Network error: {e}")

    if resp.status_code == 404:
        raise click.ClickException(f"Discovery '{resolved_id}' not found.")
    if resp.status_code != 200:
        raise click.ClickException(f"API error {resp.status_code}: {resp.text[:200]}")

    disc = resp.json().get("discovery") or {}
    jd_text = disc.get("jd_text") or ""
    if not jd_text:
        raise click.ClickException(
            "JD text not available for this discovery. "
            "Check the job URL and retry, or use `linkright tailor -j <jd.md>` manually."
        )
    click.echo(" done.")

    # Write JD to run dir
    from linkright.config import Config
    cfg = Config.load()
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    run_dir = cfg.runs_dir() / run_id
    inputs_dir = run_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    jd_path = inputs_dir / "jd.md"
    jd_path.write_text(
        f"# {disc.get('title', 'Job Description')} — {disc.get('company_name', '')}\n\n"
        f"**Location**: {disc.get('location', 'Unknown')}\n"
        f"**URL**: {disc.get('job_url', '')}\n\n"
        + jd_text
    )
    click.echo(f"JD saved to {jd_path}")

    # Resolve profile resume path
    profile_dir = cfg.profile_dir()
    resume_path = profile_dir / "inputs" / "resume.pdf"
    if not resume_path.exists():
        # Fallback: check for markdown resume
        resume_md = profile_dir / "inputs" / "resume.md"
        if resume_md.exists():
            resume_path = resume_md
        else:
            raise click.ClickException(
                "No profile resume found. Run: linkright profile create -r resume.pdf"
            )

    click.echo("Running Pillar 1 tailor pipeline...")
    click.echo(f"  Resume: {resume_path}")
    click.echo(f"  JD: {jd_path}")
    click.echo(f"  Run ID: {run_id}")
    click.echo("")

    # Invoke tailor via subprocess (same as CLI — avoids module-state collision).
    # Force --llm-mode direct: default to free Groq/Cerebras tier.
    # Per memory feedback_never_agent_mode_for_hypothesis_tests — agent mode bills
    # per-token on Claude subscription, burning $$$ for multi-pipeline runs.
    # User must explicitly set default_llm_mode="agent" in config to override.
    cfg_mode = getattr(cfg, "default_llm_mode", None)
    llm_mode = cfg_mode if cfg_mode in ("direct",) else "direct"
    result = subprocess.run(
        [sys.executable, "-m", "linkright", "resume", "tailor",
         "-r", str(resume_path),
         "-j", str(jd_path),
         "--run-id", run_id,
         "--yes",
         "--llm-mode", llm_mode],
        capture_output=False,  # stream output to terminal
    )

    if result.returncode != 0:
        raise click.ClickException(f"Tailor pipeline exited with code {result.returncode}. Check output above.")

    # Mark applied on website
    if not no_status:
        click.echo("\nMarking discovery as applied on sync.linkright.in...", nl=False)
        try:
            with _http() as client:
                status_resp = client.post(
                    f"{_LINKRIGHT_API}/api/discoveries/{resolved_id}/apply",
                    headers=headers,
                )
            if status_resp.status_code in (201, 200):
                click.echo(" done.")
            elif status_resp.status_code == 409:
                click.echo(" (already applied — OK).")
            else:
                click.echo(f" skipped (API returned {status_resp.status_code}).")
        except Exception as e:
            click.echo(f" failed ({e}) — resume was still generated.")

    click.echo(f"\nDone. Resume at: {run_dir}/output/")
    click.echo("Next: linkright jobs find   (to see remaining jobs)")


# ── status ────────────────────────────────────────────────────────────────────

@jobsearch_group.command("status")
@click.argument("discovery_id")
@click.argument("state", type=click.Choice(["new", "saved", "dismissed"]))
def status_cmd(discovery_id: str, state: str) -> None:
    """Update the status of a discovery on sync.linkright.in.

    \b
    Valid states:  new | saved | dismissed

    To mark applied, use `linkright jobs apply <id>` instead — that
    triggers resume tailoring and creates an applications record.

    \b
    Examples:
      linkright jobs status <id> saved
      linkright jobs s <id> dismissed
    """
    resolved_id = _resolve_id(discovery_id)
    headers = _auth_headers()

    try:
        with _http() as client:
            resp = client.put(
                f"{_LINKRIGHT_API}/api/discoveries/{resolved_id}/status",
                headers=headers,
                json={"status": state},
            )
    except Exception as e:
        raise click.ClickException(f"Network error: {e}")

    if resp.status_code == 401:
        click.echo("Session expired. Run: linkright auth login", err=True)
        sys.exit(1)
    if resp.status_code == 404:
        raise click.ClickException(f"Discovery '{resolved_id}' not found.")
    if resp.status_code not in (200, 201):
        raise click.ClickException(f"API error {resp.status_code}: {resp.text[:200]}")

    disc = resp.json().get("discovery") or {}
    click.echo(
        f"Updated: {disc.get('title', resolved_id)} "
        f"[{disc.get('company_name', '')}] → {state}"
    )


# ── import ────────────────────────────────────────────────────────────────────

_REQUIRED_COLS = {"title", "company"}
_OPTIONAL_DEFAULTS = {
    "url": "",
    "location": "Unknown",
    "jd_text": "",
    "salary_min": None,
    "salary_max": None,
    "currency": "INR",
    "posted_date": None,
    "seniority": "",
    "notes": "",
    "tags": "",
}


@jobsearch_group.command("import")
@click.argument("csv_path", type=click.Path(exists=True, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Validate only — do not POST to API")
def import_cmd(csv_path: Path, dry_run: bool) -> None:
    """Import jobs from a CSV file into sync.linkright.in.

    \b
    Required columns: title, company
    Optional: url, location, jd_text, salary_min, salary_max, currency,
              posted_date, seniority, notes, tags

    Imported jobs are created with enrichment_status='pending' — scores
    appear in `linkright jobs find` after 2-3 minutes.
    """
    from datetime import date

    # Validate CSV schema BEFORE requiring auth (better UX)
    rows = []
    errors = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise click.ClickException("CSV file appears empty or has no header row.")

        col_set = {c.strip().lower() for c in reader.fieldnames}
        missing_required = _REQUIRED_COLS - col_set
        if missing_required:
            raise click.ClickException(
                f"CSV missing required column(s): {', '.join(sorted(missing_required))}. "
                f"Found columns: {', '.join(sorted(col_set))}"
            )

        for i, row in enumerate(reader, 2):  # 2 = first data row
            title = (row.get("title") or "").strip()
            company = (row.get("company") or "").strip()
            if not title:
                errors.append(f"Row {i}: 'title' is empty")
                continue
            if not company:
                errors.append(f"Row {i}: 'company' is empty")
                continue

            today = date.today().isoformat()
            rows.append({
                "title": title,
                "company_name": company,
                "job_url": (row.get("url") or "").strip() or None,
                "location": (row.get("location") or "Unknown").strip(),
                "jd_text": (row.get("jd_text") or "").strip() or None,
                "salary_min": _parse_number(row.get("salary_min")),
                "salary_max": _parse_number(row.get("salary_max")),
                "currency": (row.get("currency") or "INR").strip(),
                "posted_date": (row.get("posted_date") or today).strip() or today,
                "seniority": (row.get("seniority") or "").strip() or None,
                "notes": (row.get("notes") or "").strip() or None,
                "tags": [t.strip() for t in (row.get("tags") or "").split(",") if t.strip()],
                "source_type": "manual_csv",
                "enrichment_status": "pending",
            })

    if errors:
        click.echo(f"Validation errors in {csv_path.name}:")
        for e in errors:
            click.echo(f"  • {e}")
        raise click.ClickException(f"{len(errors)} row(s) skipped due to validation errors.")

    if not rows:
        click.echo("No valid rows found in CSV.")
        return

    if dry_run:
        click.echo(f"Dry-run: {len(rows)} rows would be imported from {csv_path.name}.")
        for r in rows[:5]:
            click.echo(f"  • {r['title']} @ {r['company_name']} ({r['location']})")
        if len(rows) > 5:
            click.echo(f"  ... and {len(rows) - 5} more")
        return

    # Auth required for actual import
    headers = _auth_headers()

    # POST each row
    imported = 0
    failed = 0
    click.echo(f"Importing {len(rows)} jobs from {csv_path.name}...")
    try:
        with _http() as client:
            for row in rows:
                try:
                    resp = client.post(
                        f"{_LINKRIGHT_API}/api/discoveries",
                        headers=headers,
                        json=row,
                    )
                    if resp.status_code in (200, 201):
                        imported += 1
                    elif resp.status_code == 405:
                        # POST endpoint not yet deployed — fail fast with helpful message
                        click.echo(
                            "\n  Error: /api/discoveries POST endpoint not available (405 Method Not Allowed).\n"
                            "  The import feature requires a website deployment update.\n"
                            "  Use the web UI at sync.linkright.in to import jobs manually,\n"
                            "  or wait for the next website release.",
                            err=True,
                        )
                        raise SystemExit(1)
                    else:
                        failed += 1
                        if failed <= 3:
                            click.echo(f"  Warning: {row['title']} @ {row['company_name']} — {resp.status_code}", err=True)
                except Exception as e:
                    failed += 1
                    if failed <= 3:
                        click.echo(f"  Warning: {row['title']} @ {row['company_name']} — {e}", err=True)
    except Exception as e:
        raise click.ClickException(f"Network error: {e}")

    click.echo(f"\nImported {imported} jobs" + (f" ({failed} failed)" if failed else "") + ".")
    click.echo("Run `linkright jobs find` in 2-3 min for fit scores.")


# ── Legacy commands (preserved from scaffold) ─────────────────────────────────

@jobsearch_group.command("evaluate")
@click.option("--jd", "jd_path", required=True, type=click.Path(exists=True, path_type=Path),
              help="Path to JD text/markdown file")
@click.option("--jd-url", default=None, help="Optional source URL for the JD")
@click.option("--no-persist", is_flag=True, help="Do not write to MongoDB / disk")
def evaluate(jd_path: Path, jd_url: str | None, no_persist: bool) -> None:
    """Run 10-dimension evaluation on a JD (local MongoDB mode)."""
    from .evaluator import evaluate_jd
    jd_text = jd_path.read_text()
    try:
        result = evaluate_jd(jd_text, persist=not no_persist, jd_url=jd_url)
    except RuntimeError as e:
        raise click.ClickException(str(e))
    click.echo(f"Grade: {result['grade']}  •  Score: {result['overall_score']}/100  "
               f"•  Recommendation: {result['recommendation']}")
    click.echo("")
    click.echo("Dimensions:")
    for name, score in result["dimensions"].items():
        reason = result["dimension_reasons"].get(name, "")[:80]
        click.echo(f"  {name:22s} {score:5.1f}  — {reason}")
    click.echo("")
    click.echo(f"Persisted: {result['persisted_to']}")


@jobsearch_group.command("recommend")
@click.option("--top", "top_n", default=5, type=int, help="How many evaluations to list")
def recommend(top_n: int) -> None:
    """List top-N evaluations by overall score (queries local MongoDB)."""
    try:
        from ..db.mongo import get_db, ping
        if not ping():
            raise click.ClickException("MongoDB unreachable — run `linkright init`.")
        db = get_db()
        rows = list(db["evaluations"].find().sort("overall_score", -1).limit(top_n))
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Mongo query failed: {e}")
    if not rows:
        click.echo("No local evaluations yet. Use `linkright jobs find` for your website job feed.")
        return
    for i, r in enumerate(rows, 1):
        click.echo(f"{i}. [{r.get('grade', '?')}] {r.get('overall_score', 0):.1f}  "
                   f"{r.get('recommendation', '?'):9s}  jd={r.get('jd_hash', '')[:10]}  "
                   f"url={r.get('jd_url') or '-'}")


# ── Utilities ─────────────────────────────────────────────────────────────────

def _resolve_id(raw: str) -> str:
    """If raw looks like an integer (rank), fetch today's feed and resolve to UUID.

    Otherwise return raw as-is (assumed to be a UUID or partial UUID prefix).
    """
    raw = raw.strip()
    if raw.isdigit():
        rank = int(raw)
        try:
            from linkright.auth import require_session, api_headers
            sess = require_session()
            import httpx
            with httpx.Client(timeout=15, follow_redirects=True) as client:
                resp = client.get(
                    f"{_LINKRIGHT_API}/api/recommendations/today",
                    headers=api_headers(sess),
                )
            if resp.status_code == 200:
                rows = resp.json().get("top20") or []
                if 1 <= rank <= len(rows):
                    disc = rows[rank - 1].get("job_discoveries") or {}
                    disc_id = disc.get("id") or rows[rank - 1].get("discovery_id")
                    if disc_id:
                        return str(disc_id)
        except Exception:
            pass
        click.echo(
            f"Could not resolve rank {rank} to a discovery ID. "
            "Run `linkright jobs find` first and copy the full ID.",
            err=True,
        )
        sys.exit(1)
    return raw


def _parse_number(val: str | None) -> float | None:
    if not val:
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except Exception:
        return None


# ── find-slug — user-facing ATS slug lookup (read-only) ──────────────────────

@jobsearch_group.command("find-slug")
@click.argument("company")
@click.option("--website", default=None, help="Company website URL (improves accuracy).")
def find_slug(company: str, website: str | None) -> None:
    """Find the ATS slug for a company (read-only, no database writes).

    Useful for setting up a job watchlist — tells you which ATS provider
    a company uses and what their slug is, so you can track their jobs.

    \b
    Examples:
      linkright jobs find-slug stripe
      linkright jobs find-slug razorpay --website https://razorpay.com

    \b
    Output:
      Company: Stripe
      ATS:     greenhouse
      Slug:    stripe
      Jobs:    78 open positions
      Samples: Software Engineer, Product Manager, Data Engineer
    """
    import asyncio

    async def _run():
        from linkright.admin._slug_discovery_standalone import discover_ats_standalone, _validate, _ATS_PROBE_URLS
        import httpx

        click.echo(f"Looking up ATS for {company!r}...")
        result = await discover_ats_standalone(company, website)

        if not result.success:
            click.echo(f"\nCould not find ATS for {company!r}.")
            click.echo("Tips:")
            click.echo("  - Try passing --website https://<company>.com for better Tier 1 coverage")
            click.echo("  - Some companies use proprietary ATS (Workday, Oracle HCM) — no public API")
            return

        click.echo("")
        click.echo(f"Company : {company}")
        click.echo(f"ATS     : {result.ats_provider}")
        click.echo(f"Slug    : {result.ats_slug}")
        click.echo(f"Jobs    : {result.jobs_count} open positions")

        # Try to fetch sample job titles
        titles: list[str] = []
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=8) as client:
                url_tmpl = _ATS_PROBE_URLS.get(result.ats_provider, "")
                if url_tmpl and result.ats_slug:
                    url = url_tmpl.format(slug=result.ats_slug)
                    r = await client.get(url, timeout=8)
                    if r.status_code == 200:
                        data = r.json()
                        if result.ats_provider == "ashby":
                            jobs = data.get("jobPostings") or data.get("jobs") or []
                            titles = [j.get("title") or j.get("jobTitle") for j in jobs[:3] if j.get("title") or j.get("jobTitle")]
                        elif result.ats_provider == "greenhouse":
                            jobs = data.get("jobs") or []
                            titles = [j.get("title") for j in jobs[:3] if j.get("title")]
                        elif result.ats_provider == "lever":
                            jobs = data if isinstance(data, list) else []
                            titles = [j.get("text") for j in jobs[:3] if j.get("text")]
        except Exception:
            pass

        if titles:
            click.echo(f"Sample  : {', '.join(titles)}")

        click.echo("")
        click.echo(
            f"Use with: linkright admin companies import (to add to company DB)"
        )

    asyncio.run(_run())
