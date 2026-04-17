"""8-phase pipeline orchestrator.

Runs JD → resume generation using the user's LLM (BYOK) + local Python tools.
Each phase updates Supabase with progress for the frontend to display.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("worker")

from supabase import Client

from ..context import PipelineContext
from ..db import update_job
from ..llm import get_provider
from ..llm.base import LLMResponse
from ..data.strategies import STRATEGIES
from ..tools.parse_template import resume_parse_template, ParseTemplateInput
from ..tools.measure_width import resume_measure_width, MeasureWidthInput
from ..tools.validate_contrast import resume_validate_contrast, ContrastInput
from ..tools.validate_page_fit import resume_validate_page_fit, PageFitInput, SectionSpec
from ..tools.suggest_synonyms import resume_suggest_synonyms, SynonymInput
from ..tools.measure_width import compute_word_widths
from ..tools.track_verbs import resume_track_verbs, TrackVerbsInput
from ..data.reference_widths import format_reference_table
from ..tools.assemble_html import (
    resume_assemble_html, AssembleInput, ThemeColors, HeaderData, SectionContent,
)
from ..tools.score_bullets import resume_score_bullets, ScoreBulletsInput, CandidateBullet
from ..qmd_search import hybrid_search as qmd_hybrid_search, fallback_fts_search
from . import prompts
from .prompts import escape_llm_input
from ..langfuse_client import trace_generation, get_prompt
from ..tools.nugget_extractor import extract_nuggets, Nugget
from ..tools.nugget_embedder import embed_nuggets
from ..tools.quality_judge import judge_quality
from ..tools.hybrid_retrieval import hybrid_retrieve, format_nuggets_for_llm
from ..key_manager import KeyManager
from ..llm.oracle import OracleProvider
from ..llm.gemini import GeminiProvider
from ..llm.base import LLMProvider
from .. import config as worker_config
import os


class _FallbackLLM(LLMProvider):
    """Wraps a primary LLM and silently falls back to secondary on any error."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self._primary = primary
        self._fallback = fallback
        # Satisfy ABC — not used for routing
        super().__init__(api_key="", model_id="fallback")

    async def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        try:
            return await self._primary.complete(system, user, temperature)
        except Exception as exc:
            logger.warning(
                "Primary LLM %s failed (%s) — falling back to %s",
                type(self._primary).__name__, exc, type(self._fallback).__name__,
            )
            return await self._fallback.complete(system, user, temperature)

    async def validate_key(self) -> bool:
        return True


def _get_groq_fallback_llm() -> "GroqProvider | None":
    """70B Groq model as fallback for Gemini on heavy reasoning phases."""
    from ..llm.groq import GroqProvider
    api_key = os.environ.get("PLATFORM_GROQ_API_KEY") or os.environ.get("GROQ_API_KEY") or ""
    if not api_key:
        return None
    return GroqProvider(api_key=api_key, model_id="llama-3.3-70b-versatile")

USE_QUALITY_JUDGE = os.getenv("USE_QUALITY_JUDGE", "true").lower() == "true"

# Oracle ARM local LLM — used for Phase 5 width rewriting + Phase 3.5a summary tweaking
# Falls back to Groq automatically if Oracle is not configured or unavailable
def _get_oracle_llm() -> OracleProvider | None:
    if worker_config.ORACLE_BACKEND_URL and worker_config.ORACLE_BACKEND_SECRET:
        return OracleProvider(
            base_url=worker_config.ORACLE_BACKEND_URL,
            secret=worker_config.ORACLE_BACKEND_SECRET,
            endpoint="rewrite",
        )
    return None

# Gemini Flash — used for heavy reasoning phases (Phase 1+2, Phase 4a)
# Falls back to default user LLM (Groq) if not configured
def _get_gemini_llm() -> GeminiProvider | None:
    if worker_config.GEMINI_API_KEY:
        return GeminiProvider(
            api_key=worker_config.GEMINI_API_KEY,
            model_id=worker_config.GEMINI_MODEL_ID,
        )
    return None

REVIEW_PAUSE_SECONDS = int(os.environ.get("REVIEW_PAUSE_SECONDS", "6"))

import re as _re

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Keywords that signal a section contains professional experience or skills.
# v4: removed hardcoded company names (sprinklr, amex, etc.) — now generic.
_PROF_KEYWORDS = {
    "experience", "work", "role", "manager", "engineer", "analyst",
    "consultant", "associate", "intern", "developer", "lead", "director",
    "company", "startup", "skills", "tools", "education", "voluntary",
    "project", "product", "senior", "junior", "principal", "staff",
}


def _prepare_career_for_phase1(career_text: str, job_id: str) -> str:
    """Extract professional sections from career text for Phase 1.

    Long career profiles may have extensive personal/early-life narrative
    before professional experience.  This function splits by ## headings,
    keeps only sections relevant to resume generation (roles, skills,
    education), and caps each section at 2500 chars.
    """
    MAX_TOTAL = 50000   # PM decision C2: 50KB cap (was 20KB)
    MAX_PER_SECTION = 4000

    # If short enough already, pass through
    if len(career_text) <= MAX_TOTAL:
        return career_text

    # Split into (heading, body) pairs
    sections = _re.split(r'\n(?=## )', career_text)
    intro = sections[0] if sections else ""  # text before first ##

    kept = []
    # Always keep intro/header (first ~500 chars)
    if intro.strip():
        kept.append(intro.strip()[:500])

    for section in sections[1:]:
        heading_line = section.split("\n", 1)[0].lower()
        # Keep sections that mention professional keywords
        if any(kw in heading_line for kw in _PROF_KEYWORDS):
            if len(section) > MAX_PER_SECTION:
                # Keep heading + first 2500 chars of body
                section = section[:MAX_PER_SECTION] + "\n[... section trimmed ...]"
            kept.append(section.strip())

    result = "\n\n".join(kept)

    # Final cap
    if len(result) > MAX_TOTAL:
        result = result[:MAX_TOTAL] + "\n\n[... truncated ...]"

    logger.info(
        f"Job {job_id}: career_text condensed from {len(career_text)} to {len(result)} chars "
        f"({len(kept)} sections kept) for Phase 1"
    )
    return result


async def run_pipeline(ctx: PipelineContext, sb: Client) -> None:
    """Execute V2 pipeline: company-by-company verbose → condense → width opt.

    Phase sequence:
      1+2  → Parse JD + Strategy + Brand Colors (1 LLM call)
      2.5  → Vector retrieval per company (QMD, no LLM)
      3    → Page fit planning (no LLM)
      3.5  → Stencil draft → draft_html (no LLM)
      4a   → Verbose paragraphs per company (N LLM calls, review gates)
      4b   → Rank verbose bullets by BRS (no LLM)
      4c   → Condense all to bullets (1 LLM call)
      5    → Width optimization (1-2 LLM calls)
      6    → BRS scoring (no LLM)
      7    → Validation (no LLM)
      8    → Final assembly → output_html
    """
    llm = get_provider(ctx.model_provider, ctx.api_key, ctx.model_id)
    _gemini = _get_gemini_llm()   # Gemini Flash for heavy reasoning phases
    _oracle = _get_oracle_llm()   # Oracle 1B for simple rewriting phases

    if _gemini:
        logger.info("run_pipeline: Gemini Flash available (%s)", worker_config.GEMINI_MODEL_ID)
    if _oracle:
        logger.info("run_pipeline: Oracle ARM available for rewriting")

    # Initialize KeyManager if user has keys in DB
    km = KeyManager(sb, ctx.user_id)
    if km.get_keys("groq") or km.get_keys("jina"):
        ctx.key_manager = km
        logger.info("run_pipeline: KeyManager active (groq=%d, jina=%d keys)",
                     len(km.get_keys("groq")), len(km.get_keys("jina")))

    await phase_0_nuggets(
        ctx, sb,
        groq_api_key=os.environ.get("PLATFORM_GROQ_API_KEY") or os.environ.get("GROQ_API_KEY"),
        byok_api_key=ctx.api_key,
    )

    if ctx.career_text and hasattr(ctx, "_nuggets") and not ctx._nuggets:
        logger.warning("Phase 0 produced no nuggets — continuing with paragraph-chunk fallback")

    # For heavy reasoning phases, fall back to 70B model (not the user's 8B default)
    _groq_70b = _get_groq_fallback_llm()
    heavy_fallback = _groq_70b or llm
    gemini_with_fallback = _FallbackLLM(_gemini, heavy_fallback) if _gemini else heavy_fallback
    oracle_with_fallback = _FallbackLLM(_oracle, llm) if _oracle else llm

    await phase_1_parse_and_strategy(ctx, sb, gemini_with_fallback)  # Gemini preferred: heavy reasoning
    await phase_2_5_vector_retrieval(ctx, sb)
    await phase_3_page_fit(ctx, sb)
    await phase_3_5_stencil_draft(ctx, sb)
    await phase_4a_verbose_bullets(ctx, sb, gemini_with_fallback)  # Gemini preferred: XYZ creative writing
    await phase_4b_ranking(ctx, sb)
    await phase_4c_condense_bullets(ctx, sb, oracle_with_fallback)  # Oracle preferred: simple shortening
    await phase_3_5a_professional_summary(ctx, sb, oracle_with_fallback)  # v4: AFTER bullets — synthesizes from written bullets
    await phase_5_width_opt(ctx, sb, llm)
    await phase_6_scoring(ctx, sb)
    await phase_7_validation(ctx, sb)
    await phase_8_assembly(ctx, sb, llm)

    # Aggregate token/timing stats
    ctx.stats["llm_calls"] = len(ctx._llm_log)
    ctx.stats["total_input_tokens"] = sum(c["input_tokens"] for c in ctx._llm_log)
    ctx.stats["total_output_tokens"] = sum(c["output_tokens"] for c in ctx._llm_log)
    ctx.stats["total_llm_time_ms"] = sum(c["duration_ms"] for c in ctx._llm_log)
    ctx.stats["phase_timings"] = ctx._phase_timings


# ── Helpers ──────────────────────────────────────────────────────────────

async def _progress(ctx: PipelineContext, sb: Client, phase: int, msg: str, pct: int):
    ctx.current_phase = phase
    ctx.phase_message = msg
    update_job(sb, ctx.job_id, current_phase=msg, phase_number=phase, progress_pct=pct)


def _save_checkpoint(ctx: PipelineContext, sb: Client, phase_name: str, status: str = "completed") -> None:
    """Persist phase checkpoint to resume_jobs.stats after each phase.

    NOTE: update_job is synchronous — do NOT await this function.
    """
    import time as _time
    if "checkpoints" not in ctx.stats:
        ctx.stats["checkpoints"] = {}
    ctx.stats["checkpoints"][phase_name] = {
        "timestamp": int(_time.time()),
        "duration_ms": ctx._phase_timings.get(phase_name, 0),
        "status": status,
    }
    # Also update LLM totals
    if ctx._llm_log:
        ctx.stats["total_llm_calls"] = len(ctx._llm_log)
        ctx.stats["total_input_tokens"] = sum(e.get("input_tokens", 0) for e in ctx._llm_log)
        ctx.stats["total_output_tokens"] = sum(e.get("output_tokens", 0) for e in ctx._llm_log)
        ctx.stats["total_llm_ms"] = sum(e.get("duration_ms", 0) for e in ctx._llm_log)
    # Persist to DB
    try:
        update_job(sb, ctx.job_id, stats=ctx.stats)
    except Exception as e:
        logger.warning(f"Checkpoint save failed for {phase_name}: {e}")


MAX_LLM_RETRIES = 5


async def _oracle_call_with_fallback(
    ctx: PipelineContext,
    oracle_llm,
    fallback_llm,
    system: str,
    user: str,
    phase: int,
    temperature: float = 0.2,
) -> LLMResponse:
    """Call Oracle LLM directly (bypasses key_manager Groq routing), falls back to Groq on any error.

    Use this instead of _llm_call when you want Oracle llama3.2:1b — _llm_call's key_manager
    path ignores the llm parameter and always creates a Groq provider, bypassing Oracle.
    """
    try:
        import time as _time
        start = _time.time()
        resp = await oracle_llm.complete(system, user, temperature=temperature)
        duration = int((_time.time() - start) * 1000)
        ctx._llm_log.append({
            "phase": phase,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "duration_ms": duration,
            "model": resp.model,
        })
        return resp
    except Exception as e:
        logger.warning(f"Job {ctx.job_id} phase {phase}: Oracle failed ({e}), falling back to Groq")
        return await _llm_call(ctx, fallback_llm, system, user, phase=phase, temperature=temperature)


