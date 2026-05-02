"""`linkright admin` — Oracle Postgres admin command group.

Subcommands:
  companies import <file.json>          Upsert company JSON into Oracle PG
  companies import --dry-run <file.json> Validate only (no writes)
  companies stats                        Health stats from Oracle PG
  slug-discovery batch <names.txt>       Run Layer 1 ATS discovery

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

    pool = await asyncpg.create_pool(oracle_pg_url, min_size=1, max_size=3, ssl="require")

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

    pool = await asyncpg.create_pool(oracle_pg_url, min_size=1, max_size=2, ssl="require")
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


@admin_group.group(name="slug-discovery")
def slug_discovery_group() -> None:
    """ATS slug discovery — Layer 1 HTML scrape over company lists."""


@slug_discovery_group.command("batch")
@click.argument("names_file", type=click.Path(exists=True, path_type=Path))
@click.option("--ats", type=click.Choice(["greenhouse", "lever", "ashby", "all"]),
              default="all", help="Which ATS to probe (default: all three).")
@click.option("--dry-run", is_flag=True, default=False,
              help="Print which slugs would be tried — no HTTP calls.")
def slug_discovery_batch(names_file: Path, ats: str, dry_run: bool) -> None:
    """Run Layer 1 ATS slug discovery over a list of company names.

    NAMES_FILE: plain text, one company name per line.

    \b
    Example:
      linkright admin slug-discovery batch targets.txt --ats greenhouse
    """
    names = [
        line.strip() for line in names_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not names:
        raise click.ClickException("names_file is empty.")

    click.echo(f"Loaded {len(names)} company name(s) for slug discovery (ats={ats}).")

    if dry_run:
        for name in names:
            slug_candidate = name.lower().replace(" ", "").replace(",", "").replace(".", "")
            click.echo(f"  [dry-run] {name!r} → slug candidate: {slug_candidate!r}")
        return

    # Actual implementation stub — full Layer 1 scraper ships in Sprint B.
    # For now: print guidance and exit cleanly so the CLI surface is wired up.
    click.echo(
        "\nLayer 1 auto-discovery (Sprint B) is not yet implemented.\n"
        "This command surface is ready — implementation ships with the slug-discovery scraper.\n"
        "Interim: use `linkright admin companies import` to add verified slugs manually."
    )
