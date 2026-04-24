"""Tool: nugget_extractor - Extract atomic career nuggets from free-text career data.

Parses career text into structured Nugget records using the Two-Layer
Categorization Model (Layer A: resume sections, Layer B: life domains).
Persists results to the career_nuggets Supabase table.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import httpx

from ..langfuse_client import trace_generation, get_prompt

logger = logging.getLogger(__name__)

# Groq model used for extraction — override via env for alternate providers
_GROQ_MODEL = os.environ.get("NUGGET_LLM_MODEL", "llama-3.3-70b-versatile")
_GROQ_BASE_URL = os.environ.get("NUGGET_LLM_BASE_URL", "https://api.groq.com/openai/v1")

# Rate-limit / retry config
# Inter-batch sleep was 30s — which made a 14K-char resume spend ~2 min just
# on sleeps. Since 2026-04-17 the rate_governor proactively manages Groq's
# 30 RPM budget, so the inter-batch sleep here is redundant. 5s is kept as
# defensive padding. Extraction now completes in ~1.5 min for a typical resume.
_BATCH_SLEEP = 5           # seconds between Groq batch calls
_RETRY_BACKOFFS = [60, 120, 240, 300]  # seconds on 429

_SYSTEM_PROMPT = """\
You are a career data extractor. Extract atomic nuggets from career text.
For each nugget, classify using the Two-Layer model:
- Layer A (Resume): work_experience, independent_project, skill, education, certification, award, publication, volunteer, summary, contact_info
- Layer B (Life): Relationships, Health, Finance, Inner_Life, Logistics, Recreation

Return JSON array. Each nugget:
{
  "nugget_text": "atomic fact/achievement/metric",
  "question": "What did [person] achieve/do at [company]?",
  "alt_questions": ["alternative phrasing 1", "alternative phrasing 2"],
  "answer": "Self-contained answer with key facts/metrics (>30 chars)",
  "primary_layer": "A" or "B",
  "section_type": "work_experience" (if Layer A, one of 10 types),
  "life_domain": "Relationships" (if Layer B, one of 6 domains),
  "resume_relevance": 0.0-1.0 float,
  "resume_section_target": "experience" or "skills" etc,
  "importance": "P0=career-defining achievement (top 3 ever), P1=strong supporting achievement, P2=contextual/supporting fact, P3=peripheral/background",
  "factuality": "fact"/"opinion"/"aspiration",
  "temporality": "past"/"present"/"future",
  "company": "company name or null",
  "role": "role title or null",
  "event_date": "YYYY-MM or YYYY (approximate ok, extract from any date hint in context, null only if truly unknown)",
  "people": ["collaborator or stakeholder name if mentioned, else empty array"],
  "tags": ["tag1", "tag2"],
  "leadership_signal": "none"/"team_lead"/"individual"
}

RULES:
- Every work_experience nugget MUST have both company AND role fields set — never null for work items
- The answer field MUST be self-contained: include company name, role, and timeframe in every answer
- If a metric (%, $, count, time) exists in source text, it MUST appear in the answer
- event_date: extract approximate date even if only year mentioned (e.g. "2022" or "2022-06")
- Each nugget should be atomic — one achievement per nugget, not combined
- role: use exact title held at the time, not current title

Return ONLY valid JSON array, no other text.\
"""

_SYSTEM_PROMPT_MD = """\
You are a career data extractor. Extract atomic nuggets from career text.
Each nugget = one coherent achievement, skill, or fact.

For each nugget write a ## nugget block with these fields:

## nugget
type: work_experience
company: <company name or none>
role: <job title or none>
importance: <P0/P1/P2/P3>
answer: <self-contained sentence(s) — include company, role, metrics>
tags: <tag1, tag2, tag3>
leadership: <none/individual/team_lead>

type values: work_experience, independent_project, skill, education, certification, award
importance: P0=career-defining (top 3 ever), P1=strong, P2=supporting, P3=background
leadership: none=solo, individual=drove decisions, team_lead=managed people
tags: 2-5 lowercase labels for skills/themes

