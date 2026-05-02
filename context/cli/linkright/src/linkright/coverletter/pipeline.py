"""Cover letter 5-step mini-pipeline.

Reuses Pillar 1 primitives — no new LLM infrastructure, no new embedder.
Target: ≤2 LLM calls per cover letter (Step 1 extraction + Step 3 generation).
Steps 2, 4, 5 are fully deterministic (no LLM calls).

Module-level imports for each LLM helper keep mock-patching simple in tests.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

import click

# ── Module-level imports (patchable in tests) ─────────────────────────────────
from linkright.llm.direct import groq_chat, gemini_chat_best, LLMError  # noqa: F401
try:
    from playwright.sync_api import sync_playwright  # noqa: F401
except ImportError:  # playwright optional — only needed with --pdf
    sync_playwright = None  # type: ignore[assignment]
from linkright.resume.lib.embedder import embed  # noqa: F401
from linkright.resume.lib.metric_extract import find_fabricated  # noqa: F401
from linkright.resume.lib.jd_keyphrase import extract_jd_terms, find_fishing  # noqa: F401
from linkright.resume.lib.cosine import cosine as _cosine  # noqa: F401
from linkright.profile.pipeline import load_contact  # noqa: F401


# ── helpers ──────────────────────────────────────────────────────────────────

def _profile_dir() -> Path:
    home = os.environ.get("LINKRIGHT_HOME")
    if home:
        return Path(home) / "profile"
    return Path.home() / ".linkright" / "profile"


def _runs_dir() -> Path:
    home = os.environ.get("LINKRIGHT_HOME")
    base = Path(home) if home else Path.home() / ".linkright"
    return base / "runs"


def _strip_json(text: str) -> str:
    """Strip markdown code fences if LLM wrapped JSON."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        t = "\n".join(lines[1:])
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def _count_words(text: str) -> int:
    return len(text.split())


# ── Step 1 — Parse JD into structured requirements ───────────────────────────

_JD_PARSE_SYSTEM = """\
You are a structured data extractor. Parse the given job description and return ONLY a JSON object.

Required JSON shape:
{
  "company_name": "<string — company name from JD, or empty string>",
  "role_title": "<string — job title>",
  "hiring_manager": "<string — hiring manager name if mentioned, else empty string>",
  "must_have_skills": ["<skill1>", "<skill2>", ...],
  "tone_signals": ["<signal1>", ...],
  "mission_snippet": "<string — one concrete phrase from the JD about company mission/product/value, max 20 words>"
}

Rules:
- must_have_skills: list the 5-8 most critical hard skills/requirements explicitly stated as required/must-have
- tone_signals: list adjectives/phrases describing culture or communication style (e.g. "fast-paced", "collaborative", "data-driven")
- mission_snippet: copy an actual phrase from the JD — do NOT paraphrase or invent. If none found, empty string.
- Return ONLY the JSON object. No explanation, no markdown fences.
"""

_JD_PARSE_USER = """\
JOB DESCRIPTION:
{jd_text}
"""


def step_1_parse_jd(jd_text: str) -> tuple[dict, dict]:
    """Parse JD into structured requirements.

    Returns (parsed_jd: dict, usage: dict).
    Uses free Groq → Gemini cascade at low temp (0.1) for extraction accuracy.
    """
    user_prompt = _JD_PARSE_USER.replace("{jd_text}", jd_text[:8000])
    usage: dict = {}
    text = ""

    # Try Groq first (free, fast)
    try:
        text, usage = groq_chat(
            system=_JD_PARSE_SYSTEM,
            user=user_prompt,
            temperature=0.1,
            max_tokens=1000,
        )
    except LLMError:
        # Cascade to Gemini
        try:
            text, usage = gemini_chat_best(
                system=_JD_PARSE_SYSTEM,
                user=user_prompt,
                temperature=0.1,
                max_output_tokens=1000,
            )
        except LLMError as e:
            raise RuntimeError(f"JD parsing failed — all LLMs exhausted: {e}") from e

    try:
        parsed = json.loads(_strip_json(text))
    except json.JSONDecodeError:
        parsed = {
            "company_name": "",
            "role_title": "",
            "hiring_manager": "",
            "must_have_skills": [],
            "tone_signals": [],
            "mission_snippet": "",
        }

    # Normalize keys
    result = {
        "company_name": str(parsed.get("company_name") or "").strip(),
        "role_title": str(parsed.get("role_title") or "").strip(),
        "hiring_manager": str(parsed.get("hiring_manager") or "").strip(),
        "must_have_skills": [str(s) for s in (parsed.get("must_have_skills") or [])],
        "tone_signals": [str(s) for s in (parsed.get("tone_signals") or [])],
        "mission_snippet": str(parsed.get("mission_snippet") or "").strip(),
    }
    return result, usage


