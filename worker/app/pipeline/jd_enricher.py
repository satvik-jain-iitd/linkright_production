"""JD enricher — extract structured fields from job descriptions using local Oracle models.

Runs after jd_fetcher has populated jd_text. For each job with jd_text and
enrichment_status='pending', asks Oracle (local free model) one simple question
per field. Falls back to Cerebras if Oracle is unreachable.

Experience level taxonomy:
  early      — APM, Associate PM, 0-3 years
  mid        — PM, Product Manager, 3-5 years
  senior     — Senior PM, Senior Manager, Director, 5-8 years
  executive  — AVP, VP of Product, Group PM, 8-12 years
  cxo        — CPO, Head of Product, SVP, Chief Product Officer, 12+ years

Processes in batches of 10 to avoid overwhelming Oracle.
Runs every 30 min via internal_scheduler.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
ORACLE_URL = os.getenv("ORACLE_BACKEND_URL", "https://oracle.linkright.in")
ORACLE_SECRET = os.getenv("ORACLE_BACKEND_SECRET", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
ORACLE_TIMEOUT = 120  # seconds — longer for background enrichment vs interactive


# ──────────────────────────────────────────────────────────────────────────────
# Per-field prompts — simple yes/no or single-word answers
# ──────────────────────────────────────────────────────────────────────────────

FIELD_PROMPTS: dict[str, tuple[str, str]] = {
    # field_name: (question, valid_answers_hint)
    "remote_ok": (
        "Does this job allow remote work or hybrid work? Answer only: yes or no.",
        "yes,no",
    ),
    "work_type": (
        "What is the work arrangement for this job? Answer only one word: remote, hybrid, or onsite.",
        "remote,hybrid,onsite",
    ),
    "employment_type": (
        "What is the employment type? Answer only: full_time, contract, or part_time.",
        "full_time,contract,part_time",
    ),
    "experience_level": (
        (
            "What experience level does this job target? "
            "Look at the job title and years of experience required. "
            "Answer only one: "
            "early (APM/associate PM, 0-3 years), "
            "mid (PM, 3-5 years), "
            "senior (Senior PM/Senior Manager/Director, 5-8 years), "
            "executive (AVP/VP/Group PM, 8-12 years), "
            "cxo (CPO/Head of Product/SVP/Chief, 12+ years)."
        ),
        "early,mid,senior,executive,cxo",
    ),
    "department": (
        "What type of product role is this? Answer only one: product, growth, platform, data, design, or other.",
        "product,growth,platform,data,design,other",
    ),
    "industry": (
        "What industry is this company in? Answer only one: fintech, edtech, saas, ecommerce, health, logistics, or other.",
        "fintech,edtech,saas,ecommerce,health,logistics,other",
    ),
    "company_stage": (
        "What stage is this company at? Answer only one: startup, growth, or enterprise.",
        "startup,growth,enterprise",
    ),
    "min_years_experience": (
        "How many minimum years of experience does this job require? Answer only a single integer (e.g. 0, 3, 5, 10). If not mentioned, answer 0.",
        "integer",
    ),
}

BOOL_FIELDS = {"remote_ok"}
INT_FIELDS = {"min_years_experience"}


def _parse_answer(field: str, raw: str, valid: str) -> Optional[object]:
    """Parse a raw LLM answer into a typed value."""
    cleaned = raw.strip().lower().strip(".,;\"'`")
    if not cleaned:
        return None

    if field in INT_FIELDS:
        import re
        nums = re.findall(r"\d+", cleaned)
        if nums:
            val = int(nums[0])
            if 0 <= val <= 50:
                return val
        return None

    valid_opts = [v.strip() for v in valid.split(",")]

    if field in BOOL_FIELDS:
        if "yes" in cleaned:
            return True
        if "no" in cleaned:
            return False
        return None

    for opt in valid_opts:
        if opt in cleaned:
            return opt
    return None


# ──────────────────────────────────────────────────────────────────────────────
# LLM call helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _ask_oracle(
    client: httpx.AsyncClient,
    jd_excerpt: str,
    question: str,
) -> Optional[str]:
    """Ask Oracle local model one question about the JD. Returns raw text or None."""
    if not ORACLE_SECRET:
        return None
    prompt = f"Job description excerpt:\n{jd_excerpt[:1500]}\n\nQuestion: {question}"
    try:
        resp = await client.post(
            f"{ORACLE_URL}/lifeos/generate",
            json={"prompt": prompt, "temperature": 0.0},
            headers={"Authorization": f"Bearer {ORACLE_SECRET}"},
            timeout=ORACLE_TIMEOUT,
        )
        resp.raise_for_status()
        return (resp.json().get("text") or "").strip()
    except Exception as exc:
        logger.debug("enricher oracle error: %s", exc)
        return None


async def _ask_cerebras(
    client: httpx.AsyncClient,
    jd_excerpt: str,
    question: str,
) -> Optional[str]:
    """Cerebras fallback using OpenAI-compatible API."""
    if not CEREBRAS_API_KEY:
        return None
    messages = [
        {"role": "system", "content": "Answer the question about the job description in 1-3 words maximum. No explanation."},
        {"role": "user", "content": f"Job description:\n{jd_excerpt[:1000]}\n\nQuestion: {question}"},
    ]
    try:
        resp = await client.post(
            "https://api.cerebras.ai/v1/chat/completions",
            json={"model": "llama3.1-8b", "messages": messages, "max_tokens": 10, "temperature": 0.0},
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}"},
            timeout=30,
        )
        resp.raise_for_status()
        return (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:
        logger.debug("enricher cerebras error: %s", exc)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Main enrichment logic
# ──────────────────────────────────────────────────────────────────────────────

_SINGLE_CALL_PROMPT = """Extract structured fields from this job description. Return ONLY valid JSON, no explanation.