RULES:
- Every work_experience nugget MUST have company AND role set. If the immediate source line does not name a company, scan the nearest preceding ### header or ## section heading to identify the employer. NEVER emit "none" or empty for the company field on a work_experience nugget. If truly ambiguous, classify as independent_project or skill instead.
- answer MUST be self-contained: include company name, role, and any metric from the source
- Each nugget is atomic — one achievement per block
- Write ONLY ## nugget blocks, no other text\
"""


@dataclass
class Nugget:
    """A single atomic career nugget extracted from career text."""

    nugget_index: int
    nugget_text: str
    question: str
    alt_questions: list[str]
    answer: str
    primary_layer: str          # "A" or "B"
    section_type: Optional[str] = None   # Layer A: 10 types
    section_subtype: Optional[str] = None
    life_domain: Optional[str] = None    # Layer B: 6 domains
    life_l2: Optional[str] = None
    resume_relevance: float = 0.5
    resume_section_target: Optional[str] = None
    importance: str = "P2"       # P0-P3
    factuality: str = "fact"
    temporality: str = "past"
    duration: str = "point_in_time"
    leadership_signal: str = "none"
    company: Optional[str] = None
    role: Optional[str] = None
    event_date: Optional[str] = None
    people: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    # Set after DB insertion
    id: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _split_into_batches(text: str, max_chars: int = 3000) -> list[str]:
    """Split career_text into ~equal chunks capped at max_chars.

    Prefers paragraph boundaries (\n\n) so nugget context isn't broken.
    Falls back to hard-splitting if no boundaries are available.
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    batches: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > max_chars and current:
            batches.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += para_len

    if current:
        batches.append("\n\n".join(current))

    return batches


