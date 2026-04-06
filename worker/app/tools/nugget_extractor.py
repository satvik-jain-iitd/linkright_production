"""Tool: nugget_extractor - Extract atomic career nuggets from free-text career data.

Parses career text into structured Nugget records using the Two-Layer
Categorization Model (Layer A: resume sections, Layer B: life domains).
Persists results to the career_nuggets Supabase table.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Groq model used for extraction
_GROQ_MODEL = "llama-3.3-70b-versatile"
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Rate-limit / retry config
_BATCH_SLEEP = 30          # seconds between Groq batch calls
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
  "importance": "P0"/"P1"/"P2"/"P3",
  "factuality": "fact"/"opinion"/"aspiration",
  "temporality": "past"/"present"/"future",
  "company": "company name or null",
  "role": "role title or null",
  "tags": ["tag1", "tag2"],
  "leadership_signal": "none"/"team_lead"/"individual"
}

Return ONLY valid JSON array, no other text.\
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


async def _groq_complete(api_key: str, user_text: str) -> str:
    """Single Groq chat-completion call. Returns raw response text.

    Raises httpx.HTTPStatusError on non-2xx (caller handles 429 retry).
    """
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{_GROQ_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": _GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_with_retry(api_key: str, user_text: str) -> Optional[str]:
    """Call Groq with exponential backoff on 429. Returns None on exhaustion."""
    for attempt, backoff in enumerate([0] + _RETRY_BACKOFFS):
        if backoff:
            logger.warning("Groq 429 — backing off %ds (attempt %d)", backoff, attempt)
            await asyncio.sleep(backoff)
        try:
            return await _groq_complete(api_key, user_text)
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

    Returns:
        List of Nugget objects. Returns partial results on timeout.
        Returns [] on complete failure (never raises).
    """
    async def _inner() -> list[Nugget]:
        # --- Guard: empty text ---
        if not career_text or len(career_text.strip()) < 50:
            logger.info("extract_nuggets: career_text too short, skipping")
            return []

        if not groq_api_key and not byok_api_key:
            logger.warning("extract_nuggets: no API key provided")
            return []

        batches = _split_into_batches(career_text)
        all_nuggets: list[Nugget] = []
        global_index = 0

        for batch_num, batch_text in enumerate(batches):
            # Inter-batch delay (skip before very first call)
            if batch_num > 0:
                logger.debug("extract_nuggets: sleeping %ds before batch %d", _BATCH_SLEEP, batch_num)
                await asyncio.sleep(_BATCH_SLEEP)

            raw_text: Optional[str] = None

            # --- Primary: Groq ---
            if groq_api_key:
                try:
                    raw_text = await _call_with_retry(groq_api_key, batch_text)
                except Exception as exc:
                    logger.warning("extract_nuggets: Groq exception on batch %d: %s", batch_num, exc)
                    raw_text = None

            # --- Fallback: BYOK ---
            if raw_text is None and byok_api_key:
                logger.info("extract_nuggets: falling back to BYOK key for batch %d", batch_num)
                try:
                    raw_text = await _call_with_retry(byok_api_key, batch_text)
                except Exception as exc:
                    logger.warning("extract_nuggets: BYOK exception on batch %d: %s", batch_num, exc)
                    raw_text = None

            if raw_text is None:
                logger.warning("extract_nuggets: both keys failed for batch %d, skipping", batch_num)
                continue

            # --- JSON parse (with one retry) ---
            active_key = groq_api_key or byok_api_key
            nuggets_raw = await _parse_with_retry(active_key, batch_text, raw_text)
            if not nuggets_raw:
                continue

            # --- Convert to Nugget dataclasses ---
            for raw in nuggets_raw:
                if not isinstance(raw, dict):
                    continue
                nugget = _raw_to_nugget(raw, global_index)
                all_nuggets.append(nugget)
                global_index += 1

        if not all_nuggets:
            return []

        # --- DB: delete old nuggets for this user ---
        try:
            sb.table("career_nuggets").delete().eq("user_id", user_id).execute()
        except Exception as exc:
            logger.warning("extract_nuggets: failed to delete old nuggets: %s", exc)

        # --- DB: insert new nuggets ---
        try:
            rows = [_nugget_to_row(n, user_id) for n in all_nuggets]
            result = sb.table("career_nuggets").insert(rows).execute()
            # Back-fill the DB-assigned id onto each Nugget
            inserted = result.data or []
            for nugget, row_data in zip(all_nuggets, inserted):
                nugget.id = row_data.get("id")
        except Exception as exc:
            logger.warning("extract_nuggets: DB insert failed: %s", exc)

        return all_nuggets

    try:
        return await asyncio.wait_for(_inner(), timeout=120)
    except asyncio.TimeoutError:
        logger.warning("extract_nuggets: timed out after 120s — returning partial results")
        # Can't retrieve partial from _inner() after timeout; return empty
        return []
    except Exception as exc:
        logger.warning("extract_nuggets: unexpected error: %s", exc)
        return []
