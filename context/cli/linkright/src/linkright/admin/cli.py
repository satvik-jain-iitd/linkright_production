"""`linkright admin` — Oracle Postgres admin command group.

Subcommands:
  companies import <file.json>          Upsert company JSON into Oracle PG
  companies import --dry-run <file.json> Validate only (no writes)
  companies stats                        Health stats from Oracle PG
  slug-discovery <company>               Single company discovery (verbose)
  slug-discovery batch <names.txt>       Parallel batch discovery
  slug-discovery validate-all [--max N]  Layer 4 self-heal trigger
  slug-discovery stats                   Last-24h discovery stats

All writes go to Oracle Postgres.  ORACLE_PG_URL must be set in env or
~/.linkright/.env.  Commands refuse to proceed if it is not configured.

This command group is hidden from `linkright --help` (backend-only tooling).
Install the Oracle Postgres driver with:  pip install linkright[admin]
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Optional

import click

# ── Pydantic model for incoming company JSON ─────────────────────────────────

try:
    from pydantic import BaseModel, field_validator, model_validator
    _PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseModel, validator  # type: ignore[assignment]
    _PYDANTIC_V2 = False


class CompanyResearchRow(BaseModel):
    """Schema for a single company record in the admin import JSON file.

    Mirrors the Oracle PG `companies` table columns.
    Required: name.  Everything else is optional.
    """
    name: str
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    founded_year: Optional[int] = None
    employee_size_range: Optional[str] = None
    hq_city: Optional[str] = None
    hq_country: Optional[str] = None
    ats_provider: Optional[str] = None
    ats_slug: Optional[str] = None
    tech_stack: list[str] = []
    hiring_active: bool = False
    ai_native: bool = False
    interesting_angle: Optional[str] = None
    description: Optional[str] = None
    source: list[str] = []
    evidence_sources: list[str] = []
    confidence: str = "medium"

    if _PYDANTIC_V2:
        @field_validator("confidence")
        @classmethod
        def confidence_must_be_valid(cls, v: str) -> str:
            if v not in ("high", "medium", "low"):
                raise ValueError(f"confidence must be high/medium/low, got: {v!r}")
            return v

        @model_validator(mode="after")
        def ats_pair_required_together(self) -> "CompanyResearchRow":
            if bool(self.ats_provider) != bool(self.ats_slug):
                raise ValueError("ats_provider and ats_slug must both be set or both be absent")
            return self
    else:
        @validator("confidence")
        @classmethod
        def confidence_must_be_valid(cls, v: str) -> str:
            if v not in ("high", "medium", "low"):
                raise ValueError(f"confidence must be high/medium/low, got: {v!r}")
            return v


def _canonical_id(row: CompanyResearchRow) -> str:
    """Deterministic dedup key: sha256 of website or linkedin_url (whichever present)."""
    key = row.website or row.linkedin_url or row.name
    return hashlib.sha256(key.lower().strip().encode()).hexdigest()[:40]


def _get_oracle_pg_url() -> str:
    """Return ORACLE_PG_URL from env or ~/.linkright/.env.  Fails fast with guidance."""
    import os
    from pathlib import Path

    # Try env first (set by shell or CI)
    url = os.environ.get("ORACLE_PG_URL", "")
    if url:
        return url

    # Try ~/.linkright/.env
    env_file = Path.home() / ".linkright" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("ORACLE_PG_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                if url:
                    return url

    raise click.ClickException(
        "ORACLE_PG_URL is not set.\n\n"
        "  1. Provision Oracle Postgres by following:\n"
        "     specs/oracle-pg-runbook-2026-05-03.md\n"
        "  2. Then add to ~/.linkright/.env:\n"
        "     ORACLE_PG_URL=postgres://linkright_app:<pass>@oracle-pg.linkright.in:5432/linkright_jobs\n"
    )


def _set_oracle_pg_url_env(oracle_pg_url: str) -> None:
    """Inject ORACLE_PG_URL into os.environ so worker oracle/pg.py sees it."""
    import os
    os.environ["ORACLE_PG_URL"] = oracle_pg_url


async def _import_companies_async(
    rows: list[CompanyResearchRow],
    oracle_pg_url: str,
    dry_run: bool,
) -> dict[str, int]:
    """Async core of the import command.  Returns {imported, updated, skipped}."""
    try:
        import asyncpg  # type: ignore[import]
    except ImportError:
        raise click.ClickException(
            "asyncpg is not installed — required for Oracle Postgres admin commands.\n\n"
            "  Install with:  pip install linkright[admin]\n\n"
            "  Then follow the runbook: specs/oracle-pg-runbook-2026-05-03.md"
        )

    counts = {"imported": 0, "updated": 0, "skipped": 0, "errors": 0}

    if dry_run:
        click.echo(f"[dry-run] Validated {len(rows)} rows — no writes performed.")
        return counts

    # SSL governed by URL's sslmode param (libpq semantics) — see worker/app/oracle/pg.py
    # 10s outer timeout via wait_for so create_pool doesn't hang forever on unreachable host.
    try:
        pool = await asyncio.wait_for(
            asyncpg.create_pool(oracle_pg_url, min_size=1, max_size=3),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        raise click.ClickException(
            "Oracle PG connection timeout (10s). Check ORACLE_PG_URL or run "
            "`linkright doctor` to verify connectivity."
        )
    except OSError as exc:
        raise click.ClickException(
            f"Oracle PG connection failed: {exc}. Verify the host is reachable."
        )

    _UPSERT = """
        INSERT INTO companies (
            canonical_id, name, website, linkedin_url,
            industry, stage, founded_year, employee_size_range,
            hq_city, hq_country,
            ats_provider, ats_slug,
            tech_stack, hiring_active, ai_native,
            interesting_angle, description,
            source, evidence_sources, confidence
        ) VALUES (
            $1, $2, $3, $4,
            $5, $6, $7, $8,
            $9, $10,
            $11, $12,
            $13, $14, $15,
            $16, $17,
            $18, $19, $20
        )
        ON CONFLICT (canonical_id) DO UPDATE SET
            name              = EXCLUDED.name,
            website           = COALESCE(EXCLUDED.website, companies.website),
            linkedin_url      = COALESCE(EXCLUDED.linkedin_url, companies.linkedin_url),
            industry          = COALESCE(EXCLUDED.industry, companies.industry),
            stage             = COALESCE(EXCLUDED.stage, companies.stage),
            founded_year      = COALESCE(EXCLUDED.founded_year, companies.founded_year),
            employee_size_range = COALESCE(EXCLUDED.employee_size_range, companies.employee_size_range),
            hq_city           = COALESCE(EXCLUDED.hq_city, companies.hq_city),
            hq_country        = COALESCE(EXCLUDED.hq_country, companies.hq_country),
            ats_provider      = COALESCE(EXCLUDED.ats_provider, companies.ats_provider),
            ats_slug          = COALESCE(EXCLUDED.ats_slug, companies.ats_slug),
            hiring_active     = EXCLUDED.hiring_active,
            ai_native         = EXCLUDED.ai_native,
            interesting_angle = COALESCE(EXCLUDED.interesting_angle, companies.interesting_angle),
            description       = COALESCE(EXCLUDED.description, companies.description),
            confidence        = EXCLUDED.confidence,
            updated_at        = NOW()
        RETURNING (xmax = 0) AS inserted
    """

    try:
        async with pool.acquire() as conn:
            for row in rows:
                cid = _canonical_id(row)
                try:
                    result = await conn.fetchrow(
                        _UPSERT,
                        cid, row.name, row.website, row.linkedin_url,
                        row.industry, row.stage, row.founded_year, row.employee_size_range,
                        row.hq_city, row.hq_country,
                        row.ats_provider, row.ats_slug,
                        row.tech_stack, row.hiring_active, row.ai_native,
                        row.interesting_angle, row.description,
                        row.source, row.evidence_sources, row.confidence,
                    )
                    if result and result["inserted"]:
                        counts["imported"] += 1
                    else:
                        counts["updated"] += 1
                except Exception as e:
                    click.echo(f"  ERROR: {row.name} — {e}", err=True)
                    counts["errors"] += 1
    finally:
        await pool.close()

    return counts


async def _stats_async(oracle_pg_url: str) -> None:
    """Print health stats from Oracle PG companies table."""
    try:
        import asyncpg
    except ImportError:
        raise click.ClickException(
            "asyncpg is not installed — required for Oracle Postgres admin commands.\n\n"
            "  Install with:  pip install linkright[admin]\n\n"
            "  Then follow the runbook: specs/oracle-pg-runbook-2026-05-03.md"
        )

    # SSL governed by URL's sslmode param (libpq semantics) — see worker/app/oracle/pg.py
    # 10s outer timeout via wait_for so create_pool doesn't hang forever on unreachable host.
    try:
        pool = await asyncio.wait_for(
            asyncpg.create_pool(oracle_pg_url, min_size=1, max_size=2),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        raise click.ClickException(
            "Oracle PG connection timeout (10s). Check ORACLE_PG_URL or run "
            "`linkright doctor` to verify connectivity."
        )
    except OSError as exc:
        raise click.ClickException(
            f"Oracle PG connection failed: {exc}. Verify the host is reachable."
        )
    try:
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM companies")
            high_conf = await conn.fetchval("SELECT COUNT(*) FROM companies WHERE confidence='high'")
            hiring = await conn.fetchval("SELECT COUNT(*) FROM companies WHERE hiring_active=TRUE")
            by_ats = await conn.fetch(
                "SELECT ats_provider, COUNT(*) as n FROM companies "
                "WHERE ats_provider IS NOT NULL GROUP BY ats_provider ORDER BY n DESC"
            )
            by_industry = await conn.fetch(
                "SELECT industry, COUNT(*) as n FROM companies "
                "WHERE industry IS NOT NULL GROUP BY industry ORDER BY n DESC LIMIT 8"
            )
    finally:
        await pool.close()

    click.echo(f"\nOracle PG — companies table stats")
    click.echo(f"  Total companies   : {total}")
    click.echo(f"  High-confidence   : {high_conf}")
    click.echo(f"  Hiring active     : {hiring}")
    click.echo(f"\n  By ATS provider:")
    for r in by_ats:
        click.echo(f"    {r['ats_provider']:<20} {r['n']}")
    click.echo(f"\n  By industry (top 8):")
    for r in by_industry:
        click.echo(f"    {(r['industry'] or 'unknown'):<25} {r['n']}")


# ── Click command group ───────────────────────────────────────────────────────

@click.group(name="admin", hidden=True)
def admin_group() -> None:
    """Admin commands (backend-only — not for end users).

    These commands manage Oracle Postgres infrastructure: company-DB seed,
    slug discovery, batch ingestion. Hidden from `linkright --help`.

    \b
    All writes go to Oracle Postgres (ORACLE_PG_URL).
    Set ORACLE_PG_URL in env or ~/.linkright/.env before using.
    Requires:  pip install linkright[admin]
    """


@admin_group.group(name="companies")
def companies_group() -> None:
    """Company knowledge base — import, query, stats."""


@companies_group.command("import")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--dry-run", is_flag=True, default=False,
              help="Validate JSON schema only — no writes to Oracle PG.")
def companies_import(file: Path, dry_run: bool) -> None:
    """Import company JSON into Oracle Postgres.

    FILE must be a JSON file: either a single CompanyResearchRow object
    or a JSON array of CompanyResearchRow objects.

    \b
    Examples:
      linkright admin companies import companies.json
      linkright admin companies import --dry-run companies.json
    """
    try:
        raw: Any = json.loads(file.read_text())
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in {file}: {e}")

    # Accept single object or array
    items: list[dict] = raw if isinstance(raw, list) else [raw]
    if not items:
        raise click.ClickException("JSON file is empty — nothing to import.")

    # Validate all rows first (fail-fast — don't write partial data)
    rows: list[CompanyResearchRow] = []
    errors: list[str] = []
    for i, item in enumerate(items):
        try:
            rows.append(CompanyResearchRow(**item))
        except Exception as e:
            errors.append(f"  Row {i}: {e}")

    if errors:
        click.echo(f"Validation failed — {len(errors)} error(s):", err=True)
        for err in errors:
            click.echo(err, err=True)
        sys.exit(1)

    click.echo(f"Validated {len(rows)} row(s). ", nl=False)

    oracle_url = _get_oracle_pg_url()

    counts = asyncio.run(_import_companies_async(rows, oracle_url, dry_run))

    if not dry_run:
        click.echo(
            f"Done — imported: {counts['imported']}, "
            f"updated: {counts['updated']}, "
            f"errors: {counts['errors']}"
        )
        if counts["errors"]:
            sys.exit(1)


@companies_group.command("stats")
def companies_stats() -> None:
    """Print health stats from Oracle PG companies table."""
    oracle_url = _get_oracle_pg_url()
    asyncio.run(_stats_async(oracle_url))


# ── slug-discovery command group ─────────────────────────────────────────────

class _SlugDiscoveryGroup(click.Group):
    """Click group that accepts a company name as positional argument.

    `linkright admin slug-discovery openai` invokes the single-company discovery.
    `linkright admin slug-discovery batch companies.txt` runs the batch subcommand.
    """

    def parse_args(self, ctx, args):
        # If first arg is not a known subcommand, treat the whole invocation as
        # `single <company>`. This lets both forms work:
        #   linkright admin slug-discovery openai
        #   linkright admin slug-discovery single openai
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["single"] + args
        return super().parse_args(ctx, args)


@admin_group.group(name="slug-discovery", cls=_SlugDiscoveryGroup)
def slug_discovery_group() -> None:
    """ATS slug discovery — 3-tier auto-discovery + Layer 4 self-heal.

    \b
    Usage:
      linkright admin slug-discovery <company>       # single company (verbose)
      linkright admin slug-discovery batch <file>    # parallel batch
      linkright admin slug-discovery validate-all    # Layer 4 self-heal
      linkright admin slug-discovery stats           # last-24h stats
    """


@slug_discovery_group.command("single")
@click.argument("company")
@click.option("--website", default=None, help="Company website URL (improves Tier 1 coverage).")
def slug_discovery_single(company: str, website: Optional[str]) -> None:
    """Discover ATS slug for a single company (verbose output).

    \b
    Examples:
      linkright admin slug-discovery single openai
      linkright admin slug-discovery single razorpay --website https://razorpay.com
    """
    oracle_url = _get_oracle_pg_url()
    _set_oracle_pg_url_env(oracle_url)

    async def _run():
        from linkright.admin._slug_discovery_runner import discover_single_verbose
        return await discover_single_verbose(company, website)

    asyncio.run(_run())


@slug_discovery_group.command("batch")
@click.argument("names_file", type=click.Path(exists=True, path_type=Path))
@click.option("--concurrency", default=5, type=int,
              help="Max parallel discoveries (default: 5).")
@click.option("--dry-run", is_flag=True, default=False,
              help="Print slug candidates — no HTTP calls.")
def slug_discovery_batch(names_file: Path, concurrency: int, dry_run: bool) -> None:
    """Run 3-tier slug discovery over a list of company names in parallel.

    NAMES_FILE: plain text, one company name per line.
    Lines starting with '#' are treated as comments and skipped.

    \b
    Example:
      linkright admin slug-discovery batch targets.txt
      linkright admin slug-discovery batch targets.txt --concurrency 10
    """
    names = [
        line.strip() for line in names_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not names:
        raise click.ClickException("names_file is empty.")

    click.echo(f"Loaded {len(names)} company name(s).")

    if dry_run:
        from linkright.admin._slug_discovery_runner import slug_variants_for
        for name in names:
            variants = slug_variants_for(name)
            click.echo(f"  [dry-run] {name!r} → {variants[:3]}")
        return

    oracle_url = _get_oracle_pg_url()
    _set_oracle_pg_url_env(oracle_url)

    async def _run():
        from linkright.admin._slug_discovery_runner import discover_batch
        await discover_batch(names, concurrency=concurrency)

    asyncio.run(_run())


@slug_discovery_group.command("validate-all")
@click.option("--max", "max_companies", default=100, type=int,
              help="Maximum companies to validate in this run (default: 100).")
def slug_discovery_validate_all(max_companies: int) -> None:
    """Layer 4 self-heal: re-validate stale ATS slugs, heal dead ones.

    Picks companies with last_verified_at > 7 days ago, checks job counts,
    increments consecutive_zero_count on misses, and triggers re-discovery
    after 7 consecutive zeros.

    \b
    Example:
      linkright admin slug-discovery validate-all
      linkright admin slug-discovery validate-all --max 50
    """
    oracle_url = _get_oracle_pg_url()
    _set_oracle_pg_url_env(oracle_url)

    async def _run():
        # Layout-tolerant worker discovery lives in _slug_validator_runner — it walks
        # the ancestry trying both worker/ (worktree) and repo/worker/ (production).
        from linkright.admin._slug_validator_runner import validate_and_heal_slugs
        report = await validate_and_heal_slugs(batch_size=max_companies)
        click.echo(f"\nLayer 4 validation complete:")
        click.echo(f"  Validated       : {report.validated}")
        click.echo(f"  Healed          : {report.healed}")
        click.echo(f"  Marked zero     : {report.marked_zero}")
        click.echo(f"  Errors          : {len(report.errors)}")
        click.echo(f"  Duration        : {report.duration_ms}ms")
        if report.errors:
            click.echo("\n  Errors:")
            for err in report.errors[:5]:
                click.echo(f"    {err}")

    asyncio.run(_run())


@slug_discovery_group.command("stats")
def slug_discovery_stats() -> None:
    """Show discovery statistics from the last 24 hours."""
    oracle_url = _get_oracle_pg_url()
    _set_oracle_pg_url_env(oracle_url)

    async def _run():
        try:
            import asyncpg
        except ImportError:
            raise click.ClickException(
                "asyncpg not installed — run: pip install linkright[admin]"
            )
        # SSL governed by URL's sslmode param (libpq semantics) — see worker/app/oracle/pg.py
        # 10s outer timeout via wait_for so create_pool doesn't hang forever on unreachable host.
        try:
            pool = await asyncio.wait_for(
                asyncpg.create_pool(oracle_url, min_size=1, max_size=2),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            raise click.ClickException(
                "Oracle PG connection timeout (10s). Check ORACLE_PG_URL or run "
                "`linkright doctor` to verify connectivity."
            )
        except OSError as exc:
            raise click.ClickException(
                f"Oracle PG connection failed: {exc}. Verify the host is reachable."
            )
        try:
            async with pool.acquire() as conn:
                total_attempts = await conn.fetchval(
                    "SELECT COUNT(*) FROM slug_discovery_cache "
                    "WHERE attempted_at > NOW() - INTERVAL '24 hours'"
                )
                successful = await conn.fetchval(
                    "SELECT COUNT(*) FROM slug_discovery_cache "
                    "WHERE attempted_at > NOW() - INTERVAL '24 hours' "
                    "AND ats_provider IS NOT NULL AND jobs_count > 0"
                )
                by_tier = await conn.fetch(
                    "SELECT source_tier, COUNT(*) as n FROM slug_discovery_cache "
                    "WHERE attempted_at > NOW() - INTERVAL '24 hours' "
                    "GROUP BY source_tier ORDER BY n DESC"
                )
                by_ats = await conn.fetch(
                    "SELECT ats_provider, COUNT(*) as n FROM slug_discovery_cache "
                    "WHERE attempted_at > NOW() - INTERVAL '24 hours' "
                    "AND ats_provider IS NOT NULL "
                    "GROUP BY ats_provider ORDER BY n DESC"
                )
        finally:
            await pool.close()

        click.echo(f"\nSlug discovery stats (last 24h):")
        click.echo(f"  Total attempts  : {total_attempts}")
        click.echo(f"  Successful      : {successful}")
        if total_attempts:
            pct = int(100 * (successful or 0) / total_attempts)
            click.echo(f"  Success rate    : {pct}%")
        click.echo(f"\n  By tier:")
        for r in by_tier:
            click.echo(f"    {(r['source_tier'] or 'unknown'):<20} {r['n']}")
        click.echo(f"\n  By ATS provider (successful):")
        for r in by_ats:
            click.echo(f"    {r['ats_provider']:<20} {r['n']}")

    asyncio.run(_run())
