"""Slug discovery runner — bridges the CLI package to the worker oracle module.

The worker oracle/slug_discovery.py is the authoritative implementation.
This module re-exports its key functions and provides CLI-friendly helpers.

When run from the repository root (where `worker/` is on the path), this
module delegates to `app.oracle.slug_discovery`.  If the worker is not on the
path (e.g., the user installed only the CLI package), it falls back to a
self-contained implementation that does NOT write to Oracle PG.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click


def _ensure_worker_on_path() -> bool:
    """Try to add the worker root to sys.path. Returns True if it worked.

    Walks up from this file's location and tries each ancestor as a candidate
    repo root, looking for either `worker/` (worktree layout) or `repo/worker/`
    (production-monorepo layout). Layout-tolerant: works whether the CLI lives
    in `<repo>/context/cli/linkright/...` or `<wt>/context/cli/linkright/...`.
    """
    this_file = Path(__file__).resolve()
    # Walk up to 12 ancestors; check both layouts at each level.
    seen = {Path(p).resolve() for p in sys.path}
    for parent in this_file.parents[:12]:
        for sub in ("worker", "repo/worker"):
            candidate = parent / sub
            if candidate.exists() and candidate.resolve() not in seen:
                sys.path.insert(0, str(candidate))
                try:
                    import app.oracle.slug_discovery  # noqa: F401
                    return True
                except ImportError:
                    sys.path.pop(0)
    return False


def _import_discover_ats():
    """Import discover_ats from worker, falling back to bundled copy."""
    _ensure_worker_on_path()
    try:
        from app.oracle.slug_discovery import discover_ats
        return discover_ats
    except ImportError:
        # Bundled fallback (no Oracle PG writes)
        from linkright.admin._slug_discovery_standalone import discover_ats_standalone
        return discover_ats_standalone


def slug_variants_for(company_name: str) -> list[str]:
    """Return slug variants for a company name (for dry-run display)."""
    _ensure_worker_on_path()
    try:
        from app.oracle.slug_discovery import _slug_variants
        return _slug_variants(company_name)
    except ImportError:
        import re
        condensed  = re.sub(r"[^a-z0-9]", "", company_name.lower())
        hyphenated = re.sub(r"[^a-z0-9-]", "-", company_name.lower()).strip("-")
        return [condensed, hyphenated]


async def discover_single_verbose(
    company: str,
    website: Optional[str] = None,
) -> None:
    """Run discover_ats for a single company and print verbose results."""
    discover_ats = _import_discover_ats()

    click.echo(f"Discovering ATS slug for: {company!r}")
    if website:
        click.echo(f"  Website hint   : {website}")
    click.echo("")

    import time
    t0 = time.monotonic()
    result = await discover_ats(company, website)
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    if result.success:
        click.echo(f"  Status         : FOUND")
        click.echo(f"  ATS provider   : {result.ats_provider}")
        click.echo(f"  ATS slug       : {result.ats_slug}")
        click.echo(f"  Source tier    : {result.source_tier}")
        click.echo(f"  Jobs count     : {result.jobs_count}")
        click.echo(f"  Evidence URL   : {result.evidence_url}")
    else:
        click.echo(f"  Status         : NOT FOUND")
        click.echo(f"  Notes          : {result.notes or 'all 3 tiers failed'}")
    click.echo(f"  Elapsed        : {elapsed_ms}ms")


async def discover_batch(
    names: list[str],
    concurrency: int = 5,
) -> None:
    """Discover ATS slugs for multiple companies in parallel."""
    discover_ats = _import_discover_ats()

    sem = asyncio.Semaphore(concurrency)
    results = []

    async def _discover_one(name: str):
        async with sem:
            result = await discover_ats(name)
            return result

    import time
    t0 = time.monotonic()
    tasks = [_discover_one(name) for name in names]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    found = 0
    not_found = 0
    errors = 0

    for name, res in zip(names, all_results):
        if isinstance(res, Exception):
            click.echo(f"  ERROR  {name!r}: {res}")
            errors += 1
        elif res.success:
            click.echo(
                f"  FOUND  {name!r}: {res.ats_provider}/{res.ats_slug}"
                f" ({res.jobs_count} jobs) [{res.source_tier}]"
            )
            found += 1
        else:
            click.echo(f"  MISS   {name!r}: not found")
            not_found += 1

    click.echo(f"\nBatch complete in {elapsed_ms}ms:")
    click.echo(f"  Found     : {found}/{len(names)}")
    click.echo(f"  Not found : {not_found}/{len(names)}")
    if errors:
        click.echo(f"  Errors    : {errors}")