async def _groq_complete(api_key: str, user_text: str, system_prompt: str = "") -> str:
    """Single Groq chat-completion call. Returns raw response text.

    Raises httpx.HTTPStatusError on non-2xx (caller handles 429 retry).
    """
    sys_prompt = system_prompt or _SYSTEM_PROMPT
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{_GROQ_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": _GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_with_retry(api_key: str, user_text: str, system_prompt: str = "") -> Optional[str]:
    """Call Groq with exponential backoff on 429. Returns None on exhaustion."""
    for attempt, backoff in enumerate([0] + _RETRY_BACKOFFS):
        if backoff:
            logger.warning("Groq 429 — backing off %ds (attempt %d)", backoff, attempt)
            await asyncio.sleep(backoff)
        try:
            return await _groq_complete(api_key, user_text, system_prompt=system_prompt)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                continue
            raise
    logger.warning("Groq exhausted all retries for this batch")
    return None


async def _parse_with_retry(api_key: str, user_text: str, raw_text: str) -> Optional[list]:
    """Try to JSON-parse raw_text; if it fails, ask Groq to fix it once."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning("JSON parse failed on first attempt — sending fix prompt")
        fix_prompt = (
            "The following text is supposed to be a valid JSON array but has syntax errors. "
            "Return ONLY the corrected JSON array, no other text.\n\n"
            + raw_text
        )
        try:
            fixed_raw = await _call_with_retry(api_key, fix_prompt)
            if fixed_raw is None:
                return None
            return json.loads(fixed_raw)
        except json.JSONDecodeError:
            logger.warning("JSON parse failed on fix attempt — skipping batch")
            return None


def _parse_markdown_nuggets(text: str) -> Optional[list]:
    """Parse ## nugget blocks from Markdown-format LLM output into raw dicts."""
    import re
    blocks = re.split(r"^## nugget", text, flags=re.MULTILINE | re.IGNORECASE)
    result = []
    for block in blocks:
        if not block.strip():
            continue
        raw: dict = {}
        for line in block.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                raw[key.strip().lower()] = val.strip()
        if not raw.get("answer"):
            continue
        answer = raw["answer"]
        tags_raw = raw.get("tags", "")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        importance = raw.get("importance", "P2").upper()
        if importance not in ("P0", "P1", "P2", "P3"):
            importance = "P2"
        _KNOWN_SECTION_TYPES = {
            "work_experience", "education", "project", "independent_project",
            "volunteer", "volunteer_work", "award", "certification", "skill",
            "publication", "other", "unknown",
            # Layer B (life domains)
            "relationships", "health", "finance", "inner_life", "logistics", "recreation",
        }
        section_type = raw.get("type", "work_experience").lower()
        if section_type not in _KNOWN_SECTION_TYPES:
            section_type = "other"
        primary_layer = "B" if section_type in ("relationships", "health", "finance", "inner_life", "logistics", "recreation") else "A"
        result.append({
            "nugget_text": answer,
            "question": "",
            "alt_questions": [],
            "answer": answer,
            "primary_layer": primary_layer,
            "section_type": section_type,
            "life_domain": None,
            "resume_relevance": {"P0": 0.9, "P1": 0.75, "P2": 0.5, "P3": 0.3}.get(importance, 0.5),
            "resume_section_target": "experience" if section_type == "work_experience" else section_type,
            "importance": importance,
            "factuality": "fact",
            "temporality": "past",
            "company": raw.get("company") or None,
            "role": raw.get("role") or None,
            "event_date": None,
            "people": [],
            "tags": tags,
            "leadership_signal": raw.get("leadership", "none"),
        })
    return result if result else None


def _raw_to_nugget(raw: dict, index: int) -> Nugget:
    """Convert a raw LLM dict to a typed Nugget dataclass."""
    return Nugget(
        nugget_index=index,
        nugget_text=raw.get("nugget_text", ""),
        question=raw.get("question", ""),
        alt_questions=raw.get("alt_questions", []),
        answer=raw.get("answer", ""),
        primary_layer=raw.get("primary_layer", "A"),
        section_type=raw.get("section_type"),
        life_domain=raw.get("life_domain"),
        resume_relevance=float(raw.get("resume_relevance", 0.5)),
        resume_section_target=raw.get("resume_section_target"),
        importance=raw.get("importance", "P2"),
        factuality=raw.get("factuality", "fact"),
        temporality=raw.get("temporality", "past"),
        leadership_signal=raw.get("leadership_signal", "none"),
        company=raw.get("company"),
        role=raw.get("role"),
        event_date=raw.get("event_date"),
        people=raw.get("people", []),
        tags=raw.get("tags", []),
    )


def _nugget_to_row(nugget: Nugget, user_id: str) -> dict:
    """Map a Nugget dataclass to a career_nuggets table row dict."""
    return {
        "user_id": user_id,
        "nugget_index": nugget.nugget_index,
        "nugget_text": nugget.nugget_text,
        "question": nugget.question,
        "alt_questions": nugget.alt_questions,
        "answer": nugget.answer,
        "primary_layer": nugget.primary_layer,
        "section_type": nugget.section_type,
        "section_subtype": nugget.section_subtype,
        "life_domain": nugget.life_domain,
        "life_l2": nugget.life_l2,
        "resume_relevance": nugget.resume_relevance,
        "resume_section_target": nugget.resume_section_target,
        "importance": nugget.importance,
        "factuality": nugget.factuality,
        "temporality": nugget.temporality,
        "duration": nugget.duration,
        "leadership_signal": nugget.leadership_signal,
        "company": nugget.company,
        "role": nugget.role,
        "event_date": nugget.event_date,
        "people": nugget.people,
        "tags": nugget.tags,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_nuggets(
    user_id: str,
    career_text: str,
    sb,  # Supabase client
    groq_api_key: Optional[str] = None,
    byok_api_key: Optional[str] = None,
    key_manager=None,  # Optional KeyManager for multi-key fallback
    batch_callback=None,  # Optional[Callable[[list[Nugget]], Awaitable[None]]]
    force_delete: bool = False,  # if False, skip DELETE when nuggets already exist
) -> list[Nugget]:
    """Extract atomic career nuggets from free-text career data.

    Splits career_text into batches, calls Groq for each batch with a
    30-second inter-batch delay, and persists results to career_nuggets.
    Falls back to byok_api_key if Groq exhausts all retries.

    Args:
        user_id: Owner of the nuggets (used for DB scoping).
        career_text: Raw career/resume text to parse.
        sb: Supabase client (service-role key expected).
        groq_api_key: Primary Groq API key.
        byok_api_key: Optional BYOK fallback key (tried once if Groq fails).
        key_manager: Optional KeyManager for multi-key fallback with priority rotation.

    Returns:
        List of Nugget objects. Returns partial results on timeout.
        Returns [] on complete failure (never raises).
    """
    async def _inner() -> list[Nugget]:
        # --- Guard: empty text ---
        if not career_text or len(career_text.strip()) < 50:
            logger.info("extract_nuggets: career_text too short, skipping")
            return []

        if not groq_api_key and not byok_api_key and not key_manager:
            logger.warning("extract_nuggets: no API key provided")
            return []

        # Fetch versioned prompt from Langfuse (falls back to local _SYSTEM_PROMPT_MD)
        system_prompt, prompt_version = get_prompt("nugget_extractor_md", _SYSTEM_PROMPT_MD)

        batches = _split_into_batches(career_text)
        all_nuggets: list[Nugget] = []
        global_index = 0  # may be overridden below if existing nuggets are preserved

        # --- DB: delete old nuggets ONLY if explicitly requested ---
        if force_delete:
            try:
                # Safety log: show exactly what will be destroyed before destroying it
                count_result = sb.table("career_nuggets").select("id").eq("user_id", user_id).execute()
                count = len(count_result.data or [])
                logger.warning(
                    "extract_nuggets: FORCE DELETE — destroying %d existing nuggets for user %s. This is permanent.",
                    count, user_id
                )
                sb.table("career_nuggets").delete().eq("user_id", user_id).execute()
                logger.info("extract_nuggets: cleared old nuggets for user %s (force_delete=True)", user_id)
            except Exception as exc:
                logger.warning("extract_nuggets: failed to delete old nuggets: %s", exc)
        else:
            existing = sb.table("career_nuggets").select("nugget_index").eq("user_id", user_id).execute()
            existing_count = len(existing.data or [])
            if existing_count > 0:
                logger.info("extract_nuggets: %d existing nuggets preserved (pass force_delete=True to replace)", existing_count)
                # Offset new nugget indices past existing ones
                global_index = existing_count

        consecutive_429s = 0  # track rate-limit failures to detect daily quota exhaustion

        for batch_num, batch_text in enumerate(batches):
            # Inter-batch delay (skip before very first call)
            if batch_num > 0:
                logger.debug("extract_nuggets: sleeping %ds before batch %d", _BATCH_SLEEP, batch_num)
                await asyncio.sleep(_BATCH_SLEEP)

            raw_text: Optional[str] = None

            # --- KeyManager path: multi-key fallback ---
            if key_manager:
                try:
                    raw_text = await key_manager.call_with_fallback(
                        "groq",
                        lambda key: _groq_complete(key, batch_text, system_prompt=system_prompt),
                        fallback_key=byok_api_key,
                    )
                except Exception as exc:
                    logger.warning("extract_nuggets: key_manager fallback exhausted on batch %d: %s", batch_num, exc)
                    raw_text = None
            else:
                # --- Primary: Groq ---
                if groq_api_key:
                    try:
                        raw_text = await _call_with_retry(groq_api_key, batch_text, system_prompt=system_prompt)
                    except Exception as exc:
                        logger.warning("extract_nuggets: Groq exception on batch %d: %s", batch_num, exc)
                        raw_text = None

                # --- Fallback: BYOK ---
                if raw_text is None and byok_api_key:
                    logger.info("extract_nuggets: falling back to BYOK key for batch %d", batch_num)
                    try:
                        raw_text = await _call_with_retry(byok_api_key, batch_text, system_prompt=system_prompt)
                    except Exception as exc:
                        logger.warning("extract_nuggets: BYOK exception on batch %d: %s", batch_num, exc)
                        raw_text = None

            # Langfuse: trace the extraction call
            if raw_text is not None:
                trace_generation(
                    trace_name="nugget_extraction",
                    generation_name="extract_nuggets_batch",
                    model=_GROQ_MODEL,
                    system_prompt=system_prompt,
                    user_input=batch_text,
                    output=raw_text,
                    user_id=user_id,
                    prompt_version=prompt_version,
                )

            if raw_text is None:
                consecutive_429s += 1
                logger.warning("extract_nuggets: batch %d failed (%d consecutive)", batch_num, consecutive_429s)
                # Stop early if 4+ consecutive failures — daily quota likely exhausted
                if consecutive_429s >= 4:
                    logger.warning("extract_nuggets: stopping early — daily rate limit suspected (batch %d/%d)", batch_num, len(batches))
                    break
                continue

            consecutive_429s = 0  # reset on success

            # --- Markdown parse ---
            nuggets_raw = _parse_markdown_nuggets(raw_text)
            if not nuggets_raw:
                continue

            # --- F05 validator: drop work_experience nuggets missing company tag ---
            # Prompt already forbids null/none on work items; this is defense-in-depth
            # for the ~22% rate observed on the diagnostic run_01.
            _dropped_untagged = 0
            _kept_raw = []
            for raw in nuggets_raw:
                if not isinstance(raw, dict):
                    continue
                is_work = (raw.get("section_type") or raw.get("type") or "").lower() == "work_experience"
                company_val = (raw.get("company") or "").strip().lower()
                if is_work and company_val in ("", "none", "null"):
                    _dropped_untagged += 1
                    continue
                _kept_raw.append(raw)
            if _dropped_untagged:
                logger.warning(
                    "extract_nuggets: batch %d dropped %d work_experience nugget(s) with missing company tag",
                    batch_num, _dropped_untagged,
                )
            nuggets_raw = _kept_raw

            # --- Convert to Nugget dataclasses ---
            batch_nuggets: list[Nugget] = []
            for raw in nuggets_raw:
                if not isinstance(raw, dict):
                    continue
                nugget = _raw_to_nugget(raw, global_index)
                nugget.tags.append(f"prompt_v{prompt_version}")
                all_nuggets.append(nugget)
                batch_nuggets.append(nugget)
                global_index += 1

            # --- DB: insert this batch immediately (incremental save, with dedup) ---
            if batch_nuggets:
                try:
                    # Dedup: skip nuggets whose text already exists for this user
                    unique_nuggets: list[Nugget] = []
                    for n in batch_nuggets:
                        try:
                            dup = sb.table("career_nuggets").select("id, nugget_index") \
                                .eq("user_id", user_id).eq("nugget_text", n.nugget_text) \
                                .limit(1).execute()
                            if dup.data:
                                n.id = dup.data[0]["id"]  # reuse existing id for embedding
                                logger.debug("extract_nuggets: skipping duplicate nugget_text (id=%s)", n.id)
                                unique_nuggets.append(n)  # still embed if needed
                                continue
                        except Exception:
                            pass  # on dedup check failure, allow insert
                        unique_nuggets.append(n)

                    new_nuggets = [n for n in unique_nuggets if not n.id]
                    if new_nuggets:
                        rows = [_nugget_to_row(n, user_id) for n in new_nuggets]
                        result = sb.table("career_nuggets").insert(rows).execute()
                        inserted = result.data or []
                        for nugget, row_data in zip(new_nuggets, inserted):
                            nugget.id = row_data.get("id")
                    batch_nuggets = unique_nuggets  # use deduped list (includes existing dupes with ids) for callback
                    logger.info("extract_nuggets: batch %d → %d nuggets saved (%d new, total=%d)", batch_num, len(unique_nuggets), len(new_nuggets), len(all_nuggets))
                except Exception as exc:
                    logger.warning("extract_nuggets: DB insert failed for batch %d: %s", batch_num, exc)

                # --- Batch callback: embed immediately after save ---
                if batch_callback is not None:
                    try:
                        await batch_callback(batch_nuggets)
                    except Exception as exc:
                        logger.warning("extract_nuggets: batch_callback failed for batch %d: %s", batch_num, exc)

        return all_nuggets

    # Dynamic timeout: each batch needs up to (HTTP_TIMEOUT + BATCH_SLEEP) seconds.
    # Add a 60s buffer. Minimum 120s for small profiles.
    import math
    n_batches = max(1, math.ceil(len(career_text) / 3000))
    dynamic_timeout = max(120, n_batches * (_BATCH_SLEEP + 120) + 60)
    logger.info("extract_nuggets: %d estimated batches, timeout=%.0fs", n_batches, dynamic_timeout)

    try:
        return await asyncio.wait_for(_inner(), timeout=dynamic_timeout)
    except asyncio.TimeoutError:
        logger.warning("extract_nuggets: timed out after %.0fs — returning partial results", dynamic_timeout)
        # Can't retrieve partial from _inner() after timeout; return empty
        return []
    except Exception as exc:
        logger.warning("extract_nuggets: unexpected error: %s", exc)
        return []
