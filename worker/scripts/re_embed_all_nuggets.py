"""Re-embed all career nuggets using Oracle nomic-embed-text.

Run this once after switching from Jina to Oracle as the embedding model.
Mixed embeddings in the same table corrupt cosine similarity — all nuggets
must be re-embedded with the same model used for query embedding.

Usage:
    python -m scripts.re_embed_all_nuggets [--dry-run] [--user-id <uuid>]

Options:
    --dry-run       Print what would be done without writing to DB.
    --user-id UUID  Re-embed only nuggets for a specific user (default: all).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

import httpx
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def _embed(oracle_url: str, oracle_secret: str, text: str) -> list[float] | None:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                f"{oracle_url.rstrip('/')}/lifeos/embed",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {oracle_secret}",
                },
                json={"text": text},
            )
            if resp.status_code == 200:
                return resp.json().get("embedding")
            logger.warning("Oracle embed returned %d for text[:50]=%s", resp.status_code, text[:50])
        except Exception as exc:
            logger.warning("Oracle embed error: %s", exc)
    return None


async def re_embed(dry_run: bool, user_id: str | None) -> None:
    oracle_url = os.environ.get("ORACLE_BACKEND_URL", "")
    oracle_secret = os.environ.get("ORACLE_BACKEND_SECRET", "")
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not oracle_url:
        logger.error("ORACLE_BACKEND_URL not set — aborting")
        sys.exit(1)
    if not supabase_url or not service_key:
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY not set — aborting")
        sys.exit(1)

    sb = create_client(supabase_url, service_key)

    q = sb.table("career_nuggets").select("id, answer, user_id, embedding_model")
    if user_id:
        q = q.eq("user_id", user_id)

    result = q.execute()
    rows = result.data or []
    logger.info("Found %d nuggets to process", len(rows))

    to_embed = [
        r for r in rows
        if (r.get("answer") or "").strip()
        and r.get("embedding_model", "") != "nomic-embed-text"
    ]
    skipped = len(rows) - len(to_embed)
    re_embedded = 0

    if dry_run:
        for row in to_embed:
            logger.info("[DRY RUN] Would re-embed id=%s (current_model=%s)", row["id"], row.get("embedding_model", ""))
        re_embedded = len(to_embed)
    else:
        # Local model — no rate limits, parallelize all at once
        async def _embed_one(row: dict) -> None:
            nonlocal re_embedded
            embedding = await _embed(oracle_url, oracle_secret, (row.get("answer") or "").strip())
            if embedding:
                sb.table("career_nuggets").update(
                    {"embedding": embedding, "embedding_model": "nomic-embed-text"}
                ).eq("id", row["id"]).execute()
                re_embedded += 1
                logger.info("Re-embedded id=%s", row["id"])
            else:
                logger.warning("Failed to embed id=%s — skipping", row["id"])

        await asyncio.gather(*[_embed_one(row) for row in to_embed])

    logger.info(
        "Done. re_embedded=%d skipped=%d total=%d (dry_run=%s)",
        re_embedded, skipped, len(rows), dry_run,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-embed all nuggets with nomic-embed-text")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--user-id", help="Restrict to a specific user UUID")
    args = parser.parse_args()
    asyncio.run(re_embed(args.dry_run, args.user_id))


if __name__ == "__main__":
    main()
