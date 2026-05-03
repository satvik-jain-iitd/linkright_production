"""Click subcommand: ``linkright watch``.

Subcommands:
- ``linkright watch``                  — run the listener (foreground)
- ``linkright watch setup``            — configure shell alias + detect Chrome
- ``linkright watch install-service``  — install background daemon
- ``linkright watch uninstall-service``
- ``linkright watch status``           — one-shot diagnostic (Chrome reachable? key set? endpoint up?)
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click
import httpx

from linkright.watch import cdp, extractor, poster, service, setup as setup_mod

logger = logging.getLogger("linkright.watch")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s %(levelname)s %(name)s — %(message)s" if verbose else "%(asctime)s %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")
    # Mute noisy libraries unless --verbose
    if not verbose:
        for n in ("httpx", "httpcore", "websockets", "asyncio"):
            logging.getLogger(n).setLevel(logging.WARNING)


@click.group(invoke_without_command=True)
@click.option("--port", type=int, default=cdp.DEFAULT_PORT, show_default=True,
              help="Chrome DevTools port (Chrome must be started with --remote-debugging-port=<port>)")
@click.option("--host", default=cdp.DEFAULT_HOST, show_default=True,
              help="CDP host (almost always localhost)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose logging")
@click.pass_context
def watch_group(ctx: click.Context, port: int, host: str, verbose: bool) -> None:
    """Passive job-page capture via Chrome DevTools Protocol.

    \b
    Quick start (one-time):
      linkright watch setup           # writes shell alias + detects Chrome
      chrome                          # restart Chrome via the alias
      linkright watch                 # start the listener (foreground)

    \b
    Background daemon (optional):
      linkright watch install-service # auto-start on login
    """
    ctx.ensure_object(dict)
    ctx.obj["port"] = port
    ctx.obj["host"] = host
    ctx.obj["verbose"] = verbose
    _configure_logging(verbose)

    if ctx.invoked_subcommand is None:
        ctx.invoke(_run_watch_default)


# ── default subcommand: `linkright watch` (no further args) ─────────────────
@watch_group.command("run", hidden=True)
@click.pass_context
def _run_watch_default(ctx: click.Context) -> None:
    """Default action — start the foreground listener."""
    port: int = ctx.obj["port"]
    host: str = ctx.obj["host"]

    try:
        endpoint, capture_key = poster.load_capture_config()
    except ValueError as exc:
        click.echo(f"❌ {exc}", err=True)
        sys.exit(2)

    click.echo(f"🔍 linkright watch — listening on {host}:{port}")
    click.echo(f"   endpoint: {endpoint}")
    click.echo(f"   ctrl-C to stop\n")

    asyncio.run(_run_async(host, port, endpoint, capture_key))


async def _run_async(host: str, port: int, endpoint: str, capture_key: str) -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _stop_handler(*_args):
        if not stop_event.is_set():
            click.echo("\n👋 stopping…", err=True)
            stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop_handler)
        except NotImplementedError:
            # Windows or non-main-thread fallback
            signal.signal(sig, lambda *a: _stop_handler())

    # Single AsyncClient reused across captures (connection pooling)
    async with httpx.AsyncClient(timeout=poster.DEFAULT_TIMEOUT_SEC) as client:
        async def on_navigation(url: str, session_id: str, session) -> None:
            source = extractor.detect_portal(url)
            if source is None:
                return  # not a job page — silent skip

            logger.info("→ %s — %s", source, url)

            # Wait for SPA-style late renders before extracting
            await asyncio.sleep(cdp.SETTLE_DELAY_SEC)

            extracted = await cdp.evaluate_in_page(session, session_id, extractor.EXTRACTION_JS)
            if not extracted or not extracted.get(extractor.EXTRACTION_FAIL_KEY):
                reason = (extracted or {}).get("_reason", "no_data")
                logger.info("  skip: %s", reason)
                return

            payload = {
                "source": source,
                "job_url": extracted.get("job_url") or url.split("?")[0],
                "external_id": extracted.get("external_id"),
                "title": extracted.get("title"),
                "company_name": extracted.get("company_name"),
                "company_website": extracted.get("company_website"),
                "location": extracted.get("location"),
                "salary_text": extracted.get("salary_text"),
                "jd_text": extracted.get("jd_text"),
                "posted_at": extracted.get("posted_at"),
                "captured_at": poster.now_iso(),
                "raw_payload": extracted.get("raw_payload"),
            }

            ok, msg = await poster.post_capture(
                payload, endpoint=endpoint, capture_key=capture_key, client=client,
            )
            status = "✓" if ok else "✗"
            logger.info("  %s %s — %s", status, payload["company_name"], msg)

        try:
            await cdp.watch_loop(
                on_navigation, host=host, port=port, stop_event=stop_event,
            )
        except cdp.CDPError as exc:
            click.echo(f"❌ {exc}", err=True)
            sys.exit(1)


# ── `linkright watch setup` ─────────────────────────────────────────────────
@watch_group.command("setup")
@click.option("--dry-run", is_flag=True, help="Show what would change without writing")
@click.option("--shell-config", type=click.Path(path_type=Path),
              help="Override shell config path (default: auto-detect)")
def setup_cmd(dry_run: bool, shell_config: Optional[Path]) -> None:
    """One-time bootstrap: writes a `chrome` shell alias that launches Chrome
    with --remote-debugging-port=9222."""
    chrome_path = setup_mod.detect_chrome()
    if not chrome_path:
        click.echo("❌ Chrome / Chromium not found on this system.", err=True)
        click.echo("   Tried these paths:")
        from linkright.watch.setup import _CHROME_PATHS_DARWIN, _CHROME_PATHS_LINUX
        import platform as _plat
        for p in (_CHROME_PATHS_DARWIN if _plat.system() == "Darwin" else _CHROME_PATHS_LINUX):
            click.echo(f"     {p}")
        sys.exit(1)
    click.echo(f"✓ found Chrome: {chrome_path}")

    cfg_path = shell_config or setup_mod.detect_shell_config()
    if not cfg_path:
        click.echo("❌ Could not auto-detect your shell config. "
                   "Pass --shell-config <path> manually.", err=True)
        sys.exit(1)
    click.echo(f"✓ shell config: {cfg_path}")

    alias_line = setup_mod.build_alias_line(chrome_path, cfg_path)
    changed, msg = setup_mod.install_alias(cfg_path, alias_line, dry_run=dry_run)
    click.echo(f"{'✓' if changed else '·'} {msg}")

    click.echo("")
    click.echo("Next steps:")
    click.echo("  1. Reload your shell:    source " + str(cfg_path))
    click.echo("  2. Quit Chrome completely (cmd-Q on Mac), then start it via the alias:")
    click.echo("       chrome")
    click.echo("  3. Verify Chrome is in CDP mode:    curl http://localhost:9222/json/version")
    click.echo("  4. Start the listener:    linkright watch")


# ── `linkright watch install-service` ───────────────────────────────────────
@watch_group.command("install-service")
@click.option("--dry-run", is_flag=True, help="Print the service file without installing")
def install_service_cmd(dry_run: bool) -> None:
    """Install background daemon (launchd on Mac, systemd --user on Linux)."""
    ok, msg = service.install_service(dry_run=dry_run)
    click.echo(("✓" if ok else "✗") + " " + msg)
    if ok and not dry_run:
        click.echo("   logs:   ~/.linkright/watch.log")
        click.echo("   status: launchctl list | grep linkright    (Mac)")
        click.echo("           systemctl --user status linkright-watch  (Linux)")
    sys.exit(0 if ok else 1)


@watch_group.command("uninstall-service")
def uninstall_service_cmd() -> None:
    """Remove the background daemon."""
    ok, msg = service.uninstall_service()
    click.echo(("✓" if ok else "·") + " " + msg)


# ── `linkright watch list` ──────────────────────────────────────────────────
# Reads Oracle PG `job_discoveries` directly. This is the bridge that lets
# Phase 1 captures be SEEN from the CLI today — `linkright jobs find` reads
# Supabase via the website API, not Oracle PG, so without this command
# captures land in Oracle PG and stay invisible to the user. Phase 2 will
# unify the read path; for now this is the validation surface.
@watch_group.command("list")
@click.option("--limit", default=20, type=int, show_default=True,
              help="How many recent captures to show")
@click.option("--since", default=None,
              help='Filter to captures newer than this (e.g. "1 hour", "1 day", "1 week")')
@click.option("--source", default=None,
              help="Filter by source_type (e.g. capture_naukri)")
@click.option("--json", "as_json", is_flag=True, help="Output JSON instead of table")
def list_cmd(limit: int, since: Optional[str], source: Optional[str], as_json: bool) -> None:
    """Show recent captures from Oracle PG `job_discoveries`.

    \b
    Examples:
      linkright watch list                       # last 20 captures
      linkright watch list --limit 50
      linkright watch list --since "1 day"       # captures from past 24h
      linkright watch list --source capture_naukri
      linkright watch list --json | jq           # pipe-friendly

    \b
    Requires `pip install linkright[admin]` for the asyncpg driver.
    Reads ORACLE_PG_URL from env, then ~/.linkright/.env.oracle, then ~/.linkright/.env.
    """
    try:
        oracle_pg_url = poster.load_oracle_pg_url()
    except ValueError as exc:
        click.echo(f"✗ {exc}", err=True)
        sys.exit(2)

    try:
        import asyncpg  # noqa: F401
    except ImportError:
        click.echo(
            "✗ asyncpg not installed — required for `linkright watch list`.\n"
            "   Install with:  pip install linkright[admin]",
            err=True,
        )
        sys.exit(2)

    asyncio.run(_list_async(oracle_pg_url, limit, since, source, as_json))


async def _list_async(
    oracle_pg_url: str,
    limit: int,
    since: Optional[str],
    source: Optional[str],
    as_json: bool,
) -> None:
    import asyncpg
    import json as _json

    where_clauses: list[str] = []
    params: list = []

    if since:
        # PostgreSQL accepts INTERVAL strings like '1 hour' / '1 day' / '7 days'
        where_clauses.append(f"captured_at > NOW() - INTERVAL '{since}'")
    if source:
        params.append(source)
        where_clauses.append(f"source_type = ${len(params)}")

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.append(limit)
    sql = (
        "SELECT id::text AS id, title, company_name, location, salary_text, "
        "source_type, captured_at, job_url "
        f"FROM job_discoveries{where_sql} "
        f"ORDER BY captured_at DESC LIMIT ${len(params)}"
    )

    pool = await asyncpg.create_pool(oracle_pg_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
    finally:
        await pool.close()

    if as_json:
        out = [
            {
                "id": r["id"],
                "title": r["title"],
                "company_name": r["company_name"],
                "location": r["location"],
                "salary_text": r["salary_text"],
                "source_type": r["source_type"],
                "captured_at": r["captured_at"].isoformat() if r["captured_at"] else None,
                "job_url": r["job_url"],
            }
            for r in rows
        ]
        click.echo(_json.dumps(out, indent=2))
        return

    if not rows:
        click.echo("No captures found. Browse a Naukri job page after `linkright watch` is running.")
        return

    # Lazy import rich (already a core dep) for nice table rendering
    from rich.console import Console
    from rich.table import Table

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Captured", width=16)
    table.add_column("Source", width=16)
    table.add_column("Company", width=22, overflow="ellipsis")
    table.add_column("Title", overflow="ellipsis")
    table.add_column("Location", width=14, overflow="ellipsis")

    for i, r in enumerate(rows, 1):
        captured = r["captured_at"]
        captured_str = captured.strftime("%b %d %H:%M") if captured else "?"
        table.add_row(
            str(i),
            captured_str,
            r["source_type"] or "?",
            r["company_name"] or "?",
            r["title"] or "?",
            r["location"] or "-",
        )

    Console().print(table)
    click.echo(f"\n{len(rows)} capture(s). Use `linkright watch list --json` for full URLs / IDs.")


# ── `linkright watch status` ────────────────────────────────────────────────
@watch_group.command("status")
@click.pass_context
def status_cmd(ctx: click.Context) -> None:
    """One-shot diagnostic: Chrome CDP reachable? key set? endpoint live?"""
    port: int = ctx.obj["port"]
    host: str = ctx.obj["host"]

    asyncio.run(_status_async(host, port))


async def _status_async(host: str, port: int) -> None:
    rc = 0

    # 1. Capture config
    try:
        endpoint, key = poster.load_capture_config()
        click.echo(f"✓ capture key:   set (len={len(key)})")
        click.echo(f"✓ endpoint:      {endpoint}")
    except ValueError as exc:
        click.echo(f"✗ capture key:   {exc}")
        rc = 1
        endpoint = None

    # 2. Chrome CDP reachability
    try:
        ws_url = await cdp.discover_browser_ws(host, port, timeout=3.0)
        click.echo(f"✓ chrome CDP:    reachable at {host}:{port}")
        click.echo(f"  ws URL:        {ws_url}")
    except cdp.CDPError as exc:
        click.echo(f"✗ chrome CDP:    {exc}")
        rc = 1

    # 3. Worker /health
    if endpoint:
        health_url = endpoint.replace("/api/captures", "/health")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(health_url)
            if resp.status_code == 200:
                click.echo(f"✓ worker health: {health_url} → 200")
            else:
                click.echo(f"⚠ worker health: {health_url} → {resp.status_code}")
        except httpx.RequestError as exc:
            click.echo(f"⚠ worker health: {health_url} unreachable ({exc})")

    sys.exit(rc)
