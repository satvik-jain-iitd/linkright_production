"""JD enricher — two-phase enrichment for job_discoveries.

Phase 1 (rule-based, instant):
  Runs on every pending job regardless of jd_text.
  Extracts: experience_level, department, min_years_experience, employment_type
  from job title using keyword rules. No LLM needed.

  Rules documented in Langfuse prompt: job-enrichment-rules-v1

Phase 2 (Oracle LLM, background):
  Runs only on jobs where jd_text is populated.
  Extracts all 8 fields using gemma3:1b via oracle.linkright.in.
  Overwrites rule-based values with LLM-extracted values.

Experience level taxonomy:
  early      — APM, Associate PM, 0-3 years
  mid        — PM, Product Manager, 3-5 years
  senior     — Senior PM, Senior Manager, Director, 5-8 years
  executive  — AVP, VP of Product, Group PM, 8-12 years
  cxo        — CPO, Head of Product, SVP, Chief Product Officer, 12+ years

Runs continuously via internal_scheduler (no inter-batch sleep).
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

# ──────────────────────────────────────────────────────────────────────────────
# Phase 1: Rule-based tagging (title → fields, instant, no LLM)
# ──────────────────────────────────────────────────────────────────────────────

import re as _re

def _rule_experience_level(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["cpo", "chief product", "chief of product", "svp", "evp", "group vp"]):
        return "cxo"
    if any(x in t for x in ["vp of product", "vp product", "vice president product",
                              "head of product", "director of product", "senior director",
                              "avp", "principal pm", "principal product"]):
        return "executive"
    if any(x in t for x in ["senior product", "sr. product", "sr product", "lead product",
                              "staff product", "senior pm", "sr pm", "lead pm",
                              "senior manager product", "product director"]):
        return "senior"
    if any(x in t for x in ["associate product", "apm", "associate pm", "junior product",
                              "jr. product", "entry product", "product intern",
                              "intern pm", "graduate pm", "new grad pm"]):
        return "early"
    return "mid"


def _rule_department(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["growth", "acquisition", "retention", "monetization"]):
        return "growth"
    if any(x in t for x in ["platform", "infra", "infrastructure", "developer platform",
                              "api product", "backend product"]):
        return "platform"
    if any(x in t for x in ["data product", "analytics product", "ml product",
                              "ai product", "machine learning pm"]):
        return "data"
    if any(x in t for x in ["design", "ux product", "product design"]):
        return "design"
    if any(x in t for x in ["product manager", "product owner", " pm", "product lead",
                              "product director", "product head"]):
        return "product"
    return "other"


def _rule_min_years(title: str) -> int:
    t = title.lower()
    m = _re.search(r"(\d+)\+?\s*(?:yr|year)", t)
    if m:
        return int(m.group(1))
    if any(x in t for x in ["senior", "sr.", "lead", "staff", "principal"]):
        return 5
    if any(x in t for x in ["associate", "apm", "junior", "jr."]):
        return 0
    if any(x in t for x in ["vp", "director", "head of", "chief", "avp"]):
        return 8
    return 3


def _rule_employment_type(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["contract", "contractor", "freelance", "consultant",
                              "part-time", "part time"]):
        return "contract"
    return "full_time"


def tag_by_rules(job: dict) -> dict:
    """Phase 1: extract fields from title alone. Fast, no LLM."""
    title = job.get("title", "")
    return {
        "experience_level": _rule_experience_level(title),
        "department": _rule_department(title),
        "min_years_experience": _rule_min_years(title),
        "employment_type": _rule_employment_type(title),
    }
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

_SINGLE_CALL_PROMPT = """Extract fields from this job. Return ONLY 8 comma-separated values in this exact order:
work_type, employment_type, experience_level, department, industry, company_stage, remote_ok, min_years_experience

Allowed values:
- work_type: remote | hybrid | onsite
- employment_type: full_time | contract | part_time
- experience_level: early | mid | senior | executive | cxo
- department: product | growth | platform | data | design | other
- industry: fintech | edtech | saas | ecommerce | health | logistics | other
- company_stage: startup | growth | enterprise
- remote_ok: yes | no
- min_years_experience: integer (0 if not mentioned)

Job title: {title}
Company: {company}
JD: {excerpt}

