"""linkright.admin — Oracle Postgres admin commands.

Provides `linkright admin` command group for:
  companies import   — upsert JSON company data into Oracle PG
  companies stats    — health stats query from Oracle PG
  slug-discovery batch — run Layer 1 ATS slug discovery over a list

All writes go to Oracle Postgres (ORACLE_PG_URL).
Reads from Supabase are untouched.
"""