Job title: {title}
Company: {company}
JD excerpt: {excerpt}

Return JSON with exactly these keys:
{{
  "remote_ok": true or false,
  "work_type": "remote" | "hybrid" | "onsite",
  "employment_type": "full_time" | "contract" | "part_time",
  "experience_level": "early" | "mid" | "senior" | "executive" | "cxo",
  "department": "product" | "growth" | "platform" | "data" | "design" | "other",
  "industry": "fintech" | "edtech" | "saas" | "ecommerce" | "health" | "logistics" | "other",
  "company_stage": "startup" | "growth" | "enterprise",
  "min_years_experience": integer (0 if not mentioned)
}}"""


async def _enrich_one(
    client: httpx.AsyncClient,
    job: dict,
    fields_to_enrich: list[str],
    use_oracle_first: bool = True,
) -> dict:
    """Return a dict of {field: value} for this job — 1 LLM call for all fields."""
    import json as _json
    jd_text = job.get("jd_text") or ""
    excerpt = jd_text[:1500] if jd_text else ""
    title = job.get("title", "")
    company = job.get("company_name", "")

    prompt = _SINGLE_CALL_PROMPT.format(title=title, company=company, excerpt=excerpt)

    raw: Optional[str] = None
    if use_oracle_first:
        raw = await _ask_oracle(client, "", prompt)
    if raw is None:
        raw = await _ask_cerebras(client, excerpt, prompt)
    if not raw:
        return {}

    # Parse JSON response
    try:
        cleaned = raw.strip()
        for fence in ("```json", "```"):
            if fence in cleaned:
                cleaned = cleaned.split(fence, 1)[-1].split("```")[0]
        parsed = _json.loads(cleaned.strip())
        if isinstance(parsed, list) and parsed:
            parsed = parsed[0]
    except Exception:
        parsed = {}

    updates: dict = {}
    for field in fields_to_enrich:
        if field not in parsed:
            continue
        val = parsed[field]
        # Validate against known values
        if field == "remote_ok":
            if isinstance(val, bool):
                updates[field] = val
            elif str(val).lower() in ("true", "yes", "1"):
                updates[field] = True
            elif str(val).lower() in ("false", "no", "0"):
                updates[field] = False
        elif field == "min_years_experience":
            try:
                updates[field] = int(val)
            except (TypeError, ValueError):
                pass
        else:
            _, valid_str = FIELD_PROMPTS.get(field, ("", ""))
            valid_vals = [v.strip() for v in valid_str.split(",") if v.strip()]
            if not valid_vals or str(val).lower() in valid_vals:
                updates[field] = str(val).lower()

    return updates


async def enrich_pending_jobs(
    supabase_client,
    batch_size: int = BATCH_SIZE,
    enrichment_model: str = "oracle",
    fields_to_enrich: Optional[list[str]] = None,
) -> dict[str, int]:
    """Enrich a batch of jobs that have jd_text but enrichment_status='pending'."""
    started = time.time()

    if fields_to_enrich is None:
        fields_to_enrich = list(FIELD_PROMPTS.keys())

    # PM jobs first — order by title containing 'product' then by recency
    rows = (
        supabase_client.table("job_discoveries")
        .select("id,title,company_name,jd_text")
        .eq("enrichment_status", "pending")
        .not_.is_("jd_text", "null")
        .ilike("title", "%product%")
        .order("discovered_at", desc=True)
        .limit(batch_size)
        .execute()
    ).data or []

    # If fewer than batch_size PM jobs, fill remainder with any pending jobs
    if len(rows) < batch_size:
        pm_ids = {r["id"] for r in rows}
        extra = (
            supabase_client.table("job_discoveries")
            .select("id,title,company_name,jd_text")
            .eq("enrichment_status", "pending")
            .not_.is_("jd_text", "null")
            .order("discovered_at", desc=True)
            .limit(batch_size - len(rows) + 50)
            .execute()
        ).data or []
        rows += [r for r in extra if r["id"] not in pm_ids][: batch_size - len(rows)]

    stats = {"candidates": len(rows), "enriched": 0, "skipped": 0, "errors": 0}
    if not rows:
        return stats

    use_oracle = enrichment_model in ("oracle", "")
    now_iso = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient() as client:
        for job in rows:
            try:
                updates = await _enrich_one(client, job, fields_to_enrich, use_oracle_first=use_oracle)
                updates["enrichment_status"] = "done"
                updates["enriched_at"] = now_iso

                supabase_client.table("job_discoveries").update(updates).eq("id", job["id"]).execute()
                stats["enriched"] += 1
            except Exception as exc:
                logger.warning("enricher: failed job %s: %s", job.get("id"), exc)
                try:
                    supabase_client.table("job_discoveries").update(
                        {"enrichment_status": "skipped"}
                    ).eq("id", job["id"]).execute()
                except Exception:
                    pass
                stats["errors"] += 1

    duration = int((time.time() - started) * 1000)
    logger.info("jd_enricher: %s (%dms)", stats, duration)
    return stats