Return exactly like: remote,full_time,senior,product,saas,growth,yes,5"""

_CSV_FIELD_ORDER = [
    "work_type", "employment_type", "experience_level", "department",
    "industry", "company_stage", "remote_ok", "min_years_experience",
]

_CSV_VALID = {
    "work_type":        {"remote", "hybrid", "onsite"},
    "employment_type":  {"full_time", "contract", "part_time"},
    "experience_level": {"early", "mid", "senior", "executive", "cxo"},
    "department":       {"product", "growth", "platform", "data", "design", "other"},
    "industry":         {"fintech", "edtech", "saas", "ecommerce", "health", "logistics", "other"},
    "company_stage":    {"startup", "growth", "enterprise"},
}


def _parse_csv_response(raw: str) -> dict:
    first_line = raw.strip().split("\n")[0].strip().strip("`\"'")
    parts = [p.strip().lower() for p in first_line.split(",")]
    if len(parts) < len(_CSV_FIELD_ORDER):
        return {}
    updates: dict = {}
    for i, field in enumerate(_CSV_FIELD_ORDER):
        val = parts[i] if i < len(parts) else ""
        if field == "remote_ok":
            updates["remote_ok"] = val in ("yes", "true", "1")
        elif field == "min_years_experience":
            import re as _re
            nums = _re.findall(r"\d+", val)
            if nums:
                mye = int(nums[0])
                if 0 <= mye <= 50:
                    updates["min_years_experience"] = mye
        else:
            if val in _CSV_VALID.get(field, set()):
                updates[field] = val
    return updates


async def _enrich_one(
    client: httpx.AsyncClient,
    job: dict,
    fields_to_enrich: list[str],
    use_oracle_first: bool = True,
) -> dict:
    """Return a dict of {field: value} for this job — 1 LLM call, CSV output."""
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

    all_updates = _parse_csv_response(raw)
    return {f: v for f, v in all_updates.items() if f in fields_to_enrich}


async def enrich_pending_jobs(
    supabase_client,
    batch_size: int = BATCH_SIZE,
    enrichment_model: str = "oracle",
    fields_to_enrich: Optional[list[str]] = None,
) -> dict[str, int]:
    """Two-phase enrichment for pending jobs.

    Phase 1 (rule-based): all pending jobs → instant title-based tagging.
    Phase 2 (Oracle LLM): only jobs with jd_text → full 8-field extraction,
      overwrites rule values with LLM values.
    """
    started = time.time()

    if fields_to_enrich is None:
        fields_to_enrich = list(FIELD_PROMPTS.keys())

    # ── Phase 1: rule-tag all pending jobs (with or without jd_text) ──
    all_pending = (
        supabase_client.table("job_discoveries")
        .select("id,title,company_name,jd_text")
        .eq("enrichment_status", "pending")
        .order("discovered_at", desc=True)
        .limit(batch_size)
        .execute()
    ).data or []

    stats = {"candidates": len(all_pending), "enriched": 0, "skipped": 0, "errors": 0}
    if not all_pending:
        return stats

    now_iso = datetime.now(timezone.utc).isoformat()

    # Apply rules instantly — mark done for jobs without jd_text
    for job in all_pending:
        rule_updates = tag_by_rules(job)
        has_jd = bool(job.get("jd_text"))
        if not has_jd:
            rule_updates["enrichment_status"] = "done"
            rule_updates["enriched_at"] = now_iso
            try:
                supabase_client.table("job_discoveries").update(rule_updates).eq("id", job["id"]).execute()
                stats["enriched"] += 1
            except Exception as exc:
                logger.warning("enricher: rule-tag failed %s: %s", job.get("id"), exc)
                stats["errors"] += 1

    # ── Phase 2: Oracle LLM for jobs that have jd_text ──
    jd_jobs = [j for j in all_pending if j.get("jd_text")]
    if not jd_jobs:
        duration = int((time.time() - started) * 1000)
        logger.info("jd_enricher: %s (%dms)", stats, duration)
        return stats

    use_oracle = enrichment_model in ("oracle", "")
    async with httpx.AsyncClient() as client:
        for job in jd_jobs:
            try:
                # Start with rule-based values as base
                updates = tag_by_rules(job)
                # Override with LLM values (more accurate, uses full JD)
                llm_updates = await _enrich_one(client, job, fields_to_enrich, use_oracle_first=use_oracle)
                updates.update(llm_updates)
                updates["enrichment_status"] = "done"
                updates["enriched_at"] = now_iso

                supabase_client.table("job_discoveries").update(updates).eq("id", job["id"]).execute()
                stats["enriched"] += 1
            except Exception as exc:
                logger.warning("enricher: oracle failed %s: %s", job.get("id"), exc)
                # Fall back to rule-based only — still mark done
                try:
                    rule_fallback = tag_by_rules(job)
                    rule_fallback["enrichment_status"] = "done"
                    rule_fallback["enriched_at"] = now_iso
                    supabase_client.table("job_discoveries").update(rule_fallback).eq("id", job["id"]).execute()
                    stats["enriched"] += 1
                except Exception:
                    stats["errors"] += 1

    duration = int((time.time() - started) * 1000)
    logger.info("jd_enricher: %s (%dms)", stats, duration)
    return stats