async def _llm_call(ctx: PipelineContext, llm, system: str, user: str, phase: int, temperature: float = 0.3) -> LLMResponse:
    """Call LLM with retry on rate limit (429) and track tokens + timing.

    If ctx.key_manager is set and has keys for ctx.model_provider, uses
    multi-key fallback (tries each DB key, then falls back to ctx.api_key).
    """
    import httpx
    import random

    # --- KeyManager path: rotate through user's DB keys ---
    if ctx.key_manager and ctx.key_manager.get_keys(ctx.model_provider):
        async def _km_call(api_key: str) -> LLMResponse:
            km_llm = get_provider(ctx.model_provider, api_key, ctx.model_id)
            return await km_llm.complete(system, user, temperature=temperature)

        start = time.time()
        resp = await ctx.key_manager.call_with_fallback(
            ctx.model_provider,
            _km_call,
            fallback_key=ctx.api_key,
        )
        duration = int((time.time() - start) * 1000)
        ctx._llm_log.append({
            "phase": phase,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "duration_ms": duration,
            "model": resp.model,
        })
        return resp

    # --- Default path: single key with retry ---
    for attempt in range(MAX_LLM_RETRIES + 1):
        try:
            start = time.time()
            resp = await llm.complete(system, user, temperature=temperature)
            duration = int((time.time() - start) * 1000)
            ctx._llm_log.append({
                "phase": phase,
                "input_tokens": resp.input_tokens,
                "output_tokens": resp.output_tokens,
                "duration_ms": duration,
                "model": resp.model,
            })
            return resp
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < MAX_LLM_RETRIES:
                # Rate limited — exponential backoff with jitter
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    try:
                        wait = min(float(retry_after), 60)
                    except ValueError:
                        wait = min(2 ** (attempt + 1), 30)
                else:
                    # 2s, 4s, 8s, 16s, 30s base — with ±25% jitter
                    base = min(2 ** (attempt + 1), 30)
                    jitter = base * 0.25 * (2 * random.random() - 1)
                    wait = base + jitter
                logger.warning(
                    f"Job {ctx.job_id} phase {phase}: rate limited (429), "
                    f"retrying in {wait:.1f}s (attempt {attempt + 1}/{MAX_LLM_RETRIES})"
                )
                await asyncio.sleep(wait)
                continue
            raise


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences and trailing commas."""
    import re
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1 if lines[0].startswith("```") else 0
        end = -1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fix trailing commas (common with smaller models): ,} → } and ,] → ]
        fixed = re.sub(r',\s*([}\]])', r'\1', text)
        return json.loads(fixed)


def _load_template(template_id: str) -> str:
    path = TEMPLATES_DIR / f"{template_id}.html"
    return path.read_text()


def _extract_company_keys(budget: dict) -> list[str]:
    """Extract company bullet keys from budget dict.

    Handles LLM format variations:
      - "company_1_total", "company_2_total" (canonical)
      - "American Express_total", "Flipkart_total" (real names + _total)
      - "American Express", "Flipkart" (just company names, no suffix)
    """
    NON_COMPANY = {"awards", "voluntary", "awards_total", "voluntary_total"}
    # Try canonical format first
    keys = sorted([k for k in budget if k.startswith("company_") and k.endswith("_total")])
    if keys:
        return keys
    # Fallback: any key ending in _total that isn't awards/voluntary
    keys = sorted([k for k in budget if k.endswith("_total") and k not in NON_COMPANY])
    if keys:
        return keys
    # Fallback: any key that isn't a known non-company key (LLM used raw company names)
    keys = sorted([k for k in budget if k not in NON_COMPANY and not isinstance(budget[k], str)])
    if keys:
        return keys
    return ["company_1_total"]


def _format_qa_context(ctx: PipelineContext) -> str:
    """Format Q&A answers into a string for LLM prompts."""
    if not ctx.qa_answers:
        return ""
    lines = []
    for qa in ctx.qa_answers:
        q = qa.get("question", "")
        a = qa.get("answer", "")
        if q and a:
            # Cap individual answers — auto-fill can dump raw career text
            if len(a) > 500:
                a = a[:500] + "..."
            lines.append(f"Q: {q}\nA: {a}")
    if not lines:
        return ""
    return "\n\n## Additional Context (from candidate Q&A)\n" + "\n\n".join(lines)


# ── Story 3.3: Post-LLM Validation Guards ────────────────────────────────

_EDUCATION_FILLER_PHRASES = (
    "passion for", "interest in", "dedicated to", "committed to",
    "enthusiastic about", "skilled in", "love for", "desire to",
    "aspiration", "driven by",
)


def _validate_phase_1_2(ctx: "PipelineContext") -> list[str]:
    """Validate Phase 1+2 LLM output. Returns list of failure reasons."""
    import re
    failures = []
    if not ctx.jd_keywords:
        failures.append("jd_keywords: empty list")
    colors = ctx.theme_colors or {}
    for key, val in colors.items():
        if val and not re.match(r'^#[0-9A-Fa-f]{6}$', val):
            failures.append(f"color {key}: invalid hex {val}")
    # Education highlights must not contain generic filler phrases
    for i, edu in enumerate(ctx._parsed.get("education", [])):
        highlights = edu.get("highlights", "")
        if highlights and isinstance(highlights, str):
            lower = highlights.lower()
            for phrase in _EDUCATION_FILLER_PHRASES:
                if phrase in lower:
                    failures.append(
                        f"education[{i}].highlights: contains filler phrase '{phrase}' — "
                        "must copy verbatim from career profile or use empty string"
                    )
                    break
    return failures


def _validate_phase_4a(bullets: list[dict]) -> list[str]:
    """Validate Phase 4A verbose bullets. Returns list of failure reasons."""
    import re
    failures = []
    for i, b in enumerate(bullets):
        text = b.get("text_html", "")
        plain = re.sub(r'<[^>]+>', '', text)
        if not (150 <= len(plain) <= 500):
            failures.append(f"bullet_{i}: length {len(plain)} outside 150-500")
        if '<b>' not in text and '<strong>' not in text:
            failures.append(f"bullet_{i}: missing bold tags")
    return failures


def _validate_phase_4c(bullets: list[dict]) -> list[str]:
    """Validate Phase 4C condensed bullets. Returns list of failure reasons."""
    import re
    failures = []
    for i, b in enumerate(bullets):
        text = b.get("text_html", "")
        plain = re.sub(r'<[^>]+>', '', text)
        if not (80 <= len(plain) <= 130):
            failures.append(f"bullet_{i}: length {len(plain)} outside 80-130")
    return failures


def _record_validation_failures(ctx: "PipelineContext", phase: str, failures: list[str]) -> None:
    """Append validation failures to ctx.stats['validation_failures']."""
    if not failures:
        return
    if "validation_failures" not in ctx.stats:
        ctx.stats["validation_failures"] = []
    ctx.stats["validation_failures"].extend([
        {"phase": phase, "check": f} for f in failures
    ])
    logger.warning(f"[Phase {phase}] validation: {len(failures)} failure(s): {failures[:3]}")


def _fetch_relevant_chunks(ctx: PipelineContext, sb: Client, keywords: list[str]) -> list[str]:
    """Query career_chunks via full-text search for relevant context."""
    if not keywords:
        return []
    try:
        import re
        # Sanitize keywords: strip tsquery special chars, filter empties
        sanitized = [re.sub(r"[|&!:()'\"]", "", k).strip() for k in keywords[:10]]
        terms = [t for t in sanitized if t]
        if not terms:
            return []
        query = " | ".join(f"'{t}'" for t in terms)
        result = (
            sb.table("career_chunks")
            .select("chunk_text")
            .eq("user_id", ctx.user_id)
            .limit(10)
            .text_search("search_vector", query)
            .execute()
        )
        if result.data:
            return [c["chunk_text"] for c in result.data]
    except Exception as e:
        logger.warning(f"Job {ctx.job_id}: chunk fetch failed — {e}")
    return []


# ── Phase 0: Nugget extraction + embedding (USE_NUGGETS=true only) ──────

def _db_row_to_nugget(row: dict) -> Nugget:
    """Convert a career_nuggets DB row to a Nugget dataclass."""
    return Nugget(
        nugget_index=row.get("nugget_index", 0),
        nugget_text=row.get("nugget_text", ""),
        question=row.get("question", ""),
        alt_questions=row.get("alt_questions") or [],
        answer=row.get("answer", ""),
        primary_layer=row.get("primary_layer", "A"),
        section_type=row.get("section_type"),
        importance=row.get("importance", "P2"),
        factuality=row.get("factuality", "fact"),
        temporality=row.get("temporality", "past"),
        duration=row.get("duration", "point_in_time"),
        leadership_signal=row.get("leadership_signal", "none"),
        company=row.get("company"),
        role=row.get("role"),
        event_date=row.get("event_date"),
        people=row.get("people") or [],
        tags=row.get("tags") or [],
        id=row.get("id"),
    )


async def phase_0_nuggets(ctx: PipelineContext, sb: Client, groq_api_key: str | None = None, byok_api_key: str | None = None, force: bool = False, force_delete: bool = False):
    """Phase 0: LLM-powered nugget extraction + embedding (USE_NUGGETS=true only).

    If the user already has career_nuggets (e.g., from TruthEngine onboarding),
    skip the expensive 70B extraction and load existing nuggets instead.

    Args:
        force: If True, bypass the USE_NUGGETS feature flag AND skip-check (used by /nuggets/refresh endpoint).
        force_delete: If True, delete existing nuggets before extraction. Default False — preserves existing data.
    """
    from ..config import USE_NUGGETS
    if not USE_NUGGETS and not force:
        return

    t0 = time.time()

    # ── Skip extraction if user already has nuggets from onboarding ──
    # This saves a Groq 70B call + Jina embedding batch per resume.
    if not force and not force_delete:
        try:
            existing = sb.table("career_nuggets").select("id", count="exact").eq("user_id", ctx.user_id).execute()
            existing_count = existing.count or 0
            if existing_count > 0:
                logger.info(f"[Phase 0] User has {existing_count} existing nuggets — loading from DB (skipping extraction)")
                rows = (
                    sb.table("career_nuggets")
                    .select("*")
                    .eq("user_id", ctx.user_id)
                    .order("nugget_index")
                    .execute()
                    .data or []
                )
                ctx._nuggets = [_db_row_to_nugget(row) for row in rows]
                logger.info(f"[Phase 0] Loaded {len(ctx._nuggets)} nuggets in {int((time.time()-t0)*1000)}ms")
                return
        except Exception as e:
            logger.warning(f"[Phase 0] Failed to check existing nuggets: {e} — proceeding with extraction")

    logger.info(f"[Phase 0] Starting nugget extraction for user {ctx.user_id}")

    jina_api_key = os.environ.get("JINA_API_KEY", "")

    # Embed each batch immediately after extraction — no credits wasted if interrupted
    async def _embed_batch_callback(batch_nuggets: list) -> None:
        if jina_api_key:
            await embed_nuggets(
                nuggets=batch_nuggets,
                jina_api_key=jina_api_key,
                sb=sb,
                user_id=ctx.user_id,
            )

    try:
        nuggets = await extract_nuggets(
            user_id=ctx.user_id,
            career_text=ctx.career_text,
            sb=sb,
            groq_api_key=groq_api_key,
            byok_api_key=byok_api_key,
            key_manager=ctx.key_manager,
            batch_callback=_embed_batch_callback,
            force_delete=force_delete,
        )

        if nuggets:
            jina_api_key = os.environ.get("JINA_API_KEY", "")
            embeddings = await embed_nuggets(
                nuggets=nuggets,
                jina_api_key=jina_api_key,
                sb=sb,
                user_id=ctx.user_id,
                key_manager=ctx.key_manager,
            )
            ctx._nuggets = nuggets
            embedded_count = sum(1 for n in nuggets if getattr(n, "id", None))
            logger.info(f"[Phase 0] Extracted {len(nuggets)} nuggets, {embedded_count} embedded")
        else:
            logger.warning("[Phase 0] Nugget extraction returned empty — falling back to paragraph chunking")
            ctx._nuggets = []

    except Exception as e:
        logger.warning(f"[Phase 0] Failed: {e} — falling back to paragraph chunking")
        ctx._nuggets = []

    ctx._phase_timings["phase_0"] = int((time.time() - t0) * 1000)
    _save_checkpoint(ctx, sb, "phase_0")


# ── Phase 1+2: Parse JD + Strategy + Brand Colors (merged — 1 LLM call) ──

async def phase_1_parse_and_strategy(ctx: PipelineContext, sb: Client, llm):
    """Merged Phase 1+2: parse JD/career + pick strategy + brand colors in ONE LLM call."""
    t0 = time.time()
    await _progress(ctx, sb, 1, "Analyzing job description", 5)

    # Load and parse template first
    template_html = _load_template(ctx.template_id)
    json.loads(
        await resume_parse_template(ParseTemplateInput(template_html=template_html), ctx=ctx)
    )

    if ctx.template_config is None:
        raise RuntimeError("Template parsing failed: template_config not set")

    qa_context = _format_qa_context(ctx)
    phase_1_2_template, _ = get_prompt("phase_1_2", prompts.PHASE_1_2_SYSTEM)
    system_msg = phase_1_2_template.format(
        strategies_json=json.dumps(
            {k: {"description": v["description"], "trigger": v["trigger"]} for k, v in STRATEGIES.items()},
            indent=2,
        ),
    )
    # Smart truncation for Phase 1: prioritize professional sections over
    # early-life narrative to avoid 413 Payload Too Large on Groq.
    career_text_p1 = _prepare_career_for_phase1(ctx.career_text, ctx.job_id)
    user_msg = prompts.PHASE_1_2_USER.format(
        jd_text=escape_llm_input(ctx.jd_text),
        career_text=escape_llm_input(career_text_p1),
        qa_context=qa_context,
    )

    resp = await _llm_call(ctx, llm, system_msg, user_msg, phase=1)
    trace_generation(
        trace_name="pipeline", generation_name="phase_1_2",
        model=resp.model, system_prompt=system_msg, user_input=user_msg,
        output=resp.text, user_id=ctx.user_id,
    )
    _DEFAULT_COLORS = {
        "brand_primary": "#1a3a5c", "brand_secondary": "#2d6a9f",
        "text_primary": "#1a1a1a", "text_secondary": "#4a4a4a",
    }
    try:
        data = _parse_json(resp.text)
        ctx.career_level = data.get("career_level", "senior")
        ctx.jd_keywords = data.get("jd_keywords", [])
        ctx.strategy = data.get("strategy", "BALANCED")
        ctx.theme_colors = ctx.override_theme_colors or data.get("theme_colors") or _DEFAULT_COLORS
    except json.JSONDecodeError as e:
        raise ValueError(f"Phase 1+2: LLM returned invalid JSON — {e}. Response start: {resp.text[:300]}") from e

    ctx._parsed = data
    ctx._section_order = data.get("section_order", [])
    ctx._bullet_budget = data.get("bullet_budget", {})

    # Guard 3.3c: validate Phase 1+2 output
    p12_failures = _validate_phase_1_2(ctx)
    if p12_failures:
        logger.warning(f"Job {ctx.job_id} phase 1+2 validation failed — retrying once")
        try:
            resp_retry = await _llm_call(ctx, llm, system_msg, user_msg, phase=1)
            data_retry = _parse_json(resp_retry.text)
            ctx.career_level = data_retry.get("career_level", ctx.career_level)
            ctx.jd_keywords = data_retry.get("jd_keywords", ctx.jd_keywords)
            ctx.strategy = data_retry.get("strategy", ctx.strategy)
            ctx.theme_colors = ctx.override_theme_colors or data_retry.get("theme_colors", ctx.theme_colors)
            ctx._parsed = data_retry
            ctx._section_order = data_retry.get("section_order", ctx._section_order)
            ctx._bullet_budget = data_retry.get("bullet_budget", ctx._bullet_budget)
            p12_failures_retry = _validate_phase_1_2(ctx)
            if p12_failures_retry:
                _record_validation_failures(ctx, "1_2", p12_failures_retry)
        except Exception as e:
            logger.warning(f"Job {ctx.job_id} phase 1+2 retry failed: {e} — proceeding best-effort")
            _record_validation_failures(ctx, "1_2", p12_failures)

    # Fetch relevant career chunks via full-text search
    keyword_strs = [kw if isinstance(kw, str) else kw.get("keyword", "") for kw in ctx.jd_keywords]
    ctx._relevant_chunks = _fetch_relevant_chunks(ctx, sb, keyword_strs)

    ctx._phase_timings["phase_1_2"] = int((time.time() - t0) * 1000)
    _save_checkpoint(ctx, sb, "phase_1_2")
    await _progress(ctx, sb, 2, f"Strategy: {ctx.strategy}", 25)


# ── Phase 2.5: Vector Retrieval Per Company (QMD — no LLM) ──────────────

async def phase_2_5_vector_retrieval(ctx: PipelineContext, sb: Client):
    """Retrieve relevant career chunks per company via QMD hybrid search or hybrid_retrieve."""
    from ..config import USE_NUGGETS
    t0 = time.time()
    await _progress(ctx, sb, 2, "Retrieving relevant experience", 28)

    if USE_NUGGETS:
        # New path: hybrid retrieval over career_nuggets
        companies = ctx._parsed.get("companies", [])
        keyword_strs = [kw if isinstance(kw, str) else kw.get("keyword", "") for kw in ctx.jd_keywords]

        all_results = []
        method = "raw_text_fallback"
        for co in companies:
            co_name = co.get("name", "") if isinstance(co, dict) else str(co)
            query = f"{co_name} {' '.join(keyword_strs[:5])}"

            # similarity_threshold=0.55: drop vector matches that aren't semantically
            # close. Anti-hallucination — empty retrieval > fake retrieval. Only
            # affects vector tier once the match_career_nuggets RPC is in place.
            results, method = await hybrid_retrieve(
                sb=sb,
                user_id=ctx.user_id,
                query=query,
                company=co_name,
                limit=8,
                similarity_threshold=0.55,
            )
            all_results.extend(results)
            logger.info(f"[Phase 2.5] {co_name}: {len(results)} nuggets via {method}")

        ctx._nugget_results = all_results

        # Backward-compatible: populate _company_chunks from nugget answers (keyed by idx)
        ctx._company_chunks = {}
        for r in all_results:
            key = r.company or "general"
            # Find the index of this company in parsed companies list
            matched_idx = next(
                (i for i, co in enumerate(companies) if co.get("name", "") == r.company),
                None,
            )
            bucket = matched_idx if matched_idx is not None else key
            if bucket not in ctx._company_chunks:
                ctx._company_chunks[bucket] = []
            ctx._company_chunks[bucket].append(r.answer)

        # Also populate _relevant_chunks for backward compat (non-company-specific usage)
        ctx._relevant_chunks = [r.answer for r in all_results[:20]]

        # Telemetry
        ctx.stats["retrieval_method"] = method
        ctx.stats["nuggets_retrieved"] = len(all_results)
        ctx.stats["companies_with_zero_hits"] = [
            co.get("name", "") if isinstance(co, dict) else str(co)
            for co in companies
            if not any(
                r.company == (co.get("name", "") if isinstance(co, dict) else str(co))
                for r in all_results
            )
        ]
        logger.info(
            f"Job {ctx.job_id}: [Phase 2.5] hybrid_retrieve total={len(all_results)} "
            f"method={method} zero_hit_companies={ctx.stats['companies_with_zero_hits']}"
        )

    else:
        # Old path: QMD/FTS logic unchanged
        companies = ctx._parsed.get("companies", [])
        keyword_strs = [kw if isinstance(kw, str) else kw.get("keyword", "") for kw in ctx.jd_keywords]
        jd_query = " ".join(keyword_strs[:10])

        for idx, co in enumerate(companies):
            co_name = co.get("name", "")
            query = f"{co_name} {jd_query}"

            # Try QMD first, fall back to Supabase FTS
            chunks = qmd_hybrid_search(ctx.user_id, query, limit=8)
            if not chunks:
                chunks = fallback_fts_search(sb, ctx.user_id, query, limit=8)

            ctx._company_chunks[idx] = chunks
            logger.info(f"Job {ctx.job_id}: Company {idx} '{co_name}' — {len(chunks)} chunks retrieved")

    ctx._phase_timings["phase_2_5"] = int((time.time() - t0) * 1000)
    _save_checkpoint(ctx, sb, "phase_2_5")


# ── Phase 3.5: Stencil Draft (static sections + placeholder experience) ─

async def phase_3_5_stencil_draft(ctx: PipelineContext, sb: Client):
    """Build complete HTML for static sections and experience headers with placeholder bullets.

    Static sections (Education, Skills, Awards, Interests, Header) are FINAL from this point.
    Professional Experience shows company headers with '...' placeholders.
    """
    t0 = time.time()
    await _progress(ctx, sb, 3, "Building layout stencil", 36)

    parsed = ctx._parsed
    template_html = _load_template(ctx.template_id)
    section_order = ctx._section_order or ["Professional Experience", "Awards & Recognitions",
                                            "Voluntary Work & Projects", "Academic Achievements",
                                            "Core Competencies & Skills", "Additional Interests"]
    order_map = _get_section_order_map(section_order)
    companies = parsed.get("companies", [])

    sections = []

    # Experience section: company headers with placeholder bullets
    if "experience" in order_map:
        placeholder_bullets = []
        budget = ctx._bullet_budget
        company_keys = _extract_company_keys(budget)
        for idx, ck in enumerate(company_keys):
            num = budget.get(ck, 4)
            for j in range(num):
                placeholder_bullets.append({
                    "company_index": idx,
                    "project_group": 0,
                    "text_html": "...",
                    "verb": "",
                    "fill_percentage": 0,
                })
        sections.append(SectionContent(
            section_html=_build_experience_html(placeholder_bullets, companies),
            section_order=order_map["experience"],
        ))

    # Static sections — built once, final from this point
    if "education" in order_map:
        frozen_edu = _apply_frozen_section("education", ctx)
        if frozen_edu is not None:
            sections.append(SectionContent(section_html=frozen_edu, section_order=order_map["education"]))
        elif parsed.get("education"):
            sections.append(SectionContent(
                section_html=_build_education_html(parsed["education"]),
                section_order=order_map["education"],
            ))
    if "skills" in order_map:
        frozen_skills = _apply_frozen_section("skills", ctx)
        if frozen_skills is not None:
            sections.append(SectionContent(section_html=frozen_skills, section_order=order_map["skills"]))
        elif parsed.get("skills"):
            sections.append(SectionContent(
                section_html=_build_skills_html(parsed["skills"]),
                section_order=order_map["skills"],
            ))
    if "awards" in order_map:
        frozen_awards = _apply_frozen_section("awards", ctx)
        if frozen_awards is not None:
            sections.append(SectionContent(section_html=frozen_awards, section_order=order_map["awards"]))
        elif parsed.get("awards"):
            sections.append(SectionContent(
                section_html=_build_awards_html(parsed["awards"]),
                section_order=order_map["awards"],
            ))
    if "voluntary" in order_map:
        frozen_voluntary = _apply_frozen_section("voluntary", ctx)
        if frozen_voluntary is not None:
            sections.append(SectionContent(section_html=frozen_voluntary, section_order=order_map["voluntary"]))
        elif parsed.get("voluntary"):
            sections.append(SectionContent(
                section_html=_build_voluntary_html(parsed["voluntary"]),
                section_order=order_map["voluntary"],
            ))
    if "interests" in order_map:
        frozen_interests = _apply_frozen_section("interests", ctx)
        if frozen_interests is not None:
            sections.append(SectionContent(section_html=frozen_interests, section_order=order_map["interests"]))
        elif parsed.get("interests"):
            sections.append(SectionContent(
                section_html=_build_interests_html(parsed["interests"]),
                section_order=order_map["interests"],
            ))

    # Assemble stencil HTML
    contact = parsed.get("contact_info", {})
    colors = ctx.theme_colors or {}
    theme = ThemeColors(
        brand_primary=colors.get("brand_primary", "#4285F4"),
        brand_secondary=colors.get("brand_secondary", "#EA4335"),
        brand_tertiary=colors.get("brand_tertiary", ""),
        brand_quaternary=colors.get("brand_quaternary", ""),
    )
    contacts = []
    if contact.get("phone"):
        contacts.append(f"Phone: {contact['phone']}")
    if contact.get("email"):
        contacts.append(f"Email: {contact['email']}")
    if contact.get("linkedin"):
        contacts.append(f"LinkedIn: {contact['linkedin']}")
    if contact.get("portfolio"):
        contacts.append(f"Portfolio: {contact['portfolio']}")
    header = HeaderData(
        name=contact.get("name", ""),
        role=parsed.get("target_role", ""),
        contacts=contacts,
    )

    result = json.loads(
        await resume_assemble_html(AssembleInput(
            template_html=template_html,
            theme_colors=theme,
            header=header,
            sections=sections,
            css_overrides="",
        ))
    )

    ctx.draft_html = result.get("final_html", "")
    update_job(sb, ctx.job_id, draft_html=ctx.draft_html)

    ctx._phase_timings["phase_3_5"] = int((time.time() - t0) * 1000)
    await _progress(ctx, sb, 3, "Stencil ready", 38)


# ── Phase 3.5a: Professional Summary Width Optimization ──────────────────

async def phase_3_5a_professional_summary(ctx: PipelineContext, sb: Client, llm) -> None:
    """Optimize the professional summary to fill 95-98% of line width.

    The career_summary from Phase 1 is a 2-sentence narrative extracted by the LLM.
    This phase:
      1. Measures each summary sentence against the summary_line budget.
      2. Sentences that are already in range [95%, 100%] are kept as-is.
      3. Sentences that are TOO_SHORT or OVERFLOW are sent to a targeted LLM
         rewrite call (same pattern as phase_5 per-bullet synonym retry).
      4. Stores final HTML in ctx._summary_html for phase_8_assembly to inject.

    Width target: 95-98% of summary_line budget (matches experience bullet targets).
    """
    t0 = time.time()
    await _progress(ctx, sb, 3, "Optimizing professional summary", 39)

    summary_raw: str = ctx._parsed.get("career_summary", "")
    if not summary_raw or not summary_raw.strip():
        logger.info(f"Job {ctx.job_id} [Phase 3.5a]: no career_summary — skipping")
        ctx._phase_timings["phase_3_5a"] = int((time.time() - t0) * 1000)
        return

    # Split into individual sentences for per-sentence measurement
    import re as _re
    # Split on sentence-ending punctuation followed by space + capital or end
    raw_sentences = [s.strip() for s in _re.split(r'(?<=[.!?])\s+', summary_raw.strip()) if s.strip()]
    if not raw_sentences:
        raw_sentences = [summary_raw.strip()]

    # Get budget parameters from template_config
    bullet_budget = ctx.template_config.get("budgets", {}).get("bullet", {})
    if hasattr(bullet_budget, "model_dump"):
        bullet_budget = bullet_budget.model_dump()
    # Use summary_line budget if available, else fall back to bullet budget values
    summary_budget_cfg = ctx.template_config.get("budgets", {}).get("summary_line", {})
    if hasattr(summary_budget_cfg, "model_dump"):
        summary_budget_cfg = summary_budget_cfg.model_dump()
    raw_budget = summary_budget_cfg.get("raw_budget", bullet_budget.get("raw_budget", 101.4))
    range_min_90 = summary_budget_cfg.get("range_min_90", bullet_budget.get("range_min_90", 91.3))

    optimized_sentences: list[str] = []
    needs_fix: list[dict] = []

    # Step 1: Measure all sentences
    for i, sentence in enumerate(raw_sentences):
        try:
            result = json.loads(
                await resume_measure_width(
                    MeasureWidthInput(text_html=sentence, line_type="summary_line"),
                    template_config=ctx.template_config,
                )
            )
            status = result.get("status", "PASS")
            fill = result.get("fill_percentage", 0.0)
            weighted_total = result.get("weighted_total", 0.0)

            if status == "PASS":
                optimized_sentences.append(sentence)
                logger.info(f"[Phase 3.5a] sentence {i}: PASS ({fill:.1f}%)")
            else:
                needs_fix.append({
                    "index": i,
                    "text_html": sentence,
                    "fill_percentage": fill,
                    "weighted_total": weighted_total,
                    "status": status,
                })
                optimized_sentences.append(sentence)  # placeholder, will be replaced
                logger.info(f"[Phase 3.5a] sentence {i}: {status} ({fill:.1f}%) — needs fix")
        except Exception as e:
            logger.warning(f"[Phase 3.5a] measure_width failed for sentence {i}: {e} — keeping as-is")
            optimized_sentences.append(sentence)

    # Step 2: LLM-rewrite sentences that don't pass (same approach as phase_5 per-bullet)
    if needs_fix:
        logger.info(f"[Phase 3.5a] {len(needs_fix)} sentence(s) need width fixing")

        for m in needs_fix:
            idx = m["index"]
            fill = m["fill_percentage"]
            status = m["status"]
            direction = "trim" if status == "OVERFLOW" else "expand"
            current_text = m["text_html"]

            # Calculate gap for the prompt
            if status == "TOO_SHORT":
                gap_desc = f"need to expand by ~{round(range_min_90 - m['weighted_total'], 1)} CU to fill 95-98% of line width"
            else:
                gap_desc = f"need to shorten by ~{round(m['weighted_total'] - raw_budget, 1)} CU to fit within line width"

            action = "lengthen/expand" if direction == "expand" else "shorten/trim"
            system_prompt = (
                "You are a professional resume writer. Rewrite the given career summary sentence "
                "to adjust its length while preserving the exact meaning and professional tone. "
                "Return ONLY the rewritten sentence — no markdown, no commentary, no quotes."
            )
            user_prompt = (
                f"Rewrite this career summary sentence to {action} it slightly.\n\n"
                f"Current: {current_text}\n\n"
                f"Width issue: {gap_desc} (current fill: {fill:.1f}%, target: 95-100%).\n\n"
                f"Rules:\n"
                f"- Preserve factual content and professional tone\n"
                f"- Use <b>word</b> tags for key terms/metrics if helpful\n"
                f"- Keep it a single complete sentence\n"
                f"- Return ONLY the rewritten sentence text (with optional HTML bold tags)"
            )

            try:
                _oracle_3_5a = _get_oracle_llm()
                if _oracle_3_5a is not None:
                    resp = await _oracle_call_with_fallback(ctx, _oracle_3_5a, llm, system_prompt, user_prompt, phase=3, temperature=0.2)
                else:
                    resp = await _llm_call(ctx, llm, system_prompt, user_prompt, phase=3, temperature=0.2)
                rewritten = resp.text.strip() if resp else None
                # Strip accidental markdown fences
                if rewritten and rewritten.startswith("```"):
                    lines = rewritten.split("\n")
                    rewritten = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

                if rewritten:
                    # Verify width of rewritten sentence
                    verify = json.loads(
                        await resume_measure_width(
                            MeasureWidthInput(text_html=rewritten, line_type="summary_line"),
                            template_config=ctx.template_config,
                        )
                    )
                    new_fill = verify.get("fill_percentage", 0.0)
                    new_status = verify.get("status", "ERROR")

                    if new_status == "PASS" or (88 <= new_fill <= 103):
                        optimized_sentences[idx] = rewritten
                        logger.info(f"[Phase 3.5a] sentence {idx} fixed: {fill:.1f}% → {new_fill:.1f}%")
                    else:
                        # Keep original — rewrite didn't improve enough
                        logger.info(f"[Phase 3.5a] sentence {idx} rewrite still {new_status} ({new_fill:.1f}%) — keeping original")
            except Exception as e:
                logger.warning(f"[Phase 3.5a] LLM rewrite failed for sentence {idx}: {e} — keeping original")

    # Step 3: Build final summary HTML — each sentence on its own summary-line span
    summary_parts: list[str] = []
    for sentence in optimized_sentences:
        if sentence.strip():
            summary_parts.append(f'<span class="summary-line">{sentence}</span>')

    ctx._summary_html = "\n".join(summary_parts) if summary_parts else None

    if ctx._summary_html:
        ctx.stats["summary_sentences"] = len(optimized_sentences)
        logger.info(f"[Phase 3.5a] summary ready: {len(optimized_sentences)} sentence(s)")
    else:
        logger.warning(f"[Phase 3.5a] no summary HTML produced")

    ctx._phase_timings["phase_3_5a"] = int((time.time() - t0) * 1000)
    _save_checkpoint(ctx, sb, "phase_3_5a")


# ── Phase 4A: Verbose Bullets (one LLM call PER COMPANY) ────────────────

async def phase_4a_verbose_bullets(ctx: PipelineContext, sb: Client, llm):
    """Write verbose 200-400 char paragraphs per company, with review gates."""
    t0 = time.time()

    strategy_info = STRATEGIES.get(ctx.strategy, STRATEGIES["BALANCED"])
    budget = ctx._bullet_budget
    parsed = ctx._parsed
    companies = parsed.get("companies", [])
    company_keys = _extract_company_keys(budget)

    keyword_strs = [kw if isinstance(kw, str) else kw.get("keyword", "") for kw in ctx.jd_keywords]
    jd_keywords_compact = ", ".join(keyword_strs)

    phase_4a_template, _ = get_prompt("phase_4a_verbose", prompts.PHASE_4A_VERBOSE_SYSTEM)

    all_verbose = []
    used_verbs_so_far = []

    for idx, ck in enumerate(company_keys):
        co = companies[idx] if idx < len(companies) else {}
        co_name = co.get("name", f"Company {idx + 1}")
        num_bullets = budget.get(ck, 4)

        await _progress(ctx, sb, 4, f"Writing paragraphs — {co_name}", 40 + idx * 5)

        # Get per-company context: QMD chunks or career text fallback
        if idx in ctx._company_chunks and ctx._company_chunks[idx]:
            company_context = "\n\n---\n\n".join(ctx._company_chunks[idx])[:5000]
        else:
            company_context = _get_company_context(ctx, idx)

        system_msg = phase_4a_template.format(
            bullet_count=num_bullets,
            used_verbs=", ".join(used_verbs_so_far) if used_verbs_so_far else "none",
            strategy=ctx.strategy,
            strategy_description=strategy_info["description"],
            career_level=ctx.career_level,
        )
        # v4: build JD requirements list for covers_requirements mapping
        jd_reqs = parsed.get("requirements", [])
        jd_reqs_list = "\n".join(
            f"  {r.get('id', f'r{i+1}')}: [{r.get('importance', 'required')}] {r.get('text', '')}"
            for i, r in enumerate(jd_reqs)
        ) if jd_reqs else "(No JD requirements available)"

        user_msg = prompts.PHASE_4A_VERBOSE_USER.format(
            jd_keywords_compact=jd_keywords_compact,
            jd_requirements_list=jd_reqs_list,
            company_name=co_name,
            company_title=co.get("title", ""),
            company_dates=co.get("date_range", ""),
            company_team=co.get("team", ""),
            company_chunks=escape_llm_input(company_context),
            bullet_count=num_bullets,
        )

        resp = await _llm_call(ctx, llm, system_msg, user_msg, phase=4, temperature=0.4)
        trace_generation(
            trace_name="pipeline", generation_name="phase_4a_verbose",
            model=resp.model, system_prompt=system_msg, user_input=user_msg,
            output=resp.text, user_id=ctx.user_id,
        )
        try:
            data = _parse_json(resp.text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Phase 4A ({co_name}): invalid JSON — {e}") from e

        for p in data.get("paragraphs", []):
            p["company_index"] = idx
            all_verbose.append(p)
            if p.get("verb"):
                used_verbs_so_far.append(p["verb"])

        # Update draft_html with verbose paragraphs for this company
        _update_draft_with_verbose(ctx, all_verbose, companies)
        update_job(sb, ctx.job_id, draft_html=ctx.draft_html)

        # Review gate: pause between companies for natural pacing
        if idx < len(company_keys) - 1 and REVIEW_PAUSE_SECONDS > 0:
            logger.info(f"Job {ctx.job_id}: review gate after {co_name} — pausing {REVIEW_PAUSE_SECONDS}s")
            await asyncio.sleep(REVIEW_PAUSE_SECONDS)

    ctx._verbose_bullets = all_verbose

    # Guard 3.3a: validate Phase 4A verbose bullets
    p4a_failures = _validate_phase_4a(ctx._verbose_bullets)
    if p4a_failures:
        logger.warning(f"Job {ctx.job_id} phase 4A validation failed — retrying once")
        try:
            # Retry: rebuild all companies in a fresh pass
            all_verbose_retry: list[dict] = []
            used_verbs_retry: list[str] = []
            for idx, ck in enumerate(company_keys):
                co = companies[idx] if idx < len(companies) else {}
                co_name = co.get("name", f"Company {idx + 1}")
                num_bullets = budget.get(ck, 4)
                if idx in ctx._company_chunks and ctx._company_chunks[idx]:
                    company_context = "\n\n---\n\n".join(ctx._company_chunks[idx])[:5000]
                else:
                    company_context = _get_company_context(ctx, idx)
                sys_r = phase_4a_template.format(
                    bullet_count=num_bullets,
                    used_verbs=", ".join(used_verbs_retry) if used_verbs_retry else "none",
                    strategy=ctx.strategy,
                    strategy_description=strategy_info["description"],
                    career_level=ctx.career_level,
                )
                usr_r = prompts.PHASE_4A_VERBOSE_USER.format(
                    jd_keywords_compact=jd_keywords_compact,
                    company_name=co_name,
                    company_title=co.get("title", ""),
                    company_dates=co.get("date_range", ""),
                    company_team=co.get("team", ""),
                    company_chunks=escape_llm_input(company_context),
                    bullet_count=num_bullets,
                )
                resp_r = await _llm_call(ctx, llm, sys_r, usr_r, phase=4, temperature=0.4)
                try:
                    data_r = _parse_json(resp_r.text)
                    for p in data_r.get("paragraphs", []):
                        p["company_index"] = idx
                        all_verbose_retry.append(p)
                        if p.get("verb"):
                            used_verbs_retry.append(p["verb"])
                except json.JSONDecodeError:
                    pass
            if all_verbose_retry:
                ctx._verbose_bullets = all_verbose_retry
                all_verbose = all_verbose_retry
            p4a_failures_retry = _validate_phase_4a(ctx._verbose_bullets)
            if p4a_failures_retry:
                _record_validation_failures(ctx, "4a", p4a_failures_retry)
        except Exception as e:
            logger.warning(f"Job {ctx.job_id} phase 4A retry failed: {e} — proceeding best-effort")
            _record_validation_failures(ctx, "4a", p4a_failures)

    # Register all verbs
    verbs = [b["verb"] for b in all_verbose if b.get("verb")]
    await resume_track_verbs(TrackVerbsInput(action="register", verbs=verbs), ctx=ctx)

    ctx._phase_timings["phase_4a"] = int((time.time() - t0) * 1000)
    _save_checkpoint(ctx, sb, "phase_4a")
    await _progress(ctx, sb, 4, f"Wrote {len(all_verbose)} paragraphs", 55)


def _update_draft_with_verbose(ctx: PipelineContext, verbose_bullets: list, companies: list):
    """Replace experience section in draft_html with current verbose paragraphs."""
    if not ctx.draft_html:
        return

    # Build experience HTML from verbose paragraphs (using text_html directly)
    exp_html = _build_experience_html(verbose_bullets, companies)

    # Replace the Professional Experience section in draft_html
    import re
    pattern = r'(<div class="section-title">Professional Experience.*?)(?=<div class="section-title">|</div>\s*</div>\s*</div>\s*$)'
    # Simpler: find and replace between experience section markers
    marker_start = '<div class="section-title">Professional Experience'
    idx = ctx.draft_html.find(marker_start)
    if idx == -1:
        return

    # Find the next section-title after experience (or end of content)
    next_section = ctx.draft_html.find('<div class="section-title">', idx + len(marker_start))
    if next_section == -1:
        # Experience is the last section before closing tags
        # Find the closing </div> tags that close the page content
        close_idx = ctx.draft_html.rfind('</div>')
        if close_idx > idx:
            next_section = close_idx

    if next_section > idx:
        ctx.draft_html = ctx.draft_html[:idx] + exp_html + "\n" + ctx.draft_html[next_section:]


# ── Phase 4B: Rank Verbose Bullets by BRS (no LLM) ──────────────────────

async def phase_4b_ranking(ctx: PipelineContext, sb: Client):
    """Score and rank verbose bullets by BRS. Trim to budget."""
    t0 = time.time()
    await _progress(ctx, sb, 4, "Ranking by relevance", 57)

    candidate_bullets = []
    for i, b in enumerate(ctx._verbose_bullets):
        candidate_bullets.append(CandidateBullet(
            project_id=f"verbose_{i}",
            raw_text=b.get("text_html", ""),
            group_id=f"company_{b.get('company_index', 0)}",
            group_theme=str(b.get("project_group", 0)),
            position_in_group=i,
        ))

    score_result = json.loads(
        await resume_score_bullets(ScoreBulletsInput(
            bullets=candidate_bullets,
            jd_keywords=[{"keyword": kw, "category": "skill"} if isinstance(kw, str) else kw for kw in ctx.jd_keywords],
            career_level=ctx.career_level,
            total_bullet_budget=len(ctx._verbose_bullets),
        ))
    )

    # Sort by BRS within each company, keep all (trimming is optional)
    scored = score_result.get("scored_bullets", [])
    brs_map = {s["project_id"]: s["brs"] for s in scored}

    for i, b in enumerate(ctx._verbose_bullets):
        b["brs"] = brs_map.get(f"verbose_{i}", 0)

    # Sort within each company by BRS descending
    from collections import defaultdict
    by_company = defaultdict(list)
    for b in ctx._verbose_bullets:
        by_company[b["company_index"]].append(b)

    ranked = []
    for idx in sorted(by_company.keys()):
        company_bullets = sorted(by_company[idx], key=lambda x: x.get("brs", 0), reverse=True)
        ranked.extend(company_bullets)

    ctx._ranked_verbose_bullets = ranked
    ctx._phase_timings["phase_4b"] = int((time.time() - t0) * 1000)
    await _progress(ctx, sb, 4, "Bullets ranked", 58)


# ── Phase 4C: Condense Verbose Paragraphs to Bullets (1 LLM call) ───────

async def phase_4c_condense_bullets(ctx: PipelineContext, sb: Client, llm):
    """Condense all verbose paragraphs to 95-110 char bullets in one batched LLM call."""
    t0 = time.time()
    await _progress(ctx, sb, 4, "Condensing to bullet points", 59)

    verbose = ctx._ranked_verbose_bullets or ctx._verbose_bullets
    if not verbose:
        raise ValueError("Phase 4C: No verbose bullets to condense")

    phase_4c_template, _ = get_prompt("phase_4c_condense", prompts.PHASE_4C_CONDENSE_SYSTEM)

    # Build paragraphs section for prompt
    para_lines = []
    for i, b in enumerate(verbose):
        para_lines.append(f"PARAGRAPH {i} (Company: {b.get('company_index', 0)}, Verb: {b.get('verb', '')}):")
        para_lines.append(f'"{b.get("text_html", "")}"')
        para_lines.append("")

    system_msg = phase_4c_template.format(
        paragraph_count=len(verbose),
    )
    user_msg = prompts.PHASE_4C_CONDENSE_USER.format(
        paragraphs_section="\n".join(para_lines),
    )

    resp = await _llm_call(ctx, llm, system_msg, user_msg, phase=4, temperature=0.2)
    trace_generation(
        trace_name="pipeline", generation_name="phase_4c_condense",
        model=resp.model, system_prompt=system_msg, user_input=user_msg,
        output=resp.text, user_id=ctx.user_id,
    )
    try:
        data = _parse_json(resp.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Phase 4C: invalid JSON — {e}") from e

    # Map condensed bullets back to their verbose originals
    condensed_map = {}
    for b in data.get("bullets", []):
        condensed_map[b["paragraph_index"]] = b

    all_bullets = []
    for i, v in enumerate(verbose):
        c = condensed_map.get(i)
        if c:
            bullet = {
                "company_index": v["company_index"],
                "project_group": v.get("project_group", 0),
                "text_html": c["text_html"],
                "verb": c.get("verb", v.get("verb", "")),
                # v4: carry forward verbose_context + xyz from Phase 4A for per-bullet width opt
                "verbose_context": v.get("verbose_context", ""),
                "xyz": v.get("xyz", {}),
                "covers_requirements": v.get("covers_requirements", []),
            }
        else:
            # Fallback: use verbose text directly (condense missed this one)
            bullet = {
                "company_index": v["company_index"],
                "project_group": v.get("project_group", 0),
                "text_html": v["text_html"],
                "verb": v.get("verb", ""),
                "verbose_context": v.get("verbose_context", ""),
                "xyz": v.get("xyz", {}),
                "covers_requirements": v.get("covers_requirements", []),
            }
        all_bullets.append(bullet)

    ctx._raw_bullets = all_bullets

    # Guard 3.3b: validate Phase 4C condensed bullets
    p4c_failures = _validate_phase_4c(ctx._raw_bullets)
    if p4c_failures:
        logger.warning(f"Job {ctx.job_id} phase 4C validation failed — retrying once")
        try:
            resp_retry = await _llm_call(ctx, llm, system_msg, user_msg, phase=4, temperature=0.2)
            data_retry = _parse_json(resp_retry.text)
            condensed_map_retry: dict = {}
            for b in data_retry.get("bullets", []):
                condensed_map_retry[b["paragraph_index"]] = b
            all_bullets_retry: list[dict] = []
            for i, v in enumerate(verbose):
                c = condensed_map_retry.get(i)
                if c:
                    bullet = {
                        "company_index": v["company_index"],
                        "project_group": v.get("project_group", 0),
                        "text_html": c["text_html"],
                        "verb": c.get("verb", v.get("verb", "")),
                        "verbose_context": v.get("verbose_context", ""),
                        "xyz": v.get("xyz", {}),
                        "covers_requirements": v.get("covers_requirements", []),
                    }
                else:
                    bullet = {
                        "company_index": v["company_index"],
                        "project_group": v.get("project_group", 0),
                        "text_html": v["text_html"],
                        "verb": v.get("verb", ""),
                        "verbose_context": v.get("verbose_context", ""),
                        "xyz": v.get("xyz", {}),
                        "covers_requirements": v.get("covers_requirements", []),
                    }
                all_bullets_retry.append(bullet)
            if all_bullets_retry:
                ctx._raw_bullets = all_bullets_retry
                all_bullets = all_bullets_retry
            p4c_failures_retry = _validate_phase_4c(ctx._raw_bullets)
            if p4c_failures_retry:
                _record_validation_failures(ctx, "4c", p4c_failures_retry)
        except Exception as e:
            logger.warning(f"Job {ctx.job_id} phase 4C retry failed: {e} — proceeding best-effort")
            _record_validation_failures(ctx, "4c", p4c_failures)

    # Update draft_html with condensed bullets
    companies = ctx._parsed.get("companies", [])
    _update_draft_with_verbose(ctx, all_bullets, companies)
    update_job(sb, ctx.job_id, draft_html=ctx.draft_html)

    ctx._phase_timings["phase_4c"] = int((time.time() - t0) * 1000)
    _save_checkpoint(ctx, sb, "phase_4c")
    await _progress(ctx, sb, 4, f"Condensed {len(all_bullets)} bullets", 62)


# ── Phase 3: Page Fit Planning ────────────────────────────────────────────

async def phase_3_page_fit(ctx: PipelineContext, sb: Client):
    await _progress(ctx, sb, 3, "Planning page layout", 30)

    # LLM already gave us section_order + bullet_budget in Phase 2.
    # We build SectionSpec objects and validate with the tool.
    budget = ctx._bullet_budget
    section_order = ctx._section_order

    # Build section specs from the budget
    sections = [SectionSpec(section_type="header", entry_count=1)]

    for section_name in section_order:
        s_lower = section_name.lower()
        if "experience" in s_lower or "professional" in s_lower:
            # Experience section: derive from budget
            company_keys = _extract_company_keys(budget)
            entry_count = len(company_keys)
            project_counts = []
            for ck in company_keys:
                total = budget.get(ck, 4)
                # Split bullets into groups of 2-3
                if total <= 3:
                    project_counts.append(1)
                elif total <= 6:
                    project_counts.append(2)
                else:
                    project_counts.append(3)
            sections.append(SectionSpec(
                section_type="experience",
                entry_count=entry_count,
                project_count_per_entry=project_counts,
                bullets_per_project=max(budget.get(company_keys[0], 4) // max(project_counts[0] if project_counts else 1, 1), 2),
                has_entry_subhead=True,
            ))
        elif "award" in s_lower or "recognition" in s_lower:
            sections.append(SectionSpec(
                section_type="awards",
                entry_count=1,
                bullets_per_project=budget.get("awards", 2),
                has_entry_subhead=False,
            ))
        elif "voluntary" in s_lower or "project" in s_lower:
            sections.append(SectionSpec(
                section_type="voluntary",
                entry_count=1,
                bullets_per_project=budget.get("voluntary", 2),
                has_entry_subhead=False,
            ))
        elif "education" in s_lower or "academic" in s_lower:
            sections.append(SectionSpec(
                section_type="education",
                entry_count=1,
                edge_to_edge_lines=1,
                has_entry_subhead=True,
            ))
        elif "skill" in s_lower or "competenc" in s_lower:
            sections.append(SectionSpec(
                section_type="skills",
                entry_count=1,
                edge_to_edge_lines=1,
                has_entry_subhead=False,
            ))
        elif "interest" in s_lower:
            sections.append(SectionSpec(
                section_type="interests",
                entry_count=1,
                edge_to_edge_lines=1,
                has_entry_subhead=False,
            ))

    fit_result = json.loads(
        await resume_validate_page_fit(
            PageFitInput(sections=sections, career_level=ctx.career_level),
            template_config=ctx.template_config,
        )
    )

    ctx._page_fit = fit_result
    ctx._section_specs = sections
    ctx.stats["fits_one_page"] = fit_result.get("fits_one_page", False)
    ctx.stats["remaining_mm"] = fit_result.get("remaining_mm", 0)

    await _progress(ctx, sb, 3, "Layout planned", 35)


# ── Phase 4: Batched Bullet Writing (all companies in 1 LLM call) ────────

def _get_company_context(ctx: PipelineContext, company_index: int) -> str:
    """Extract career context for a specific company.

    Strategy:
    1. Use company name from Phase 1 parsed companies list
    2. Search career_text for ALL paragraphs mentioning that company (not just ## headings)
    3. Fall back to relevant_chunks if FTS was available
    4. Truncate to ~5000 chars to fit in small context windows (Groq 8K)
    """
    companies = ctx._parsed.get("companies", [])
    company_name = companies[company_index]["name"] if company_index < len(companies) else ""

    if not company_name:
        # Fallback: split career text by ## sections and pick by index
        import re as _re
        sections = _re.split(r'\n(?=## )', ctx.career_text)
        if company_index < len(sections):
            return sections[company_index][:5000]  # TODO: replace with hybrid_retrieve in v2.0
        return ctx.career_text[:5000]  # TODO: replace with hybrid_retrieve in v2.0

    # Split into paragraphs (double newline) and find ALL that mention this company
    paragraphs = ctx.career_text.split("\n\n")
    relevant = []
    company_lower = company_name.lower()

    for para in paragraphs:
        if company_lower in para.lower():
            relevant.append(para.strip())

    # If no paragraph-level matches, try section-level (## headings)
    if not relevant:
        import re as _re
        sections = _re.split(r'\n(?=## )', ctx.career_text)
        for section in sections:
            if company_lower in section.lower():
                relevant.append(section.strip())

    if relevant:
        context = "\n\n".join(relevant)[:5000]  # TODO: replace with hybrid_retrieve in v2.0
        logger.info(f"Job {ctx.job_id}: Company '{company_name}' context: {len(relevant)} paragraphs, {len(context)} chars")
    elif ctx._relevant_chunks:
        # Fall back to FTS chunks
        context = "\n\n---\n\n".join(ctx._relevant_chunks)[:5000]  # TODO: replace with hybrid_retrieve in v2.0
        logger.info(f"Job {ctx.job_id}: Company '{company_name}' — no direct match, using {len(ctx._relevant_chunks)} FTS chunks")
    else:
        # Last resort: full career text truncated
        context = ctx.career_text[:5000]  # TODO: replace with hybrid_retrieve in v2.0
        logger.warning(f"Job {ctx.job_id}: Company '{company_name}' — no context found, using truncated career text")

    # Prepend Q&A context if available
    qa_context = _format_qa_context(ctx)
    if qa_context:
        context = qa_context + "\n\n" + context

    return context


def _build_companies_section(
    ctx: PipelineContext,
    companies: list[dict],
    company_keys: list[str],
    budget: dict,
    target_role: str,
) -> str:
    """Build the companies section for the batched Phase 4 prompt."""
    sections = []
    for idx, ck in enumerate(company_keys):
        num_bullets = budget.get(ck, 4)
        co = companies[idx] if idx < len(companies) else {}
        co_name = co.get("name", f"Company {idx + 1}")
        location = co.get("location", "")
        title = co.get("title", "")
        team = co.get("team", "")
        date_range = co.get("date_range", "")

        header_parts = [f"COMPANY {idx}: {co_name}"]
        if location:
            header_parts.append(location)
        if title:
            header_parts.append(title)
        if team:
            header_parts.append(team)
        if date_range:
            header_parts.append(date_range)
        header = " | ".join(header_parts)

        context = _get_company_context(ctx, idx)

        # Determine project groups from budget
        if num_bullets <= 3:
            groups = 1
        elif num_bullets <= 6:
            groups = 2
        else:
            groups = 3

        section = (
            f"=== {header} ===\n"
            f"Budget: {num_bullets} bullets in {groups} project groups\n"
            f"Target role: {target_role}\n\n"
            f"Context:\n{context}"
        )
        sections.append(section)

    return "\n\n".join(sections)


async def phase_4_bullets(ctx: PipelineContext, sb: Client, llm):
    """Batched Phase 4: write bullets for ALL companies in ONE LLM call."""
    t0 = time.time()
    await _progress(ctx, sb, 4, "Writing bullets", 40)

    strategy_info = STRATEGIES.get(ctx.strategy, STRATEGIES["BALANCED"])
    budget = ctx._bullet_budget
    parsed = ctx._parsed
    companies = parsed.get("companies", [])
    target_role = parsed.get("target_role", "")

    # Compact keywords: comma-separated string instead of JSON array
    keyword_strs = [kw if isinstance(kw, str) else kw.get("keyword", "") for kw in ctx.jd_keywords]
    jd_keywords_compact = ", ".join(keyword_strs)

    # Collect company keys from budget (handles both "company_N_total" and "CompanyName_total")
    company_keys = _extract_company_keys(budget)

    logger.info(f"Job {ctx.job_id}: Phase 4 batched — {len(company_keys)} companies, budget={budget}")

    # Build companies section for the batched prompt
    companies_section = _build_companies_section(ctx, companies, company_keys, budget, target_role)

    system_msg = prompts.PHASE_4_BATCHED_SYSTEM.format(
        strategy=ctx.strategy,
        strategy_description=strategy_info["description"],
        career_level=ctx.career_level,
    )
    user_msg = prompts.PHASE_4_BATCHED_USER.format(
        jd_keywords_compact=jd_keywords_compact,
        companies_section=escape_llm_input(companies_section),
    )

    resp = await _llm_call(ctx, llm, system_msg, user_msg, phase=4, temperature=0.4)
    try:
        data = _parse_json(resp.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Phase 4: LLM returned invalid JSON — {e}. Response start: {resp.text[:300]}") from e

    # Flatten batched response into bullet list
    all_bullets = []
    for co_data in data.get("companies", []):
        co_idx = co_data.get("company_index", 0)
        for b in co_data.get("bullets", []):
            b["company_index"] = co_idx
            all_bullets.append(b)

    ctx._raw_bullets = all_bullets
    if not ctx._raw_bullets:
        raise ValueError("Phase 4: No bullets written")

    # Register all verbs
    verbs = [b["verb"] for b in ctx._raw_bullets if b.get("verb")]
    await resume_track_verbs(
        TrackVerbsInput(action="register", verbs=verbs),
        ctx=ctx,
    )

    ctx._phase_timings["phase_4"] = int((time.time() - t0) * 1000)
    await _progress(ctx, sb, 4, f"Wrote {len(ctx._raw_bullets)} bullets", 50)


# ── Phase 5: Width Optimization Loop ─────────────────────────────────────

async def phase_5_width_opt(ctx: PipelineContext, sb: Client, llm):
    t0 = time.time()
    await _progress(ctx, sb, 5, "Optimizing bullet widths", 55)

    # Use Oracle local LLM (llama3.2:1b) for width rewriting — free, fast, no rate limits
    # Falls back to Groq if Oracle is unavailable
    _oracle = _get_oracle_llm()
    _phase5_llm = _oracle if _oracle is not None else llm
    logger.info(f"Job {ctx.job_id} phase 5: using {'Oracle llama3.2:1b' if _oracle else 'Groq (fallback)'} for rewriting")

    # Get bullet budget numbers for prompts
    bullet_budget = ctx.template_config.get("budgets", {}).get("bullet", {})
    if hasattr(bullet_budget, "model_dump"):
        bullet_budget = bullet_budget.model_dump()
    raw_budget = bullet_budget.get("raw_budget", 101.4)
    range_min_90 = bullet_budget.get("range_min_90", 91.3)

    # Step 1: Measure ALL bullets locally (instant)
    measurements = []
    for i, bullet in enumerate(ctx._raw_bullets):
        result = json.loads(
            await resume_measure_width(
                MeasureWidthInput(text_html=bullet["text_html"], line_type="bullet"),
                template_config=ctx.template_config,
            )
        )
        measurements.append({
            "index": i,
            "text_html": bullet["text_html"],
            "weighted_total": result.get("weighted_total", 0),
            "fill_percentage": result.get("fill_percentage", 0),
            "status": result.get("status", "PASS"),
        })

    needs_fix = [m for m in measurements if m["status"] != "PASS"]
    logger.info(f"Job {ctx.job_id} phase 5: {len(measurements)} bullets measured, {len(needs_fix)} need fixing")

    if not needs_fix:
        # All bullets already pass — skip LLM entirely
        for m in measurements:
            ctx._raw_bullets[m["index"]]["fill_percentage"] = m["fill_percentage"]
        ctx._optimized_bullets = ctx._raw_bullets
        ctx._phase_timings["phase_5"] = int((time.time() - t0) * 1000)
        await _progress(ctx, sb, 5, "All bullets pass — no LLM needed", 70)
        return

    # Step 2: Compute per-word width breakdowns for bullets that need fixing
    for m in needs_fix:
        m["word_widths"] = compute_word_widths(m["text_html"])

    # Step 3: Split into chunks (8 bullets/batch to fit smaller context windows)
    MAX_PHASE_5_BATCH = 8
    chunks = [needs_fix[i:i + MAX_PHASE_5_BATCH] for i in range(0, len(needs_fix), MAX_PHASE_5_BATCH)]
    batch_word = "batch" if len(chunks) == 1 else "batches"
    logger.info(f"Job {ctx.job_id} phase 5: {len(needs_fix)} bullets in {len(chunks)} {batch_word}")
    await _progress(ctx, sb, 5, f"Optimizing {len(needs_fix)} bullets in {len(chunks)} {batch_word}", 58)

    phase_5_template, _ = get_prompt("phase_5_width", prompts.PHASE_5_BATCHED_SYSTEM)
    system_msg = phase_5_template.format(
        raw_budget=raw_budget,
        range_min_90=range_min_90,
    )

    still_failing = []
    for chunk_idx, chunk in enumerate(chunks):
        # Build subset of measurements for this chunk
        chunk_indices = {m["index"] for m in chunk}
        chunk_measurements = [m for m in measurements if m["index"] in chunk_indices or m["status"] == "PASS"]

        bullets_section = _build_batched_bullets_section(chunk_measurements, chunk, raw_budget, range_min_90)
        user_msg = prompts.PHASE_5_BATCHED_USER.format(
            reference_table=format_reference_table(),
            raw_budget=raw_budget,
            range_min_90=range_min_90,
            bullets_section=bullets_section,
        )

        if _oracle is not None:
            resp = await _oracle_call_with_fallback(ctx, _oracle, llm, system_msg, user_msg, phase=5, temperature=0.2)
        else:
            resp = await _llm_call(ctx, llm, system_msg, user_msg, phase=5, temperature=0.2)
        trace_generation(
            trace_name="pipeline", generation_name="phase_5_width",
            model=resp.model, system_prompt=system_msg, user_input=user_msg,
            output=resp.text, user_id=ctx.user_id,
        )
        try:
            revisions = _parse_json(resp.text).get("revised_bullets", [])
        except (json.JSONDecodeError, KeyError):
            logger.warning(f"Job {ctx.job_id} phase 5 batch {chunk_idx}: failed to parse LLM response")
            revisions = []

        # Apply revisions + verify locally
        for rev in revisions:
            idx = rev.get("bullet_index")
            new_html = rev.get("revised_text_html", "")
            if idx is None or not new_html:
                continue

            verify = json.loads(
                await resume_measure_width(
                    MeasureWidthInput(text_html=new_html, line_type="bullet"),
                    template_config=ctx.template_config,
                )
            )
            v_status = verify.get("status", "ERROR")
            v_fill = verify.get("fill_percentage", 0)

            if v_status == "PASS":
                ctx._raw_bullets[idx]["text_html"] = new_html
                ctx._raw_bullets[idx]["fill_percentage"] = v_fill
            else:
                still_failing.append({
                    "index": idx,
                    "text_html": new_html,
                    "weighted_total": verify.get("weighted_total", 0),
                    "fill_percentage": v_fill,
                    "status": v_status,
                })

    # Apply fill_percentage for bullets that were already PASS (not sent to LLM)
    for m in measurements:
        if m["status"] == "PASS":
            ctx._raw_bullets[m["index"]]["fill_percentage"] = m["fill_percentage"]

    # Step 6: Optional second pass for failures (rare)
    if still_failing:
        logger.info(f"Job {ctx.job_id} phase 5: {len(still_failing)} bullets still failing, second pass")
        await _progress(ctx, sb, 5, f"Second pass for {len(still_failing)} bullets", 65)

        for m in still_failing:
            m["word_widths"] = compute_word_widths(m["text_html"])

        retry_section = _build_batched_bullets_section(still_failing, still_failing, raw_budget, range_min_90)
        retry_user = prompts.PHASE_5_BATCHED_USER.format(
            reference_table=format_reference_table(),
            raw_budget=raw_budget,
            range_min_90=range_min_90,
            bullets_section=retry_section,
        )
        if _oracle is not None:
            resp2 = await _oracle_call_with_fallback(ctx, _oracle, llm, system_msg, retry_user, phase=5, temperature=0.2)
        else:
            resp2 = await _llm_call(ctx, llm, system_msg, retry_user, phase=5, temperature=0.2)
        try:
            revisions2 = _parse_json(resp2.text).get("revised_bullets", [])
        except (json.JSONDecodeError, KeyError):
            revisions2 = []

        for rev in revisions2:
            idx = rev.get("bullet_index")
            new_html = rev.get("revised_text_html", "")
            if idx is None or not new_html:
                continue
            verify = json.loads(
                await resume_measure_width(
                    MeasureWidthInput(text_html=new_html, line_type="bullet"),
                    template_config=ctx.template_config,
                )
            )
            v_fill = verify.get("fill_percentage", 0)
            if verify.get("status") == "PASS":
                ctx._raw_bullets[idx]["text_html"] = new_html
                ctx._raw_bullets[idx]["fill_percentage"] = v_fill
            else:
                # Keep whatever we have — close enough after 2 attempts
                ctx._raw_bullets[idx]["fill_percentage"] = v_fill
                # Track width failures for quality report
                if "width_failures" not in ctx.stats:
                    ctx.stats["width_failures"] = []
                ctx.stats["width_failures"].append({
                    "bullet_index": idx,
                    "fill_pct": v_fill,
                    "text": new_html[:100],
                })

    # ── Story 3.4: 3rd pass — per-bullet synonym retry for persistent failures ──
    if ctx.stats.get("width_failures"):
        await _progress(ctx, sb, 5, f"Synonym pass for {len(ctx.stats['width_failures'])} bullets", 68)
        for failure in ctx.stats["width_failures"][:]:  # iterate copy
            fail_idx = failure["bullet_index"]
            fill_pct = failure["fill_pct"]
            bullet = ctx._raw_bullets[fail_idx]
            direction = "trim" if fill_pct > 100 else "expand"

            # Strip HTML for synonym lookup
            plain_text = _re.sub(r'<[^>]+>', '', bullet.get("text_html", ""))

            # Measure current width for synonym input
            try:
                mw_result = json.loads(
                    await resume_measure_width(
                        MeasureWidthInput(text_html=bullet["text_html"], line_type="bullet"),
                        template_config=ctx.template_config,
                    )
                )
                current_width = mw_result.get("weighted_total", 0)
                target_width = mw_result.get("target_95", raw_budget * 0.95)
            except Exception:
                current_width = 0.0
                target_width = raw_budget * 0.95

            # Get synonym suggestions
            try:
                syn_result = json.loads(
                    await resume_suggest_synonyms(SynonymInput(
                        text=plain_text,
                        current_width=current_width,
                        target_width=target_width,
                        direction=direction,
                    ))
                )
                suggestions = syn_result.get("suggestions", [])
            except Exception as e:
                logger.warning(f"[Phase 5 3rd pass] suggest_synonyms failed for bullet {fail_idx}: {e}")
                continue

            if not suggestions:
                continue

            syn_context = "\n".join(
                f"- '{s['original_word']}' → '{s['replacement_word']}' (width delta {s.get('width_delta', 0):+.1f} CU)"
                for s in suggestions[:3]
            )

            # Targeted LLM rewrite for this single bullet
            try:
                rewritten = await _rewrite_bullet_with_synonyms(ctx, _phase5_llm, bullet, syn_context, direction)
            except Exception as e:
                logger.warning(f"[Phase 5 3rd pass] rewrite failed for bullet {fail_idx}: {e}")
                continue

            if not rewritten:
                continue

            # Re-measure
            try:
                new_verify = json.loads(
                    await resume_measure_width(
                        MeasureWidthInput(text_html=rewritten, line_type="bullet"),
                        template_config=ctx.template_config,
                    )
                )
                new_fill = new_verify.get("fill_percentage", 0)
                ctx._raw_bullets[fail_idx]["text_html"] = rewritten
                ctx._raw_bullets[fail_idx]["fill_percentage"] = new_fill
                if 88 <= new_fill <= 102:
                    ctx.stats["width_failures"] = [
                        f for f in ctx.stats["width_failures"]
                        if f["bullet_index"] != fail_idx
                    ]
                    logger.info(f"[Phase 5 3rd pass] bullet {fail_idx} fixed: {fill_pct:.1f}% → {new_fill:.1f}%")
            except Exception as e:
                logger.warning(f"[Phase 5 3rd pass] re-measure failed for bullet {fail_idx}: {e}")
                continue

        # Track remaining synonym failures
        remaining = ctx.stats.get("width_failures", [])
        if remaining:
            ctx.stats["synonym_failures"] = ctx.stats.get("synonym_failures", 0) + len(remaining)
            logger.info(f"[Phase 5 3rd pass] {len(remaining)} bullet(s) still failing after synonym pass")

    ctx._optimized_bullets = ctx._raw_bullets
    ctx._phase_timings["phase_5"] = int((time.time() - t0) * 1000)
    _save_checkpoint(ctx, sb, "phase_5")
    await _progress(ctx, sb, 5, "Width optimization complete", 70)


async def _rewrite_bullet_with_synonyms(ctx: PipelineContext, llm, bullet: dict, syn_context: str, direction: str) -> str | None:
    """Single targeted LLM call to rewrite one bullet using synonym suggestions."""
    action = "shorten" if direction == "trim" else "expand slightly"
    prompt = (
        f"Rewrite this resume bullet to {action} it using the synonym suggestions below.\n\n"
        f"Current bullet: {bullet.get('text_html', '')}\n\n"
        f"Synonym suggestions:\n{syn_context}\n\n"
        "Return ONLY the rewritten bullet HTML. Preserve all formatting tags. Same meaning, better width fit."
    )
    try:
        resp = await _llm_call(ctx, llm, "", prompt, phase=5, temperature=0.1)
        text = resp.text.strip() if resp else None
        # Strip any accidental markdown fences
        if text and text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return text if text else None
    except Exception:
        return None


def _build_batched_bullets_section(
    all_measurements: list[dict],
    needs_fix: list[dict],
    raw_budget: float,
    range_min_90: float,
) -> str:
    """Build the bullets section of the batched Phase 5 prompt."""
    needs_fix_indices = {m["index"] for m in needs_fix}
    lines = []

    for m in all_measurements:
        idx = m["index"]
        fill = m["fill_percentage"]
        total = m["weighted_total"]
        status = m["status"]

        if idx not in needs_fix_indices:
            lines.append(f"── BULLET {idx} — PASS ({fill}%) — no changes needed ──")
            lines.append(f'"{m["text_html"]}"')
            lines.append(f"Total: {total} / Budget: {raw_budget}")
            lines.append("")
        else:
            # Determine gap description
            if status == "TOO_SHORT":
                gap_min = round(range_min_90 - total, 1)
                gap_max = round(raw_budget - total, 1)
                gap_desc = f"need +{gap_min} to +{gap_max} CU"
            else:  # OVERFLOW
                excess_min = round(total - raw_budget, 1)
                excess_max = round(total - range_min_90, 1)
                gap_desc = f"need to remove {excess_min} to {excess_max} CU"

            lines.append(f"── BULLET {idx} — NEEDS_FIX ({fill}% — {status}, {gap_desc}) ──")
            lines.append(f'"{m["text_html"]}"')
            lines.append("Word widths:")

            word_widths = m.get("word_widths", [])
            word_parts = []
            space_count = 0
            for ww in word_widths:
                tag = "[b]" if ww["is_bold"] else ""
                word_parts.append(f"  {ww['word']}={ww['width']}{tag}")
            if word_widths:
                space_count = len(word_widths) - 1
            lines.extend(word_parts)
            lines.append(f"  Spaces: {space_count} × 0.516 = {round(space_count * 0.516, 2)}")
            lines.append(f"Total: {total} / Budget: {raw_budget} / Gap: {gap_desc}")
            lines.append("")

    return "\n".join(lines)


# ── Phase 6: BRS Scoring ──────────────────────────────────────────────────

async def phase_6_scoring(ctx: PipelineContext, sb: Client):
    await _progress(ctx, sb, 6, "Scoring bullets", 72)

    candidate_bullets = []
    for i, b in enumerate(ctx._optimized_bullets):
        candidate_bullets.append(CandidateBullet(
            project_id=f"bullet_{i}",
            raw_text=b["text_html"],
            group_id=f"company_{b.get('company_index', 0)}",
            group_theme=b.get("project_title", ""),
            position_in_group=b.get("project_group", 0),
        ))

    score_result = json.loads(
        await resume_score_bullets(ScoreBulletsInput(
            bullets=candidate_bullets,
            jd_keywords=[{"keyword": kw, "category": "skill"} if isinstance(kw, str) else kw for kw in ctx.jd_keywords],
            career_level=ctx.career_level,
            total_bullet_budget=len(ctx._optimized_bullets),
        ))
    )

    ctx.bullet_scores = score_result.get("scored_bullets", [])
    ctx.stats["avg_brs"] = (
        sum(b["brs"] for b in ctx.bullet_scores) / len(ctx.bullet_scores)
        if ctx.bullet_scores else 0
    )
    ctx.stats["tier_1_count"] = score_result.get("tier_1_count", 0)

    await _progress(ctx, sb, 6, f"Avg BRS: {ctx.stats['avg_brs']:.0%}", 78)


# ── Phase 7: Validation ──────────────────────────────────────────────────

async def phase_7_validation(ctx: PipelineContext, sb: Client):
    t0 = time.time()
    await _progress(ctx, sb, 7, "Validating colors & layout", 80)

    colors = ctx.theme_colors or {}
    warnings = []

    # ── Always: contrast check + page-fit (needed by both code paths) ────────
    # Validate contrast for brand_primary on white
    if colors.get("brand_primary"):
        contrast_result = json.loads(
            await resume_validate_contrast(ContrastInput(
                foreground_hex=colors["brand_primary"],
                background_hex="#FFFFFF",
            ))
        )
        if not contrast_result.get("passes_wcag_aa_normal_text", False):
            warnings.append(f"Primary color {colors['brand_primary']} fails WCAG AA contrast")
            # Use the suggested fix if available
            if contrast_result.get("suggested_fix"):
                colors["brand_primary"] = contrast_result["suggested_fix"]

    # Re-validate page fit with final bullet counts
    fit_result = json.loads(
        await resume_validate_page_fit(
            PageFitInput(sections=ctx._section_specs, career_level=ctx.career_level),
            template_config=ctx.template_config,
        )
    )

    ctx.stats["final_fits_page"] = fit_result.get("fits_one_page", False)
    # Store full page-fit result for quality_judge to consume
    ctx._page_fit = fit_result
    ctx.theme_colors = colors

    if USE_QUALITY_JUDGE:
        # ── Story 2.1: delegate all quality scoring to quality_judge ─────────
        report = judge_quality(ctx)

        ctx.stats["quality_grade"] = report.grade
        ctx.stats["quality_score"] = report.score
        ctx.stats["quality_checks"] = [
            {
                "name": c.name,
                "score": c.score,
                "passed": c.passed,
                "detail": c.detail,
            }
            for c in report.checks
        ]
        ctx.stats["quality_suggestions"] = report.suggestions
        ctx.stats["ats_blocked"] = report.ats_blocked
        ctx.stats["validation_warnings"] = warnings

        await _progress(ctx, sb, 7, f"Quality: {report.grade} ({report.score:.0f}/100)", 85)

    else:
        # ── Legacy inline Phase 7 logic (preserved, feature-flagged off) ─────
        bullets = ctx._optimized_bullets or []
        quality_score = 0.0

        # Check 1: Verb repetition — all verbs should be unique
        verbs = [b.get("verb", "").lower() for b in bullets if b.get("verb")]
        unique_verbs = set(verbs)
        has_duplicates = len(verbs) != len(unique_verbs)
        if has_duplicates:
            dupes = [v for v in unique_verbs if verbs.count(v) > 1]
            warnings.append(f"Duplicate verbs detected: {', '.join(dupes)}")
        verb_score = 50.0 if has_duplicates else 100.0

        # Check 2: Metric density — ≥60% of bullets should contain a number
        import re as _re
        metric_count = sum(1 for b in bullets if _re.search(r'\d', b.get("text_html", "")))
        metric_pct = (metric_count / len(bullets) * 100) if bullets else 0
        if metric_pct < 60:
            warnings.append(f"Low metric density: {metric_pct:.0f}% of bullets contain numbers (target: ≥60%)")

        # Check 3: Keyword coverage — ≥40% of JD keywords in bullets
        all_bullet_text = " ".join(b.get("text_html", "").lower() for b in bullets)
        kw_list = [kw["keyword"] if isinstance(kw, dict) else kw for kw in (ctx.jd_keywords or [])]
        matched_kw = sum(1 for kw in kw_list if _re.search(r'\b' + _re.escape(kw) + r'\b', all_bullet_text, _re.IGNORECASE))
        kw_coverage = (matched_kw / len(kw_list) * 100) if kw_list else 100
        if kw_coverage < 40:
            missing = [kw for kw in kw_list if not _re.search(r'\b' + _re.escape(kw) + r'\b', all_bullet_text, _re.IGNORECASE)][:5]
            warnings.append(f"Low keyword coverage: {kw_coverage:.0f}% (target: ≥40%). Missing: {', '.join(missing)}")

        # Check 4: Width fill average
        fills = [b.get("fill_percentage", 0) for b in bullets if b.get("fill_percentage")]
        avg_fill = sum(fills) / len(fills) if fills else 0
        overflow_count = sum(1 for b in bullets if b.get("fill_percentage", 0) > 102)
        short_count = sum(1 for b in bullets if 0 < b.get("fill_percentage", 0) < 90)
        if overflow_count:
            warnings.append(f"{overflow_count} bullet(s) overflow (>102% fill)")
        if short_count:
            warnings.append(f"{short_count} bullet(s) too short (<90% fill)")

        # Check 5: Tense consistency — all verbs should be past tense
        present_tense = {"lead", "drive", "build", "manage", "develop", "create", "design",
                         "implement", "optimize", "launch", "grow", "run", "own", "scale"}
        bad_tense = [v for v in verbs if v in present_tense]
        if bad_tense:
            warnings.append(f"Present tense verbs detected (should be past): {', '.join(set(bad_tense))}")

        # Compute weighted quality score (0-100)
        quality_score = (
            kw_coverage * 0.30 +
            metric_pct * 0.25 +
            verb_score * 0.15 +
            (100.0 if ctx.stats.get("final_fits_page") else 0.0) * 0.15 +
            avg_fill * 0.10 +
            (100.0 if not bad_tense else 50.0) * 0.05
        )
        grade = "A" if quality_score >= 90 else "B" if quality_score >= 75 else "C" if quality_score >= 60 else "D" if quality_score >= 40 else "F"

        ctx.stats["quality_score"] = round(quality_score, 1)
        ctx.stats["quality_grade"] = grade
        ctx.stats["keyword_coverage"] = round(kw_coverage, 1)
        ctx.stats["metric_density"] = round(metric_pct, 1)
        ctx.stats["avg_fill"] = round(avg_fill, 1)
        ctx.stats["validation_warnings"] = warnings

        await _progress(ctx, sb, 7, f"Quality: {grade} ({quality_score:.0f}/100)", 85)

    ctx._phase_timings["phase_7"] = int((time.time() - t0) * 1000)
    _save_checkpoint(ctx, sb, "phase_7")


# ── Template Locking Helpers ──────────────────────────────────────────────

def apply_brand_colors_to_html(html: str, brand_colors: dict) -> str:
    """Replace color placeholders and specific hex values with actual brand colors.

    Handles two replacement modes:
    1. Placeholder tokens: {brand_primary}, {brand_secondary}, etc. (template placeholders)
    2. Common hardcoded hex patterns in inline styles / CSS — replace known defaults
       with the actual brand color so frozen HTML picks up the user's brand palette.

    Args:
        html: Frozen section HTML from a template.
        brand_colors: dict with keys brand_primary, brand_secondary, brand_tertiary, brand_quaternary.

    Returns:
        HTML with brand colors applied.
    """
    import re as _re

    # Map placeholder names → actual color values (skip empty values)
    replacements = {
        name: value
        for name, value in brand_colors.items()
        if value and isinstance(value, str) and value.startswith("#")
    }

    if not replacements:
        return html

    result = html

    # Pass 1: replace {brand_primary} style placeholder tokens
    for name, color in replacements.items():
        result = result.replace("{" + name + "}", color)
        result = result.replace("{{" + name + "}}", color)  # double-brace variants

    # Pass 2: replace hardcoded default hex values in style attributes.
    # These defaults match what assemble_html injects when no override is given.
    DEFAULT_COLOR_MAP = {
        "#1B2A4A": "brand_primary",   # default dark navy primary
        "#4285F4": "brand_primary",   # default blue primary
        "#EA4335": "brand_secondary", # default red secondary
        "#2563EB": "brand_primary",   # alternate blue
        "#1E3A5F": "brand_primary",   # alternate dark
    }

    for default_hex, brand_key in DEFAULT_COLOR_MAP.items():
        if brand_key in replacements:
            # Replace only inside style="" attributes or <style> blocks to avoid
            # clobbering visible text that happens to contain a hex code.
            pattern = r'(style\s*=\s*["\'][^"\']*?)' + _re.escape(default_hex) + r'([^"\']*?["\'])'
            result = _re.sub(
                pattern,
                lambda m, _hex=replacements[brand_key]: m.group(1) + _hex + m.group(2),
                result,
            )

    return result


def _apply_frozen_section(section_name: str, ctx: PipelineContext) -> str | None:
    """Return frozen HTML for a locked section, with brand colors applied.

    Returns None if the section is not locked or has no frozen HTML.
    """
    if section_name not in ctx.locked_sections:
        return None
    frozen = ctx.section_html_frozen.get(section_name)
    if not frozen:
        logger.warning(f"[locked] section '{section_name}' is locked but has no frozen HTML — will regenerate")
        return None
    colors = ctx.theme_colors or {}
    updated = apply_brand_colors_to_html(frozen, colors)
    logger.info(f"[locked] Using frozen HTML for section '{section_name}' ({len(updated)} chars)")
    return updated


# ── Section Builders (programmatic HTML — no LLM) ────────────────────────

def _get_section_order_map(section_order: list) -> dict:
    """Map section names to template comment numbers.

    Template convention:
        1 = Professional Experience
        2 = Awards & Recognitions
        3 = Voluntary Work & Projects
        4 = Academic Achievements / Education
        5 = Core Competencies & Skills
        6 = Additional Interests
    """
    mapping = {}
    for name in section_order:
        lower = name.lower()
        if "experience" in lower or "professional" in lower:
            mapping["experience"] = 1
        elif "award" in lower or "recognition" in lower:
            mapping["awards"] = 2
        elif "voluntary" in lower or "project" in lower:
            mapping["voluntary"] = 3
        elif "education" in lower or "academic" in lower or "achievement" in lower:
            mapping["education"] = 4
        elif "skill" in lower or "competenc" in lower:
            mapping["skills"] = 5
        elif "interest" in lower:
            mapping["interests"] = 6
    return mapping


def _build_experience_html(bullets: list, companies: list) -> str:
    """Build Professional Experience section HTML from optimized bullets + company metadata."""
    from collections import defaultdict
    html_parts = [
        '<div class="section-title">Professional Experience<div class="section-divider"></div></div>'
    ]

    # Group bullets by company_index
    by_company = defaultdict(list)
    for b in bullets:
        by_company[b.get("company_index", 0)].append(b)

    for idx in sorted(by_company.keys()):
        company_bullets = by_company[idx]

        # Get company metadata
        co = companies[idx] if idx < len(companies) else {}
        name = co.get("name", f"Company {idx + 1}")
        location = co.get("location", "")
        title = co.get("title", "")
        team = co.get("team", "")
        date_range = co.get("date_range", "")

        right_header = " | ".join(filter(None, [location, date_range]))

        html_parts.append('<div class="entry">')
        html_parts.append(
            f'<div class="entry-header"><span>{name}</span><span>{right_header}</span></div>'
        )
        if title or team:
            html_parts.append(
                f'<div class="entry-subhead"><span>{title}</span><span>{team}</span></div>'
            )

        # Group bullets by project_group
        by_project = defaultdict(list)
        for b in company_bullets:
            by_project[b.get("project_group", 0)].append(b)

        for pg_idx in sorted(by_project.keys()):
            pg_bullets = by_project[pg_idx]
            # V2: No project-title divs — groups separated by ul-group-gap CSS
            html_parts.append("<ul>")
            for b in pg_bullets:
                text = b.get("text_html", "")
                fill = b.get("fill_percentage", 0)
                # Only justify when line fills ≥98% of budget — below that,
                # word-spacing stretches visibly and looks artificial.
                css_class = "li-content" if fill >= 98 else "li-content-natural"
                html_parts.append(f'<li><span class="{css_class}">{text}</span></li>')
            html_parts.append("</ul>")

        html_parts.append("</div>")  # close .entry

    return "\n".join(html_parts)


def _build_education_html(education: list) -> str:
    """Build Education section from structured education data."""
    html_parts = [
        '<div class="section-title">Education<div class="section-divider"></div></div>'
    ]
    for edu in education:
        institution = edu.get("institution", "")
        degree = edu.get("degree", "")
        year = edu.get("year", "")
        gpa = edu.get("gpa", "")
        highlights = edu.get("highlights", "")

        html_parts.append('<div class="entry">')
        html_parts.append(
            f'<div class="entry-header"><span>{institution}</span><span>{year}</span></div>'
        )
        if degree or gpa:
            html_parts.append(
                f'<div class="entry-subhead"><span>{degree}</span><span>{gpa}</span></div>'
            )
        if highlights:
            # Split highlights on newlines or · separator into multiple edge-to-edge lines
            lines = [h.strip() for h in highlights.replace(" · ", "\n").split("\n") if h.strip()]
            for line in lines:
                html_parts.append(
                    f'<span class="edge-to-edge-line">{line}</span>'
                )
        html_parts.append("</div>")

    return "\n".join(html_parts)


def _build_skills_html(skills: dict) -> str:
    """Build Core Competencies & Skills section from skills dict."""
    html_parts = [
        '<div class="section-title">Core Competencies &amp; Skills<div class="section-divider"></div></div>'
    ]
    for category, skill_list in skills.items():
        if isinstance(skill_list, list):
            skills_str = ", ".join(skill_list)
        else:
            skills_str = str(skill_list)
        html_parts.append(f'<div class="entry-header">{category}</div>')
        # Use text-line (no justify) — skills are not width-optimized
        html_parts.append(f'<span class="text-line">{skills_str}</span>')

    return "\n".join(html_parts)


def _build_awards_html(awards: list) -> str:
    """Build Awards & Recognitions section from awards list."""
    html_parts = [
        '<div class="section-title">Awards &amp; Recognitions<div class="section-divider"></div></div>',
        "<ul>",
    ]
    for award in awards:
        title = award.get("title", "")
        detail = award.get("detail", "")
        text = f"<b>{title}</b> — {detail}" if detail else f"<b>{title}</b>"
        # Use li-content-natural (no justify) — awards are not width-optimized
        html_parts.append(f'<li><span class="li-content-natural">{text}</span></li>')
    html_parts.append("</ul>")

    return "\n".join(html_parts)


def _build_voluntary_html(voluntary: list) -> str:
    """Build Voluntary Experience & Projects section."""
    html_parts = [
        '<div class="section-title">Voluntary Experience &amp; Projects<div class="section-divider"></div></div>',
        "<ul>",
    ]
    for item in voluntary:
        title = item.get("title", "")
        detail = item.get("detail", "")
        text = f"<b>{title}</b> — {detail}" if detail else f"<b>{title}</b>"
        # Use li-content-natural (no justify) — voluntary items are not width-optimized
        html_parts.append(f'<li><span class="li-content-natural">{text}</span></li>')
    html_parts.append("</ul>")

    return "\n".join(html_parts)


def _build_interests_html(interests: str) -> str:
    """Build Additional Interests section from comma-separated string."""
    html_parts = [
        '<div class="section-title">Additional Interests<div class="section-divider"></div></div>',
        # Use text-line (no justify) — interests are not width-optimized
        f'<span class="text-line">{interests}</span>',
    ]
    return "\n".join(html_parts)


# ── Phase 8: HTML Assembly (Programmatic — no LLM) ──────────────────────

async def phase_8_assembly(ctx: PipelineContext, sb: Client, llm):
    """Programmatic HTML assembly — no LLM call needed.

    Builds section HTML from optimized bullets + structured career data
    using pure functions, then feeds to assemble_html tool for injection.
    """
    t0 = time.time()
    await _progress(ctx, sb, 8, "Assembling final HTML", 88)

    parsed = ctx._parsed
    template_html = _load_template(ctx.template_id)
    section_order = ctx._section_order or ["Professional Experience", "Awards & Recognitions",
                                            "Voluntary Work & Projects", "Academic Achievements",
                                            "Core Competencies & Skills", "Additional Interests"]
    order_map = _get_section_order_map(section_order)
    companies = parsed.get("companies", [])

    # Build section HTML programmatically (no LLM)
    sections = []

    # Experience: never frozen (always freshly generated per JD)
    if "experience" in order_map and ctx._optimized_bullets:
        sections.append(SectionContent(
            section_html=_build_experience_html(ctx._optimized_bullets, companies),
            section_order=order_map["experience"],
        ))

    if "education" in order_map:
        frozen_edu = _apply_frozen_section("education", ctx)
        if frozen_edu is not None:
            sections.append(SectionContent(section_html=frozen_edu, section_order=order_map["education"]))
        elif parsed.get("education"):
            sections.append(SectionContent(
                section_html=_build_education_html(parsed["education"]),
                section_order=order_map["education"],
            ))

    if "skills" in order_map:
        frozen_skills = _apply_frozen_section("skills", ctx)
        if frozen_skills is not None:
            sections.append(SectionContent(section_html=frozen_skills, section_order=order_map["skills"]))
        elif parsed.get("skills"):
            sections.append(SectionContent(
                section_html=_build_skills_html(parsed["skills"]),
                section_order=order_map["skills"],
            ))

    if "awards" in order_map:
        frozen_awards = _apply_frozen_section("awards", ctx)
        if frozen_awards is not None:
            sections.append(SectionContent(section_html=frozen_awards, section_order=order_map["awards"]))
        elif parsed.get("awards"):
            sections.append(SectionContent(
                section_html=_build_awards_html(parsed["awards"]),
                section_order=order_map["awards"],
            ))

    if "voluntary" in order_map:
        frozen_voluntary = _apply_frozen_section("voluntary", ctx)
        if frozen_voluntary is not None:
            sections.append(SectionContent(section_html=frozen_voluntary, section_order=order_map["voluntary"]))
        elif parsed.get("voluntary"):
            sections.append(SectionContent(
                section_html=_build_voluntary_html(parsed["voluntary"]),
                section_order=order_map["voluntary"],
            ))

    if "interests" in order_map:
        frozen_interests = _apply_frozen_section("interests", ctx)
        if frozen_interests is not None:
            sections.append(SectionContent(section_html=frozen_interests, section_order=order_map["interests"]))
        elif parsed.get("interests"):
            sections.append(SectionContent(
                section_html=_build_interests_html(parsed["interests"]),
                section_order=order_map["interests"],
            ))

    # Build tool inputs
    contact = parsed.get("contact_info", {})
    colors = ctx.theme_colors or {}

    theme = ThemeColors(
        brand_primary=colors.get("brand_primary", "#4285F4"),
        brand_secondary=colors.get("brand_secondary", "#EA4335"),
        brand_tertiary=colors.get("brand_tertiary", ""),
        brand_quaternary=colors.get("brand_quaternary", ""),
    )

    # Build contacts list — only include non-empty fields
    contacts = []
    if contact.get("phone"):
        contacts.append(f"Phone: {contact['phone']}")
    if contact.get("email"):
        contacts.append(f"Email: {contact['email']}")
    if contact.get("linkedin"):
        contacts.append(f"LinkedIn: {contact['linkedin']}")
    if contact.get("portfolio"):
        contacts.append(f"Portfolio: {contact['portfolio']}")

    header = HeaderData(
        name=contact.get("name", ""),
        role=parsed.get("target_role", ""),
        contacts=contacts,
    )

    assemble_result = json.loads(
        await resume_assemble_html(AssembleInput(
            template_html=template_html,
            theme_colors=theme,
            header=header,
            sections=sections,
            css_overrides="",
        ))
    )

    final_html: str = assemble_result.get("final_html", "")

    # Inject professional summary below the header div (if phase_3_5a produced one)
    if ctx._summary_html:
        import re as _inject_re
        # Find the closing </div> of the header block and inject summary after it
        header_close_pattern = r'(</div>\s*)(<!--)'
        # More reliable: find the header div and its closing tag
        header_div_match = _inject_re.search(
            r'(<div[^>]*class="[^"]*header[^"]*"[^>]*>.*?</div>)',
            final_html,
            flags=_inject_re.DOTALL | _inject_re.IGNORECASE,
        )
        if header_div_match:
            insert_pos = header_div_match.end()
            summary_block = f'\n<div class="professional-summary">\n{ctx._summary_html}\n</div>'
            final_html = final_html[:insert_pos] + summary_block + final_html[insert_pos:]
            logger.info(f"[Phase 8] Professional summary injected ({len(ctx._summary_html)} chars)")
        else:
            logger.warning("[Phase 8] Could not find header div to inject summary — summary skipped")

    ctx.output_html = final_html
    ctx.stats["assembly_warnings"] = assemble_result.get("warnings", [])
    ctx.stats["sections_injected"] = len(sections)
    if ctx._summary_html:
        ctx.stats["summary_injected"] = True

    ctx._phase_timings["phase_8"] = int((time.time() - t0) * 1000)
    await _progress(ctx, sb, 8, "Resume complete", 98)
