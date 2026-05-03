#!/usr/bin/env python3
"""Oracle Postgres smoke test — run AFTER migrations + seed are applied.

Usage:
    ORACLE_PG_URL=postgres://... python scripts/smoke_oracle_pg.py

Checks:
  1. Connect + server version
  2. Extensions: vector, pg_trgm
  3. Tables: companies, slug_discovery_cache, enriched_jobs_cache
  4. Seed count: >= 31 rows in companies
  5. Round-trip: INSERT test row + DELETE

Exit code 0 = all checks PASS.
Exit code 1 = one or more checks FAIL.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import textwrap

GREEN = "\033[32m"
RED   = "\033[31m"
DIM   = "\033[2m"
RST   = "\033[0m"

ORACLE_PG_URL = os.environ.get("ORACLE_PG_URL", "")
EXPECTED_TABLES = {"companies", "slug_discovery_cache", "enriched_jobs_cache"}
EXPECTED_EXTENSIONS = {"vector", "pg_trgm"}
MIN_SEED_ROWS = 31


def _ok(msg: str) -> None:
    print(f"  {GREEN}PASS{RST}  {msg}")

def _fail(msg: str) -> None:
    print(f"  {RED}FAIL{RST}  {msg}", file=sys.stderr)


async def run_smoke() -> bool:
    """Run all checks.  Returns True if all pass."""
    if not ORACLE_PG_URL:
        print(
            f"{RED}ERROR{RST}: ORACLE_PG_URL is not set.\n"
            "Export ORACLE_PG_URL before running this script.\n"
            "  export ORACLE_PG_URL=postgres://linkright_app:<pass>@oracle-pg.linkright.in:5432/linkright_jobs",
            file=sys.stderr,
        )
        return False

    try:
        import asyncpg
    except ImportError:
        print(f"{RED}ERROR{RST}: asyncpg not installed. Run: pip install asyncpg", file=sys.stderr)
        return False

    # SSL governed by URL's sslmode param (libpq semantics) — see app/oracle/pg.py.
    # Today: sslmode=prefer in URL; switch to sslmode=require once Let's Encrypt is on the VPS.
    #
    # Determine whether the URL explicitly mandates TLS — if it does, we MUST NOT
    # fall back to ssl=False on connect failure, because that would silently turn
    # a cert-verification problem into an accepted plaintext connection (security
    # downgrade). Only allow the plaintext fallback for permissive sslmodes
    # (prefer/allow/disable) where the URL author has signalled it's acceptable.
    from urllib.parse import urlparse, parse_qs
    _qs = parse_qs(urlparse(ORACLE_PG_URL).query)
    _sslmode = (_qs.get("sslmode", [""])[0] or "prefer").lower()
    _strict_tls = _sslmode in ("require", "verify-ca", "verify-full")

    try:
        pool = await asyncpg.create_pool(ORACLE_PG_URL, min_size=1, max_size=2, command_timeout=15)
    except Exception as primary_exc:
        if _strict_tls:
            _fail(f"Could not connect to Oracle PG (sslmode={_sslmode}, no plaintext fallback): {primary_exc}")
            return False
        try:
            pool = await asyncpg.create_pool(ORACLE_PG_URL, min_size=1, max_size=2, ssl=False,
                                              command_timeout=15)
            print(f"  {DIM}Note: connected without SSL (sslmode={_sslmode} permits plaintext; not safe for production){RST}")
        except Exception as e:
            _fail(f"Could not connect to Oracle PG: {e}")
            return False

    all_pass = True
    async with pool.acquire() as conn:

        # ── Check 1: Server version ──────────────────────────────────────────
        try:
            version = await conn.fetchval("SELECT version()")
            _ok(f"Connected — {version[:60]}")
        except Exception as e:
            _fail(f"version() failed: {e}")
            all_pass = False

        # ── Check 2: Extensions ──────────────────────────────────────────────
        try:
            installed = {
                r["extname"]
                for r in await conn.fetch(
                    "SELECT extname FROM pg_extension WHERE extname = ANY($1)",
                    list(EXPECTED_EXTENSIONS),
                )
            }
            missing_ext = EXPECTED_EXTENSIONS - installed
            if missing_ext:
                _fail(f"Missing extensions: {missing_ext} — run `CREATE EXTENSION IF NOT EXISTS ...`")
                all_pass = False
            else:
                _ok(f"Extensions present: {', '.join(sorted(EXPECTED_EXTENSIONS))}")
        except Exception as e:
            _fail(f"Extension check failed: {e}")
            all_pass = False

        # ── Check 3: Tables ──────────────────────────────────────────────────
        try:
            tables = {
                r["tablename"]
                for r in await conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public'"
                )
            }
            missing_tables = EXPECTED_TABLES - tables
            if missing_tables:
                _fail(f"Missing tables: {missing_tables} — run migrations 001-003")
                all_pass = False
            else:
                _ok(f"Tables present: {', '.join(sorted(EXPECTED_TABLES))}")
        except Exception as e:
            _fail(f"Table check failed: {e}")
            all_pass = False

        # ── Check 4: Seed count ──────────────────────────────────────────────
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM companies")
            if count < MIN_SEED_ROWS:
                _fail(f"Seed count {count} < {MIN_SEED_ROWS} — run migration 004")
                all_pass = False
            else:
                _ok(f"Seed rows: {count} (>= {MIN_SEED_ROWS} required)")
        except Exception as e:
            _fail(f"Seed count check failed: {e}")
            all_pass = False

        # ── Check 5: Round-trip INSERT + DELETE ──────────────────────────────
        test_id = "smoke_test_" + hashlib.sha256(b"linkright_smoke").hexdigest()[:16]
        try:
            await conn.execute(
                """
                INSERT INTO companies (canonical_id, name, confidence)
                VALUES ($1, $2, 'low')
                ON CONFLICT (canonical_id) DO NOTHING
                """,
                test_id, "__smoke_test__",
            )
            inserted = await conn.fetchval(
                "SELECT name FROM companies WHERE canonical_id = $1", test_id
            )
            assert inserted == "__smoke_test__", f"Read-back mismatch: {inserted!r}"
            await conn.execute("DELETE FROM companies WHERE canonical_id = $1", test_id)
            _ok("Round-trip INSERT/SELECT/DELETE complete")
        except Exception as e:
            _fail(f"Round-trip test failed: {e}")
            # Cleanup attempt
            try:
                await conn.execute("DELETE FROM companies WHERE canonical_id = $1", test_id)
            except Exception:
                pass
            all_pass = False

    await pool.close()
    return all_pass


def main() -> None:
    print("\nOracle PG Smoke Test\n" + "=" * 40)
    passed = asyncio.run(run_smoke())
    print("=" * 40)
    if passed:
        print(f"\n{GREEN}Oracle PG ready.{RST} All checks passed.\n")
        sys.exit(0)
    else:
        print(
            f"\n{RED}Smoke test FAILED.{RST} Fix issues above, then re-run.\n"
            "Runbook: specs/oracle-pg-runbook-2026-05-03.md\n",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