# ── Step 2 — Retrieve top-N matching nuggets (deterministic, no LLM) ─────────

def step_2_retrieve_nuggets(
    must_have_skills: list[str],
    top_n: int = 7,
    profile_dir: Optional[Path] = None,
) -> list[dict]:
    """Embed each must_have skill, cosine vs all nuggets, return top-N.

    Returns list of nugget dicts enriched with 'retrieval_score' and 'nugget_id'.
    No LLM calls — purely deterministic embedding + cosine.
    """
    pd = profile_dir or _profile_dir()
    nuggets_path = pd / "nuggets.jsonl"
    embeddings_path = pd / "embeddings.npz"

    if not nuggets_path.exists():
        raise RuntimeError(
            "No profile found. Run `linkright profile create -r resume.pdf` first."
        )
    if not embeddings_path.exists():
        raise RuntimeError(
            "No embeddings found in profile. Run `linkright profile create -r resume.pdf`."
        )

    # Load nuggets + embeddings
    nuggets = []
    with open(nuggets_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                nuggets.append(json.loads(line))

    data = np.load(str(embeddings_path), allow_pickle=True)
    ids: np.ndarray = data["ids"]
    vectors: np.ndarray = data["vectors"]

    if len(ids) == 0 or len(nuggets) == 0:
        return []

    # Build id → row map for nuggets
    id_to_nugget: dict[str, dict] = {}
    for n in nuggets:
        nid = str(n.get("nugget_index", n.get("nugget_text", "")[:80]))
        id_to_nugget[nid] = n

    # Embed each must_have skill
    skill_vecs: list[list[float]] = []
    for skill in must_have_skills:
        try:
            vec, _ = embed(skill)
            skill_vecs.append(vec)
        except Exception:
            pass

    if not skill_vecs:
        # No embeddings could be generated — return top nuggets by importance heuristic
        priority = {"P0": 3, "P1": 2, "P2": 1}
        sorted_nuggets = sorted(
            nuggets,
            key=lambda n: priority.get(str(n.get("importance", "")).upper(), 0),
            reverse=True,
        )
        return sorted_nuggets[:top_n]

    # For each nugget, compute max cosine across all skill queries
    scored: list[tuple[float, dict]] = []
    for i, nid in enumerate(ids):
        nid_str = str(nid)
        vec_n = vectors[i].tolist()
        nugget = id_to_nugget.get(nid_str)
        if not nugget:
            continue
        max_sim = max(_cosine(sv, vec_n) for sv in skill_vecs)
        scored.append((max_sim, nugget))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Deduplicate by (company, role) — keep highest-scoring per pair
    seen_pairs: set[tuple[str, str]] = set()
    result: list[dict] = []
    for sim, n in scored:
        company = str(n.get("company") or "").strip()
        role = str(n.get("role") or "").strip()
        pair = (company[:40], role[:40])
        nid_str = str(n.get("nugget_index", ""))

        if pair in seen_pairs and len(result) >= top_n // 2:
            continue
        seen_pairs.add(pair)

        enriched = dict(n)
        enriched["retrieval_score"] = round(float(sim), 4)
        enriched["nugget_id"] = nid_str
        result.append(enriched)

        if len(result) >= top_n:
            break

    return result


# ── Step 3 — Generate 3-paragraph draft (LLM, medium temp) ───────────────────

_TONE_SYSTEM_MAP = {
    "formal": (
        "You are a professional cover letter writer. "
        "Tone: formal, measured, precise. "
        "Use complete sentences. No contractions. Avoid superlatives. Be concise and authoritative."
    ),
    "conversational": (
        "You are a professional cover letter writer. "
        "Tone: warm, conversational, direct. "
        "Use natural language. Some contractions are fine. Show genuine interest without sounding generic."
    ),
    "enthusiastic": (
        "You are a professional cover letter writer. "
        "Tone: enthusiastic, energetic, forward-looking. "
        "Show excitement through vivid verbs. Communicate genuine passion for the mission. Be energetic but credible."
    ),
}

_GENERATION_SYSTEM_BASE = """\
{tone_instruction}

You write cover letters that are precise, evidence-backed, and free of clichés.

HARD RULES (violating any → your output will be rejected):
1. Exactly 3 paragraphs. No headers, no bullet points — only flowing prose paragraphs.
2. Paragraph 1 (Hook, 50-70 words): Why THIS company and THIS role. Reference at least one specific detail from the JD (mission, product, or recent signal). Do NOT introduce yourself here.
3. Paragraph 2 (Fit, 150-180 words): 2-3 claims backed by real achievements from the evidence pool. Each claim MUST cite specific quantified evidence from the evidence pool. Cite the nugget_id in [brackets] inline e.g. "I delivered X [n:3]". Use ONLY numbers that appear in the evidence pool — do not invent metrics.
4. Paragraph 3 (Close, 30-50 words): Invite a conversation. Sign off naturally.
5. NO generic phrases: "results-driven", "passionate about", "team player", "synergy", "leverage", "dynamic".
6. NO skills or technologies the candidate has not demonstrated in the evidence pool.
7. Output ONLY the letter body — no greeting ("Dear ...") and no signature block. Those are added separately.
"""

_GENERATION_USER = """\
ROLE: {role_title} at {company_name}
MISSION SNIPPET: "{mission_snippet}"
JD MUST-HAVE SKILLS: {must_have_skills}
TONE SIGNALS FROM JD: {tone_signals}

EVIDENCE POOL — use ONLY this data for claims and numbers:
{evidence_block}

Write the 3-paragraph cover letter body now.
"""


def _format_evidence_block(nuggets: list[dict]) -> str:
    """Format nuggets as a numbered evidence block for the LLM."""
    lines = []
    for n in nuggets:
        nid = n.get("nugget_id") or n.get("nugget_index") or "?"
        company = n.get("company") or ""
        role = n.get("role") or ""
        text = n.get("nugget_text") or n.get("answer") or ""
        importance = n.get("importance") or ""
        lines.append(f"[n:{nid}] [{importance}] {company} / {role}: {text}")
    return "\n".join(lines)


def step_3_generate_draft(
    jd_parsed: dict,
    nuggets: list[dict],
    tone: str = "conversational",
) -> tuple[str, dict]:
    """Generate 3-paragraph cover letter body.

    Returns (draft_text: str, usage: dict).
    Uses free Groq → Gemini cascade at medium temp (0.6) for generation.
    """
    tone_key = tone.lower() if tone.lower() in _TONE_SYSTEM_MAP else "conversational"
    tone_instruction = _TONE_SYSTEM_MAP[tone_key]
    system = _GENERATION_SYSTEM_BASE.replace("{tone_instruction}", tone_instruction)

    evidence_block = _format_evidence_block(nuggets)
    user_prompt = (
        _GENERATION_USER
        .replace("{role_title}", jd_parsed.get("role_title") or "the role")
        .replace("{company_name}", jd_parsed.get("company_name") or "the company")
        .replace("{mission_snippet}", jd_parsed.get("mission_snippet") or "")
        .replace("{must_have_skills}", ", ".join(jd_parsed.get("must_have_skills") or []))
        .replace("{tone_signals}", ", ".join(jd_parsed.get("tone_signals") or []))
        .replace("{evidence_block}", evidence_block)
    )

    usage: dict = {}
    text = ""

    # Groq first (free, fast)
    try:
        text, usage = groq_chat(
            system=system,
            user=user_prompt,
            temperature=0.6,
            max_tokens=800,
        )
    except LLMError:
        # Cascade to Gemini
        try:
            text, usage = gemini_chat_best(
                system=system,
                user=user_prompt,
                temperature=0.6,
                max_output_tokens=800,
            )
        except LLMError as e:
            raise RuntimeError(f"Cover letter generation failed — all LLMs exhausted: {e}") from e

    return text.strip(), usage


# ── Step 4 — Truth-engine validation (deterministic, no LLM) ─────────────────

# Terms that are too generic to trigger fishing guard even if in JD
_FISHING_ALLOWLIST = {
    "role", "team", "work", "join", "help", "make", "build",
    "lead", "grow", "drive", "own", "hire", "seek", "look",
    "manage", "create", "deliver", "ensure", "support", "product",
    "service", "data", "business", "process", "platform", "system",
    "client", "customer", "user", "market", "industry", "strong",
    "deep", "broad", "great", "good", "best", "well", "high",
}

# Minimum fishing terms in a sentence to trigger drop (conservative threshold)
_FISHING_DROP_THRESHOLD = 3


def step_4_validate(
    draft: str,
    nuggets: list[dict],
    jd_text: str,
) -> tuple[str, list[str]]:
    """Run metric-fidelity + JD-fishing guards on the draft.

    Returns (cleaned_draft: str, violations: list[str]).
    violations is empty list on clean pass.
    Fishing guard only fires when ≥3 domain-specific JD terms inject per sentence.
    """
    source_texts = []
    for n in nuggets:
        t = n.get("nugget_text") or n.get("answer") or ""
        if t:
            source_texts.append(t)

    violations: list[str] = []
    sentences = re.split(r"(?<=[.!?])\s+", draft)
    cleaned_sentences: list[str] = []

    jd_terms = extract_jd_terms(jd_text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Check metric fabrication — hard guard
        fabricated_metrics = find_fabricated(sentence, source_texts)
        if fabricated_metrics:
            violations.append(
                f"METRIC_FABRICATION: '{sentence[:100]}' "
                f"unsupported metrics: {fabricated_metrics}"
            )
            continue  # Drop this sentence

        # Check JD-fishing (conservative: only drop if many domain-specific injections)
        fishing_terms = find_fishing(sentence, jd_terms, source_texts)
        significant_fishing = [
            t for t in fishing_terms
            if (
                len(t) >= 5
                and t not in _FISHING_ALLOWLIST
            )
        ]
        if len(significant_fishing) >= _FISHING_DROP_THRESHOLD:
            violations.append(
                f"JD_FISHING: '{sentence[:100]}' "
                f"injects JD terms absent from source: {significant_fishing[:5]}"
            )
            continue  # Drop this sentence

        cleaned_sentences.append(sentence)

    cleaned_draft = " ".join(cleaned_sentences)

    # Safety: if we stripped more than 50% of content, raise severe validation flag.
    # We do NOT silently revert to the fabricated original — that would undermine the
    # truth-engine guarantee.  The orchestrator checks for this sentinel and refuses to
    # write the output file.
    original_words = _count_words(draft)
    cleaned_words = _count_words(cleaned_draft)
    if original_words > 0 and cleaned_words < original_words * 0.5:
        # Keep the cleaned (stripped) draft — DO NOT revert to original fabricated draft.
        # Append sentinel so the orchestrator can detect and abort.
        violations.append(
            f"VALIDATION_FALLBACK: {len(violations)} sentences dropped "
            f"({cleaned_words}/{original_words} words retained) — "
            f"refusing to save fabricated content"
        )

    return cleaned_draft, violations


# ── Step 5 — Format output (deterministic) ────────────────────────────────────

def step_5_format(
    draft: str,
    contact: dict,
    jd_parsed: dict,
    run_id: str,
) -> str:
    """Assemble the final cover letter markdown with header, greeting, body, sign-off."""
    today = date.today().strftime("%B %d, %Y")
    name = contact.get("name") or "Applicant"
    email = contact.get("email") or ""
    phone = contact.get("phone") or ""
    linkedin = contact.get("linkedin") or ""
    portfolio = contact.get("portfolio") or ""

    # Header block
    header_parts = [name]
    if email:
        header_parts.append(email)
    if phone:
        header_parts.append(phone)
    if linkedin:
        header_parts.append(linkedin)
    if portfolio:
        header_parts.append(portfolio)

    header = "  |  ".join(header_parts)

    # Greeting
    hiring_manager = jd_parsed.get("hiring_manager") or ""
    if hiring_manager:
        greeting = f"Dear {hiring_manager},"
    else:
        company = jd_parsed.get("company_name") or ""
        if company:
            greeting = f"Dear Hiring Team at {company},"
        else:
            greeting = "Dear Hiring Team,"

    # Sign-off
    sign_off = f"Best regards,\n{name}"

    letter = f"""{header}

{today}

{greeting}

{draft}

{sign_off}
"""
    return letter



# ── HTML rendering (deterministic) ───────────────────────────────────────────

def _parse_3_paragraphs(letter_md: str) -> list[str]:
    """Extract 3 prose paragraphs from the markdown letter body.

    Skips the header line (name | email | ...), date line, greeting, and
    sign-off block.  Returns a list of exactly 3 strings; pads with empty
    strings if fewer than 3 paragraphs are found.
    """
    lines = letter_md.splitlines()
    # A "paragraph" is a block of non-empty lines separated by blank lines.
    # We collect all paragraph blocks first, then heuristically skip header /
    # date / greeting / sign-off.
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line.strip())
        else:
            if current:
                blocks.append(" ".join(current))
                current = []
    if current:
        blocks.append(" ".join(current))

    # Filter out well-known non-body blocks:
    #   • header (contains " | " separator used in step_5_format)
    #   • date line (matches month-day-year pattern, e.g. "May 02, 2026")
    #   • greeting ("Dear ...")
    #   • sign-off ("Best regards," or candidate name after sign-off)
    import re as _re
    body_blocks: list[str] = []
    date_pat = _re.compile(
        r"^(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},\s+\d{4}$"
    )
    for block in blocks:
        if "  |  " in block:          # header contact line
            continue
        if date_pat.match(block):      # date
            continue
        if block.startswith("Dear "):  # greeting
            continue
        if block.startswith("Best regards"):  # sign-off line 1
            continue
        # Last block often = candidate name alone (sign-off line 2).
        # Heuristic: ≤4 words, no punctuation, comes after sign-off was seen.
        # We relax this — just collect all remaining blocks and trim to 3.
        body_blocks.append(block)

    # Return exactly 3; pad with empty if fewer found
    while len(body_blocks) < 3:
        body_blocks.append("")
    return body_blocks[:3]


def render_cover_letter_html(letter_md: str, contact: dict, jd_meta: dict) -> str:
    """Convert cover letter markdown to professional A4 HTML.

    Parses 3 paragraphs from markdown body, substitutes into the HTML template
    with contact info, date, recipient, and signature blocks.

    Args:
        letter_md: Full formatted cover letter markdown (output of step_5_format).
        contact:   Dict with keys: name, email, phone, linkedin, location.
        jd_meta:   Dict with key: hiring_manager (may be empty).

    Returns:
        HTML string ready for browser preview or PDF rendering.
    """
    paragraphs = _parse_3_paragraphs(letter_md)

    template_path = Path(__file__).parent / "templates" / "cover-letter.html"
    template = template_path.read_text(encoding="utf-8")

    name = contact.get("name") or ""
    email = contact.get("email") or ""
    phone = contact.get("phone") or ""
    linkedin = contact.get("linkedin") or ""
    location = contact.get("location") or ""

    # Build contact sub-separators: only show separator before a field if the field has value
    phone_sep = '<span class="separator"> | </span>' if phone else ""
    linkedin_sep = '<span class="separator"> | </span>' if linkedin else ""
    location_sep = '<span class="separator"> | </span>' if location else ""

    recipient = jd_meta.get("hiring_manager") or "Hiring Team"
    today_str = date.today().strftime("%B %d, %Y")

    html = template
    html = html.replace("{{name}}", name)
    html = html.replace("{{email}}", email)
    html = html.replace("{{phone}}", phone)
    html = html.replace("{{phone_sep}}", phone_sep)
    html = html.replace("{{linkedin}}", linkedin)
    html = html.replace("{{linkedin_sep}}", linkedin_sep)
    html = html.replace("{{location}}", location)
    html = html.replace("{{location_sep}}", location_sep)
    html = html.replace("{{date}}", today_str)
    html = html.replace("{{recipient}}", recipient)
    html = html.replace("{{paragraph_1}}", paragraphs[0])
    html = html.replace("{{paragraph_2}}", paragraphs[1])
    html = html.replace("{{paragraph_3}}", paragraphs[2])

    return html


# ── Main pipeline orchestrator ─────────────────────────────────────────────────

def run_cover_letter_pipeline(
    jd_text: str,
    tone: str = "conversational",
    output_path: Optional[Path] = None,
    render_pdf: bool = False,
    render_html: bool = True,
    profile_dir: Optional[Path] = None,
    run_id: Optional[str] = None,
) -> dict:
    """Run the full 5-step cover letter pipeline.

    By default writes two output files:
      - cover_letter.md  — raw markdown (always written)
      - cover_letter.html — A4 HTML for browser preview (written unless render_html=False)

    Optionally (render_pdf=True):
      - cover_letter.pdf — recruiter-ready PDF via Playwright (HTML-first rendering)

    Returns result dict with:
      letter_md: str — final markdown letter
      letter_html: str | None — HTML string (None if render_html=False)
      letter_path: Path — where .md was saved
      html_path: Path | None — where .html was saved
      pdf_path: Path | None — where .pdf was saved (None unless render_pdf=True)
      telemetry: dict — api_calls, tokens, wall_time, cost, validator_failures
      nuggets_used: list — top-N nugget dicts
      violations: list — truth-engine violations found (and dropped)
      run_id: str
    """
    t_start = time.time()
    run_id = run_id or f"cl_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # Setup output dir
    runs_dir = _runs_dir()
    run_dir = runs_dir / run_id
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    api_calls = 0
    total_tokens = 0
    prompt_tokens_total = 0
    completion_tokens_total = 0
    total_cost = 0.0
    usages: list[dict] = []

    # ── Step 1: Parse JD ──────────────────────────────────────────────────
    jd_parsed, usage1 = step_1_parse_jd(jd_text)
    api_calls += 1
    usages.append(usage1)
    pt1 = int(usage1.get("prompt_tokens") or 0)
    ct1 = int(usage1.get("completion_tokens") or 0)
    prompt_tokens_total += pt1
    completion_tokens_total += ct1
    total_tokens += pt1 + ct1
    (artifacts_dir / "01_jd_parsed.json").write_text(
        json.dumps({"jd_parsed": jd_parsed, "usage": usage1}, indent=2)
    )

    # ── Step 2: Retrieve nuggets ───────────────────────────────────────────
    nuggets = step_2_retrieve_nuggets(
        must_have_skills=jd_parsed.get("must_have_skills") or [],
        top_n=7,
        profile_dir=profile_dir,
    )
    nuggets_used_count = len(nuggets)
    (artifacts_dir / "02_nuggets_retrieved.json").write_text(
        json.dumps({"nuggets": nuggets, "count": nuggets_used_count}, indent=2)
    )

    # ── Step 3: Generate draft ─────────────────────────────────────────────
    draft, usage3 = step_3_generate_draft(jd_parsed, nuggets, tone=tone)
    api_calls += 1
    usages.append(usage3)
    pt3 = int(usage3.get("prompt_tokens") or 0)
    ct3 = int(usage3.get("completion_tokens") or 0)
    prompt_tokens_total += pt3
    completion_tokens_total += ct3
    total_tokens += pt3 + ct3
    (artifacts_dir / "03_draft.txt").write_text(draft)

    # ── Step 4: Validate ───────────────────────────────────────────────────
    cleaned_draft, violations = step_4_validate(draft, nuggets, jd_text)
    validator_failures = len(violations)
    (artifacts_dir / "04_validated.txt").write_text(cleaned_draft)
    (artifacts_dir / "04_violations.json").write_text(
        json.dumps({"violations": violations}, indent=2)
    )

    # ── Truth-engine integrity gate ────────────────────────────────────────
    # If >50% of sentences were fabricated, refuse to continue.  The cleaned_draft
    # is heavily truncated and unfit to send; the original was fabricated. Abort.
    validation_fallback = any("VALIDATION_FALLBACK" in v for v in violations)
    if validation_fallback:
        # Collect first 3 non-fallback violations for the error message
        sample_violations = [v for v in violations if "VALIDATION_FALLBACK" not in v][:3]
        viol_summary = "\n".join(f"  \u2022 {v[:120]}" for v in sample_violations) if sample_violations else "  (no individual violations logged)"
        n_flagged = len([v for v in violations if "VALIDATION_FALLBACK" not in v])
        raise click.ClickException(
            f"\n\u274c Cover letter generation failed truth-engine validation.\n\n"
            f"The LLM produced too many unverifiable claims for the available career\n"
            f"evidence. This usually means:\n"
            f"  1. Your career profile is too sparse — run `linkright profile create`\n"
            f"     or `linkright profile enrich <id>` to add more career nuggets\n"
            f"  2. The JD requires skills not present in your profile — consider\n"
            f"     a different role or be honest about gaps\n\n"
            f"{n_flagged} sentences flagged:\n{viol_summary}\n\n"
            f"We refuse to write a cover letter with unverified claims.\n"
            f"Re-run after expanding your profile."
        )

    # ── Step 5: Format ─────────────────────────────────────────────────────
    contact = load_contact(profile_dir=profile_dir or _profile_dir())
    letter_md = step_5_format(cleaned_draft, contact, jd_parsed, run_id)
    (artifacts_dir / "05_cover_letter.md").write_text(letter_md)

    # Save to requested output path or default
    if output_path:
        output_path = Path(output_path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(letter_md)
        except (PermissionError, OSError) as e:
            raise click.ClickException(
                f"Could not write cover letter to {output_path}: {e}\n"
                f"Check directory permissions or pick a different --output path."
            )
        letter_path = output_path
    else:
        letter_path = artifacts_dir / "cover_letter.md"

    # ── HTML rendering (default: on) ──────────────────────────────────────────
    # Always build HTML string from the markdown letter — it's cheap and deterministic.
    # Only skip writing to disk if render_html=False (--no-html flag).
    letter_html: Optional[str] = None
    html_path: Optional[Path] = None
    if render_html:
        try:
            letter_html = render_cover_letter_html(letter_md, contact, jd_parsed)
            html_path = letter_path.with_suffix(".html")
            html_path.write_text(letter_html, encoding="utf-8")
            (artifacts_dir / "05_cover_letter.html").write_text(letter_html, encoding="utf-8")
        except Exception as e:
            violations.append(f"HTML_RENDER_ERROR: {e}")

    # ── PDF rendering (optional: --pdf flag) — HTML-first path ────────────────
    # Renders from the HTML string via Playwright headless Chromium.
    # This is the correct path: markdown → HTML template → PDF (not markdown → PDF).
    pdf_path: Optional[Path] = None
    if render_pdf:
        # Ensure we have an HTML string to render from
        if letter_html is None:
            try:
                letter_html = render_cover_letter_html(letter_md, contact, jd_parsed)
            except Exception as e:
                violations.append(f"HTML_BUILD_ERROR: {e}")
                letter_html = None

        if letter_html is not None:
            try:
                if sync_playwright is None:
                    raise ImportError(
                        "playwright not installed. Run: pip install playwright && playwright install chromium"
                    )
                pdf_path = letter_path.with_suffix(".pdf")
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    page = browser.new_page()
                    page.set_content(letter_html, wait_until="networkidle")
                    page.pdf(
                        path=str(pdf_path),
                        format="A4",
                        print_background=True,
                        margin={"top": "25mm", "bottom": "25mm", "left": "25mm", "right": "25mm"},
                    )
                    browser.close()
            except Exception as e:
                violations.append(f"PDF_RENDER_ERROR: {e}")
                pdf_path = None

    # ── Telemetry ──────────────────────────────────────────────────────────
    wall_time_s = round(time.time() - t_start, 2)

    # Estimate cost (same rate table as main telemetry.py)
    for u in usages:
        prov = u.get("provider", "unknown")
        if any(p in prov for p in ("groq", "cerebras", "oracle")):
            pass  # $0
        elif "gemini" in prov:
            pt = int(u.get("prompt_tokens") or 0)
            ct = int(u.get("completion_tokens") or 0)
            total_cost += (pt / 1_000_000) * 0.075 + (ct / 1_000_000) * 0.30
        elif "openrouter" in prov:
            pt = int(u.get("prompt_tokens") or 0)
            ct = int(u.get("completion_tokens") or 0)
            total_cost += (pt / 1_000_000) * 0.07 + (ct / 1_000_000) * 0.25

    telemetry = {
        "run_id": run_id,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "wall_time_s": wall_time_s,
        "api_calls": api_calls,
        "tokens": total_tokens,
        "prompt_tokens": prompt_tokens_total,
        "completion_tokens": completion_tokens_total,
        "cost": round(total_cost, 6),
        "cost_usd": round(total_cost, 6),
        "nuggets_retrieved": nuggets_used_count,
        "validator_failures": validator_failures,
        "tone": tone,
        "providers": list({u.get("provider") for u in usages if u.get("provider")}),
        "violations": violations,
        "pdf_rendered": pdf_path is not None,
        "html_rendered": html_path is not None,
    }
    (run_dir / "telemetry.json").write_text(json.dumps(telemetry, indent=2))

    return {
        "letter_md": letter_md,
        "letter_html": letter_html,
        "letter_path": letter_path,
        "html_path": html_path,
        "pdf_path": pdf_path,
        "telemetry": telemetry,
        "nuggets_used": nuggets,
        "violations": violations,
        "run_id": run_id,
        "jd_parsed": jd_parsed,
    }
