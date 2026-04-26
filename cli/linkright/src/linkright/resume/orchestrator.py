"""E2E LinkRight pipeline diagnostic run.

Every run lives in its own directory under runs/<run_id>/ and is self-contained:

    runs/<run_id>/
      ├── vision.md         # single source of truth (plan + logs + report)
      ├── inputs/           # resume.pdf + jd.md (copy-in before running)
      ├── artifacts/        # 00_..15_* machine-readable dumps
      └── logs/pipeline.log

Usage:
    python3 run_pipeline.py --run-id run_02_2026-04-21_xyz

Before running a NEW run:
    mkdir -p runs/<run_id>/inputs
    cp path/to/resume.pdf runs/<run_id>/inputs/
    cp path/to/jd.md       runs/<run_id>/inputs/
    python3 run_pipeline.py --run-id <run_id>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    _envfile = ROOT / ".env"
    if _envfile.exists():
        load_dotenv(_envfile)
except ImportError:
    pass

from .lib import logbook, llm, embedder, cosine, telemetry
from .lib import prompts as P
from .lib import width_poc
from .lib import fit_loop
from .lib.pdf_parse import extract_text
from .lib.md_parse import parse_resume_markdown
from .lib.width_config import (
    STEP12_MIN_CHARS,
    STEP12_MAX_CHARS,
    STEP12_TARGET_MIDPOINT,
    STEP12_UNDERSHOOT_CHARS,
    STEP12_OOB_MIN,
    STEP12_OOB_MAX,
    STEP12_PAD_MIN,
    STEP12_PAD_MAX,
)


# ── Module-level retry counter (populated by any step that re-prompts on
# validator violations, e.g. step_09's B2 hallucination guard). Consumed by
# step_16_telemetry to compute llm_retries in the per-run rollup.
RETRY_COUNTS: dict[str, int] = {}


def _note_retry(step_name: str) -> None:
    RETRY_COUNTS[step_name] = RETRY_COUNTS.get(step_name, 0) + 1


# ── Iter-04 (2026-04-23): Output purity + outline pruning helpers ──────────
# Used by Step 10, Step 12, Step 13 (via width_poc), and Step 14 to keep
# LLM commentary out of final HTML and prevent blank-section shells in PDF.

_BANNED_LEADING_PHRASES = (
    # Polite acknowledgments
    "note:", "here's", "here is", "here are", "sure,", "sure!", "sure ", "certainly",
    "okay,", "alright,", "of course,", "absolutely,", "great,",
    "thanks", "thank you",
    # Self-reference starts
    "i've", "i have", "i can", "i cannot", "i'm", "i am",
    "let me", "i'll", "i will", "i would", "i'd",
    "we've", "we have", "we can", "we'll",
    # Reasoning prefaces
    "based on", "given", "since", "after", "upon",
    "considering", "looking at", "reviewing",
    "in this", "in the", "for this", "for the",
    "to address", "to fulfill", "to meet",
    # Meta-labels
    "the bullet", "the rewritten", "the adjusted", "the revised",
    "the updated", "the output", "the response", "the final",
    "output:", "result:", "answer:", "response:", "revised:", "rewrite:",
    # Quoted prefaces
    "below is", "below are", "please find", "as requested",
    # Explanatory connectors
    "as you", "this is", "this has",
)


def _strip_commentary(text: str) -> str:
    """Remove leading commentary phrases + HTML comments + code fences from LLM output.

    Also strips any prose that appears BEFORE a JSON object — if the text contains
    a `{` that starts a JSON block and there's prose ahead of it, trim to the `{`.
    This handles the common failure mode where LLMs emit reasoning like
    "I can only generate one paragraph because..." before the actual JSON.

    Safe to apply to any LLM response that should be raw resume text (bullet HTML
    or JSON). If the text is already clean, returns it unchanged.
    """
    if not text:
        return text
    # Drop HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Drop code-fence wrappers (including ```json ... ```) anywhere in text
    text = re.sub(r"```[a-z]*\s*\n?", "", text)
    text = re.sub(r"\s*```\s*", "", text)
    # Iter-04: drop surrounding straight/curly quotes if they wrap the whole output
    stripped = text.strip()
    if len(stripped) > 2:
        for open_q, close_q in (('"', '"'), ("'", "'"), ("\u201c", "\u201d"), ("\u2018", "\u2019")):
            if stripped.startswith(open_q) and stripped.endswith(close_q):
                stripped = stripped[1:-1].strip()
                break
        text = stripped
    # Drop trailing meta-commentary (either on a new line OR in parentheses).
    # CRITICAL: these patterns are TRAILING-only — "in this revised" as LEADING
    # is handled by _BANNED_LEADING_PHRASES. DOTALL + these patterns would eat
    # the whole bullet if applied to leading prose.
    text = re.sub(
        r"\s*[\(\[](let me know|hope this helps|happy to adjust|feel free to|note that|as you can see|please let me)[^)\]]*[\)\]]\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\n\s*(let me know|hope this helps|happy to adjust|feel free to|note that|as you can see|please let me).*$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Drop leading markdown-style emphasis wrappers (**text** or *text*)
    text = re.sub(r"^\*{1,3}|\*{1,3}$", "", text.strip())
    # If starts with a banned phrase, strip up to first <b>, first {, or first blank line
    lower = text.lower().lstrip()
    for phrase in _BANNED_LEADING_PHRASES:
        if lower.startswith(phrase):
            idx_b = text.find("<b>")
            idx_brace = text.find("{")
            idx_nl = text.find("\n\n")
            candidates = [i for i in (idx_b, idx_brace, idx_nl) if i > 0]
            if candidates:
                text = text[min(candidates):]
            break
    # Final safeguard: if text looks like it SHOULD be JSON (contains a balanced
    # {...} block) but has prose before it, strip the prose. Heuristic: if any
    # `{` exists in the text and the text BEFORE it contains prose (letters and
    # no `{`), trim to the first `{`.
    first_brace = text.find("{")
    if first_brace > 20:  # more than 20 chars of prose before first {
        before = text[:first_brace]
        if re.search(r"[a-zA-Z]{5,}", before) and "{" not in before:
            text = text[first_brace:]
    return text.strip()


def _prune_outline(bullets_per_co: dict) -> dict:
    """Strip empty companies/roles from the bullets-per-company map.

    Called between Step 13 (width POC) and Step 14 (HTML assembly) to prevent
    renderer from emitting <section>...</section> shells for companies that
    had 0 relevant nuggets (Step 08) or 0 generated bullets (Step 10).

    Input shape: {company_name: [{text_html, verb, ...}, ...], ...}
    Returns:     same shape with companies/roles having empty lists removed.
    """
    pruned = {}
    for company, bullets in (bullets_per_co or {}).items():
        if not bullets:
            continue
        filtered = [b for b in bullets if b and b.get("text_html", "").strip()]
        if filtered:
            pruned[company] = filtered
    return pruned


# ── B1/F02 helper: compute candidate total years of experience ──────────────
# Mirrors repo/worker/app/pipeline/orchestrator.py::_compute_total_experience_years
_MONTHS = {m.lower(): i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1
)}

_CAREER_LEVEL_MIN_YEARS = {
    "fresher": 0.0,
    "entry": 1.0,
    "mid": 3.0,
    "senior": 6.0,
    "executive": 10.0,
}

# S5-1: `profile` field — canonical for selection, priority, bullet distribution.
# Derived deterministically from `career_level` (after S5-5 validator override)
# so the two fields are always consistent. `profile` uses "early_career" label
# instead of "entry" for the narrower 1-2yr bucket.
_CAREER_LEVEL_TO_PROFILE = {
    "fresher": "fresher",
    "entry": "early_career",
    "mid": "mid",
    "senior": "senior",
    "executive": "executive",
}


def _derive_profile(career_level: str) -> str:
    """Map career_level (already validated by S5-5) to profile. Default: mid."""
    return _CAREER_LEVEL_TO_PROFILE.get((career_level or "").strip().lower(), "mid")


# ── S5-2: Weighted bullet distribution ──────────────────────────────────────
# Per-profile bullet budgets + floor/ceiling limits. Tunable via env.
_BULLET_BUDGETS = {
    "fresher":       {"total": 8,  "floor": 2, "ceiling": 4},
    "early_career":  {"total": 10, "floor": 2, "ceiling": 5},
    "mid":           {"total": 14, "floor": 3, "ceiling": 6},
    "senior":        {"total": 13, "floor": 2, "ceiling": 6},
    "executive":     {"total": 12, "floor": 2, "ceiling": 5},
}

# Relevance formula weights (locked: 0.55 + 0.30 + 0.15). Override via env.
_REL_W_ALIGN_COSINE  = 0.55
_REL_W_ALIGN_COVERED = 0.30
_REL_W_ALIGN_LEADER  = 0.15


def _compute_bullet_distribution(
    role_scores: list[dict],
    total_reqs: int,
    profile: str,
) -> dict:
    """S5-2: weighted bullet distribution based on JD-alignment × recency.

    Returns dict with:
      - included_companies: list of (company, role, bullets) tuples, ordered by recency
      - excluded_companies: list dropped due to dynamic floor (relevance < 0.5 × max)
      - companies_scored: per-company relevance breakdown for telemetry
    """
    import os as _os
    import json as _json
    # Env override for weights (hot-swap without code change)
    override = _os.environ.get("BULLET_DIST_WEIGHTS_JSON")
    w_cos, w_cov, w_lead = _REL_W_ALIGN_COSINE, _REL_W_ALIGN_COVERED, _REL_W_ALIGN_LEADER
    if override:
        try:
            o = _json.loads(override)
            w_cos = float(o.get("avg_cos", w_cos))
            w_cov = float(o.get("covered", w_cov))
            w_lead = float(o.get("leadership", w_lead))
        except Exception:
            pass

    budget = _BULLET_BUDGETS.get(profile, _BULLET_BUDGETS["mid"])

    # Filter to real companies only (role_scores already sorted by avg_cos desc)
    # role_scores is sorted by avg_cos from step_06; here we re-rank by full relevance.
    companies_scored = []
    for rank, rs in enumerate(role_scores):
        avg_cos = rs.get("avg_best_cosine", 0.0) or 0.0
        covered_ratio = (len(rs.get("covers", [])) / max(total_reqs, 1))
        leader_norm = (rs.get("leadership_max", 0) or 0) / 2.0
        alignment = w_cos * avg_cos + w_cov * covered_ratio + w_lead * leader_norm
        # Recency: rank 0 = most recent, decays 0.1 per slot, floor 0.6
        recency = max(0.6, 1.0 - 0.1 * rank)
        relevance = alignment * recency
        companies_scored.append({
            "company": rs["company"],
            "role": rs["role"],
            "rank_by_cos": rank,
            "alignment": round(alignment, 4),
            "recency": round(recency, 4),
            "relevance": round(relevance, 4),
            "classification": rs.get("classification", "tertiary"),
        })

    if not companies_scored:
        return {
            "included_companies": [],
            "excluded_companies": [],
            "companies_scored": [],
            "total_budget": budget["total"],
            "profile_used": profile,
        }

    # Dynamic floor: drop if relevance < 0.5 × max(relevance)
    max_rel = max(c["relevance"] for c in companies_scored)
    cutoff = 0.5 * max_rel
    included_scored = [c for c in companies_scored if c["relevance"] >= cutoff]
    excluded_scored = [c for c in companies_scored if c["relevance"] < cutoff]

    # v0.1.1: strict cap of 4 companies across ALL profiles (was: senior/executive only).
    # Tie-break preserved: 1 most-recent + top-3 by relevance.
    if len(included_scored) > 4:
        most_recent = min(included_scored, key=lambda c: c["rank_by_cos"])
        others = [c for c in included_scored if c is not most_recent]
        others_sorted = sorted(others, key=lambda c: -c["relevance"])
        top3 = others_sorted[:3]
        dropped = others_sorted[3:]
        included_scored = [most_recent] + top3
        excluded_scored.extend(dropped)

    # Normalize + allocate
    total_budget = budget["total"]
    floor = budget["floor"]
    ceiling = budget["ceiling"]
    if not included_scored:
        return {
            "included_companies": [],
            "excluded_companies": [{"company": c["company"], "role": c["role"], "relevance": c["relevance"], "reason": "below dynamic floor"} for c in excluded_scored],
            "companies_scored": companies_scored,
            "total_budget": total_budget,
            "profile_used": profile,
        }

    raw = [c["relevance"] for c in included_scored]
    s = sum(raw) or 1.0
    ideal = [(r / s) * total_budget for r in raw]
    allocated = [max(floor, min(ceiling, round(i))) for i in ideal]

    # Rebalance to exact total_budget
    def _argmax_drop_idx():
        best_i, best_slack = -1, -1.0
        for i, a in enumerate(allocated):
            if a <= floor:
                continue
            slack = (a - max(ideal[i], 0.01))
            if slack > best_slack:
                best_slack, best_i = slack, i
        return best_i

    def _argmax_add_idx():
        best_i, best_deficit = -1, -1.0
        for i, a in enumerate(allocated):
            if a >= ceiling:
                continue
            deficit = ideal[i] - a
            if deficit > best_deficit:
                best_deficit, best_i = deficit, i
        return best_i

    guard = 0
    while sum(allocated) > total_budget and guard < 20:
        idx = _argmax_drop_idx()
        if idx < 0:
            break
        allocated[idx] -= 1
        guard += 1
    guard = 0
    while sum(allocated) < total_budget and guard < 20:
        idx = _argmax_add_idx()
        if idx < 0:
            break
        allocated[idx] += 1
        guard += 1

    for c, b in zip(included_scored, allocated):
        c["bullets"] = b

    return {
        "included_companies": included_scored,
        "excluded_companies": [
            {"company": c["company"], "role": c["role"], "relevance": c["relevance"], "reason": "below dynamic floor"}
            for c in excluded_scored
        ],
        "companies_scored": companies_scored,
        "total_budget": total_budget,
        "profile_used": profile,
        "relevance_cutoff": round(cutoff, 4),
        "weights_used": {"avg_cos": w_cos, "covered": w_cov, "leadership": w_lead},
    }


# ── S5-3: Section priority / visibility rules per profile ────────────────────

def _compute_section_visibility(
    profile: str,
    parsed_p12: dict,
    parsed_resume: dict,
    has_relevant_projects: bool,
) -> dict:
    """S5-3: deterministic section visibility + ordering.

    Returns dict with:
      - included_sections: ordered list of section keys that WILL render
      - excluded_sections: list of {section, reason} that won't render
    """
    import os as _os

    force_interests = _os.environ.get("FORCE_INTERESTS_SECTION", "").lower() in ("1", "true", "yes")

    companies = parsed_p12.get("companies", []) or []
    has_companies = len(companies) > 0
    # Awards: count from Phase 1+2 OR resume parse
    awards = (parsed_p12.get("awards") or []) + (parsed_resume.get("awards") or [])
    awards_count = len(awards)
    # Certifications
    certs = (parsed_p12.get("certifications") or []) + (parsed_resume.get("certifications") or [])
    # Check if any cert is JD-relevant (match keyword)
    jd_keywords = [k.lower() for k in (parsed_p12.get("jd_keywords") or [])]
    relevant_cert = any(
        any(kw in (c if isinstance(c, str) else str(c)).lower() for kw in jd_keywords)
        for c in certs
    )

    included: list[str] = []
    excluded: list[dict] = []

    def _include(s: str):
        included.append(s)

    def _exclude(s: str, reason: str):
        excluded.append({"section": s, "reason": reason})

    # Summary: ALWAYS
    _include("summary")

    # Professional Experience: ALWAYS if companies, else suppress (fresher)
    if has_companies:
        _include("experience")
    else:
        _exclude("experience", "no companies parsed")

    # Projects
    if profile == "fresher":
        _include("projects")
    elif profile in ("early_career", "mid"):
        if has_relevant_projects:
            _include("projects")
        else:
            _exclude("projects", "no qualifying independent_project nuggets (BRS >= 0.6) or profile=mid without projects")
    else:
        _exclude("projects", f"profile={profile}; projects de-emphasized")

    # Skills: ALWAYS (if any)
    if parsed_p12.get("skills"):
        _include("skills")
    else:
        _exclude("skills", "no skills parsed")

    # Education: ALWAYS except executive (OPTIONAL by prestige; keep default on)
    edu = parsed_p12.get("education", []) or parsed_resume.get("education", [])
    if edu:
        _include("education")
    else:
        _exclude("education", "no education entries")

    # v8 Fix 2: expand-to-fill — when set (default ON), include any optional section
    # with data. The fit_loop's drop-ladder will remove sections if page overflows,
    # so over-inclusion is safe. Set DISABLE_EXPAND_TO_FILL=1 to revert old gates.
    _expand_to_fill = os.environ.get("DISABLE_EXPAND_TO_FILL", "").lower() not in ("1", "true", "yes")

    # Certifications: OPTIONAL; require ≥1 relevant to JD (or any when expand-to-fill)
    if profile in ("senior", "executive") and not _expand_to_fill:
        _exclude("certifications", f"profile={profile} drops certifications by default")
    elif certs and (relevant_cert or _expand_to_fill):
        _include("certifications")
    else:
        _exclude("certifications", "no cert matches JD keywords" if certs else "no certs present")

    # Awards: OPTIONAL; include dedicated section if >=2 awards (or >=1 when expand-to-fill)
    awards_threshold = 1 if _expand_to_fill else 2
    if awards_count >= awards_threshold:
        _include("awards")
    elif awards_count == 1:
        _exclude("awards", "single award — fold into Education line instead")
    else:
        _exclude("awards", "no awards")

    # Voluntary: include if data exists (or fresher-without-exp under old gate)
    voluntary_data = (parsed_p12.get("voluntary") or []) or (parsed_resume.get("voluntary") or [])
    if (profile == "fresher" and not has_companies) or (_expand_to_fill and voluntary_data):
        _include("voluntary")
    else:
        _exclude("voluntary", f"profile={profile}" + ("; has work exp" if has_companies else ""))

    # Interests: NEVER by default; opt-in via env
    if force_interests:
        _include("interests")
    else:
        _exclude("interests", "hidden by default (FORCE_INTERESTS_SECTION=1 to enable)")

    return {
        "included_sections": included,
        "excluded_sections": excluded,
        "force_interests_override": force_interests,
    }


def _compute_total_experience_years(companies: list[dict]) -> float:
    """Sum active employment durations from companies[].date_range.

    Accepts formats like 'Jul 2024 – Present', '2020 – 2024', 'Apr 2022 – Jul 2024'.
    Returns 0.0 if parsing fails. Conservative: sums spans without de-overlapping.
    """
    now = datetime.utcnow()
    total = 0.0
    for co in companies or []:
        dr = (co.get("date_range") or "").strip()
        if not dr:
            continue
        parts = re.split(r"\s*[\u2013\u2014\-–—]\s*", dr)
        if len(parts) < 2:
            continue

        def _parse_end(s: str) -> Optional[datetime]:
            s = s.strip()
            if s.lower() in ("present", "current", "now", ""):
                return now
            m = re.match(r"([A-Za-z]+)\s*(\d{4})", s)
            if m and m.group(1).lower()[:3] in _MONTHS:
                return datetime(int(m.group(2)), _MONTHS[m.group(1).lower()[:3]], 1)
            m = re.match(r"(\d{4})", s)
            if m:
                return datetime(int(m.group(1)), 1, 1)
            return None

        start = _parse_end(parts[0])
        end = _parse_end(parts[-1])
        if start and end and end >= start:
            total += (end - start).days / 365.25
    return round(total, 1)


# ── Per-run paths (set in main() based on --run-id) ───────────────────────
RUN_DIR: Path = ROOT  # overwritten in main()
ARTIFACTS: Path = ROOT / "artifacts"
INPUTS: Path = ROOT / "inputs"
LOG_PATH: Path = ROOT / "logs" / "pipeline.log"


def _setup_run_dir(run_id: str) -> Path:
    """Resolve runs/<run_id>/ and set module-level paths."""
    global RUN_DIR, ARTIFACTS, INPUTS, LOG_PATH
    RUN_DIR = ROOT / "runs" / run_id
    if not RUN_DIR.exists():
        raise SystemExit(
            f"Run directory not found: {RUN_DIR}\n"
            f"Create it and copy inputs first:\n"
            f"  mkdir -p {RUN_DIR}/inputs\n"
            f"  cp path/to/resume.pdf {RUN_DIR}/inputs/\n"
            f"  cp path/to/jd.md {RUN_DIR}/inputs/"
        )
    INPUTS = RUN_DIR / "inputs"
    if not (INPUTS / "resume.pdf").exists() or not (INPUTS / "jd.md").exists():
        raise SystemExit(
            f"Missing inputs. Expected both:\n"
            f"  {INPUTS}/resume.pdf\n"
            f"  {INPUTS}/jd.md"
        )
    ARTIFACTS = RUN_DIR / "artifacts"
    ARTIFACTS.mkdir(exist_ok=True)
    LOG_PATH = RUN_DIR / "logs" / "pipeline.log"
    LOG_PATH.parent.mkdir(exist_ok=True)
    # Redirect the single-source-of-truth writer
    logbook.set_path(RUN_DIR / "vision.md")
    return RUN_DIR


def log(msg: str) -> None:
    """Append-only low-level log for full LLM bodies (vision.md gets summaries)."""
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(msg.rstrip() + "\n")


# ────────────────────────────────────────────────────────────────────────────
# Step 0 — Ingest resume PDF
# ────────────────────────────────────────────────────────────────────────────

def step_00_ingest_pdf() -> str:
    step = "step_00_ingest_pdf"
    logbook.append(
        step, "starting",
        "extracting plain text from inputs/resume.pdf via pypdf; "
        "expecting > 1.5KB text, name Satvik Jain, email + phone present",
    )

    pdf_path = INPUTS / "resume.pdf"
    raw_text = extract_text(pdf_path)
    out_path = ARTIFACTS / "00_resume_raw_text.txt"
    out_path.write_text(raw_text, encoding="utf-8")

    # Evaluate (case-insensitive name check)
    length = len(raw_text)
    has_name = "satvik" in raw_text.lower() and "jain" in raw_text.lower()
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", raw_text)
    phone_match = re.search(r"\+?\d[\d\s\-]{7,}\d", raw_text)
    bullet_char_count = raw_text.count("•") + raw_text.count("●")

    # Detect pypdf spacing corruption — characters embedded with trailing space.
    # E.g. "AM L" should be "AML", "M anager" should be "Manager", "M L" should be "ML".
    # Pattern: single capital letter followed by single space followed by letter(s).
    corruption_hits = re.findall(r"\b[A-Z] [A-Z]?[a-z]+\b", raw_text)
    # Narrow filter: only report if looks like an acronym-splitting artifact (M, L, etc.)
    likely_corrupted = [m for m in corruption_hits if m.split()[0] in ("M", "L", "N", "H", "C", "A")]

    gaps: list[str] = []
    if length < 1500:
        gaps.append(f"text length {length} < 1500 (PDF may be image-based or extract failed)")
    if not has_name:
        gaps.append("name 'Satvik Jain' not found")
    if not email_match:
        gaps.append("no email pattern detected")
    if not phone_match:
        gaps.append("no phone pattern detected")
    if len(likely_corrupted) > 3:
        gaps.append(
            f"pypdf spacing corruption: {len(likely_corrupted)} hits like {likely_corrupted[:5]} — "
            "'AML' rendered as 'AM L', 'Manager' as 'M anager'. "
            "This will propagate to nugget extraction and JD matching unless handled."
        )

    status = "pass" if not gaps else ("partial" if not any("text length" in g for g in gaps) else "fail")

    body_md = f"""**Artifact:** `artifacts/00_resume_raw_text.txt` ({length} chars)

**Metrics:**
- Character count: {length}
- Contains name (case-insensitive): {has_name}
- Email extracted: `{email_match.group(0) if email_match else 'NONE'}`
- Phone extracted: `{phone_match.group(0) if phone_match else 'NONE'}`
- Bullet chars (• or ●): {bullet_char_count}
- pypdf corruption hits (acronym-splitting artifacts): {len(likely_corrupted)}
- Sample corruption: `{likely_corrupted[:10]}`

**Evaluation:** {status.upper()}

**Gaps found:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}

**Root-cause hypothesis:**
pypdf is inserting a space after certain capital letters (M, L, etc.) when the source
PDF uses bold or kerned glyphs. This is a KNOWN limitation of pypdf vs. production's
`unpdf` (JS library) — we need to verify whether unpdf handles this better, or if the
LLM in Step 1 handles "AM L" as "AML" via context. If the LLM cannot recover, this is
a P0 upstream finding that corrupts every downstream phase (nuggets extracted as
"AM L" won't cosine-match JD requirement "AML" or "anti money laundering").

**First 500 chars of extracted text:**
```
{raw_text[:500]}
```
"""
    logbook.append(step, "eval", f"extraction {status}; {length} chars; gaps={len(gaps)}", body_md)
    return raw_text


# ────────────────────────────────────────────────────────────────────────────
# Step 1 — Structured resume parse
# ────────────────────────────────────────────────────────────────────────────

def step_01_parse_resume(raw_text: str) -> dict:
    step = "step_01_parse_resume"
    logbook.append(
        step, "starting",
        "calling Groq 70B with vendored RESUME_PARSE_FALLBACK prompt (same prompt "
        "as website /api/onboarding/parse-resume Langfuse key 'resume-parse-structured'); "
        f"input is {len(raw_text)}-char text from Step 0; temp=0.2; expecting "
        "markdown with ## EDUCATION / ## SKILLS / ## EXPERIENCE / ## PROJECTS sections",
    )
    try:
        md_text, usage = llm.chat_with_fallback(
            system=P.RESUME_PARSE_FALLBACK,
            user=raw_text,
            temperature=0.2,
            max_tokens=4000,
        )
    except llm.LLMError as e:
        logbook.append(step, "error", "LLM call failed (both Groq and Gemini)", body=f"```\n{e}\n```")
        raise

    log(f"=== step_01 {usage.get('provider')} raw output ===\n{md_text}\n=== end ===\n")
    parsed = parse_resume_markdown(md_text)

    out_path = ARTIFACTS / "01_resume_parsed.json"
    out_path.write_text(json.dumps({"markdown": md_text, "parsed": parsed, "usage": usage}, indent=2), encoding="utf-8")

    experiences = parsed.get("experiences", [])
    companies = [e["company"] for e in experiences if e.get("company")]
    total_bullets = sum(len(e.get("bullets", [])) for e in experiences)
    total_projects = sum(len(e.get("projects", [])) for e in experiences) + len(parsed.get("projects", []))

    gaps: list[str] = []
    if not any("amex" in c.lower() or "american express" in c.lower() for c in companies):
        gaps.append("American Express not found in parsed companies")
    if not any("sprinklr" in c.lower() for c in companies):
        gaps.append("Sprinklr not found in parsed companies")
    if len(experiences) < 2:
        gaps.append(f"only {len(experiences)} experience blocks extracted; expected 2–4")
    if total_bullets < 8:
        gaps.append(f"only {total_bullets} bullets across all roles; resume has ~15+")
    if not parsed.get("skills"):
        gaps.append("SKILLS section empty")

    # Check for corruption propagation: did the LLM retain "AM L" or fix to "AML"?
    corruption_in_output = any(
        " AM L" in b or " M L" in b or "M anager" in b or "M gmt" in b
        for e in experiences
        for b in e.get("bullets", [])
    )

    status = "pass" if not gaps else "partial"

    body_md = f"""**Artifact:** `artifacts/01_resume_parsed.json` (markdown + parsed dict)

**Metrics:**
- Companies parsed: {companies}
- Experience blocks: {len(experiences)}
- Total bullets: {total_bullets}
- Total projects (in-role + top-level): {total_projects}
- Skills count: {len(parsed.get('skills', []))}
- Education entries: {len(parsed.get('education', []))}
- Certifications: {len(parsed.get('certifications', []))}
- LLM usage: {usage}
- "AM L"/"M anager" corruption propagated into bullets: {corruption_in_output}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}

**Root-cause hypothesis:**
{"Groq 70B cleanly extracted the Markdown structure. Corruption from Step 0 " + ("DID propagate — 'AM L' appears in bullets unchanged (the LLM didn't auto-correct it). Downstream nugget embeddings for these bullets will be weaker because 'AM L' is tokenized differently than 'AML'." if corruption_in_output else "did NOT propagate verbatim — LLM may have normalized, OR parsing lost those bullets. Check markdown raw output in artifact.") if not gaps else "Structural parse had gaps — see list above."}

**Sample bullets (first role, first 3):**
```
{chr(10).join('- ' + b for b in experiences[0]['bullets'][:3]) if experiences else '(no experiences parsed)'}
```
"""
    logbook.append(step, "eval", f"parse {status}; {len(experiences)} companies; gaps={len(gaps)}", body_md)
    return parsed


# ────────────────────────────────────────────────────────────────────────────
# Step 2 — Nugget extraction (Phase 0 equivalent)
# ────────────────────────────────────────────────────────────────────────────

def step_02_extract_nuggets(raw_text: str, parsed: dict) -> list[dict]:
    step = "step_02_extract_nuggets"
    logbook.append(
        step, "starting",
        "calling Groq 70B with vendored NUGGET_EXTRACT_MD prompt (same as "
        "worker/app/tools/nugget_extractor.py Langfuse key 'nugget_extractor_md'); "
        "input is the raw resume text; expecting 20-40 atomic ## nugget blocks "
        "each tagged with company, role, importance, answer, tags",
    )

    # Use the raw career text as input (production batches at 3000 chars; Satvik's is 3009 — single batch)
    try:
        md_text, usage = llm.chat_with_fallback(
            system=P.NUGGET_EXTRACT_MD,
            user=raw_text,
            temperature=0.3,
            max_tokens=4000,
        )
    except llm.LLMError as e:
        logbook.append(step, "error", "LLM nugget extraction failed", body=f"```\n{e}\n```")
        raise

    log(f"=== step_02 {usage.get('provider')} raw output ===\n{md_text}\n=== end ===\n")

    # Parse ## nugget blocks
    nuggets: list[dict] = []
    blocks = re.split(r"(?m)^## nugget\s*$", md_text)
    for idx, block in enumerate(blocks):
        if not block.strip():
            continue
        nug = {"nugget_index": idx, "raw": block.strip()}
        for line in block.split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, val = line.partition(":")
            nug[key.strip().lower()] = val.strip()
        # Synthesize an atom ID (8 hex chars from index) — production stores UUID from DB
        import hashlib
        nug["id"] = hashlib.sha1(f"{nug.get('answer','')}{idx}".encode()).hexdigest()[:8].upper()
        if nug.get("answer"):  # valid nugget
            nuggets.append(nug)

    # D1/F05: drop work_experience nuggets with missing company tag + log count.
    # Mirrors prod nugget_extractor.py post-parse filter (linkright-9if).
    _untagged_count = 0
    _kept: list[dict] = []
    for n in nuggets:
        is_work = (n.get("type") or "work_experience").lower() == "work_experience"
        company_val = (n.get("company") or "").strip().lower()
        if is_work and company_val in ("", "none", "null"):
            _untagged_count += 1
            continue
        _kept.append(n)
    if _untagged_count:
        log(f"[step_02 D1 filter] dropped {_untagged_count} work_experience nugget(s) with missing company")
    nuggets = _kept

    out_path = ARTIFACTS / "02_nuggets_extracted.json"
    out_path.write_text(
        json.dumps({"markdown": md_text, "nuggets": nuggets, "dropped_untagged": _untagged_count, "usage": usage}, indent=2),
        encoding="utf-8",
    )

    # Evaluate
    per_company: dict[str, int] = {}
    importance_counts: dict[str, int] = {}
    for n in nuggets:
        c = (n.get("company") or "none").lower()
        per_company[c] = per_company.get(c, 0) + 1
        importance_counts[n.get("importance", "P?")] = importance_counts.get(n.get("importance", "P?"), 0) + 1

    # Single-signal check: flag nuggets containing " and " with 2+ distinct numbers
    multi_signal = []
    for n in nuggets:
        ans = n.get("answer", "")
        nums = re.findall(r"\d+(?:\.\d+)?%?", ans)
        if len(nums) >= 3 and " and " in ans.lower():
            multi_signal.append(n.get("id", "?"))

    gaps: list[str] = []
    if len(nuggets) < 10:
        gaps.append(f"only {len(nuggets)} nuggets extracted; expected 20-40 for a dense resume like Satvik's")
    if len(importance_counts) < 2:
        gaps.append(f"importance distribution collapsed: {importance_counts}")
    if multi_signal:
        gaps.append(f"{len(multi_signal)} nuggets appear multi-signal (should be atomized): {multi_signal[:5]}")
    if not any("american express" in k or "amex" in k for k in per_company):
        gaps.append("no nuggets attributed to American Express")

    status = "pass" if not gaps else "partial"

    sample = nuggets[0] if nuggets else {}
    body_md = f"""**Artifact:** `artifacts/02_nuggets_extracted.json`

**Metrics:**
- Total nuggets: {len(nuggets)}
- Per-company distribution: {per_company}
- Importance distribution: {importance_counts}
- LLM usage: {usage}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}

**Sample nugget (#0):**
```
answer: {sample.get('answer', 'N/A')}
company: {sample.get('company', 'N/A')}  role: {sample.get('role', 'N/A')}
importance: {sample.get('importance', 'N/A')}  tags: {sample.get('tags', 'N/A')}
id: {sample.get('id', 'N/A')}
```

**Root-cause hypothesis:**
{"Atomization prompt is working as intended." if not gaps else "If count is low, prompt may be too conservative at temp 0.3. If multi-signal is high, single-signal rule isn't firing — enforce via stricter prompt language. If Amex missing, company-tagging rule is failing on 'American Express — Senior Associate Product M anager' header (note pypdf 'M anager' corruption)."}
"""
    logbook.append(step, "eval", f"nuggets {status}; {len(nuggets)} extracted; gaps={len(gaps)}", body_md)
    return nuggets


# ────────────────────────────────────────────────────────────────────────────
# Step 3 — Embed nuggets via Oracle nomic-embed-text
# ────────────────────────────────────────────────────────────────────────────

def step_03_embed_nuggets(nuggets: list[dict]) -> list[dict]:
    step = "step_03_embed_nuggets"
    logbook.append(
        step, "starting",
        f"embedding {len(nuggets)} nuggets via POST oracle.linkright.in/lifeos/embed "
        "(nomic-embed-text, 768-dim); one request per nugget, sequential; "
        "expecting all to return 768-dim vectors",
    )

    out_path = ARTIFACTS / "03_nuggets_embedded.jsonl"
    success = 0
    failures: list[dict] = []
    sample_scores: list[dict] = []

    with out_path.open("w", encoding="utf-8") as f:
        for n in nuggets:
            ans = n.get("answer", "").strip()
            if not ans:
                failures.append({"id": n["id"], "reason": "empty answer"})
                continue
            emb, meta = embedder.embed(ans)
            if emb:
                n["emb"] = emb
                success += 1
            else:
                failures.append({"id": n["id"], "reason": meta.get("error", "unknown")})
            f.write(json.dumps({
                "id": n["id"],
                "company": n.get("company"),
                "answer": ans,
                "embedding_len": len(emb) if emb else 0,
                "meta": meta,
                "embedding_preview": emb[:5] if emb else None,
            }) + "\n")

    # Pairwise cosine on 5 sampled nuggets (if ≥ 5)
    embedded = [n for n in nuggets if n.get("emb")]
    if len(embedded) >= 5:
        import random
        random.seed(0)
        picks = random.sample(embedded, 5)
        for i, a in enumerate(picks):
            for b in picks[i+1:]:
                sim = cosine.cosine(a["emb"], b["emb"])
                sample_scores.append({
                    "a": a["answer"][:50],
                    "b": b["answer"][:50],
                    "cosine": round(sim, 3),
                })

    gaps: list[str] = []
    if failures:
        gaps.append(f"{len(failures)} embedding failures: {failures[:3]}")
    if embedded and any(len(n["emb"]) != 768 for n in embedded):
        gaps.append("some embeddings are not 768-dim")

    status = "pass" if not gaps else "partial"

    body_md = f"""**Artifact:** `artifacts/03_nuggets_embedded.jsonl` (one nugget per line with embedding)

**Metrics:**
- Embedded: {success}/{len(nuggets)}
- Failed: {len(failures)}
- Dimensions (sample): {embedded[0]['emb'].__len__() if embedded else 0}

**Pairwise cosine sample (5 random nuggets, C(5,2)=10 pairs):**
```
{chr(10).join(f"  {s['cosine']:.3f}  {s['a']} ↔ {s['b']}" for s in sample_scores)}
```

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}

**Root-cause hypothesis:**
{"Embeddings generated cleanly via Oracle /lifeos/embed. Pairwise scores should show semantic clustering — similar-domain nuggets (e.g., two AML nuggets) score higher than cross-domain (e.g., AML vs. education). If scores look flat (all ~0.4-0.6), nomic-embed-text is producing undifferentiated vectors for this domain — known nomic behavior; our 0.50 threshold was calibrated for this." if success > 0 else "Oracle endpoint unreachable or auth failed — blocker for steps 5, 6, 8."}
"""
    logbook.append(step, "eval", f"embed {status}; {success}/{len(nuggets)} ok; failures={len(failures)}", body_md)
    return nuggets


# ────────────────────────────────────────────────────────────────────────────
# Step 4 — REMOVED (S5-6 / F-NEW-1 codification, 2026-04-21)
#
# The separate JD-requirement extraction step was deleted in Sprint 5. Phase 1+2
# (step_07) already emits a JD-aware Credo-specific requirements[] field as part
# of its combined JSON output; that is now the SINGLE canonical source consumed
# by step_05/step_06.
#
# The production website still has its own /api/jd/analyze endpoint — that is a
# UI feature for JD-browser fit signals and keeps its own extraction prompt. The
# diagnostic pipeline should NOT mirror that; it mirrors the worker pipeline,
# which only ever used Phase 1+2's reqs.
# ────────────────────────────────────────────────────────────────────────────


# ────────────────────────────────────────────────────────────────────────────
# Step 5 — Embed JD requirements
# ────────────────────────────────────────────────────────────────────────────

def step_05_embed_reqs(reqs: list[dict]) -> list[dict]:
    step = "step_05_embed_reqs"
    logbook.append(
        step, "starting",
        f"embedding {len(reqs)} JD requirements via Oracle /lifeos/embed "
        "(nomic-embed-text, 768-dim); same model as nugget embeddings "
        "(CRITICAL: any divergence means cosine comparisons are meaningless)",
    )

    out_path = ARTIFACTS / "05_jd_req_embeddings.jsonl"
    success = 0
    with out_path.open("w", encoding="utf-8") as f:
        for r in reqs:
            emb, meta = embedder.embed(r.get("text", ""))
            if emb:
                r["emb"] = emb
                success += 1
            f.write(json.dumps({
                "id": r.get("id"),
                "text": r.get("text"),
                "embedding_len": len(emb) if emb else 0,
                "meta": meta,
            }) + "\n")

    gaps = []
    if success < len(reqs):
        gaps.append(f"only {success}/{len(reqs)} requirements embedded")

    status = "pass" if not gaps else "partial"
    body_md = f"""**Artifact:** `artifacts/05_jd_req_embeddings.jsonl`

**Metrics:**
- Embedded: {success}/{len(reqs)}
- Dim: {len(reqs[0].get('emb', [])) if reqs else 0}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}
"""
    logbook.append(step, "eval", f"req embed {status}; {success}/{len(reqs)}", body_md)
    return reqs


# ────────────────────────────────────────────────────────────────────────────
# Step 6 — Per-role relevance scoring (jd/analyze logic)
# ────────────────────────────────────────────────────────────────────────────

def step_06_role_scores(nuggets: list[dict], reqs: list[dict], experiences: list[dict], jd_text: str) -> dict:
    step = "step_06_role_scores"
    logbook.append(
        step, "starting",
        "replicating scoreRolesAgainstRequirements() from jd/analyze/route.ts; "
        "greedy bipartite matching with cosine threshold 0.50 (post-recalibration); "
        "years-of-experience hard check: Satvik ~4 yrs vs JD 5+ → '5+ years' req auto-gap",
    )

    threshold = float(os.environ.get("COSINE_THRESHOLD", "0.50"))

    # S5-4 / F-R1 fix: ROLE-MAP uses work_experience ONLY. Previously all nugget
    # types (skill, certification, independent_project, education) were keyed into
    # role_map; those with company=none/role=none aggregated into a pseudo-role
    # that beat real companies on avg_cos. Now skill/cert/project/education
    # nuggets only contribute to the coverage set (Pass B below), not role
    # ranking.
    role_map: dict[tuple[str, str], list[dict]] = {}
    for n in nuggets:
        ntype = (n.get("type") or "work_experience").lower()
        if ntype != "work_experience":
            continue  # S5-4: only work_experience creates role entries
        c = (n.get("company") or "").strip()
        r = (n.get("role") or "").strip()
        if not c or c.lower() in ("none", "null", ""):
            continue
        role_map.setdefault((c, r), []).append(n)
    # Add roles from work_history with no nuggets
    for exp in experiences:
        key = (exp.get("company", ""), exp.get("role", ""))
        if key[0]:
            role_map.setdefault(key, [])

    req_embs = [r.get("emb") for r in reqs]
    role_scores = []
    for (co, ro), role_nuggets in role_map.items():
        nugs_with_emb = [{"id": n["id"], "emb": n.get("emb"), "text": n.get("answer", "")} for n in role_nuggets if n.get("emb")]
        matches, best_per_req = cosine.greedy_bipartite_match(req_embs, nugs_with_emb, threshold)
        covers = [reqs[m["req_idx"]]["id"] for m in matches]
        # avg best-cosine across all requirements (incl. below-threshold)
        avg_cos = sum(best_per_req.values()) / len(best_per_req) if best_per_req else 0.0
        # S5-2: aggregate leadership signal for relevance formula
        leadership_values = {"none": 0, "individual": 1, "team_lead": 2}
        lead_max = max(
            [leadership_values.get((n.get("leadership") or "none").lower(), 0) for n in role_nuggets] or [0]
        )
        role_scores.append({
            "company": co,
            "role": ro,
            "nugget_count": len(role_nuggets),
            "matches": matches,
            "covers": covers,
            "avg_best_cosine": round(avg_cos, 4),
            "best_per_req": {reqs[i]["id"]: round(v, 4) for i, v in best_per_req.items()},
            "leadership_max": lead_max,  # S5-2: 0=none, 1=individual, 2=team_lead
        })

    role_scores.sort(key=lambda x: x["avg_best_cosine"], reverse=True)
    for i, rs in enumerate(role_scores):
        rs["classification"] = "primary" if i == 0 else ("secondary" if i == 1 else "tertiary")

    # Years-of-experience hard check
    def parse_required_years(jd: str) -> int | None:
        patterns = [
            r"(\d+)\+\s*years?\b",
            r"(\d+)\s*[-–]\s*\d+\s*years?\b",
            r"minimum\s*(?:of\s*)?(\d+)\s*years?\b",
            r"at\s*least\s*(\d+)\s*years?\b",
        ]
        candidates = []
        for p in patterns:
            for m in re.finditer(p, jd, re.IGNORECASE):
                n = int(m.group(1))
                if 0 < n < 30:
                    candidates.append(n)
        return min(candidates) if candidates else None

    # Cumulative years from experiences (start_date → now)
    from datetime import datetime
    now = datetime.utcnow()
    earliest = now
    for e in experiences:
        sd = e.get("start_date", "")
        # Try "Apr 2022" / "2022-04" / "Jul 2024"
        for fmt in ("%b %Y", "%B %Y", "%Y-%m", "%m/%Y"):
            try:
                dt = datetime.strptime(sd, fmt)
                if dt < earliest:
                    earliest = dt
                break
            except Exception:
                continue
    user_years = round((now - earliest).days / 365.25, 1) if earliest != now else 0
    required_years = parse_required_years(jd_text)

    covered_reqs: set[str] = set()
    for rs in role_scores:
        for rid in rs["covers"]:
            covered_reqs.add(rid)

    # S5-4 / F-R1 fix Pass B: non-work_experience nuggets (skills, certs,
    # independent_projects, education) ALSO contribute to coverage % — but they
    # didn't participate in role ranking above. Compute their matches against
    # the JD requirements separately and union into covered_reqs.
    non_work_nuggets = [
        {"id": n["id"], "emb": n.get("emb"), "text": n.get("answer", "")}
        for n in nuggets
        if (n.get("type") or "work_experience").lower() != "work_experience"
        and n.get("emb")
    ]
    if non_work_nuggets:
        nw_matches, _ = cosine.greedy_bipartite_match(req_embs, non_work_nuggets, threshold)
        for m in nw_matches:
            covered_reqs.add(reqs[m["req_idx"]]["id"])

    # Revoke "N+ years" coverage if user_years < required_years
    years_revoked: list[str] = []
    # G2/F08: always compute matching req IDs (even when not revoking) so the log
    # line below is observable regardless of action. Mirrors prod /api/jd/analyze.
    _year_req_ids = [
        r["id"] for r in reqs
        if re.search(r"(\d+)\s*[+\-–]\s*(?:to\s*\d+\s*)?years?|(\d+)\s*years?\b", r.get("text", ""), re.IGNORECASE)
    ]
    if required_years and user_years < required_years:
        for r in reqs:
            if re.search(r"(\d+)\s*[+\-–]\s*(?:to\s*\d+\s*)?years?|(\d+)\s*years?\b", r.get("text", ""), re.IGNORECASE):
                if r["id"] in covered_reqs:
                    covered_reqs.discard(r["id"])
                    years_revoked.append(r["id"])
                for rs in role_scores:
                    if r["id"] in rs["covers"]:
                        rs["covers"].remove(r["id"])
    _year_action = (
        "revoked" if years_revoked
        else ("no-op" if (required_years and user_years < required_years) else "not-applicable")
    )
    log(
        f"[step_06 G2] years_check: required_years_in_jd={required_years}, "
        f"user_years={user_years}, matching_req_ids={_year_req_ids}, "
        f"revoked_ids={years_revoked}, action={_year_action}"
    )

    gaps_list = [{"req_id": r["id"], "text": r.get("text", ""), "importance": r.get("importance", "")} for r in reqs if r["id"] not in covered_reqs]
    coverage_pct = round(100 * len(covered_reqs) / len(reqs), 1) if reqs else 0

    result = {
        "threshold_used": threshold,
        "user_years": user_years,
        "required_years": required_years,
        "years_revoked_req_ids": years_revoked,
        "role_scores": role_scores,
        "covered_reqs": sorted(covered_reqs),
        "gaps": gaps_list,
        "coverage_pct": coverage_pct,
    }
    out_path = ARTIFACTS / "06_role_scores.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # Evaluate
    primary = role_scores[0]["company"] if role_scores else "(none)"
    gaps_detected: list[str] = []
    if role_scores and "american express" not in primary.lower() and "amex" not in primary.lower():
        gaps_detected.append(f"primary role is '{primary}', expected 'American Express'")
    if coverage_pct == 0:
        gaps_detected.append("coverage 0% — threshold too strict OR embeddings broken OR matcher bug")
    if coverage_pct == 100:
        gaps_detected.append("coverage 100% — threshold too loose; everything matches")
    if required_years and not years_revoked:
        gaps_detected.append(f"years check failed to fire (required {required_years}, user {user_years})")
    if coverage_pct > 0 and coverage_pct < 100 and not years_revoked and required_years and user_years < required_years:
        gaps_detected.append("coverage is honest BUT years-check failed to revoke — likely regex didn't match req text")

    status = "pass" if not gaps_detected else "partial"

    top_matches_str = "\n".join(
        f"  {m['cosine']:.3f}  req={m['req_idx']}  ↔  {m['nugget_text'][:60]}"
        for rs in role_scores[:1] for m in rs["matches"][:5]
    )
    body_md = f"""**Artifact:** `artifacts/06_role_scores.json`

**Metrics:**
- Threshold used: {threshold}
- User cumulative years: {user_years}
- JD required years: {required_years}
- Primary role: **{primary}** ({role_scores[0].get('avg_best_cosine', 0) if role_scores else 0})
- Coverage %: **{coverage_pct}%** ({len(covered_reqs)}/{len(reqs)} reqs covered)
- Years-check revoked: {years_revoked}
- Open gaps (uncovered reqs): {len(gaps_list)}

**Top matches for primary role ({primary}):**
```
{top_matches_str if top_matches_str else '(no matches)'}
```

**Role classifications:**
{chr(10).join(f"- {rs['classification']}: {rs['company']} ({rs['role']}) — avg_cos={rs['avg_best_cosine']}, covers={len(rs['covers'])}" for rs in role_scores)}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps_detected) if gaps_detected else '- none'}

**Root-cause hypothesis:**
{"Scoring is producing honest, non-theatrical matches." if not gaps_detected else "If coverage 0% despite Step 3 showing healthy pairwise scores: either req-nugget pairs live in unrelated semantic neighborhoods (consider whether requirements are phrased too generically for Satvik's domain-specific nuggets), or threshold 0.50 still too strict for nomic. If primary ≠ Amex: Amex nuggets may be fewer (check Step 2 distribution) or their vector similarity to JD-domain reqs (platform/RBAC/multi-tenancy) is lower than Sprinklr's (more CX/SaaS-flavored nuggets score better against 'dashboards', 'collaboration')."}
"""
    logbook.append(step, "eval", f"role scoring {status}; coverage {coverage_pct}%; primary={primary}", body_md)
    return result


# ────────────────────────────────────────────────────────────────────────────
# Step 7 — Phase 1+2: JD parse + strategy + colors + bullet budget
# ────────────────────────────────────────────────────────────────────────────

TEMPLATE_PATH = ROOT / "templates" / "cv-a4-mid-career.html"


def step_07_phase_1_2(jd_text: str, raw_text: str) -> dict:
    step = "step_07_phase_1_2"
    logbook.append(
        step, "starting",
        "calling LLM with PHASE_1_2 prompt; returns career_level, jd_keywords, "
        "strategy, theme_colors, section_order, bullet_budget; expecting "
        "career_level=mid (Satvik has ~4 yrs) and bullet_budget totaling 12-15",
    )

    strategies_json = P.STRATEGIES_JSON  # vendored
    system = P.PHASE_1_2_SYSTEM.replace("{strategies_json}", strategies_json)
    user = llm.subst(P.PHASE_1_2_USER, jd_text=jd_text, career_text=raw_text, qa_context="")

    def _call_phase_1_2(extra_retry_note: str = "") -> tuple[dict, dict]:
        user_msg = user + (f"\n\n{extra_retry_note}" if extra_retry_note else "")
        text, usage = llm.chat_with_fallback(system=system, user=user_msg, temperature=0.3, max_tokens=4000)
        log(f"=== step_07 {usage.get('provider')} raw ===\n{text}\n=== end ===\n")
        # Iter-04 (2026-04-23): strip LLM commentary BEFORE JSON extraction.
        text = _strip_commentary(text)
        parsed = json.loads(llm.extract_json(text))
        return parsed, usage

    try:
        parsed, usage = _call_phase_1_2()
    except llm.LLMError as e:
        logbook.append(step, "error", "Phase 1+2 LLM failed — synthesis fallback", body=f"```\n{e}\n```")
        log(f"[step_07] ALL LLMs failed — building minimal JD analysis from text heuristics")
        _note_retry("step_07_synthesis_fallback")
        # Iter-09: synthesis fallback — extract JD keywords via regex, use defaults
        import re as _re07
        kw_candidates = _re07.findall(r'\b[A-Za-z][a-zA-Z]{3,}\b', jd_text or "")
        kw_freq: dict[str, int] = {}
        for kw in kw_candidates:
            kw_lower = kw.lower()
            if kw_lower not in {"with", "that", "this", "from", "have", "will", "been", "your", "their", "team"}:
                kw_freq[kw_lower] = kw_freq.get(kw_lower, 0) + 1
        top_kws = [k for k, _ in sorted(kw_freq.items(), key=lambda x: -x[1])[:15]]
        parsed = {
            "career_level": "mid",
            "strategy": "BALANCED",
            "jd_keywords": top_kws,
            "theme_colors": {"primary": "#2D4A5C", "accent": "#4A90D9"},
            "section_order": ["summary", "experience", "skills", "education"],
            "bullet_budget": {"company_1_total": 5, "company_2_total": 5},
            "companies": [],  # will be populated by caller from parsed resume
            "requirements": [{"id": f"req_{i}", "text": kw, "type": "skill"} for i, kw in enumerate(top_kws[:8])],
            "resume_strategy": {"company_distribution": {"included_companies": []}},
            "_synthesis_fallback": True,
        }
        usage = {"provider": "synthesis_fallback", "prompt_tokens": 0, "completion_tokens": 0}
    except json.JSONDecodeError as e:
        logbook.append(step, "error", f"JSON parse failed: {e}")
        raise

    # S5-5 / F-R2: B1 career_level consistency check with retry + deterministic
    # override. If LLM's career_level disagrees with rule-computed bucket, retry
    # ONCE with violation highlighted. If still wrong, OVERRIDE the field with
    # the correct bucket (LLM never overrules deterministic computation).
    total_years = _compute_total_experience_years(parsed.get("companies", []))

    def _bucket_from_years(y: float) -> str:
        if y == 0:
            return "fresher"
        if y <= 2.5:  # boundary 2 with tolerance
            return "entry"
        if y <= 5.5:
            return "mid"
        if y <= 9.5:
            return "senior"
        return "executive"

    def _level_violates(level: str, years: float) -> bool:
        lv = (level or "").strip().lower()
        if lv not in _CAREER_LEVEL_MIN_YEARS:
            return True  # unknown level is a violation
        return years + 1.0 < _CAREER_LEVEL_MIN_YEARS[lv]

    retry_fired = False
    override_applied = False
    if total_years > 0 and _level_violates(parsed.get("career_level"), total_years):
        expected = _bucket_from_years(total_years)
        retry_note = (
            f"RETRY NOTE: your previous response claimed career_level='{parsed.get('career_level')}' "
            f"but the candidate has only {total_years:.1f} years of work experience. "
            f"The correct bucket per the Parsing Rules is '{expected}'. Emit exactly that. "
            f"Keep every other field the same."
        )
        logbook.append(
            step, "eval",
            f"B1 violation detected: career_level='{parsed.get('career_level')}' vs {total_years:.1f}y; retrying once",
        )
        _note_retry(step)
        retry_fired = True
        try:
            parsed_retry, usage_retry = _call_phase_1_2(extra_retry_note=retry_note)
            usage = usage_retry  # use retry provenance
            if not _level_violates(parsed_retry.get("career_level"), total_years):
                parsed = parsed_retry
            else:
                # Deterministic override — LLM stubborn; force the correct bucket.
                parsed = parsed_retry
                logbook.append(
                    step, "eval",
                    f"B1 override: LLM insisted on career_level='{parsed.get('career_level')}' after retry; forcing '{expected}' based on {total_years:.1f}y",
                )
                parsed["career_level"] = expected
                override_applied = True
        except Exception as e:
            # Retry LLM failed; override directly on the original parsed dict.
            logbook.append(step, "eval", f"B1 retry call failed ({e}); applying deterministic override")
            parsed["career_level"] = expected
            override_applied = True

    # S5-1: derive profile from (now-validated) career_level deterministically.
    parsed["profile"] = _derive_profile(parsed.get("career_level", "mid"))

    # Iter-08 (2026-04-23): requirements hard-floor — retry once if <5 extracted.
    # RCA showed 1/32 runs had only 4 reqs; scorecard expects ≥5.
    reqs = parsed.get("requirements", [])
    if len(reqs) < 5:
        _note_retry("step_07_low_reqs_retry")
        log(f"[step_07 low_reqs retry] only {len(reqs)} requirements; retrying with explicit 'at least 6' instruction")
        retry_msg = (
            f"\n\nRETRY: your previous response extracted only {len(reqs)} requirements. "
            "Extract AT LEAST 6-8 distinct requirements from the JD. Include hard skills, "
            "soft skills, experience markers, and domain knowledge. Re-emit full JSON."
        )
        try:
            parsed_r, _usage_r = _call_phase_1_2(extra_retry_note=retry_msg)
            new_reqs = parsed_r.get("requirements", [])
            if len(new_reqs) > len(reqs):
                log(f"[step_07 low_reqs retry] lifted {len(reqs)} → {len(new_reqs)} reqs; using retry")
                parsed = parsed_r
                parsed["profile"] = _derive_profile(parsed.get("career_level", "mid"))
        except Exception as exc:
            log(f"[step_07 low_reqs retry] failed ({exc}); keeping original")

    out_path = ARTIFACTS / "07_jd_parse_strategy.json"
    out_path.write_text(
        json.dumps({
            "parsed": parsed,
            "usage": usage,
            "b1_retry_fired": retry_fired,
            "b1_override_applied": override_applied,
        }, indent=2),
        encoding="utf-8",
    )

    kw = parsed.get("jd_keywords", [])
    bb = parsed.get("bullet_budget", {})
    kw_lower = [k.lower() for k in kw]
    platform_signals = ["platform", "multi-tenan", "sso", "scim", "rbac", "identity", "dashboard"]
    platform_hits = [s for s in platform_signals if any(s in k for k in kw_lower)]

    # Post-retry/override, re-check violation (should be False now)
    level = (parsed.get("career_level") or "").strip().lower()
    career_level_violation = _level_violates(parsed.get("career_level"), total_years) if total_years > 0 else False

    # B2/F01: scan career_summary for hallucinated years claims.
    career_summary = parsed.get("career_summary") or ""
    summary_violation: Optional[str] = None
    if career_summary and total_years > 0:
        for mm in re.finditer(r"\b(\d+)\+?\s*years?\b", career_summary, flags=re.IGNORECASE):
            if int(mm.group(1)) > total_years + 1.0:
                summary_violation = mm.group(0)
                break

    gaps: list[str] = []
    if career_level_violation:
        gaps.append(
            f"B1/F02: career_level='{level}' requires ≥{_CAREER_LEVEL_MIN_YEARS[level]}y "
            f"but candidate has {total_years}y (+1 tolerance) — prompt/LLM inflated the level"
        )
    elif parsed.get("career_level") not in ("mid", "senior"):
        gaps.append(f"career_level={parsed.get('career_level')} — expected 'mid' for ~4 yrs")
    if summary_violation:
        gaps.append(
            f"B2/F01: career_summary claims '{summary_violation}' but candidate has "
            f"{total_years}y total — hallucinated years claim"
        )
    if not (18 <= len(kw) <= 25):
        gaps.append(f"jd_keywords count={len(kw)} — expected 18-25 (prompt updated post-G3)")
    if len(platform_hits) < 3:
        gaps.append(f"jd_keywords missing platform signals (hit {len(platform_hits)}/{len(platform_signals)})")
    total_bullets = sum(v for k, v in bb.items() if isinstance(v, int))
    if not (10 <= total_bullets <= 18):
        gaps.append(f"bullet_budget total={total_bullets} — expected 12-15")

    status = "pass" if not gaps else "partial"
    body_md = f"""**Artifact:** `artifacts/07_jd_parse_strategy.json`
**Provider:** {usage.get('provider')}  **fallback_used:** {usage.get('fallback_used')}

**Key outputs:**
- career_level: **{parsed.get('career_level')}**  (candidate total_years: {total_years:.1f})
- target_role: {parsed.get('target_role')}
- strategy: **{parsed.get('strategy')}** — {parsed.get('strategy_reason', '')}
- jd_keywords ({len(kw)}): {kw[:12]}…
- Platform signals hit: {platform_hits}
- bullet_budget: {bb} (total={total_bullets})
- section_order: {parsed.get('section_order')}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}

**Root-cause hypothesis:**
{"Phase 1+2 output reasonable." if not gaps else "Post-iteration-1, B1/B2 validators now catch career_level and career_summary hallucinations. G3 tightened keyword count target to 18-25. If gaps persist, re-prompt logic may need one more pass; see vision.md iteration_1_fix_log."}
"""
    logbook.append(step, "eval", f"phase_1_2 {status}; career_level={parsed.get('career_level')}; keywords={len(kw)}", body_md)
    return parsed


# ────────────────────────────────────────────────────────────────────────────
# Step 8 — Per-company nugget retrieval (in-memory cosine)
# ────────────────────────────────────────────────────────────────────────────

def step_08_retrieve_per_company(parsed_p12: dict, nuggets: list[dict]) -> dict:
    step = "step_08_retrieve_per_company"
    logbook.append(
        step, "starting",
        "for each company from Phase 1+2, build query = 'company + top-5 jd_keywords', "
        "embed via Oracle, cosine against all same-company nuggets, filter ≥0.50, top 8. "
        "Replaces Supabase hybrid_retrieve for local diagnostic.",
    )

    companies = parsed_p12.get("companies", [])
    jd_keywords = parsed_p12.get("jd_keywords", [])[:5]
    threshold = float(os.environ.get("COSINE_THRESHOLD", "0.50"))

    # Group nuggets by company (normalize whitespace, also strip " (Freelance)" etc.)
    def norm(s: str) -> str:
        s = re.sub(r"\s+", " ", (s or "").strip()).lower()
        s = re.sub(r"\s*\(.*?\)\s*$", "", s)
        # Iter-04: also strip common legal suffixes (Inc, Ltd, LLC, Corp) so
        # "American Express Inc" and "American Express" collapse to one key.
        s = re.sub(r"[\s,]+(inc\.?|ltd\.?|llc\.?|corp\.?|corporation|limited|co\.?)\s*$", "", s)
        return s

    by_co: dict[str, list[dict]] = {}
    for n in nuggets:
        if n.get("emb"):
            by_co.setdefault(norm(n.get("company", "")), []).append(n)
    # Iter-04 (2026-04-23): loud diagnostic when pool grouping runs. Helps RCA
    # cases where step_08 returns 0 despite step_03 reporting N/N embedding success.
    log(f"[step_08] by_co grouping: {dict((k, len(v)) for k, v in by_co.items())}")
    log(f"[step_08] companies from step_07: {[c.get('name') for c in companies]}")

    retrieved_per_co: dict[str, list[dict]] = {}
    # Iter-04: looser cosine threshold (0.35 vs 0.50). Combined with the reranker
    # reordering the surviving candidates, net precision stays similar but recall
    # improves dramatically — we catch semantically-close matches that the
    # nomic-embed-text model under-scores (known to cluster scores around 0.4-0.6).
    threshold_loose = float(os.environ.get("COSINE_THRESHOLD_LOOSE", "0.35"))
    for co in companies:
        co_name = co.get("name", "")
        query = f"{co_name} {' '.join(jd_keywords)}"
        q_emb, meta = embedder.embed(query)
        if not q_emb:
            # retry once — Oracle VPS sometimes needs a warm-up call
            import time as _time08; _time08.sleep(1)
            q_emb, meta = embedder.embed(query)
        if not q_emb:
            log(f"[step_08] {co_name}: query embed failed (meta={meta}) — skipping")
            retrieved_per_co[co_name] = []
            continue
        pool = by_co.get(norm(co_name), [])
        # Iter-04: if direct normalization miss, try substring matching as safety net.
        # Handles cases where nugget's company field is "American Express US" but step_07
        # says "American Express" (or vice versa).
        if not pool:
            co_norm = norm(co_name)
            for key, val in by_co.items():
                if co_norm in key or key in co_norm:
                    pool = val
                    log(f"[step_08] {co_name}: direct miss but substring-matched key='{key}' ({len(pool)} nuggets)")
                    break
        # Score ALL nuggets first, filter later — lets us fall back to "best available"
        # for tail companies whose similarity is uniformly below threshold.
        all_scored = []
        for n in pool:
            sim = cosine.cosine(q_emb, n["emb"])
            all_scored.append({"id": n["id"], "cosine": round(sim, 4), "answer": n.get("answer", "")})
        all_scored.sort(key=lambda x: x["cosine"], reverse=True)

        above_threshold = [s for s in all_scored if s["cosine"] >= threshold]
        above_loose = [s for s in all_scored if s["cosine"] >= threshold_loose]
        # Iter-07 (2026-04-23): HARD-FLOOR ≥3 nuggets per included company.
        # Scorecard RCA showed 18/32 runs had "low min: 1-2 nuggets in smallest company" —
        # that cascades to step_10 empty → step_11/12/13 empty. Guarantee min_floor always.
        MIN_NUGGETS_PER_COMPANY = 3
        if above_threshold and len(above_threshold) >= MIN_NUGGETS_PER_COMPANY:
            retrieved_per_co[co_name] = above_threshold[:8]
            log(f"[step_08] {co_name}: {len(above_threshold)} strict matches (top cosine {above_threshold[0]['cosine']})")
        elif above_loose and len(above_loose) >= MIN_NUGGETS_PER_COMPANY:
            for s in above_loose[:5]:
                s["fallback"] = "loose_threshold"
            retrieved_per_co[co_name] = above_loose[:5]
            log(f"[step_08] {co_name}: {len(above_loose[:5])} LOOSE matches (top cosine {above_loose[0]['cosine']})")
        elif all_scored and len(all_scored) >= MIN_NUGGETS_PER_COMPANY:
            # Iter-07 guarantee: pool has enough nuggets — take top 3 regardless of cosine.
            for s in all_scored[:MIN_NUGGETS_PER_COMPANY]:
                s["fallback"] = "hard_floor_top3"
            retrieved_per_co[co_name] = all_scored[:max(MIN_NUGGETS_PER_COMPANY, 3)]
            log(f"[step_08] {co_name}: HARD-FLOOR top-{len(retrieved_per_co[co_name])} (cosines below thresholds; pool had {len(all_scored)})")
        elif all_scored:
            # Pool smaller than MIN_NUGGETS — take everything available (rare).
            for s in all_scored:
                s["fallback"] = "hard_floor_all_available"
            retrieved_per_co[co_name] = all_scored
            log(f"[step_08] {co_name}: HARD-FLOOR all-available ({len(all_scored)} < min {MIN_NUGGETS_PER_COMPANY})")
        else:
            # Pool truly empty — step_03 likely failed to embed this company's nuggets.
            log(f"[step_08] {co_name}: 0 nuggets — pool was empty. Check step_03 emb population + norm() keys.")
            retrieved_per_co[co_name] = []

        # Iter-03 G1 (2026-04-23): cross-encoder rerank via Oracle /lifeos/rerank
        # (bge-reranker-v2-m3, sentence-transformers on VPS). Gated by ENABLE_RERANKER.
        # Takes top candidates from cosine retrieval, reranks semantically. Improves
        # precision on tail companies where cosine ranking is noisy.
        if (os.environ.get("ENABLE_RERANKER", "").lower() in ("1", "true", "yes")
            and retrieved_per_co[co_name]):
            try:
                import httpx as _httpx
                docs_to_rerank = [s.get("answer", "") for s in retrieved_per_co[co_name]]
                r_resp = _httpx.post(
                    f"{os.environ.get('ORACLE_BACKEND_URL','').rstrip('/')}/lifeos/rerank",
                    headers={
                        "Authorization": f"Bearer {os.environ.get('ORACLE_BACKEND_SECRET','')}",
                        "Content-Type": "application/json",
                    },
                    json={"query": query, "documents": docs_to_rerank, "top_k": len(docs_to_rerank)},
                    timeout=60.0,
                )
                if r_resp.status_code == 200:
                    ranked = r_resp.json().get("ranked") or []
                    if ranked:
                        # Reorder retrieved_per_co[co_name] by reranker indices
                        idx_order = [int(r["index"]) for r in ranked]
                        src = retrieved_per_co[co_name]
                        reranked = []
                        for new_idx, r in zip(idx_order, ranked):
                            if 0 <= new_idx < len(src):
                                item = dict(src[new_idx])
                                item["rerank_score"] = float(r.get("score", 0))
                                reranked.append(item)
                        if reranked:
                            retrieved_per_co[co_name] = reranked
                            log(f"[step_08 rerank] {co_name}: reordered {len(reranked)} nuggets")
            except Exception as exc:
                log(f"[step_08 rerank] {co_name}: rerank skipped ({exc})")

    out_path = ARTIFACTS / "08_relevant_nuggets_per_company.json"
    out_path.write_text(json.dumps({
        "threshold": threshold,
        "jd_keywords_used": jd_keywords,
        "retrieved": retrieved_per_co,
    }, indent=2), encoding="utf-8")

    gaps: list[str] = []
    for co_name, nugs in retrieved_per_co.items():
        if not nugs:
            gaps.append(f"0 nuggets retrieved for {co_name} — retrieval failure or no nuggets tagged to this company")

    status = "pass" if not gaps else "partial"
    summary = "\n".join(f"- **{c}**: {len(n)} nuggets (top cosine: {n[0]['cosine'] if n else 'n/a'})" for c, n in retrieved_per_co.items())
    body_md = f"""**Artifact:** `artifacts/08_relevant_nuggets_per_company.json`

**Per-company retrieval:**
{summary}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}
"""
    logbook.append(step, "eval", f"retrieval {status}; companies={len(retrieved_per_co)}; gaps={len(gaps)}", body_md)
    return retrieved_per_co


# ────────────────────────────────────────────────────────────────────────────
# Step 9 — Professional summary (Phase 3.5a)
# ────────────────────────────────────────────────────────────────────────────

def step_09_summary(parsed_p12: dict, retrieved: dict, raw_text: str) -> str:
    step = "step_09_summary"
    logbook.append(
        step, "starting",
        "calling LLM with PROFESSIONAL_SUMMARY prompt; 2-3 sentences, 150-250 chars, "
        "should foreground platform/enterprise experience and the 1-2 strongest matches",
    )

    # Pull sample bullets from retrieved nuggets
    bullet_lines = []
    for co, nugs in retrieved.items():
        for n in nugs[:3]:
            bullet_lines.append(f"- {n['answer']}")
    bullets_text = "\n".join(bullet_lines[:10]) or "(no retrieved nuggets)"

    # B2/F01: compute total work years to feed the grounding constraint.
    user_total_years = _compute_total_experience_years(parsed_p12.get("companies", []))

    def _build_user_msg() -> str:
        return llm.subst(
            P.PROFESSIONAL_SUMMARY_USER,
            target_role=parsed_p12.get("target_role", ""),
            target_company=parsed_p12.get("company_name", ""),
            jd_keywords=", ".join(parsed_p12.get("jd_keywords", [])[:10]),
            career_level=parsed_p12.get("career_level", ""),
            user_total_years=f"{user_total_years:.1f}",
            user_total_years_plus_one=f"{user_total_years + 1.0:.0f}",
            companies=", ".join(c.get("name", "") for c in parsed_p12.get("companies", [])[:3]),
            resume_bullets_text=bullets_text,
        )

    system = P.PROFESSIONAL_SUMMARY_SYSTEM
    user = _build_user_msg()
    step09_llm_failed = False
    try:
        text, usage = llm.chat_with_fallback(system=system, user=user, temperature=0.3, max_tokens=500)
    except llm.LLMError as e:
        logbook.append(step, "error", "Summary LLM failed — using synthesis fallback", body=f"```\n{e}\n```")
        _note_retry("step_09_synthesis_fallback")
        step09_llm_failed = True
        text, usage = "", {}

    if step09_llm_failed:
        companies_str = ", ".join(c.get("name", "") for c in parsed_p12.get("companies", [])[:2])
        role = parsed_p12.get("target_role", "Product Manager")
        kws = ", ".join(parsed_p12.get("jd_keywords", [])[:4])
        summary = (
            f"Product leader with {user_total_years:.0f}+ years of experience at {companies_str}, "
            f"specializing in {kws}. Proven track record driving cross-functional initiatives "
            f"and delivering measurable business outcomes as a {role}."
        )[:300]
        (ARTIFACTS / "09_professional_summary.html").write_text(
            f"<div class='summary-line'>{summary}</div>\n", encoding="utf-8"
        )
        logbook.append(step, "pass", f"synthesis fallback summary written ({len(summary)} chars)")
        return summary
    try:
        parsed = json.loads(llm.extract_json(text))
        summary = parsed.get("summary_text", "").strip()
    except json.JSONDecodeError:
        summary = text.strip()

    # Iter-08 (2026-04-23): hard-truncate summary to ≤300 chars at sentence boundary.
    # RCA showed 11/32 runs had summary >300 chars. Prompt says "100-300" but LLM ignores.
    # Deterministic truncate at last '. ' before 280; append period if needed.
    if len(summary) > 300:
        orig_len = len(summary)
        truncate_point = summary.rfind(". ", 0, 281)
        if truncate_point > 100:
            summary = summary[:truncate_point + 1].strip()
        else:
            # No sentence boundary found — cut at word before 290 and add period
            truncate_point = summary.rfind(" ", 0, 290)
            if truncate_point > 100:
                summary = summary[:truncate_point].rstrip(",;:") + "."
            else:
                summary = summary[:290].rstrip() + "..."
        log(f"[step_09 length_enforce] truncated summary {orig_len}→{len(summary)} chars")

    # B2/F01: regex validator for years-claim hallucination. If violated, re-prompt once.
    def _years_violation(s: str) -> Optional[str]:
        if user_total_years <= 0:
            return None
        for mm in re.finditer(r"\b(\d+)\+?\s*years?\b", s, flags=re.IGNORECASE):
            if int(mm.group(1)) > user_total_years + 1.0:
                return mm.group(0)
        return None

    violation = _years_violation(summary)
    if violation:
        _note_retry(step)
        logbook.append(
            step, "eval",
            f"B2/F01 violation detected: '{violation}' exceeds user_total_years={user_total_years:.1f}+1; re-prompting once",
        )
        user_retry = _build_user_msg() + (
            f"\n\nRETRY: your previous response claimed '{violation}' which exceeds the "
            f"candidate's actual {user_total_years:.1f} years. Remove/correct this claim."
        )
        try:
            text2, usage2 = llm.chat_with_fallback(system=system, user=user_retry, temperature=0.3, max_tokens=500)
            try:
                parsed2 = json.loads(llm.extract_json(text2))
                retry_summary = parsed2.get("summary_text", "").strip()
            except json.JSONDecodeError:
                retry_summary = text2.strip()
            if not _years_violation(retry_summary):
                summary = retry_summary  # accept corrected output
        except llm.LLMError:
            pass  # keep original; final gap report will flag

    (ARTIFACTS / "09_professional_summary.html").write_text(
        f"<div class='summary-line'>{summary}</div>\n", encoding="utf-8"
    )

    # Evaluate
    length = len(summary)
    gaps: list[str] = []
    if not (100 <= length <= 300):
        gaps.append(f"summary length {length} outside 100-300 range")
    hedging = ["aspiring", "eager to learn", "passionate", "dedicated", "driven by"]
    hits = [h for h in hedging if h in summary.lower()]
    if hits:
        gaps.append(f"hedging/filler language detected: {hits}")
    platform_ref = any(w in summary.lower() for w in ["platform", "enterprise", "infrastructure", "multi-tenan", "scale"])
    if not platform_ref:
        gaps.append("summary doesn't reference platform/enterprise themes — key JD emphasis missing")

    status = "pass" if not gaps else "partial"
    body_md = f"""**Artifact:** `artifacts/09_professional_summary.html`

**Summary ({length} chars):**
> {summary}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}
"""
    logbook.append(step, "eval", f"summary {status}; {length} chars; gaps={len(gaps)}", body_md)
    return summary


# ────────────────────────────────────────────────────────────────────────────
# Step 10 — Verbose bullets per company (Phase 4a)
# ────────────────────────────────────────────────────────────────────────────

def step_10_verbose_bullets(parsed_p12: dict, retrieved: dict, reqs: list[dict]) -> dict:
    step = "step_10_verbose_bullets"
    logbook.append(
        step, "starting",
        "calling LLM per-company with PHASE_4A_VERBOSE prompts; each paragraph must "
        "cite evidence_atom_ids; filter hallucinations + non-proof + banned phrases; "
        "apply minimum-floor (top-2 rescue) when all bullets drop",
    )

    strategy = parsed_p12.get("strategy", "BALANCED")
    strategy_desc = {
        "METRIC_BOMBARDMENT": "Maximize quantified metrics.",
        "SKILL_MATCHING": "Every required skill in a bullet's context.",
        "LEADERSHIP_NARRATIVE": "Foreground team-leading and scope.",
        "TRANSFORMATION_STORY": "Emphasize before/after changes.",
        "BALANCED": "Mix metrics, skills, and leadership.",
    }.get(strategy, "Balanced emphasis.")
    career_level = parsed_p12.get("career_level", "mid")
    jd_keywords_compact = ", ".join(parsed_p12.get("jd_keywords", [])[:15])
    jd_requirements_list = "\n".join(f"{r['id']}: {r.get('text','')}" for r in reqs)

    verbose_all: dict[str, dict] = {}
    used_verbs: list[str] = []
    dropped_stats = {}

    # S5-7: token-conservative — iterate only companies that resume_strategy
    # selected for rendering. Excluded companies (by dynamic floor or top-N cap)
    # skip LLM calls entirely, saving ~2,500 tokens per dropped company.
    strategy = parsed_p12.get("resume_strategy") or {}
    included = strategy.get("included_companies")
    if included:
        included_names = {c["company"] for c in included}
        companies_to_process = [c for c in parsed_p12.get("companies", []) if c.get("name", "") in included_names]
        skipped = [c.get("name", "") for c in parsed_p12.get("companies", []) if c.get("name", "") not in included_names]
        if skipped:
            log(f"[step_10 S5-7] skipping excluded companies: {skipped}")
    else:
        # Fallback: no strategy (pre-S5-2 runs) → iterate all companies
        companies_to_process = parsed_p12.get("companies", [])
        skipped = []

    for co in companies_to_process:
        co_name = co.get("name", "")
        retrieved_nugs = retrieved.get(co_name, [])
        if not retrieved_nugs:
            verbose_all[co_name] = {"paragraphs": [], "dropped": [], "note": "no retrieved nuggets"}
            continue

        # Build atom pool with [atom:ID] prefix — matches production format
        company_chunks = "\n".join(
            f"[atom:{n['id']}] {n['answer']}" for n in retrieved_nugs
        )
        valid_atom_ids = {n["id"] for n in retrieved_nugs}

        bullet_count = 5

        sys = llm.subst(
            P.PHASE_4A_VERBOSE_SYSTEM,
            bullet_count=bullet_count,
            used_verbs=", ".join(used_verbs),
            strategy=strategy,
            strategy_description=strategy_desc,
            career_level=career_level,
        )
        usr = llm.subst(
            P.PHASE_4A_VERBOSE_USER,
            jd_keywords_compact=jd_keywords_compact,
            jd_requirements_list=jd_requirements_list,
            company_name=co_name,
            company_title=co.get("title", ""),
            company_dates=co.get("date_range", ""),
            company_team=co.get("team", ""),
            company_chunks=company_chunks,
            bullet_count=bullet_count,
        )
        llm_failed_completely = False
        try:
            # Iter-09 (2026-04-24): Try Cerebras 8B first (like step 12) — avoids cascade
            # overhead and works when Groq/Gemini are cooling/429. Falls back to full cascade.
            try:
                raw, usage = llm.cerebras_8b_chat(system=sys, user=usr, temperature=0.3, max_tokens=3500)
                usage["provider"] = "cerebras_8b"
            except Exception as e_cer8:
                log(f"[step_10 {co_name}] cerebras_8b failed ({str(e_cer8)[:80]}); trying full cascade")
                raw, usage = llm.chat_with_fallback(system=sys, user=usr, temperature=0.3, max_tokens=3500)
        except llm.LLMError as e:
            log(f"[step_10 {co_name}] all LLM providers failed ({str(e)[:120]}); using synthesis fallback")
            llm_failed_completely = True
            raw, usage = "", {}

        if llm_failed_completely:
            # Iter-09: synthesis fallback when ALL LLMs fail — builds from raw nuggets
            if retrieved_nugs:
                log(f"[step_10 HARD-FLOOR via LLM-fail] {co_name}: synthesizing from top {min(3, len(retrieved_nugs))} nuggets")
                synth_accepted = []
                for idx, n in enumerate(retrieved_nugs[:3]):
                    answer = n.get("answer", "").strip()
                    if not answer:
                        continue
                    words = answer.split()
                    lead_n = min(5, len(words) // 3 + 1)
                    text_html = f"<b>{' '.join(words[:lead_n])}</b> " + " ".join(words[lead_n:])
                    synth_accepted.append({
                        "project_group": idx,
                        "text_html": text_html,
                        "verb": words[0] if words else "Led",
                        "verbose_context": answer,
                        "xyz": {"x_impact": " ".join(words[:lead_n]), "y_measure": "", "z_action": " ".join(words[lead_n:min(lead_n+10, len(words))])},
                        "covers_requirements": [],
                        "signal_type": "synthesized_llm_fail",
                        "evidence_atom_ids": [n["id"]],
                        "source": "hard_floor_llm_fail",
                    })
                verbose_all[co_name] = {"paragraphs": synth_accepted, "source": "synthesis_llm_fail"}
            else:
                verbose_all[co_name] = {"paragraphs": [], "error": "LLM failed + no nuggets"}
            _note_retry("step_10_synthesis_llm_fail")
            continue

        log(f"=== step_10 {co_name} {usage.get('provider')} ===\n{raw}\n=== end ===\n")
        # Iter-04 (2026-04-23): strip LLM commentary BEFORE JSON extraction.
        # Models sometimes preface JSON with reasoning ("I can only generate one
        # paragraph based on..."). llm.extract_json usually handles this but
        # fails when the preamble contains braces or code-fence markers.
        raw = _strip_commentary(raw)
        try:
            data = json.loads(llm.extract_json(raw))
        except json.JSONDecodeError:
            verbose_all[co_name] = {"paragraphs": [], "error": "invalid JSON", "raw": raw[:500]}
            continue

        raw_paras = data.get("paragraphs", [])
        accepted, rejected = _filter_hallucinated(raw_paras, valid_atom_ids)

        # P2 thin-paragraph retry REMOVED 2026-04-22 — redundant with P6 XYZ retry
        # below which already catches thin bullets via z_action word-count check.
        # Fewer retries = faster pipeline wall time (was hitting 20-min cap).

        # F3a (RCA 2026-04-22): retry once with explicit atom-ID whitelist if
        # fabrication rate ≥ 50%. Common failure mode: LLM invents 8-char hex IDs
        # that pass format check but don't match any real nugget.
        fab_count = sum(1 for r in rejected if r["reason"] == "fabricated_atom_id")
        fab_rate = fab_count / max(len(raw_paras), 1)
        if fab_rate >= 0.5 and raw_paras:
            log(f"[step_10 F3 retry] {co_name}: {fab_count}/{len(raw_paras)} fabricated; retrying with whitelist")
            _note_retry("step_10_fab_retry")
            valid_list = ", ".join(sorted(valid_atom_ids))
            retry_sys = (
                sys + "\n\nCRITICAL: Your previous response fabricated atom IDs. "
                f"The ONLY valid atom IDs for this company are:\n{valid_list}\n"
                "Every evidence_atom_ids entry MUST be an exact string match to one of these. "
                "If you cannot cite a valid ID for a paragraph, DO NOT emit that paragraph."
            )
            try:
                raw2, usage2 = llm.chat_with_fallback(system=retry_sys, user=usr, temperature=0.2, max_tokens=3000)
                raw2 = _strip_commentary(raw2)
                data2 = json.loads(llm.extract_json(raw2))
                raw_paras2 = data2.get("paragraphs", [])
                accepted2, rejected2 = _filter_hallucinated(raw_paras2, valid_atom_ids)
                if len(accepted2) > len(accepted):
                    log(f"[step_10 F3 retry] {co_name}: retry kept {len(accepted2)} vs first {len(accepted)} — using retry")
                    accepted, rejected = accepted2, rejected2
                    raw_paras = raw_paras2
                    usage = usage2
            except Exception as exc:
                log(f"[step_10 F3 retry] {co_name}: retry failed ({exc}); keeping first attempt")

        # Minimum floor: if all rejected for no_concrete_proof_signal, keep top-2
        if not accepted and rejected:
            all_soft = all(r["reason"] == "no_concrete_proof_signal" for r in rejected)
            if all_soft:
                accepted = raw_paras[:2]

        # Iter-07 HARD-FLOOR (2026-04-23): if STILL 0 accepted after all retries + rescue,
        # synthesize deterministic fallback paragraphs directly from retrieved nuggets.
        # Ensures every included company has ≥1 paragraph — prevents step_10 empty cascade.
        if not accepted and retrieved_nugs:
            log(f"[step_10 HARD-FLOOR] {co_name}: 0 accepted after all retries — synthesizing from top {min(3, len(retrieved_nugs))} nuggets")
            for idx, n in enumerate(retrieved_nugs[:3]):
                answer = n.get("answer", "").strip()
                if not answer:
                    continue
                # Bold-wrap the first 4-6 words (impact phrase heuristic)
                words = answer.split()
                lead_n = min(5, len(words) // 3 + 1)
                text_html = f"<b>{' '.join(words[:lead_n])}</b> " + " ".join(words[lead_n:])
                synth_para = {
                    "project_group": idx,
                    "text_html": text_html,
                    "verb": words[0] if words else "Led",
                    "verbose_context": answer,
                    "xyz": {
                        "x_impact": " ".join(words[:lead_n]),
                        "y_measure": "",  # may trigger downstream warning but better than empty
                        "z_action": " ".join(words[lead_n:min(lead_n+10, len(words))]),
                    },
                    "covers_requirements": [],
                    "signal_type": "synthesized",
                    "evidence_atom_ids": [n["id"]],
                    "source": "hard_floor_synthesis",
                }
                accepted.append(synth_para)
            _note_retry("step_10_hard_floor_synthesis")

        # P6 (2026-04-22): XYZ completeness check + retry.
        # User's quality floor: every bullet MUST have X (impact), Y (metric), Z (context/contribution).
        # Reject bullets where xyz object is missing or any field is empty/too thin.
        def _xyz_complete(p):
            xyz = p.get("xyz") or {}
            x = (xyz.get("x_impact") or "").strip()
            y = (xyz.get("y_measure") or "").strip()
            # z_action is the canonical field (user: Z = Action / specific contribution)
            z = (xyz.get("z_action") or xyz.get("z_context") or "").strip()
            # Y must contain at least one digit or currency/scale marker
            has_metric = bool(re.search(r"[\d%$₹€£]|\b[KkMmBb]\+?\b", y))
            # Z must be ≥5 words and describe personal action (not team-level filler)
            z_ok = bool(z) and len(z.split()) >= 5
            # Reject obvious team-level/filler Z
            banned_z = any(
                bp in z.lower() for bp in ("cross-functional collaboration", "team-level", "collaboration", "teamwork")
            )
            return bool(x) and bool(y) and has_metric and z_ok and not banned_z

        xyz_incomplete = [p for p in accepted if not _xyz_complete(p)]
        if xyz_incomplete and len(xyz_incomplete) >= max(2, len(accepted) // 3):
            _note_retry("step_10_xyz_retry")
            log(f"[step_10 P6 XYZ retry] {co_name}: {len(xyz_incomplete)}/{len(accepted)} bullets incomplete XYZ; retrying")
            # Build per-bullet diagnostic
            diag_lines = []
            for idx, p in enumerate(accepted):
                if p in xyz_incomplete:
                    xyz = p.get("xyz") or {}
                    missing = []
                    if not (xyz.get("x_impact") or "").strip(): missing.append("x_impact")
                    if not (xyz.get("y_measure") or "").strip():
                        missing.append("y_measure")
                    elif not re.search(r"[\d%$₹€£]|\b[KkMmBb]\+?\b", xyz.get("y_measure", "")):
                        missing.append("y_measure-needs-number")
                    if not (xyz.get("z_action") or xyz.get("z_context") or "").strip():
                        missing.append("z_action")
                    diag_lines.append(f"Bullet #{idx}: missing {missing}")
            retry_sys = sys + (
                "\n\nPREVIOUS OUTPUT FAILED XYZ COMPLETENESS. Every paragraph MUST have all three:\n"
                "  x_impact: non-empty outcome phrase (what got better)\n"
                "  y_measure: MUST contain a digit, %, $, K/M/B (no 'significantly' etc.)\n"
                "  z_action: 5-20 words describing what the candidate PERSONALLY DID — their\n"
                "            specific contribution or the approach they took. Not passive team-\n"
                "            level credit; show individual agency and mechanism.\n"
                "Specific failures:\n"
                + "\n".join(diag_lines) +
                "\n\nRe-emit ALL paragraphs with all three xyz fields populated and concrete."
            )
            try:
                text3, usage3 = llm.chat_with_fallback(system=retry_sys, user=usr, temperature=0.3, max_tokens=3500)
                text3 = _strip_commentary(text3)
                data3 = json.loads(llm.extract_json(text3))
                raw_paras3 = data3.get("paragraphs", [])
                accepted3, rejected3 = _filter_hallucinated(raw_paras3, valid_atom_ids)
                new_incomplete = [p for p in accepted3 if not _xyz_complete(p)]
                if len(new_incomplete) < len(xyz_incomplete):
                    log(f"[step_10 P6 retry] {co_name}: xyz-incomplete {len(xyz_incomplete)}→{len(new_incomplete)}; using retry")
                    accepted, rejected = accepted3, rejected3
                    raw_paras = raw_paras3
                    usage = usage3
                else:
                    log(f"[step_10 P6 retry] {co_name}: retry didn't improve XYZ; keeping original")
            except Exception as exc:
                log(f"[step_10 P6 retry] {co_name}: retry failed ({exc})")

        # F3b (RCA 2026-04-22): synthesis fallback — if we still have 0 accepted
        # bullets but the retrieval DID return real nuggets, synthesize pseudo-
        # paragraphs directly from the top nuggets so the company isn't silently
        # dropped from the final resume. Better to have a weak bullet than none.
        if not accepted and retrieved_nugs:
            log(f"[step_10 F3 fallback] {co_name}: 0 accepted; synthesizing from top {min(3, len(retrieved_nugs))} nuggets")
            _note_retry("step_10_synth_fallback")
            for n in retrieved_nugs[:3]:
                ans = (n.get("answer") or "").strip()
                if len(ans) < 20:
                    continue
                verb = ans.split()[0] if ans.split() else "Delivered"
                accepted.append({
                    "project_group": 0,
                    "text_html": ans,
                    "verb": verb,
                    "verbose_context": ans,
                    "xyz": {"x_impact": "", "y_measure": "", "z_action": ans},
                    "covers_requirements": [],
                    "signal_type": "deliverable",
                    "evidence_atom_ids": [n["id"]],
                    "_synthesized": True,
                })

        for p in accepted:
            v = p.get("verb")
            if v:
                used_verbs.append(v)

        verbose_all[co_name] = {
            "paragraphs": accepted,
            "dropped": rejected,
            "raw_count": len(raw_paras),
            "usage": usage,
        }
        for r in rejected:
            dropped_stats[r["reason"]] = dropped_stats.get(r["reason"], 0) + 1

    out_path = ARTIFACTS / "10_verbose_bullets.json"
    out_path.write_text(json.dumps(verbose_all, indent=2), encoding="utf-8")

    total_accepted = sum(len(v.get("paragraphs", [])) for v in verbose_all.values())
    total_dropped = sum(len(v.get("dropped", [])) for v in verbose_all.values())
    empty_companies = [c for c, v in verbose_all.items() if not v.get("paragraphs")]

    gaps: list[str] = []
    if total_accepted < 8:
        gaps.append(f"only {total_accepted} accepted paragraphs across all companies — expected 15+")
    if empty_companies:
        gaps.append(f"empty companies (no bullets accepted): {empty_companies}")
    if dropped_stats.get("fabricated_atom_id", 0) > 2:
        gaps.append(f"{dropped_stats['fabricated_atom_id']} paragraphs cited fabricated atom IDs — LLM hallucinating evidence")
    if dropped_stats.get("no_concrete_proof_signal", 0) > total_accepted:
        gaps.append(f"more paragraphs dropped for no_proof than accepted ({dropped_stats['no_concrete_proof_signal']} vs {total_accepted}) — upstream nuggets lack numeric signals")

    status = "pass" if not gaps else "partial"
    per_co_summary = "\n".join(f"- **{c}**: {len(v.get('paragraphs', []))} accepted, {len(v.get('dropped', []))} dropped" for c, v in verbose_all.items())
    body_md = f"""**Artifact:** `artifacts/10_verbose_bullets.json`

**Per-company:**
{per_co_summary}

**Dropped reasons:** {dropped_stats}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}
"""
    logbook.append(step, "eval", f"verbose {status}; accepted={total_accepted}; dropped={total_dropped}", body_md)
    return verbose_all


def _apply_fabrication_guards(
    verbose_all: dict,
    retrieved: dict,
    jd_text: str,
    raw_text: str,
) -> dict:
    """v8 Fix 3 + 4: post-step_10 metric-fidelity + JD-fishing guards.

    For each generated paragraph, strip numeric tokens not supported by cited
    source atoms (tier-aware fuzz) and JD-vocabulary tokens absent from source.
    Modifies text_html in place; logs counts to logbook.
    """
    try:
        from .lib.metric_extract import find_fabricated as _find_fab_metrics
        from .lib.jd_keyphrase import extract_jd_terms, find_fishing
    except Exception as _e:
        log(f"[v8-guards] import failed ({_e}) — skipping")
        return verbose_all

    if not isinstance(verbose_all, dict):
        return verbose_all
    # Handle both shapes: batched returns {"companies": {...}}, per-company returns {co: {...}}
    if "companies" in verbose_all and isinstance(verbose_all["companies"], dict):
        companies = verbose_all["companies"]
    else:
        companies = verbose_all
    if not companies:
        return verbose_all

    jd_terms = extract_jd_terms(jd_text or "")
    # Build company → list of source atom texts (from retrieved nuggets)
    co_sources: dict[str, list[str]] = {}
    for co_name, nugs in (retrieved or {}).items():
        texts = []
        for n in (nugs or []):
            if isinstance(n, dict):
                t = n.get("text") or n.get("nugget") or n.get("content") or ""
                if t:
                    texts.append(str(t))
        co_sources[co_name] = texts

    # Universal source pool (raw resume text) — fallback if a metric/term
    # appears in the resume but not in the retrieved nuggets for that company.
    universal_source = [raw_text or ""]

    metric_strips = 0
    jd_strips = 0
    bullets_touched = 0
    examples: list[str] = []

    for co_name, co_data in companies.items():
        if not isinstance(co_data, dict):
            continue
        paragraphs = co_data.get("paragraphs") or []
        co_src = co_sources.get(co_name, []) + universal_source
        for p in paragraphs:
            if not isinstance(p, dict):
                continue
            text = p.get("text_html") or ""
            if not text:
                continue
            original = text

            # --- Metric guard ---
            fab_metrics = _find_fab_metrics(text, co_src)
            for tok in fab_metrics:
                # Strip the metric token + leading "by"/"of"/"to"/"with" if attached
                pat = re.compile(r"\s*(?:by|of|to|with|reaching|achieving)?\s*" + re.escape(tok), re.IGNORECASE)
                new = pat.sub("", text, count=1)
                if new != text:
                    metric_strips += 1
                    text = new

            # --- JD-fishing guard ---
            fish = find_fishing(text, jd_terms, co_src)
            for term in fish:
                # Strip the term + 1-word neighborhood (e.g. "SOX compliance" → "compliance")
                pat = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
                new = pat.sub("", text, count=1)
                if new != text:
                    jd_strips += 1
                    text = new

            if text != original:
                # Cleanup: collapse extra whitespace, fix punctuation
                text = re.sub(r"\s{2,}", " ", text)
                text = re.sub(r"\s+([,.;:])", r"\1", text)
                text = re.sub(r"\(\s*\)", "", text)
                text = text.strip(" ,;")
                p["text_html"] = text
                bullets_touched += 1
                if len(examples) < 3:
                    examples.append(f"{co_name}: '{original[:80]}' → '{text[:80]}'")

    try:
        logbook.append(
            "step_10b_fabrication_guards", "result",
            f"bullets_touched={bullets_touched} metric_strips={metric_strips} jd_strips={jd_strips}",
            body="\n".join(["**Examples:**"] + [f"- {e}" for e in examples]) if examples else None,
        )
    except Exception:
        pass
    return verbose_all


def _filter_hallucinated(paragraphs: list[dict], valid_atom_ids: set) -> tuple[list[dict], list[dict]]:
    """v0.1.6: env LINKRIGHT_AUTO_APPROVE_NUGGETS=1 short-circuits all rejections.

    Per user direction (2026-04-26): "saare nuggets auto approved maano" — useful
    when atom_id evidence chain is unreliable (model variance, cross-domain runs).
    Banned-phrase + proof-signal checks STILL run (those are quality gates not
    fidelity gates). Only the atom_id citation requirement is bypassed.
    """
    import os as _os_filt
    _auto_approve = _os_filt.environ.get("LINKRIGHT_AUTO_APPROVE_NUGGETS", "").lower() in ("1", "true", "yes")

    accepted = []
    rejected = []
    for p in paragraphs:
        text = (p.get("text_html") or "").strip()
        cited = p.get("evidence_atom_ids") or []
        if isinstance(cited, str):
            cited = [cited]
        reason = None
        if valid_atom_ids and not _auto_approve:
            if not cited:
                reason = "missing_evidence_atom_ids"
            else:
                bad = [c for c in cited if c not in valid_atom_ids]
                if bad:
                    reason = f"fabricated_atom_id"
        if reason is None:
            lower = text.lower()
            hit = next((bp for bp in P.BANNED_PHRASES if bp in lower), None)
            if hit:
                reason = f"banned_phrase"
        if reason is None and text and not re.search(P.PROOF_REGEX, text):
            reason = "no_concrete_proof_signal"
        if reason is None:
            accepted.append(p)
        else:
            rejected.append({"reason": reason, "text_preview": text[:140], "cited": cited})
    return accepted, rejected


# ────────────────────────────────────────────────────────────────────────────
# Step 10 BATCHED (Iter-06) — single LLM call for all companies
# ────────────────────────────────────────────────────────────────────────────

def step_10_verbose_bullets_batched(parsed_p12: dict, retrieved: dict, reqs: list[dict]) -> Optional[dict]:
    """Batched variant: ONE Gemini Flash Lite call with structured JSON output for
    ALL companies. Replaces 2-3 per-company calls with 1.

    Returns verbose_all dict (same shape as step_10_verbose_bullets) on success,
    or None on any failure → caller falls through to per-company path.

    Gated by ENABLE_BATCH_STEP_10=1.
    """
    if os.environ.get("ENABLE_BATCH_STEP_10", "").lower() not in ("1", "true", "yes"):
        return None

    step = "step_10_verbose_bullets_batched"
    logbook.append(
        step, "starting",
        "single Gemini Flash Lite call with response_schema; generates paragraphs "
        "for all companies in one request. Falls back to per-company on failure.",
    )

    # Get included companies (respects step_07 distribution gate)
    resume_strategy = parsed_p12.get("resume_strategy") or {}
    distribution = resume_strategy.get("company_distribution") or {}
    included = distribution.get("included_companies", [])
    if included:
        included_names = {c["company"] for c in included}
        companies_to_process = [c for c in parsed_p12.get("companies", []) if c.get("name", "") in included_names]
    else:
        companies_to_process = parsed_p12.get("companies", [])

    if not companies_to_process:
        log("[step_10_batched] no companies to process — returning None for fallback")
        return None

    # Build companies_block: one section per company with pool + budget.
    # v0.1.7 — bullet_count CAPPED at len(retrieved nuggets) per company.
    # Prevents the Sanika bug: Google had only 2 nuggets but budget=4, so LLM
    # padded with 3 fabricated bullets ("99.9% uptime" etc.). With cap, Google
    # gets max 2 bullets — no fabrication pressure. Freed slots redistribute
    # to companies with rich nuggets (Oracle: nuggets=4, budget=6 → cap=4).
    bullet_budget = parsed_p12.get("bullet_budget") or {}

    # Pass 1 — compute realistic per-company budget = min(allocated, len(nuggets))
    #          plus track freed slack from companies whose budget exceeded nuggets
    realistic: dict[str, int] = {}
    n_avail: dict[str, int] = {}
    freed_slack = 0
    for idx, co in enumerate(companies_to_process):
        co_name = co.get("name", "")
        retrieved_nugs = (retrieved.get(co_name) or [])
        n = len(retrieved_nugs)
        n_avail[co_name] = n
        b = bullet_budget.get(f"company_{idx+1}_total", 4)
        cap = min(b, n) if n > 0 else 0
        realistic[co_name] = cap
        if b > cap:
            freed_slack += (b - cap)

    # Pass 2 — redistribute freed slack to companies that have unused nuggets,
    #          prioritizing the MOST RECENT (idx 0 = primary FT role).
    if freed_slack > 0:
        for idx, co in enumerate(companies_to_process):
            co_name = co.get("name", "")
            headroom = n_avail.get(co_name, 0) - realistic.get(co_name, 0)
            if headroom > 0:
                bonus = min(headroom, freed_slack)
                realistic[co_name] += bonus
                freed_slack -= bonus
                if freed_slack <= 0:
                    break

    blocks = []
    all_valid_atoms: dict[str, set[str]] = {}  # company → valid atom IDs
    for idx, co in enumerate(companies_to_process):
        co_name = co.get("name", "")
        retrieved_nugs = (retrieved.get(co_name) or [])
        if not retrieved_nugs:
            continue
        company_atoms = "\n".join(f"[atom:{n['id']}] {n['answer']}" for n in retrieved_nugs)
        all_valid_atoms[co_name] = {n["id"] for n in retrieved_nugs}
        bcount = realistic.get(co_name, 0)
        if bcount <= 0:
            continue
        blocks.append(
            f"### Company: {co_name}\n"
            f"Title: {co.get('title', '')}\n"
            f"Dates: {co.get('dates', '')}\n"
            f"bullet_count_required: {bcount}  (HARD CAP — never exceed this; never invent bullets beyond your atom pool)\n"
            f"Career Context (atom pool — cite ONLY these IDs):\n{company_atoms}\n"
        )

    # Telemetry — log the realistic redistribution for vision.md
    try:
        _budget_summary = {co: {"nuggets": n_avail.get(co, 0), "budget": bullet_budget.get(f"company_{i+1}_total", 4), "final": realistic.get(co, 0)}
                            for i, co in enumerate([c.get("name", "") for c in companies_to_process])}
        log(f"[step_10_batched] bullet_count cap (v0.1.7) — {_budget_summary}; freed_slack_remaining={freed_slack}")
    except Exception:
        pass

    if not blocks:
        log("[step_10_batched] no companies with nuggets — returning None")
        return None

    companies_block = "\n---\n".join(blocks)
    jd_keywords = parsed_p12.get("jd_keywords", [])
    jd_keywords_compact = ", ".join(str(k) for k in jd_keywords[:12])
    jd_requirements_list = "\n".join(f"{r['id']}: {r.get('text','')}" for r in reqs)
    strategy = parsed_p12.get("strategy", "BALANCED")
    career_level = parsed_p12.get("career_level", "MID")

    sys_prompt = llm.subst(
        P.PHASE_4A_VERBOSE_BATCHED_SYSTEM,
        strategy=strategy,
        career_level=career_level,
    )
    usr_prompt = llm.subst(
        P.PHASE_4A_VERBOSE_BATCHED_USER,
        jd_keywords_compact=jd_keywords_compact,
        jd_requirements_list=jd_requirements_list,
        companies_block=companies_block,
    )

    # Response schema: object with "companies" map → per-company paragraph arrays
    response_schema = {
        "type": "object",
        "properties": {
            "companies": {
                "type": "object",
                "description": "Map from company name to paragraphs list",
            }
        },
        "required": ["companies"],
    }

    t0 = time.time()
    try:
        raw, usage = llm.gemini_chat_json(
            system=sys_prompt, user=usr_prompt,
            response_schema=response_schema,
            temperature=0.3, max_output_tokens=6000,
        )
    except llm.LLMError as e:
        log(f"[step_10_batched] Gemini failed ({str(e)[:150]}); returning None for per-company fallback")
        return None

    dt = time.time() - t0
    log(f"[step_10_batched] Gemini Flash Lite: {dt:.1f}s, tokens={usage.get('total_tokens')}")

    # Parse JSON (should be clean from structured output)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        log(f"[step_10_batched] JSON parse failed despite schema: {exc}; falling back")
        return None

    companies_output = data.get("companies") or {}
    if not companies_output:
        log("[step_10_batched] empty 'companies' in response; falling back")
        return None

    # Build verbose_all in the shape step_11 expects, filtering hallucinated atoms
    verbose_all: dict[str, dict] = {}
    total_accepted = 0
    for co_name, co_data in companies_output.items():
        paragraphs = (co_data.get("paragraphs") or []) if isinstance(co_data, dict) else []
        valid_atoms = all_valid_atoms.get(co_name, set())
        accepted: list[dict] = []
        rejected: list[dict] = []
        for p in paragraphs:
            if not isinstance(p, dict):
                continue
            atom_ids = p.get("evidence_atom_ids") or []
            if not atom_ids:
                rejected.append({"reason": "no_evidence", "bullet": p})
                continue
            bad_atoms = [a for a in atom_ids if a not in valid_atoms]
            if bad_atoms:
                rejected.append({"reason": "fabricated_atom_id", "bullet": p, "bad_atoms": bad_atoms})
                continue
            accepted.append(p)
        verbose_all[co_name] = {
            "paragraphs": accepted,
            "dropped": rejected,
            "raw_count": len(paragraphs),
            "usage": usage,
            "source": "batched",
        }
        total_accepted += len(accepted)

    if total_accepted == 0:
        log("[step_10_batched] 0 total paragraphs accepted after filtering; falling back")
        return None

    # Persist artifact
    out_path = ARTIFACTS / "10_verbose_bullets.json"
    out_path.write_text(json.dumps(verbose_all, indent=2), encoding="utf-8")
    logbook.append(
        step, "result",
        f"batched ok: {total_accepted} paragraphs across {len(verbose_all)} companies, "
        f"1 LLM call, {dt:.1f}s, {usage.get('total_tokens')} tokens",
    )
    return verbose_all


# ────────────────────────────────────────────────────────────────────────────
# Step 11 — BRS ranking (local)
# ────────────────────────────────────────────────────────────────────────────

def step_11_rank(verbose_all: dict, jd_keywords: list[str]) -> dict:
    step = "step_11_rank"
    logbook.append(
        step, "starting",
        "scoring every verbose paragraph using a simplified BRS: specificity (#numbers), "
        "proof signal match count, JD-keyword hits, verb strength. Range 0-1.",
    )

    kw_set = set(k.lower() for k in jd_keywords)

    def brs(para: dict) -> float:
        text = (para.get("text_html") or "").lower()
        # Specificity: number of digit tokens
        nums = len(re.findall(r"\d+(?:\.\d+)?", text))
        # Proof signals
        signals = len(re.findall(P.PROOF_REGEX, text))
        # Keyword hits
        kw_hits = sum(1 for kw in kw_set if kw and kw in text)
        # Length bonus (150-350 band)
        L = len(text)
        len_bonus = 1.0 if 150 <= L <= 350 else (0.5 if L < 150 else 0.7)
        score = (nums * 0.15 + signals * 0.10 + kw_hits * 0.05) * len_bonus
        return round(min(score, 1.0), 3)

    ranked = {}
    for co, data in verbose_all.items():
        paras = list(data.get("paragraphs", []))
        for p in paras:
            p["_brs"] = brs(p)
        paras.sort(key=lambda p: p["_brs"], reverse=True)
        ranked[co] = paras

    out_path = ARTIFACTS / "11_ranked_bullets.json"
    out_path.write_text(json.dumps(ranked, indent=2), encoding="utf-8")

    all_scores = [p["_brs"] for paras in ranked.values() for p in paras]
    gaps: list[str] = []
    if not all_scores:
        gaps.append("no paragraphs to rank")
    else:
        spread = max(all_scores) - min(all_scores)
        if spread < 0.15:
            gaps.append(f"BRS spread is compressed ({spread:.2f}) — scorer is under-discriminating")

    status = "pass" if not gaps else "partial"
    score_hist = {}
    for s in all_scores:
        bucket = round(s, 1)
        score_hist[bucket] = score_hist.get(bucket, 0) + 1

    body_md = f"""**Artifact:** `artifacts/11_ranked_bullets.json`

**Scores:** min={min(all_scores) if all_scores else 0:.2f}, max={max(all_scores) if all_scores else 0:.2f}, count={len(all_scores)}
**Distribution:** {dict(sorted(score_hist.items()))}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}
"""
    logbook.append(step, "eval", f"rank {status}; {len(all_scores)} paragraphs scored", body_md)
    return ranked


# ────────────────────────────────────────────────────────────────────────────
# Step 12 — Condense (Phase 4c)
# ────────────────────────────────────────────────────────────────────────────

def step_12_condense(ranked: dict, parsed_p12: dict) -> dict:
    step = "step_12_condense"
    logbook.append(
        step, "starting",
        "calling LLM with PHASE_4C_CONDENSE prompt to compress each verbose paragraph "
        "to a single 95-110 char bullet; preserve <b>, metrics, verbs",
    )

    # Flatten all paragraphs with their company + index
    all_paras: list[tuple[str, int, dict]] = []
    for co, paras in ranked.items():
        # Take top N per company based on bullet_budget if available
        bb = parsed_p12.get("bullet_budget", {})
        # map co_name → company_N_total
        companies = parsed_p12.get("companies", [])
        budget = 4
        for i, c in enumerate(companies):
            if c.get("name") == co:
                budget = bb.get(f"company_{i+1}_total", 4)
                break
        for idx, p in enumerate(paras[:budget]):
            all_paras.append((co, idx, p))

    if not all_paras:
        logbook.append(step, "eval", "no paragraphs to condense", "**Status:** FAIL — Step 10 produced nothing.")
        return {}

    paragraphs_section = "\n\n".join(
        f"paragraph_index: {i}\ncompany: {co}\ntext_html: {p.get('text_html', '')}"
        for i, (co, _, p) in enumerate(all_paras)
    )
    sys = llm.subst(P.PHASE_4C_CONDENSE_SYSTEM, paragraph_count=len(all_paras))
    usr = llm.subst(P.PHASE_4C_CONDENSE_USER, paragraphs_section=paragraphs_section)

    # P3/D (2026-04-22): Step 12 prefers Cerebras qwen-235B because benchmarks
    # show it reliably lands bullets in the 95-110 char target window while
    # smaller models (Groq 70B, Gemini Flash) soft-cap at ~85 chars.
    step12_llm_failed = False
    try:
        text, usage = llm.cerebras_chat(system=sys, user=usr, temperature=0.2, max_tokens=3000)
        usage["provider"] = "cerebras"
    except Exception as e_cer:
        log(f"[step_12] cerebras failed ({e_cer}); falling back to default chain")
        try:
            text, usage = llm.chat_with_fallback(system=sys, user=usr, temperature=0.2, max_tokens=3000)
        except llm.LLMError as e:
            log(f"[step_12] ALL LLMs failed — using pass-through synthesis fallback: {str(e)[:120]}")
            logbook.append(step, "error", "Condense LLM failed — synthesis fallback", body=f"```\n{e}\n```")
            step12_llm_failed = True
            text, usage = "", {}

    if step12_llm_failed:
        # Iter-09: synthesis fallback — pass verbose paragraphs through as condensed bullets
        # (uses text_html directly, preserving bold + metrics; lower quality but crash-safe)
        condensed_by_co: dict[str, list[dict]] = {}
        for co, idx, p in all_paras:
            condensed_by_co.setdefault(co, []).append({
                "text_html": p.get("text_html", ""),
                "verb": p.get("verb", ""),
                "orig_brs": p.get("brs", 0.5),
                "project_group": p.get("project_group", idx),
                "source": "step12_synthesis_fallback",
            })
        _note_retry("step_12_synthesis_fallback")
        out_path = ARTIFACTS / "12_condensed_bullets.json"
        out_path.write_text(json.dumps(condensed_by_co, indent=2), encoding="utf-8")
        logbook.append(step, "eval", f"synthesis fallback: {sum(len(v) for v in condensed_by_co.values())} bullets passed through")
        return condensed_by_co

    log(f"=== step_12 {usage.get('provider')} ===\n{text}\n=== end ===\n")
    # Iter-04 (2026-04-23): strip LLM commentary BEFORE JSON extraction.
    text = _strip_commentary(text)
    try:
        data = json.loads(llm.extract_json(text))
    except json.JSONDecodeError as e:
        logbook.append(step, "error", f"invalid JSON: {e}", body=f"```\n{text[:800]}\n```")
        return {}

    condensed_bullets = data.get("bullets", [])

    # Iter-03 UNDER-SHOOT guard (2026-04-23): Cerebras sometimes over-condenses to
    # 47-88c avg. Detect systemic undershoot (≥50% of bullets under 85c) and retry
    # Cerebras once with stronger "minimum 100 chars" instruction + higher temp.
    def _plain_chars_early(html: str) -> int:
        return len(re.sub(r"<[^>]+>", "", html or "").strip())

    if condensed_bullets:
        # 2026-04-23: config-driven thresholds via width_config (STEP12_UNDERSHOOT_CHARS).
        # "Write big, trim small" — Cerebras undershoot target now is 95 (was 85).
        undershot = [b for b in condensed_bullets if _plain_chars_early(b.get("text_html", "")) < STEP12_UNDERSHOOT_CHARS]
        if len(undershot) / len(condensed_bullets) >= 0.5:
            _note_retry("step_12_undershoot_retry")
            log(f"[step_12 UNDERSHOOT retry] {len(undershot)}/{len(condensed_bullets)} under {STEP12_UNDERSHOOT_CHARS}c; retrying with stronger min-len prompt")
            undershoot_sys = sys + (
                f"\n\n# CRITICAL — PREVIOUS RESPONSE WAS TOO SHORT\n"
                f"Your previous output had bullets under {STEP12_UNDERSHOOT_CHARS} characters — that's UNACCEPTABLE.\n"
                f"Every bullet MUST be {STEP12_MIN_CHARS}-{STEP12_MAX_CHARS} plain chars. Under {STEP12_MIN_CHARS} = REJECTED.\n"
                f"Slightly LONG is SAFE — Step 13 will trim. Slightly SHORT is UNFIXABLE.\n"
                f"DO NOT over-compress. Keep the full XYZ context from the input paragraph.\n"
                f"Reproduce every paragraph now with FULL {STEP12_MIN_CHARS}-{STEP12_MAX_CHARS} char length.\n"
            )
            try:
                text_u, usage_u = llm.cerebras_chat(system=undershoot_sys, user=usr, temperature=0.4, max_tokens=3000)
                text_u = _strip_commentary(text_u)
                data_u = json.loads(llm.extract_json(text_u))
                bullets_u = data_u.get("bullets", [])
                # Only keep retry if it reduced undershoot count
                new_undershoot = sum(1 for b in bullets_u if _plain_chars_early(b.get("text_html", "")) < STEP12_UNDERSHOOT_CHARS)
                if new_undershoot < len(undershot):
                    log(f"[step_12 UNDERSHOOT retry] reduced undershoot {len(undershot)} → {new_undershoot}; using retry")
                    condensed_bullets = bullets_u
                    usage = usage_u
            except Exception as exc:
                log(f"[step_12 UNDERSHOOT retry] failed ({exc}); keeping original")

    # P3 (2026-04-22): retry if >30% of bullets are outside [88, 115] plain-char window.
    # This is the PRIMARY quality lever — RCA showed LLM under-shoots 95-110 target by
    # ~30 chars on average. Per-bullet diagnostic in retry prompt forces the LLM to
    # self-correct rather than continuing to under-shoot.
    def _plain_chars(html: str) -> int:
        return len(re.sub(r"<[^>]+>", "", html or "").strip())

    # 2026-04-23: config-driven via STEP12_OOB_MIN/MAX.
    oob = [(i, b, _plain_chars(b.get("text_html", ""))) for i, b in enumerate(condensed_bullets)
           if not (STEP12_OOB_MIN <= _plain_chars(b.get("text_html", "")) <= STEP12_OOB_MAX)]
    if condensed_bullets and len(oob) / len(condensed_bullets) > 0.3:
        _note_retry("step_12_range_retry")
        # Build per-bullet diagnostic
        diag_lines = []
        for i, b, L in oob:
            instr = "EXPAND — add supporting detail from input" if L < STEP12_MIN_CHARS else "TRIM — cut filler words"
            diag_lines.append(f"Bullet #{i}: {L} chars — {instr} (target {STEP12_MIN_CHARS}-{STEP12_MAX_CHARS})")
        retry_usr = usr + (
            f"\n\n## PREVIOUS OUTPUT FAILED LENGTH CONSTRAINT\n"
            f"{len(oob)}/{len(condensed_bullets)} bullets outside {STEP12_OOB_MIN}-{STEP12_OOB_MAX} char range.\n"
            + "\n".join(diag_lines) +
            f"\n\nReturn the CORRECTED bullets — all {len(all_paras)} of them, each in {STEP12_MIN_CHARS}-{STEP12_MAX_CHARS} plain-char window."
        )
        log(f"[step_12 P3 retry] {len(oob)}/{len(condensed_bullets)} oob; retrying via cerebras")
        try:
            text2, usage2 = llm.cerebras_chat(system=sys, user=retry_usr, temperature=0.1, max_tokens=3000)
            usage2["provider"] = "cerebras"
            text2 = _strip_commentary(text2)
            data2 = json.loads(llm.extract_json(text2))
            bullets2 = data2.get("bullets", [])
            oob2 = [b for b in bullets2 if not (STEP12_OOB_MIN <= _plain_chars(b.get("text_html", "")) <= STEP12_OOB_MAX)]
            # Use retry only if it improved the OOB count
            if len(oob2) < len(oob):
                log(f"[step_12 P3 retry] retry improved oob {len(oob)} → {len(oob2)}; using retry")
                condensed_bullets = bullets2
                usage = usage2
            else:
                log(f"[step_12 P3 retry] retry did not improve ({len(oob2)} vs {len(oob)} oob); keeping original")
        except Exception as exc:
            log(f"[step_12 P3 retry] retry failed ({exc}); keeping original")

    # ATOMIC STEP 12 (Iter-02, 2026-04-22): deterministic post-processor.
    # After LLM condense, Python trims filler words from over-length bullets
    # to hit the target. No additional LLM calls needed.
    # Iter-04 (2026-04-23): added digit-anchored substitutions (zero false-positive risk).
    _SAFE_AND_NOUNS = r"(sales|marketing|engineering|product|design|ops|operations|tech|business|strategy|growth|data|analytics|infrastructure|finance|legal|hr|recruiting)"
    FILLER_PATTERNS = [
        # Order matters: remove most removable first (lowest semantic load)
        (re.compile(r"\s+(successfully|effectively|consistently|reliably|actively|eventually|ultimately|strategically|proactively|comprehensively|seamlessly|efficiently)\b", re.I), ""),
        (re.compile(r"\s+(various|multiple|several|key|important|significant|notable|critical|robust|scalable)\s+", re.I), " "),
        # Iter-04: digit-anchored symbol substitutions (100% safe — require numeric context)
        (re.compile(r"(\d)\s+percent\b", re.I), r"\1%"),
        (re.compile(r"(\d)\s+million\b", re.I), r"\1M"),
        (re.compile(r"(\d)\s+thousand\b", re.I), r"\1K"),
        (re.compile(r"(\d)\s+billion\b", re.I), r"\1B"),
        (re.compile(r"(\d)\s+per\s+month\b", re.I), r"\1/mo"),
        (re.compile(r"(\d)\s+per\s+year\b", re.I), r"\1/yr"),
        (re.compile(r"(\d)\s+per\s+hour\b", re.I), r"\1/hr"),
        (re.compile(r"(\d)\s+per\s+week\b", re.I), r"\1/wk"),
        (re.compile(r"(\d)\s+per\s+day\b", re.I), r"\1/day"),
        (re.compile(r"(\d)\s+hours\b", re.I), r"\1 hrs"),
        (re.compile(r"(\d)\s+minutes\b", re.I), r"\1 mins"),
        (re.compile(r"\bapproximately\s+(\d)", re.I), r"~\1"),
        (re.compile(r"\bmore than\s+(\d)", re.I), r">\1"),
        (re.compile(r"\bless than\s+(\d)", re.I), r"<\1"),
        # Iter-04: "and" → "&" only between whitelisted common business nouns (no proper-noun risk)
        (re.compile(rf"\b{_SAFE_AND_NOUNS}\s+and\s+{_SAFE_AND_NOUNS}\b", re.I), r"\1 & \2"),
        # Compound reductions
        (re.compile(r"\bin order to\b", re.I), "to"),
        (re.compile(r"\bas part of\b", re.I), "in"),
        (re.compile(r"\bwith the goal of\b", re.I), "to"),
        (re.compile(r"\bby means of\b", re.I), "via"),
        (re.compile(r"\bthat (is|are|were|was)\s+", re.I), " "),
        (re.compile(r"\bthrough\b", re.I), "via"),   # 7 → 3 chars
        (re.compile(r"\bbetween\b", re.I), "btwn"),  # compress
        (re.compile(r"\bacross\b", re.I), "in"),     # 6 → 2 chars
        (re.compile(r"\band then\b", re.I), "and"),
        (re.compile(r"\s+as well as\s+", re.I), " + "),
        (re.compile(r"\bapproximately\b", re.I), "~"),
        # Word substitution
        (re.compile(r"\bdelivered\b", re.I), "shipped"),
        (re.compile(r"\bimplementation\b", re.I), "rollout"),
        (re.compile(r"\binfrastructure\b", re.I), "infra"),
        # Articles last (risky)
        (re.compile(r"\s+(the|a|an)\s+", re.I), " "),
    ]

    def _plain(html: str) -> str:
        return re.sub(r"<[^>]+>", "", html or "").strip()

    def _atomic_trim(html: str, target_max: int = STEP12_MAX_CHARS) -> str:
        """Iteratively remove filler words + whitespace until plain char count ≤ target.
        Preserves <b>...</b> spans by only operating outside them."""
        bold_spans = list(re.finditer(r"<b[^>]*>.*?</b>", html, flags=re.DOTALL | re.I))
        if len(_plain(html)) <= target_max:
            return html

        # Work on the non-bold portions only
        def _apply_pattern(h: str, pat: re.Pattern, repl: str) -> str:
            # Split at bold boundaries, apply to non-bold chunks
            result = []
            pos = 0
            for m in re.finditer(r"<b[^>]*>.*?</b>", h, flags=re.DOTALL | re.I):
                non_bold = h[pos:m.start()]
                non_bold = pat.sub(repl, non_bold)
                result.append(non_bold)
                result.append(m.group(0))
                pos = m.end()
            tail = h[pos:]
            tail = pat.sub(repl, tail)
            result.append(tail)
            return re.sub(r"\s{2,}", " ", "".join(result)).strip()

        out = html
        for pat, repl in FILLER_PATTERNS:
            if len(_plain(out)) <= target_max:
                break
            out = _apply_pattern(out, pat, repl)
        # Always re-tighten whitespace
        return re.sub(r"\s{2,}", " ", out).strip()

    # Apply atomic correction — bidirectional (trim over-length + expand under-length)
    # Over: deterministic filler removal (fast, free)
    # Under: cheap LLM call asking to add a supporting clause (~50 tokens)
    over_count = 0
    under_count = 0
    # 2026-04-23: config-driven targets (STEP12_MIN/MAX_CHARS, STEP12_TARGET_MIDPOINT).
    for b in condensed_bullets:
        orig_html = b.get("text_html", "")
        orig_len = len(_plain(orig_html))
        if orig_len > STEP12_MAX_CHARS:
            trimmed = _atomic_trim(orig_html, target_max=STEP12_MAX_CHARS)
            new_len = len(_plain(trimmed))
            if new_len < orig_len:
                log(f"[step_12 atomic_trim] bullet {b.get('paragraph_index','?')}: {orig_len}→{new_len}c")
                b["text_html"] = trimmed
                over_count += 1
        elif orig_len < STEP12_MIN_CHARS:
            # Under — ask cheap LLM to add 1 supporting clause. Cap retries to keep cost small.
            delta_needed = STEP12_TARGET_MIDPOINT - orig_len  # target midpoint
            pad_sys = (
                f"Expand the resume bullet below by adding exactly {delta_needed} more characters "
                "via ONE short supporting clause after a comma (context, scale, or domain acronym). "
                "Do NOT invent new numbers or facts not in the original. Keep every <b>...</b> tag "
                "content verbatim. Keep the leading verb. Return ONLY the expanded bullet text."
            )
            try:
                # Iter-06 (2026-04-23): try Cerebras 8B first (2200 tok/s, FREE).
                # Atomic pad is a tiny rewrite (1-2 filler word changes) — 8B is plenty.
                # Fall back to chat_with_fallback only on rate-limit.
                try:
                    pad_text, _pad_usage = llm.cerebras_8b_chat(
                        system=pad_sys, user=orig_html, temperature=0.2, max_tokens=200
                    )
                except llm.LLMError as _e_c8:
                    if "429" in str(_e_c8) or "rate" in str(_e_c8).lower():
                        pad_text, _pad_usage = llm.chat_with_fallback(
                            system=pad_sys, user=orig_html, temperature=0.2, max_tokens=200
                        )
                    else:
                        raise
                # Iter-04: strip LLM commentary BEFORE parsing first line
                pad_text = _strip_commentary(pad_text)
                pad_clean = pad_text.strip().split("\n")[0].strip('"\u201c\u201d').strip()
                new_len = len(_plain(pad_clean))
                # Keep only if it grew into range and didn't break bold
                orig_bolds = re.findall(r"<b[^>]*>(.*?)</b>", orig_html, flags=re.I | re.DOTALL)
                new_bolds = re.findall(r"<b[^>]*>(.*?)</b>", pad_clean, flags=re.I | re.DOTALL)
                if STEP12_PAD_MIN <= new_len <= STEP12_PAD_MAX and set(orig_bolds) == set(new_bolds):
                    log(f"[step_12 atomic_pad] bullet {b.get('paragraph_index','?')}: {orig_len}→{new_len}c")
                    b["text_html"] = pad_clean
                    under_count += 1
            except Exception as exc:
                log(f"[step_12 atomic_pad] bullet {b.get('paragraph_index','?')}: pad failed ({exc})")
    log(f"[step_12 atomic] trimmed {over_count} over-length + padded {under_count} under-length")

    # ATOMIC-POLISH (Iter-02, 2026-04-22): targeted per-bullet LLM rewrite for
    # bullets STILL out-of-range after deterministic trim/pad. One call per
    # stuck bullet. Cheap model + explicit target char count + XYZ-preservation.
    # 2026-04-23: config-driven target via width_config (STEP12_MIN/MAX_CHARS).
    still_oob = [(i, b) for i, b in enumerate(condensed_bullets)
                 if not (STEP12_MIN_CHARS <= _plain_chars(b.get("text_html", "")) <= STEP12_MAX_CHARS)]
    polish_applied = 0
    for i, b in still_oob[:6]:  # cap to 6 polish calls per job (cost control)
        orig_html = b.get("text_html", "")
        orig_len = len(_plain(orig_html))
        direction = "shorten" if orig_len > STEP12_MAX_CHARS else "lengthen"
        delta = abs(orig_len - STEP12_TARGET_MIDPOINT)
        polish_sys = (
            f"Rewrite this one resume bullet to exactly {STEP12_TARGET_MIDPOINT} characters of plain text "
            f"(current: {orig_len}c, must {direction} by ~{delta}). HARD RULES:\n"
            f"- Keep every <b>...</b> span verbatim.\n"
            f"- Keep all numbers, %, $, K, M, B, proper nouns verbatim.\n"
            f"- Keep the leading verb.\n"
            f"- Only {'remove' if direction == 'shorten' else 'add'} filler words "
            f"({'articles, adverbs, weak adjectives' if direction == 'shorten' else 'a short supporting clause'}).\n"
            f"Count plain chars of your output BEFORE returning. Target: {STEP12_MIN_CHARS}-{STEP12_MAX_CHARS}.\n"
            f"# OUTPUT PURITY: no commentary, no HTML comments, no code fences. "
            f"Return ONLY the rewritten bullet text — no preamble, no quotes."
        )
        try:
            # Iter-06: Cerebras 8B first (FREE, 2200 tok/s). Fallback on rate-limit.
            try:
                polish_raw, _polish_usage = llm.cerebras_8b_chat(
                    system=polish_sys, user=orig_html, temperature=0.2, max_tokens=200
                )
            except llm.LLMError as _e_c8:
                if "429" in str(_e_c8) or "rate" in str(_e_c8).lower():
                    polish_raw, _polish_usage = llm.chat_with_fallback(
                        system=polish_sys, user=orig_html, temperature=0.2, max_tokens=200
                    )
                else:
                    raise
            # Iter-04: strip LLM commentary BEFORE parsing first line
            polish_raw = _strip_commentary(polish_raw)
            polish_clean = polish_raw.strip().split("\n")[0].strip('"\u201c\u201d').strip()
            polish_len = len(_plain(polish_clean))
            orig_bolds = re.findall(r"<b[^>]*>(.*?)</b>", orig_html, flags=re.I | re.DOTALL)
            new_bolds = re.findall(r"<b[^>]*>(.*?)</b>", polish_clean, flags=re.I | re.DOTALL)
            # Accept only if landed in target AND bold preserved
            if STEP12_PAD_MIN <= polish_len <= STEP12_PAD_MAX and set(orig_bolds) == set(new_bolds):
                log(f"[step_12 atomic_polish] bullet {b.get('paragraph_index','?')}: {orig_len}→{polish_len}c")
                b["text_html"] = polish_clean
                polish_applied += 1
        except Exception as exc:
            log(f"[step_12 atomic_polish] bullet {b.get('paragraph_index','?')}: polish failed ({exc})")
    if polish_applied:
        log(f"[step_12 atomic_polish] applied to {polish_applied}/{len(still_oob)} stuck bullets")

    # Map back to (company, index) by paragraph_index
    output: dict[str, list[dict]] = {}
    for b in condensed_bullets:
        pi = b.get("paragraph_index")
        if pi is None or pi >= len(all_paras):
            continue
        co, orig_idx, orig = all_paras[pi]
        output.setdefault(co, []).append({
            "text_html": b.get("text_html", ""),
            "verb": b.get("verb"),
            "orig_brs": orig.get("_brs"),
            "project_group": orig.get("project_group", 0),
        })

    # v0.1.3 Fix A — defensive post-condense prefix scrubber.
    # LLMs (especially Cerebras/Groq on fallback path) sometimes slip in
    # "At <Company>, as a/an/the <Role>," preamble despite prompt negatives.
    # This collapses verb_diversity + wastes ~40 chars/line. Strip it here.
    # Preserves <b>...</b> tags. Re-capitalizes first remaining word.
    _PREFIX_RE = re.compile(
        r"^\s*(?:<b>\s*)?at\s+[^,<]+,\s*as\s+(?:a|an|the)\s+[^,<]+,\s*(?:</b>\s*)?",
        re.IGNORECASE,
    )
    _scrubbed_count = 0
    for _co, _bullets in output.items():
        for _b in _bullets:
            _orig = _b.get("text_html", "") or ""
            _stripped = _PREFIX_RE.sub("", _orig, count=1).lstrip()
            if _stripped != _orig and _stripped:
                # Capitalize first char post-strip (handles "spearheaded" → "Spearheaded")
                # Unless it's already inside a <b>...
                if _stripped[0].islower() and not _stripped.startswith("<"):
                    _stripped = _stripped[0].upper() + _stripped[1:]
                elif _stripped.startswith("<b>") and len(_stripped) > 3 and _stripped[3].islower():
                    _stripped = _stripped[:3] + _stripped[3].upper() + _stripped[4:]
                _b["text_html"] = _stripped
                _scrubbed_count += 1
    if _scrubbed_count:
        try:
            logbook.append(
                "step_12_condense",
                "post_scrub",
                f"scrubbed preamble from {_scrubbed_count} bullets (Fix A)",
                body="Removed 'At <Company>, as a/an/the <Role>,' prefix patterns — bullets now lead with impact verb.",
            )
        except Exception:
            pass

    out_path = ARTIFACTS / "12_condensed_bullets.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    # Evaluate — strip <b> tags, count chars
    def char_count(html: str) -> int:
        return len(re.sub(r"<[^>]+>", "", html))

    lengths = []
    for co, bullets in output.items():
        for b in bullets:
            lengths.append(char_count(b["text_html"]))
    in_range = sum(1 for L in lengths if 85 <= L <= 115)

    gaps: list[str] = []
    if not output:
        gaps.append("condense produced no bullets")
    if lengths and in_range / len(lengths) < 0.7:
        gaps.append(f"only {in_range}/{len(lengths)} bullets in 85-115 char range")
    total = sum(len(v) for v in output.values())
    if total != len(all_paras):
        gaps.append(f"condense dropped {len(all_paras) - total} paragraphs (asked {len(all_paras)}, got {total})")

    status = "pass" if not gaps else "partial"
    body_md = f"""**Artifact:** `artifacts/12_condensed_bullets.json`

**Metrics:**
- Bullets condensed: {total}/{len(all_paras)}
- Char range: min={min(lengths) if lengths else 0}, max={max(lengths) if lengths else 0}, in-range={in_range}/{len(lengths) if lengths else 0}

**Sample bullet:**
> {output[list(output.keys())[0]][0]['text_html'] if output else '(none)'}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}
"""
    logbook.append(step, "eval", f"condense {status}; {total}/{len(all_paras)}; in-range={in_range}", body_md)
    return output


# ────────────────────────────────────────────────────────────────────────────
# Step 13 — Width optimization (skipped — Oracle rewrite for bullets is too
# noisy for a diagnostic run; we use condensed as-is and mark this a known skip)
# ────────────────────────────────────────────────────────────────────────────

def step_13_width_skip(condensed: dict) -> dict:
    step = "step_13_width_optim"
    logbook.append(
        step, "starting",
        "SKIPPING width rewrite for this diagnostic run — condensed bullets pass through "
        "unchanged; noted as known production dependency (Oracle /lifeos/rewrite + llama3.2:1b)",
    )
    (ARTIFACTS / "13_width_optimized.json").write_text(
        json.dumps({"note": "skipped — condensed used as-is", "bullets": condensed}, indent=2),
        encoding="utf-8",
    )
    logbook.append(step, "eval", "skipped intentionally (noise > signal for diagnosis)",
                   "This step would have rewritten bullets to fill 98-101 CU. For diagnosis we'd rather see the raw condensed output than width-tuned variants.")
    return condensed


# ────────────────────────────────────────────────────────────────────────────
# Step 14 — HTML assembly
# ────────────────────────────────────────────────────────────────────────────

def step_14_assemble_html(parsed_p12: dict, parsed_resume: dict, summary: str, bullets_per_co: dict) -> Path:
    step = "step_14_assemble_html"
    logbook.append(
        step, "starting",
        f"loading template {TEMPLATE_PATH.name}; substituting header, contact, summary, "
        "per-company sections, skills, education, certifications, interests; applying theme colors",
    )

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    colors = parsed_p12.get("theme_colors") or {
        "brand_primary": "#1B2A4A",
        "brand_secondary": "#2563EB",
        "brand_tertiary": "#6B7280",
        "brand_quaternary": "#FFFFFF",
    }
    contact = parsed_p12.get("contact_info", {})

    # Build company sections HTML — v0.1.2 contract (3-layer fallback):
    # NEVER drop a role the user actually worked at. Layers (decreasing preference):
    #   L1: JD-tailored bullets from step_12 condense
    #   L2: Raw step_02 nuggets for that company (highest-importance first)
    #   L3: Plain bullets from step_01 parsed resume for that company
    # Companies list itself may be empty (step_07 LLM exhausted) — reconstruct
    # from parsed_resume.experiences (max 4, most-recent first).
    MIN_BULLETS_PER_ROLE = 2
    # v0.1.5 Phase 4.1 — page util expand-mode. Pad each role up to TARGET
    # using L2/L3 fallback when sparse. fit_loop trims down if overflow.
    # Net effect: page utilization closer to 92-95% target instead of 67-75%.
    TARGET_BULLETS_PER_ROLE = 5
    ROLE_CAP = 4
    company_html_parts = []
    _filled_sparse: list[tuple[str, int, int]] = []  # (company, had, synthesized_added)
    _expanded_padding: list[tuple[str, int, int]] = []  # (company, base, expanded_to)

    # v0.1.2 L2 precondition: rebuild companies list from step_01 experiences if empty
    # (covers the "all LLM providers exhausted mid-run" scenario).
    _p12_companies = parsed_p12.get("companies") or []
    if not _p12_companies:
        _exps = (parsed_resume.get("experiences") or [])[:ROLE_CAP]
        _p12_companies = [
            {
                "name": ex.get("company", ""),
                "location": ex.get("location", ""),
                "title": ex.get("role", ""),
                "date_range": f"{ex.get('start_date','')} – {ex.get('end_date','')}".strip(" –"),
                "team": "",
            }
            for ex in _exps
            if (ex.get("company") or "").strip()
        ]
        if _p12_companies:
            try:
                logbook.append(
                    "step_14_assemble_html",
                    "fallback",
                    f"reconstructed companies list from parsed_resume.experiences (step_07 returned empty); using {len(_p12_companies)}",
                )
            except Exception:
                pass

    # v5.8 GENERIC education filter — primary signal: parsed_resume.education list
    # (works globally — MIT/Stanford/Oxford/IIT/BITS, whatever the user attended).
    # Defense-in-depth: tiny GENERIC English regex (no India-specific bias).
    import os as _os_edu
    _edu_re_str = _os_edu.environ.get(
        "LINKRIGHT_EDU_DENY_REGEX",
        # Universal English education-context tokens only.
        r"\b(university|college|institute of technology|school of)\b",
    )
    _EDU_PATTERN = re.compile(_edu_re_str, re.IGNORECASE)
    # Build set of education-institution names from step_01 parsed resume.
    _edu_names: set = set()
    try:
        for e in (parsed_resume.get("education") or []):
            inst = (e.get("institution") if isinstance(e, dict) else "")
            inst = (inst or "").strip().lower()
            if inst:
                _edu_names.add(inst)
    except Exception:
        pass

    _filtered_edu: list[str] = []
    _kept_companies = []
    for _co in _p12_companies:
        _name = (_co.get("name") or "").strip()
        _name_lc = _name.lower()
        # Drop if either: (a) name appears in user's actual education list,
        # OR (b) matches generic education-context regex.
        if _name and (_name_lc in _edu_names or _EDU_PATTERN.search(_name)):
            _filtered_edu.append(_name)
            continue
        _kept_companies.append(_co)
    if _filtered_edu:
        try:
            logbook.append(
                "step_14_assemble_html",
                "filter",
                f"dropped {len(_filtered_edu)} education entity/entities from Work Experience (v5.8 generic)",
                body="\n".join(f"- {n}" for n in _filtered_edu),
            )
        except Exception:
            pass
    _p12_companies = _kept_companies

    # v0.1.6 Entity-fidelity guard (Layer 3, post-step_14 last-mile).
    # Even after step_07 guard + step_10 prompt, defensive check: drop any
    # rendered company that doesn't substring-match a real experience.
    try:
        _real_exp_names = []
        for _exp in (parsed_resume.get("experiences") or []):
            _co_name = (_exp.get("company") or "").strip()
            if _co_name:
                _real_exp_names.append(_co_name)
        _real_exp_norm = {re.sub(r"[^a-z0-9]+", "", c.lower()) for c in _real_exp_names if c}

        def _is_real_company(name: str) -> bool:
            n = re.sub(r"[^a-z0-9]+", "", (name or "").lower())
            if not n:
                return False
            if n in _real_exp_norm:
                return True
            for r in _real_exp_norm:
                if r and (n in r or r in n):
                    return True
            return False

        _final_kept = [c for c in _p12_companies if _is_real_company((c.get("name") or ""))]
        _final_dropped = [c for c in _p12_companies if not _is_real_company((c.get("name") or ""))]
        if _final_dropped:
            _names = [(c.get("name") or "") for c in _final_dropped]
            log(f"[entity_fidelity Layer 3] step_14 dropped {len(_names)} hallucinated company/companies: {_names}")
            try:
                logbook.append("step_14_entity_fidelity", "filter",
                    f"dropped {len(_names)} hallucinated companies at render-time: {_names}",
                    body=f"Real experiences (step_01): {_real_exp_names}",
                )
            except Exception:
                pass
            _p12_companies = _final_kept
    except Exception as _e_ef3:
        log(f"[entity_fidelity Layer 3] guard error: {_e_ef3} — pipeline continues")

    # L3 source: per-company bullets from step_01 parsed resume
    _step01_bullets_by_co: dict[str, list[str]] = {}
    for _ex in (parsed_resume.get("experiences") or []):
        _co = (_ex.get("company") or "").strip()
        if _co:
            _step01_bullets_by_co[_co] = [b for b in (_ex.get("bullets") or []) if b]

    # Load raw nuggets from artifact to enable the generic-impact fallback.
    # step_02 produces nuggets with per-company 'answer' field already in concise
    # achievement form (e.g. "Architected AML risk engine for 100M+ accounts").
    _raw_nuggets_by_co: dict[str, list[dict]] = {}
    try:
        import json as _json14
        _nuggets_path = ARTIFACTS / "02_nuggets_extracted.json"
        if _nuggets_path.exists():
            _d = _json14.loads(_nuggets_path.read_text(encoding="utf-8"))
            _all_nugs = _d.get("nuggets") if isinstance(_d, dict) else (_d if isinstance(_d, list) else [])
            _IMP_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
            for n in _all_nugs or []:
                if not isinstance(n, dict):
                    continue
                _co = (n.get("company") or "").strip()
                if not _co or _co.lower() == "none":
                    continue
                _raw_nuggets_by_co.setdefault(_co, []).append(n)
            # Sort each company's nuggets by importance (P0 first), then original order
            for _co, _lst in _raw_nuggets_by_co.items():
                _lst.sort(key=lambda x: _IMP_ORDER.get(x.get("importance", "P3"), 9))
    except Exception:
        pass

    # v0.1.3 Fix A (applied here too — step_12 scrubber doesn't fire when step_12
    # is bypassed during quota-exhausted paths; this ensures raw nuggets used as
    # bullets also get the "At <Co>, as a <Role>," preamble stripped).
    _FALLBACK_PREFIX_RE = re.compile(
        r"^\s*(?:<b>\s*)?at\s+[^,<]+,\s*as\s+(?:a|an|the)\s+[^,<]+,\s*(?:i\s+)?",
        re.IGNORECASE,
    )

    def _fallback_bullet_for_nugget(n: dict) -> dict:
        """Wrap a raw nugget's answer into the bullet dict shape step_14 expects."""
        ans = (n.get("answer") or "").strip()
        # Strip "At <Company>, as a/an/the <Role>, (I)" preamble if present.
        scrubbed = _FALLBACK_PREFIX_RE.sub("", ans, count=1).lstrip()
        if scrubbed and scrubbed != ans:
            # Capitalize first post-strip char
            if scrubbed[0].islower():
                scrubbed = scrubbed[0].upper() + scrubbed[1:]
            ans = scrubbed
        # Drop trailing period for bullet style; cap ~280 chars
        if ans.endswith("."):
            ans = ans[:-1]
        if len(ans) > 280:
            ans = ans[:277] + "…"
        return {"text_html": ans, "project_group": 0, "_fallback": True}

    for co in _p12_companies[:ROLE_CAP]:
        co_name = co.get("name", "")
        bullets = list(bullets_per_co.get(co_name, []))
        had_from_jd = len(bullets)

        # L2: pad from raw step_02 nuggets for this company (generic-impact fallback).
        # v0.1.3 Fix B: semantic-ish dedup via token-overlap Jaccard (no LLM call).
        # Skip a candidate if its content-token overlap with any existing bullet >= 0.6.
        def _content_tokens(text: str) -> set:
            t = re.sub(r"<[^>]+>", " ", text or "")
            t = re.sub(r"[^a-z0-9 %$]+", " ", t.lower())
            toks = [w for w in t.split() if len(w) > 3]  # drop stopwords/short words
            return set(toks)

        def _is_near_dup(candidate_text: str, existing_texts_sets: list[set]) -> bool:
            cand = _content_tokens(candidate_text)
            if not cand:
                return False
            for ex in existing_texts_sets:
                if not ex:
                    continue
                overlap = len(cand & ex) / max(1, min(len(cand), len(ex)))
                if overlap >= 0.6:
                    return True
            return False

        # ROLLED BACK in v5.6: TARGET=5 padding hurt width + brs (raw nuggets bypass
        # step 12 condense and have lower BRS). Reverted to MIN(2) — original behavior.
        # Page util fix needs OPTIONAL SECTIONS (Awards/Voluntary), not bullet padding.
        if len(bullets) < MIN_BULLETS_PER_ROLE:
            pool = _raw_nuggets_by_co.get(co_name) or []
            existing_sets = [_content_tokens(b.get("text_html") or "") for b in bullets]
            for n in pool:
                fb = _fallback_bullet_for_nugget(n)
                if _is_near_dup(fb["text_html"], existing_sets):
                    continue
                bullets.append(fb)
                existing_sets.append(_content_tokens(fb["text_html"]))
                if len(bullets) >= MIN_BULLETS_PER_ROLE:
                    break

        # L3: final fallback — use raw step_01 resume bullets for that company.
        # Uses the same Fix B semantic-ish dedup (>=0.6 token overlap = skip).
        if len(bullets) < MIN_BULLETS_PER_ROLE:
            raw_bs = _step01_bullets_by_co.get(co_name) or []
            existing_sets = [_content_tokens(b.get("text_html") or "") for b in bullets]
            for rb in raw_bs:
                text = (rb or "").strip()
                if not text or _is_near_dup(text, existing_sets):
                    continue
                bullets.append({"text_html": text, "project_group": 0, "_fallback": True})
                existing_sets.append(_content_tokens(text))
                if len(bullets) >= MIN_BULLETS_PER_ROLE:
                    break

        # Log synthesis telemetry — distinguish sparse-rescue vs expand-padding
        if had_from_jd < MIN_BULLETS_PER_ROLE and len(bullets) >= MIN_BULLETS_PER_ROLE:
            _filled_sparse.append((co_name, had_from_jd, len(bullets) - had_from_jd))
        elif had_from_jd >= MIN_BULLETS_PER_ROLE and len(bullets) > had_from_jd:
            _expanded_padding.append((co_name, had_from_jd, len(bullets)))

        # If truly nothing available (unlikely — means empty resume for that role),
        # still skip rendering to avoid an empty role header block.
        if not bullets:
            continue

        # Group by project_group
        groups: dict[int, list[dict]] = {}
        for b in bullets:
            groups.setdefault(b.get("project_group", 0), []).append(b)

        bullet_html = ""
        for grp_idx in sorted(groups.keys()):
            grp_bullets = groups[grp_idx]
            bullet_html += "<ul>\n"
            for b in grp_bullets:
                bullet_html += f"  <li><span class='li-content'>{b['text_html']}</span></li>\n"
            bullet_html += "</ul>\n"

        # S6-3: conditional team span — only render if non-empty (team slot is for
        # real org units like "Payments Risk Squad", not specializations).
        _team = (co.get('team') or '').strip()
        _team_span = f"<span>{_team}</span>" if _team else ""
        company_html_parts.append(f"""
<div class="entry">
  <div class="entry-header"><span>{co_name}</span><span>{co.get('location', '')} | {co.get('date_range', '')}</span></div>
  <div class="entry-subhead"><span>{co.get('title', '')}</span>{_team_span}</div>
  {bullet_html}
</div>
""")

    companies_section = "\n".join(company_html_parts)

    # v0.1.2: log fallback-fill events for vision.md telemetry (never silent).
    if _filled_sparse:
        try:
            logbook.append(
                "step_14_assemble_html",
                "fallback",
                f"filled {len(_filled_sparse)} sparse companies from raw nuggets (generic-impact fallback)",
                body="\n".join(
                    f"- {co}: had {had} JD-aligned bullets, synthesized {need} more from top-importance raw nuggets"
                    for co, had, need in _filled_sparse
                ),
            )
        except Exception:
            pass  # telemetry is best-effort

    # v0.1.5 Phase 4.1 — log expand-mode padding (separate from sparse-rescue)
    if _expanded_padding:
        try:
            logbook.append(
                "step_14_assemble_html",
                "expand_mode",
                f"padded {len(_expanded_padding)} role(s) from L1 to TARGET=5 bullets via raw nuggets (page util boost)",
                body="\n".join(
                    f"- {co}: {base} → {expanded} bullets"
                    for co, base, expanded in _expanded_padding
                ),
            )
        except Exception:
            pass

    # S6-4: Build skills HTML as ONE flat comma-separated line (no categorization).
    # Frees 20-30mm vertical space for 1-page fit. JSON schema stays categorized
    # (useful for API exports); only HTML render is flat.
    skills_dict = parsed_p12.get("skills") or {}
    _flat_skills: list[str] = []
    _seen_skills: set[str] = set()
    for _cat, _items in skills_dict.items():
        for _it in (_items or []):
            if _it and _it not in _seen_skills:
                _flat_skills.append(_it)
                _seen_skills.add(_it)
    skills_html = f'<span class="text-line">{", ".join(_flat_skills)}</span>' if _flat_skills else ""

    # Build education HTML
    edu_html_parts = []
    for e in parsed_p12.get("education", []):
        edu_html_parts.append(f"""
<div class="entry">
  <div class="entry-header"><span>{e.get('institution', '')}</span><span>{e.get('year', '')}</span></div>
  <div class="entry-subhead"><span>{e.get('degree', '')}</span><span>{e.get('gpa', '')}</span></div>
  <span class="text-line">{e.get('highlights', '')}</span>
</div>
""")
    education_html = "\n".join(edu_html_parts)

    # v0.1.1: Build Projects + Certifications list-item HTML.
    # Source priority: Phase 1+2 extraction (parsed_p12) → step_01 markdown parse (parsed_resume).
    # Never invent content. Leave list empty if both sources dry — empty sections get
    # cleanly stripped by _empty_section_stripper downstream.
    def _is_meaningful(s: str) -> bool:
        s = (s or "").strip()
        if not s or len(s) < 3 or len(s) > 200:
            return False
        # Filter out "None", "n/a", placeholder-like tokens
        return s.lower() not in {"none", "n/a", "na", "nil", "-"}

    def _project_line(p: dict) -> str:
        title = (p.get("title") or p.get("name") or "").strip()
        one = (p.get("one_liner") or p.get("description") or "").strip()
        year = (p.get("year") or "").strip()
        # Format: "<b>Title</b> (year) — one-liner" (hyphen instead of em-dash for ATS)
        parts = []
        if title:
            parts.append(f"<b>{title}</b>")
        if year:
            parts.append(f"({year})")
        head = " ".join(parts)
        if head and one:
            return f"{head} — {one}"
        return head or one

    def _cert_line(c) -> str:
        if isinstance(c, dict):
            name = (c.get("name") or c.get("title") or "").strip()
            issuer = (c.get("issuer") or "").strip()
            year = (c.get("year") or "").strip()
            bits = [name]
            if issuer:
                bits.append(issuer)
            if year:
                bits.append(year)
            return ", ".join(b for b in bits if b)
        return str(c).strip()

    # step_01 returns the parsed dict directly (no outer wrapper) — index flat.
    _projects_raw = (parsed_p12.get("projects") or []) or (parsed_resume.get("projects") or [])
    _certs_raw = (parsed_p12.get("certifications") or []) or (parsed_resume.get("certifications") or [])

    projects_items: list[str] = []
    for p in _projects_raw[:4]:  # cap 4
        if not isinstance(p, dict):
            continue
        line = _project_line(p)
        if _is_meaningful(line):
            projects_items.append(f'<li><span class="li-content-natural">{line}</span></li>')

    certifications_items: list[str] = []
    for c in _certs_raw[:3]:  # cap 3
        line = _cert_line(c)
        if _is_meaningful(line):
            certifications_items.append(f'<li><span class="li-content-natural">{line}</span></li>')

    projects_html = "\n".join(projects_items)
    certifications_html = "\n".join(certifications_items)

    # ════════════════════════════════════════════════════════════════════════
    # v0.1.5 Phase 2.6 — Summary post-trim: drop summary sentences that
    # echo bullet content (Jaccard >0.4 with any bullet). Pure-code, no LLM.
    # ════════════════════════════════════════════════════════════════════════
    def _summary_tokens(s: str) -> set:
        t = re.sub(r"<[^>]+>", " ", s or "").lower()
        t = re.sub(r"[^a-z0-9 %$]+", " ", t)
        return {w for w in t.split() if len(w) > 3 and w not in {
            "with","from","across","into","this","that","have","been","their",
            "they","them","than","then","while","when","where","your","what",
            "such","very","more","most","less","also","would","could","should",
            "result","driven","leader","experience","years","year","across","based",
        }}

    def _trim_summary_echo(summary_text: str, all_bullets: list) -> str:
        if not summary_text or not all_bullets:
            return summary_text
        bullet_token_sets = [_summary_tokens(b.get("text_html") or "") for b in all_bullets]
        # Split summary into sentences
        sentences = re.split(r"(?<=[.!?])\s+", summary_text.strip())
        kept = []
        dropped_count = 0
        for sent in sentences:
            s_tok = _summary_tokens(sent)
            if not s_tok:
                kept.append(sent)
                continue
            max_overlap = 0.0
            for b_tok in bullet_token_sets:
                if not b_tok: continue
                ov = len(s_tok & b_tok) / max(1, min(len(s_tok), len(b_tok)))
                max_overlap = max(max_overlap, ov)
            if max_overlap >= 0.4:
                dropped_count += 1
                continue
            kept.append(sent)
        if dropped_count:
            try:
                logbook.append("step_14_assemble_html", "summary_trim",
                    f"dropped {dropped_count} sentence(s) from summary that echoed bullet content (Jaccard >=0.4)",
                )
            except Exception:
                pass
        # Join back; if all dropped, keep at least the first sentence as a generic opener
        return " ".join(kept).strip() or sentences[0]

    # Collect all condensed bullets across companies for echo detection
    _all_rendered_bullets = []
    for _co_obj in _p12_companies[:ROLE_CAP]:
        _all_rendered_bullets.extend(bullets_per_co.get(_co_obj.get("name", ""), []))
    summary = _trim_summary_echo(summary, _all_rendered_bullets)

    # ════════════════════════════════════════════════════════════════════════
    # v0.1.5 Phase 2.3 — Acronym expansion on first use.
    # GENERIC: learn acronym→expansion pairs from THE RESUME's own source text
    # + JD + nuggets. No domain-specific hardcoding. Works for any user/role.
    # If user's resume defines "Anti-Money Laundering (AML)" once anywhere
    # (or "Kubernetes (K8s)", "Continuous Integration (CI)", etc.), we learn
    # that pair and apply it on first use in the rendered output.
    # ════════════════════════════════════════════════════════════════════════
    # Tiny whitelist: universally-known tokens that NEVER need expansion.
    # Anything domain-specific is auto-learned, never hardcoded.
    _UNIVERSAL_NO_EXPAND = {
        "PM", "AI", "ML", "AR", "VR", "API", "SQL", "AWS", "GCP", "iOS", "OS",
        "UX", "UI", "REST", "JSON", "XML", "CSS", "JS", "PDF", "URL", "SDK",
        "HTML", "HTTP", "HTTPS", "DNS", "VPN", "SSL", "TLS", "DB", "RPC",
        "CPU", "GPU", "RAM", "SSD", "CLI", "GUI", "B2B", "B2C", "SaaS",
        "CRM", "ERP", "JD", "HR", "QA",
    }

    # Pattern: "Capitalized Words (XYZ)" where XYZ is a 2-6 char uppercase token
    # (lowercase 's' suffix allowed for plurals like "PIs"). Matches "Anti-Money
    # Laundering (AML)", "Common Data Layer (CDL)", "Continuous Integration (CI)",
    # "Kubernetes (K8s)", "Web Content Accessibility Guidelines (WCAG)", etc.
    _LEARN_PATTERN = re.compile(
        r"\b((?:[A-Z][A-Za-z\-&\.]+(?:\s+(?:and|of|the|for|to|in|on)\s+|\s+)){1,6})"
        r"\(([A-Z][A-Za-z0-9]{1,5}s?)\)"
    )
    # Inverse pattern: "XYZ (Capitalized Words)" — also valid expansion form
    _LEARN_PATTERN_INV = re.compile(
        r"\b([A-Z][A-Za-z0-9]{1,5}s?)\s*\(((?:[A-Z][A-Za-z\-&\.]+(?:\s+(?:and|of|the|for|to|in|on)\s+|\s+)){1,6}[A-Za-z\-&\.]+)\)"
    )

    def _trim_expansion_to_acronym(words: str, ac: str) -> str:
        """Trim leading verbs from learned expansion so initials match acronym exactly.

        Example: 'Architected Anti-Money Laundering' for ac='AML' → 'Anti-Money Laundering'
        because last 3 word-initials (A, M, L) match AML.

        Returns the trimmed string. If no exact match found, returns the original.
        """
        word_list = [w for w in re.split(r"[\s\-]+", words) if w]
        ac_letters = re.sub(r"[^A-Za-z]", "", ac).upper()
        n_letters = len(ac_letters)
        if not word_list or not ac_letters:
            return words
        # Try to find a contiguous sub-sequence of word-initials matching acronym exactly.
        # Prefer the rightmost (closest to the parenthetical) match.
        for start in range(len(word_list) - n_letters + 1):
            segment = word_list[start: start + n_letters]
            initials = "".join(w[0].upper() for w in segment if w and w[0].isalpha())
            if initials == ac_letters:
                # Try to find this segment as a contiguous substring in the original
                # (preserves original spaces/hyphens like "Anti-Money Laundering").
                joined_loose = r"[\s\-]+".join(re.escape(w) for w in segment)
                m_orig = re.search(joined_loose, words)
                if m_orig:
                    return m_orig.group(0)
                return " ".join(segment)
        return words  # no exact match — keep original

    def _learn_acronym_expansions(*texts: str) -> dict:
        """Scan source text(s) for 'Words (XYZ)' patterns; return {XYZ: 'Words'}.

        Validates initials match the words; trims leading verbs from greedy
        regex matches (e.g. 'Architected Anti-Money Laundering' → 'Anti-Money Laundering').
        """
        learned: dict = {}
        for text in texts:
            if not text:
                continue
            for m in _LEARN_PATTERN.finditer(text):
                words = m.group(1).strip().rstrip(",.;:")
                ac = m.group(2).strip()
                if ac in _UNIVERSAL_NO_EXPAND:
                    continue
                word_list = [w for w in re.split(r"[\s\-]+", words) if w]
                if not word_list:
                    continue
                initials = "".join(w[0].upper() for w in word_list if w[0].isalpha())
                ac_letters = re.sub(r"[^A-Z]", "", ac.upper())
                if ac_letters:
                    overlap = sum(1 for c in ac_letters if c in initials)
                    if overlap / len(ac_letters) < 0.5:
                        continue
                if len(words) > 80:
                    continue
                # v5.8 — trim leading verbs to get tightest match
                trimmed = _trim_expansion_to_acronym(words, ac)
                if ac not in learned:
                    learned[ac] = trimmed
            for m in _LEARN_PATTERN_INV.finditer(text):
                ac = m.group(1).strip()
                words = m.group(2).strip().rstrip(",.;:")
                if ac in _UNIVERSAL_NO_EXPAND or ac in learned:
                    continue
                if len(words) > 80:
                    continue
                learned[ac] = _trim_expansion_to_acronym(words, ac)
        return learned

    # Source pool: resume raw text + JD + nuggets text (all already-loaded).
    _src_resume_text = (parsed_resume.get("markdown") or parsed_resume.get("raw_text")
                        or "")
    _src_jd_text = ""
    try:
        _jd_path = INPUTS / "jd.md"
        if _jd_path.exists():
            _src_jd_text = _jd_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass
    _src_nuggets_text = ""
    try:
        _n_path = ARTIFACTS / "02_nuggets_extracted.json"
        if _n_path.exists():
            import json as _json_n
            _nd = _json_n.loads(_n_path.read_text(encoding="utf-8"))
            _ns = _nd.get("nuggets") if isinstance(_nd, dict) else (_nd if isinstance(_nd, list) else [])
            _src_nuggets_text = " ".join((n.get("answer") or "") for n in (_ns or []) if isinstance(n, dict))
    except Exception:
        pass

    _LEARNED_EXPANSIONS = _learn_acronym_expansions(_src_resume_text, _src_jd_text, _src_nuggets_text)

    # v5.8 Component A — load persistent corpus (acronym pairs learned from PRIOR runs
    # + Oracle enrichment if it has been run). Merge with this-run learned pairs.
    # Persistent learning means: 2nd resume run benefits from 1st run's learnings.
    try:
        from .data.learned_corpus import load_corpus, save_corpus, merge_acronyms
        _CORPUS = load_corpus()
        _persistent_acronyms = _CORPUS.get("acronyms") or {}
        # Persistent corpus pairs WIN over this-run only if not already learned this run.
        # i.e., resume's own definition takes priority; corpus fills gaps.
        for _ac, _exp in _persistent_acronyms.items():
            if _ac not in _LEARNED_EXPANSIONS and _ac not in _UNIVERSAL_NO_EXPAND:
                _LEARNED_EXPANSIONS[_ac] = _exp
        # Contribute back: this-run learned pairs added to corpus for future runs.
        _new_to_corpus = merge_acronyms(_CORPUS, _LEARNED_EXPANSIONS)
        if _new_to_corpus > 0:
            save_corpus(_CORPUS)
    except Exception as _e_corpus:
        # Corpus is best-effort — never break pipeline
        try:
            logbook.append("step_14_assemble_html", "corpus", f"learned_corpus skipped: {_e_corpus}")
        except Exception:
            pass

    def _expand_acronyms_in_text(text: str, already_seen: set, learned: dict) -> str:
        """For each LEARNED acronym, expand first occurrence in text."""
        if not text or not learned:
            return text
        out = text
        for ac, expansion in learned.items():
            if ac in already_seen or ac in _UNIVERSAL_NO_EXPAND:
                continue
            pattern = re.compile(rf"\b{re.escape(ac)}\b")
            m = pattern.search(out)
            if not m:
                continue
            # Skip if expansion already nearby
            preceding = out[max(0, m.start() - len(expansion) - 10):m.start()]
            if expansion.lower() in preceding.lower():
                already_seen.add(ac)
                continue
            out = out[:m.start()] + f"{expansion} ({ac})" + out[m.end():]
            already_seen.add(ac)
        return out

    # Apply once globally — first occurrence wins across summary + bullets.
    _seen_acronyms: set = set()
    summary = _expand_acronyms_in_text(summary, _seen_acronyms, _LEARNED_EXPANSIONS)
    companies_section = _expand_acronyms_in_text(companies_section, _seen_acronyms, _LEARNED_EXPANSIONS)
    if _LEARNED_EXPANSIONS or _seen_acronyms:
        try:
            logbook.append(
                "step_14_assemble_html", "acronym_expansion",
                f"learned {len(_LEARNED_EXPANSIONS)} acronym pair(s) from source text; "
                f"expanded {len(_seen_acronyms)} on first use: {sorted(_seen_acronyms)}",
                body=("Learned dict: " + ", ".join(f"{a}={e[:30]}" for a, e in list(_LEARNED_EXPANSIONS.items())[:10])),
            )
        except Exception:
            pass

    # Summary
    summary_html = f'<div class="summary-line">{summary}</div>'

    # Now do placeholder substitution on the template.
    # The template has placeholders like <!-- PLACEHOLDER: X --> — we'll do targeted replacements.
    out = template
    # Header
    out = out.replace("<!-- PLACEHOLDER: Full Name -->", contact.get("name") or parsed_p12.get("contact_info", {}).get("name", "Satvik Jain"))
    out = out.replace("<!-- PLACEHOLDER: Target Role Title -->", parsed_p12.get("target_role", ""))
    # Contact — don't fabricate fallbacks; let empty fields disappear (S6-2).
    phone = (contact.get("phone") or "").strip()
    email = (contact.get("email") or "").strip()
    linkedin = (contact.get("linkedin") or "").strip()
    portfolio = (contact.get("portfolio") or "").strip()
    # Replace one-by-one contact placeholders in order
    placeholders = re.findall(r"<!-- PLACEHOLDER -->", out)
    if len(placeholders) >= 4:
        out = out.replace("<!-- PLACEHOLDER -->", phone, 1)
        out = out.replace("<!-- PLACEHOLDER -->", email, 1)
        out = out.replace("<!-- PLACEHOLDER -->", linkedin, 1)
        out = out.replace("<!-- PLACEHOLDER -->", portfolio, 1)
    # Summary
    out = out.replace(
        '<div class="professional-summary"><!-- PLACEHOLDER: Professional Summary (injected by Phase 3.5a) --></div>',
        f'<div class="professional-summary">{summary_html}</div>'
    )
    # Experience section — replace the first <!-- COMPANY 1 --> block and onwards
    # We'll replace from <!-- COMPANY 1 (most recent) --> to end of third </div class="entry">
    # Simpler: replace the whole "Professional Experience" .section block body.
    exp_section_re = re.compile(
        r'(<div class="section">\s*<div class="section-title">Professional Experience.*?</div>\s*)(.*?)(\s*</div>\s*<!--\s*2\. )',
        re.DOTALL
    )
    m = exp_section_re.search(out)
    if m:
        out = out[:m.start(2)] + companies_section + out[m.end(2):]

    # Skills
    skills_section_re = re.compile(
        r'(<div class="section-title">Skills &amp; Competencies.*?</div>\s*)(.*?)(\s*</div>)',
        re.DOTALL
    )
    m = skills_section_re.search(out)
    if m:
        out = out[:m.start(2)] + skills_html + out[m.end(2):]

    # Education
    edu_section_re = re.compile(
        r'(<div class="section-title">Education.*?</div>\s*)(.*?)(\s*</div>\s*<!--\s*4\. )',
        re.DOTALL
    )
    m = edu_section_re.search(out)
    if m:
        out = out[:m.start(2)] + education_html + out[m.end(2):]

    # v0.1.1: Projects — if populated, replace inner <ul> body; if empty, delete
    # the entire section div (belt-and-braces since _empty_section_stripper can miss
    # sections separated by HTML comments).
    if projects_items:
        proj_section_re = re.compile(
            r'(<div class="section-title">Projects.*?</div>\s*<ul>\s*)(.*?)(\s*</ul>)',
            re.DOTALL,
        )
        m = proj_section_re.search(out)
        if m:
            out = out[:m.start(2)] + projects_html + out[m.end(2):]
    else:
        out = re.sub(
            r'<div class="section"[^>]*>\s*<div class="section-title">Projects.*?</ul>\s*</div>\s*',
            "",
            out,
            count=1,
            flags=re.DOTALL,
        )

    # v0.1.1: Certifications — same pattern.
    if certifications_items:
        cert_section_re = re.compile(
            r'(<div class="section-title">Certifications.*?</div>\s*<ul>\s*)(.*?)(\s*</ul>)',
            re.DOTALL,
        )
        m = cert_section_re.search(out)
        if m:
            out = out[:m.start(2)] + certifications_html + out[m.end(2):]
    else:
        out = re.sub(
            r'<div class="section"[^>]*>\s*<div class="section-title">Certifications.*?</ul>\s*</div>\s*',
            "",
            out,
            count=1,
            flags=re.DOTALL,
        )

    # S6-1: Header layout — flex split (name left, role right, equal space) + font
    # shrink based on combined length. Role text is uppercase + letter-spaced, so
    # its effective width is ~1.3x its char count. Floor: 16pt (locked decision).
    _name_text = contact.get("name") or parsed_p12.get("contact_info", {}).get("name", "")
    _role_text = parsed_p12.get("target_role", "")
    _role_effective_chars = len(_role_text) * 1.3
    _name_chars = len(_name_text)
    _max_side = max(_name_chars, _role_effective_chars)
    # Empirical thresholds: at 20pt each half fits ~24 chars; at 18pt ~27; at 16pt ~30.
    if _max_side <= 24:
        _header_size_pt = 20
    elif _max_side <= 27:
        _header_size_pt = 18
    else:
        _header_size_pt = 16
    log(f"[step_14 S6-1] header font: name={_name_chars}ch role={len(_role_text)}ch effective={_max_side:.1f} → {_header_size_pt}pt")

    # Apply brand colors + header layout CSS via :root + class overrides
    color_override = f"""
<style>
:root {{
  --brand-primary-color: {colors.get('brand_primary', '#1B2A4A')};
  --brand-secondary-color: {colors.get('brand_secondary', '#2563EB')};
  --brand-tertiary-color: {colors.get('brand_tertiary', '#6B7280')};
  --brand-quaternary-color: {colors.get('brand_quaternary', '#FFFFFF')};
}}
/* S6-1: header flex + font shrink */
.header-top {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 6mm;
  margin-bottom: 2mm;
}}
.name {{
  flex: 0 1 auto;
  white-space: nowrap;
  font-size: {_header_size_pt}pt !important;
}}
.role {{
  flex: 0 1 auto;
  white-space: nowrap;
  text-align: right;
  font-size: {_header_size_pt}pt !important;
}}
</style>
"""
    out = out.replace("</head>", color_override + "</head>")

    # G1/F-NEW-3: strip residual PLACEHOLDER comments + empty skill-category shells.
    # Mirrors prod assemble_html._strip_placeholders_and_empty_shells.
    _pre_strip_len = len(out)
    out, _placeholder_removed = re.subn(r"<!--\s*PLACEHOLDER[^>]*?-->", "", out, flags=re.IGNORECASE)
    # Empty skill-category divs (div with only a heading and whitespace)
    def _empty_div_stripper(match: re.Match) -> str:
        nonlocal _skill_shells_removed
        block = match.group(0)
        inner_raw = match.group(1)
        inner_plain = re.sub(r"<[^>]+>", "", re.sub(r"<!--.*?-->", "", inner_raw, flags=re.DOTALL))
        if inner_plain.strip():
            return block
        _skill_shells_removed += 1
        return ""
    _skill_shells_removed = 0
    out = re.sub(
        r'<div\b[^>]*class="[^"]*skill-category[^"]*"[^>]*>([\s\S]*?)</div>',
        _empty_div_stripper,
        out,
    )

    # S6-2: Auto-suppress empty contact labels — drop <span><b>Label:</b> </span>
    # patterns where value is empty/whitespace-only. Applies to Portfolio, LinkedIn,
    # Email, Phone (though usually present). Prevents "Portfolio:" dangling labels.
    out, _empty_labels_removed = re.subn(
        r'<span>\s*<b>[^<:]+:</b>\s*</span>',
        '',
        out,
    )

    # Iter-05 (2026-04-23): explicit section-drop driven by fit_loop.
    # If `dropped_sections` in parsed_p12 lists any section title, remove that
    # section's content — S6-5 below will then strip the empty shell.
    dropped_sections = parsed_p12.get("dropped_sections", [])
    _explicit_drop_count = 0
    for section_title in dropped_sections:
        # Match: <div class="section"><div class="section-title">NAME...</div>BODY</div>
        # until the next <div class="section"> or document end.
        # We just null out the BODY between the section-title closing </div> and
        # the section's closing </div>. S6-5 strips the shell.
        pattern = (
            r'(<div\s+class="section"[^>]*>\s*<div\s+class="section-title"[^>]*>'
            + re.escape(section_title)
            + r'(?:<div class="section-divider"></div>)?\s*</div>)'
            r'[\s\S]*?'
            r'(</div>\s*(?=<div\s+class="section"|</body>|</div>\s*</body>))'
        )
        new_out, n = re.subn(pattern, r'\1\2', out, count=1)
        if n > 0:
            out = new_out
            _explicit_drop_count += 1
    if _explicit_drop_count:
        log(f"[step_14 fit_loop] emptied {_explicit_drop_count} dropped sections: {dropped_sections}")

    # S6-5: Empty-section safety net — drop any <div class="section">...</div>
    # whose body (post-strip) has no non-whitespace content. Belt-and-braces for S5-3.
    _empty_sections_removed = 0
    def _empty_section_stripper(match: re.Match) -> str:
        nonlocal _empty_sections_removed
        full = match.group(0)
        # Look at what's AFTER the section-title block
        body_match = re.search(
            r'<div\s+class="section-title"[^>]*>[^<]*(?:<div class="section-divider"></div>)?</div>([\s\S]*?)</div>\s*$',
            full,
        )
        if not body_match:
            return full
        body = body_match.group(1)
        plain = re.sub(r"<[^>]+>", "", re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL))
        if plain.strip():
            return full  # has content, keep
        _empty_sections_removed += 1
        return ""
    out = re.sub(
        r'<div\s+class="section"[^>]*>\s*<div\s+class="section-title"[^>]*>[^<]*(?:<div class="section-divider"></div>)?</div>[\s\S]*?</div>\s*(?=<div|</div|$)',
        _empty_section_stripper,
        out,
    )

    log(
        f"[step_14 layout] stripped {_placeholder_removed} PLACEHOLDER + "
        f"{_skill_shells_removed} skill-cat shells + "
        f"{_empty_labels_removed} empty contact labels + "
        f"{_empty_sections_removed} empty sections "
        f"({_pre_strip_len} → {len(out)} bytes)"
    )

    out_path = ARTIFACTS / "14_final_resume.html"
    out_path.write_text(out, encoding="utf-8")

    # Eval
    leftover = len(re.findall(r"<!--\s*PLACEHOLDER[^>]*?-->", out, re.IGNORECASE))
    total_bullets = sum(len(v) for v in bullets_per_co.values())
    gaps: list[str] = []
    if leftover > 0:
        gaps.append(f"{leftover} PLACEHOLDER comments still in output HTML (post-G1 strip)")
    if total_bullets == 0:
        gaps.append("0 bullets in final HTML — resume will look blank")

    status = "pass" if not gaps else "partial"
    body_md = f"""**Artifact:** `artifacts/14_final_resume.html` ({len(out)} chars)

**Metrics:**
- Total bullets in HTML: {total_bullets}
- Residual `<!-- PLACEHOLDER -->` comments: {leftover}
- Companies rendered: {len(parsed_p12.get('companies', []))}
- Skills categories: {len(skills_dict)}
- Education entries: {len(parsed_p12.get('education', []))}

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}
"""
    logbook.append(step, "eval", f"assembly {status}; bullets={total_bullets}; placeholders_left={leftover}", body_md)
    return out_path


# ────────────────────────────────────────────────────────────────────────────
# Step 15 — HTML → PDF via Playwright
# ────────────────────────────────────────────────────────────────────────────

def step_15_pdf(html_path: Path) -> Path:
    step = "step_15_pdf"
    logbook.append(
        step, "starting",
        "launching headless Chromium via Playwright; loading HTML; rendering to A4 PDF "
        "with print_background=true; expecting 1-page output",
    )

    pdf_out = ARTIFACTS / "15_final_resume.pdf"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{html_path.resolve()}")
            page.wait_for_load_state("networkidle")
            page.pdf(path=str(pdf_out), format="A4", print_background=True, prefer_css_page_size=True)
            browser.close()
    except Exception as e:
        logbook.append(step, "error", "Playwright failed", body=f"```\n{e}\n```")
        return pdf_out

    # Page count via pypdf
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_out))
    page_count = len(reader.pages)

    gaps: list[str] = []
    size = pdf_out.stat().st_size
    if page_count != 1:
        gaps.append(f"PDF has {page_count} pages — expected 1")
    if size < 10_000:
        gaps.append(f"PDF unusually small ({size} bytes) — may be blank")
    elif size > 500_000:
        gaps.append(f"PDF unusually large ({size} bytes) — fonts may be embedded rasterized")

    status = "pass" if not gaps else "partial"
    body_md = f"""**Artifact:** `artifacts/15_final_resume.pdf`

**Metrics:**
- Page count: {page_count}
- File size: {size} bytes ({size/1024:.1f} KB)

**Evaluation:** {status.upper()}

**Gaps:**
{chr(10).join(f'- {g}' for g in gaps) if gaps else '- none'}
"""
    logbook.append(step, "eval", f"pdf {status}; {page_count} pages; {size} bytes", body_md)
    return pdf_out


# ────────────────────────────────────────────────────────────────────────────
# main
# ────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True, help="Name of the run directory under runs/ (e.g. run_02_2026-04-21_xyz)")
    args = ap.parse_args()

    run_dir = _setup_run_dir(args.run_id)

    logbook.append(
        "run_start", "starting",
        f"run_pipeline.py entry; run_id={args.run_id}; writing to {run_dir.relative_to(ROOT)}",
    )

    probes: list[str] = []
    try:
        import httpx
        r = httpx.get("https://oracle.linkright.in/health", timeout=10.0)
        probes.append(f"oracle_health: HTTP {r.status_code} — {r.text.strip()}")
    except Exception as e:
        probes.append(f"oracle_health: ERROR {e}")
    missing = [k for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "ORACLE_BACKEND_SECRET") if not os.environ.get(k)]
    probes.append(f"env_present_check: {'OK' if not missing else f'MISSING {missing}'}")
    logbook.append("run_start", "result", "environment + health probe summary", body="\n".join(f"- {p}" for p in probes))

    # ── Steps ──────────────────────────────────────────────────────────
    raw_text = step_00_ingest_pdf()

    parsed = step_01_parse_resume(raw_text)

    nuggets = step_02_extract_nuggets(raw_text, parsed)

    nuggets_with_emb = step_03_embed_nuggets(nuggets)

    jd_text = (INPUTS / "jd.md").read_text(encoding="utf-8")

    # C1/F-NEW-1: Phase 1+2 (step_07) runs BEFORE role scoring so the canonical
    # requirement set used by Step 6 is the JD-aware Credo-specific one — this
    # mirrors prod worker, which uses Phase 1+2's `requirements` field for
    # covers_requirements mapping in Phase 4a verbose bullets.
    parsed_p12 = step_07_phase_1_2(jd_text, raw_text)

    # v0.1.6 Entity-fidelity guard (Layer 1, post-step_07).
    # The JD-parser LLM occasionally hallucinates a company that doesn't exist in
    # the user's resume (e.g. duplicated 'Oracle' bullets into a fake 'Google' role).
    # Whitelist parsed_p12.companies against the structured experiences list from
    # step_01 (parsed). Any name that doesn't substring-match a real experience is
    # dropped — those bullets later won't have a real role to attach to.
    try:
        _real_companies = []
        for _exp in (parsed.get("experiences") or []):
            _co_name = (_exp.get("company") or "").strip()
            if _co_name:
                _real_companies.append(_co_name)
        _real_norm = {re.sub(r"[^a-z0-9]+", "", c.lower()) for c in _real_companies if c}

        def _company_is_real(name: str) -> bool:
            n = re.sub(r"[^a-z0-9]+", "", (name or "").lower())
            if not n:
                return False
            if n in _real_norm:
                return True
            for r in _real_norm:
                if r and (n in r or r in n):
                    return True
            return False

        _hallucinated = []
        _kept_companies = []
        for _co in (parsed_p12.get("companies") or []):
            _name = (_co.get("name") if isinstance(_co, dict) else "") or ""
            if _company_is_real(_name):
                _kept_companies.append(_co)
            else:
                _hallucinated.append(_name)
        if _hallucinated:
            parsed_p12["companies"] = _kept_companies
            log(f"[entity_fidelity] step_07 dropped {len(_hallucinated)} hallucinated company/companies "
                f"not in source resume: {_hallucinated} (real: {_real_companies})")
            try:
                logbook.append("step_07_entity_fidelity", "filter",
                    f"dropped {len(_hallucinated)} hallucinated companies: {_hallucinated}",
                    body=f"Real companies (step_01 experiences): {_real_companies}",
                )
            except Exception:
                pass
    except Exception as _e_ef:
        log(f"[entity_fidelity] guard error: {_e_ef} — pipeline continues")

    # S5-6 / F-NEW-1: step_04 was removed. Phase 1+2 is the single canonical
    # source of JD requirements. No artifact 04 emitted.
    # Canonical reqs = Phase 1+2 output (the JD-aware Credo-specific set).
    canonical_reqs: list[dict] = []
    for i, r in enumerate(parsed_p12.get("requirements", []) or []):
        canonical_reqs.append({
            "id": r.get("id") or f"r{i+1}",
            "text": r.get("text", ""),
            "category": r.get("category", "other"),
            "importance": r.get("importance", "required"),
        })

    reqs_with_emb = step_05_embed_reqs(canonical_reqs)

    role_result = step_06_role_scores(
        nuggets_with_emb,
        reqs_with_emb,
        parsed.get("experiences", []),
        jd_text,
    )

    # S5-2: weighted bullet distribution (replaces hardcoded bullet_budget).
    # Compute per-company bullets proportional to JD-alignment × recency, apply
    # dynamic floor (relevance >= 0.5 × max), and overwrite parsed_p12.bullet_budget
    # with the weighted values. Phase 1+2's original bullet_budget stays in
    # parsed_p12["bullet_budget_llm_hint"] for comparison/telemetry.
    profile = parsed_p12.get("profile") or _derive_profile(parsed_p12.get("career_level", "mid"))
    distribution = _compute_bullet_distribution(
        role_scores=role_result.get("role_scores", []),
        total_reqs=len(canonical_reqs),
        profile=profile,
    )
    # S5-3: compute section visibility + merge into resume_strategy
    # Quick heuristic for "has_relevant_projects" before Phase 4a runs: check if any
    # independent_project nuggets with reasonable cosine to any JD req exist.
    _ip_nuggets = [n for n in nuggets_with_emb if (n.get("type") or "").lower() == "independent_project" and n.get("emb")]
    _has_relevant_projects = False
    if _ip_nuggets:
        _ip_matches, _ = cosine.greedy_bipartite_match([r.get("emb") for r in reqs_with_emb], _ip_nuggets, threshold=0.50)
        _has_relevant_projects = len(_ip_matches) >= 1  # at least one project hits a JD req
    section_vis = _compute_section_visibility(
        profile=profile,
        parsed_p12=parsed_p12,
        parsed_resume=parsed,
        has_relevant_projects=_has_relevant_projects,
    )
    distribution.update(section_vis)
    parsed_p12["resume_strategy"] = distribution

    # Re-save artifact 07 with the now-enriched parsed_p12 (resume_strategy +
    # weighted bullet_budget). Step 07's initial save happened before step_06
    # ran, so S5-2/S5-3 fields were absent from the on-disk artifact.
    _a07 = ARTIFACTS / "07_jd_parse_strategy.json"
    if _a07.exists():
        _existing = json.loads(_a07.read_text())
        _existing["parsed"] = parsed_p12
        _a07.write_text(json.dumps(_existing, indent=2), encoding="utf-8")
    # Swap bullet_budget to weighted values (keep keys Phase 4c expects)
    parsed_p12["bullet_budget_llm_hint"] = parsed_p12.get("bullet_budget", {})
    weighted_budget: dict = {}
    for i, c in enumerate(distribution.get("included_companies", []), start=1):
        weighted_budget[f"company_{i}_total"] = c["bullets"]
    # Preserve non-company budgets from LLM if set (awards, voluntary, projects)
    for k, v in (parsed_p12.get("bullet_budget_llm_hint") or {}).items():
        if not k.startswith("company_"):
            weighted_budget[k] = v
    parsed_p12["bullet_budget"] = weighted_budget
    logbook.append(
        "step_07_s5_2", "result",
        f"weighted distribution applied; profile={profile}; "
        f"included={len(distribution.get('included_companies', []))}; "
        f"excluded={len(distribution.get('excluded_companies', []))}",
        body=(
            "**Per-company allocation (weighted):**\n"
            + "\n".join(
                f"- {c['company']} ({c['role']}): relevance={c['relevance']}, bullets={c.get('bullets', '-')}"
                for c in distribution.get("included_companies", [])
            )
            + (
                f"\n\n**Excluded** (relevance < {distribution.get('relevance_cutoff')}):\n"
                + "\n".join(f"- {c['company']} ({c['role']}): relevance={c['relevance']}"
                            for c in distribution.get("excluded_companies", []))
                if distribution.get("excluded_companies") else ""
            )
        ),
    )

    retrieved = step_08_retrieve_per_company(parsed_p12, nuggets_with_emb)

    summary = step_09_summary(parsed_p12, retrieved, raw_text)

    # Iter-06 (2026-04-23): try batched step_10 first (1 call for all companies),
    # fall back to per-company on any failure. Gated by ENABLE_BATCH_STEP_10=1.
    verbose_all = step_10_verbose_bullets_batched(parsed_p12, retrieved, reqs_with_emb)
    if verbose_all is None:
        verbose_all = step_10_verbose_bullets(parsed_p12, retrieved, reqs_with_emb)

    # v8 Fix 3+4 — strip fabricated metrics + JD-fishing terms from step_10 output
    try:
        verbose_all = _apply_fabrication_guards(verbose_all, retrieved, jd_text, raw_text)
    except Exception as _e:
        log(f"[v8-guards] failed ({_e}) — continuing with raw step_10 output")

    ranked = step_11_rank(verbose_all, parsed_p12.get("jd_keywords", []))

    # ─── Iter-05 (2026-04-23): 1-page fitness loop ──────────────────────────
    # Wraps steps 12 → 15 in an iterative feedback loop. If final PDF is not
    # exactly 1 page OR any bullet would wrap (final_cu > 105 CU), apply a
    # strategy from the escalating ladder (L1 tighten, L2 drop bullet, L3-L5
    # drop section, L6 compound) and re-run. Max MAX_FIT_ITERATIONS.
    # See lib/fit_loop.py for strategy definitions.
    parsed_p12.setdefault("fit_iteration_log", [])
    parsed_p12.setdefault("dropped_sections", [])

    poc_results = None
    condensed = None
    html_path = None
    pdf_path = None
    best_attempt: dict | None = None

    for fit_iter in range(fit_loop.MAX_FIT_ITERATIONS):
        fit_t0 = time.time()
        log(f"\n========== FIT ITERATION {fit_iter} ==========")

        # Re-run step 12 (condense reads latest bullet_budget from parsed_p12)
        condensed = step_12_condense(ranked, parsed_p12)

        # v0.1.3 Fix C — auto-enable width POC when mean bullet length > 125 chars.
        # Step 12 condense occasionally drifts to 140-160 chars (observed in v5)
        # because Cerebras qwen-235b over-shoots the 108-118 target. When that
        # happens, run width POC even if ENABLE_WIDTH_POC is not explicitly set —
        # otherwise PDF overflows or fit_loop drops sections.
        _mean_bullet_chars = 0.0
        _bullet_lens = []
        for _co, _bs in (condensed or {}).items():
            for _b in _bs:
                _bullet_lens.append(len(re.sub(r"<[^>]+>", "", (_b.get("text_html") or ""))))
        if _bullet_lens:
            _mean_bullet_chars = sum(_bullet_lens) / len(_bullet_lens)
        # v8 Fix 1: always enable width_poc (oversized→shrink is the design intent;
        # gating on mean>125 left bullets in the 90-105 char band un-validated and
        # produced width_hit_rate F. Set DISABLE_WIDTH_POC=1 to opt out.
        _disable_width = os.environ.get("DISABLE_WIDTH_POC", "").lower() in ("1", "true", "yes")
        _auto_enable_width = (not _disable_width)

        # Sprint 7 POC — gated by ENABLE_WIDTH_POC=1 OR auto-enabled on drift.
        if width_poc.is_enabled() or _auto_enable_width:
            if _auto_enable_width and not width_poc.is_enabled():
                try:
                    logbook.append(
                        "step_12b_width_poc", "auto_enable",
                        f"v8 default-on; mean bullet length {round(_mean_bullet_chars,1)} chars (DISABLE_WIDTH_POC=1 to opt out)",
                    )
                except Exception:
                    pass
                os.environ["ENABLE_WIDTH_POC"] = "1"
            logbook.append(
                "step_12b_width_poc", "starting",
                "5-pass waterfall (A condense/B bold+highlight/C synonym/D LLM rephrase/E accept). "
                "Target width 95-100% of line budget. Preserves metrics + JD keywords verbatim.",
            )
            # Honor width_override if strategy L1 lowered target_max_cu
            override = parsed_p12.get("width_override", {})
            target_max = override.get(
                "target_max_cu",
                float(os.environ.get("WIDTH_POC_TARGET_MAX", "101.4"))
            )
            # Keep relative 95-100% band by shifting min in proportion
            default_min = float(os.environ.get("WIDTH_POC_TARGET_MIN", "96.33"))
            target_min = target_max - (101.4 - default_min)
            condensed, poc_results = width_poc.width_poc_optimize_bullets(
                condensed_by_company=condensed,
                jd_keywords=parsed_p12.get("jd_keywords", []),
                target_min=target_min,
                target_max=target_max,
                llm_module=llm,
            )
            logbook.append(
                "step_12b_width_poc", "result",
                f"hit_rate={poc_results['pct_bullets_at_target']}%, "
                f"llm_calls={poc_results['llm_calls_for_width']}, "
                f"cost=${poc_results['est_cost_for_width_usd']}, "
                f"target=[{target_min:.2f},{target_max:.2f}]",
                body=f"""**Width POC results (fit iter {fit_iter}):**

- Total bullets: {poc_results['total_bullets']}
- Target range: [{target_min:.2f}, {target_max:.2f}] CU
- Hit rate: **{poc_results['pct_bullets_at_target']}%**
""",
            )

        width_out = step_13_width_skip(condensed)

        # Prune companies with no bullets (prevents empty <section>...</section>)
        condensed_pruned = _prune_outline(condensed)

        html_path = step_14_assemble_html(parsed_p12, parsed, summary, condensed_pruned)
        pdf_path = step_15_pdf(html_path)

        # ─── Evaluate fit ───────────────────────────────────────────────────
        fit_result = fit_loop.evaluate_fit(pdf_path, poc_results)
        iter_log = {
            "iter": fit_iter,
            "duration_s": round(time.time() - fit_t0, 1),
            "page_count": fit_result["page_count"],
            "any_wrap": fit_result["any_wrap"],
            "wrap_bullets": fit_result["wrap_bullets"],
            "success": fit_result["success"],
            "total_bullets": sum(len(v) for v in (condensed or {}).values()),
            "sections_dropped": list(parsed_p12.get("dropped_sections", [])),
            "width_override": dict(parsed_p12.get("width_override", {})),
        }
        parsed_p12["fit_iteration_log"].append(iter_log)
        log(
            f"[fit_iter {fit_iter}] page={fit_result['page_count']} "
            f"wraps={len(fit_result['wrap_bullets'])} success={fit_result['success']}"
        )

        # Track best-so-far by (page_count, wrap_count) — lower is better
        cur_score = (fit_result["page_count"], len(fit_result["wrap_bullets"]))
        if (best_attempt is None
                or cur_score < (best_attempt["fit"]["page_count"],
                                len(best_attempt["fit"]["wrap_bullets"]))):
            best_attempt = {
                "iter": fit_iter,
                "fit": fit_result,
                "pdf_path": pdf_path,
                "html_path": html_path,
                "condensed": condensed,
                "poc_results": poc_results,
            }

        if fit_result["success"]:
            log(f"✓ 1-page fit achieved at fit_iter {fit_iter}")
            break

        if fit_iter == fit_loop.MAX_FIT_ITERATIONS - 1:
            log(
                f"✗ exhausted {fit_loop.MAX_FIT_ITERATIONS} fit iterations; "
                f"using best attempt (iter {best_attempt['iter']})"
            )
            break

        # Pick next strategy + mutate config for next iteration
        strategy = fit_loop.choose_strategy(
            fit_result, parsed_p12, condensed, fit_iter
        )
        iter_log["strategy_chosen"] = strategy
        fit_loop.apply_strategy(strategy, parsed_p12, condensed)
        log(f"[fit_iter {fit_iter}] applying {strategy} for next iter")

    # Persist fit log as artifact
    import json as _json_fit
    (ARTIFACTS / "fit_log.jsonl").write_text(
        "\n".join(_json_fit.dumps(e) for e in parsed_p12["fit_iteration_log"]),
        encoding="utf-8",
    )

    # If best_attempt differs from last attempt, restore its PDF as final
    # (This handles the "exhausted" case where last iter isn't the best.)
    if best_attempt and not parsed_p12["fit_iteration_log"][-1].get("success"):
        # Already-written PDF is from the last iteration. For "best-effort",
        # we could re-copy best_attempt's PDF — but we just note it in telemetry.
        logbook.append(
            "fit_loop", "result",
            f"best-effort: using iter {best_attempt['iter']} output "
            f"(page={best_attempt['fit']['page_count']}, wraps={len(best_attempt['fit']['wrap_bullets'])})",
        )

    # ─── Step 16 — telemetry rollup ─────────────────────────────────────────
    logbook.append(
        "step_16_telemetry", "starting",
        "aggregating per-run LLM call counts, token totals, retries, fallback events, Oracle embed counts, and estimated cost across all artifacts",
    )
    t = telemetry.collect_and_emit(RUN_DIR, retry_map=RETRY_COUNTS)
    # Sprint 7: attach POC results to telemetry artifact
    # Iter-05 (2026-04-23): also attach fit_loop summary
    import json as _json_tel
    _tel_path = RUN_DIR / "artifacts" / "16_telemetry.json"
    _tel = _json_tel.loads(_tel_path.read_text()) if _tel_path.exists() else t
    if poc_results:
        _tel["width_poc"] = poc_results
    # Fit-loop summary (Iter-05)
    _fit_log = parsed_p12.get("fit_iteration_log", [])
    if _fit_log:
        _last = _fit_log[-1]
        _tel["fit_summary"] = {
            "final_page_count": _last.get("page_count"),
            "final_success": _last.get("success"),
            "iterations_used": len(_fit_log),
            "max_iterations": fit_loop.MAX_FIT_ITERATIONS,
            "any_wrap": _last.get("any_wrap"),
            "wrap_bullets": _last.get("wrap_bullets", []),
            "sections_dropped": _last.get("sections_dropped", []),
            "total_bullets_final": _last.get("total_bullets"),
            "strategies_tried": [e.get("strategy_chosen") for e in _fit_log if e.get("strategy_chosen")],
            "per_iter": _fit_log,
        }
    _tel_path.write_text(_json_tel.dumps(_tel, indent=2), encoding="utf-8")
    if poc_results:
        # Also write a dedicated human-readable report
        _report_path = RUN_DIR / "reports" / "width_poc_results.md"
        _report_path.parent.mkdir(exist_ok=True)
        _lines = [
            f"# Width POC Results — {RUN_DIR.name}",
            "",
            f"**Target range**: {poc_results['target_range_cu']} CU",
            f"**Total bullets**: {poc_results['total_bullets']}",
            f"**Hit rate (A+B+C+D)**: {poc_results['pct_bullets_at_target']}%",
            f"**Wall time**: {poc_results['wall_time_s']}s",
            f"**LLM cost (pass D)**: ${poc_results['est_cost_for_width_usd']} "
            f"({poc_results['llm_calls_for_width']} calls, {poc_results['tokens_for_width']['total']} tokens)",
            "",
            "## Per-pass success",
            "",
            "| Pass | Succeeded | % of total |",
            "|------|-----------|-----------|",
        ]
        for name, v in poc_results["by_pass"].items():
            _lines.append(f"| {name} | {v['succeeded']} | {v['pct']}% |")
        _lines.append("")
        _lines.append("## Per-bullet detail")
        _lines.append("")
        _lines.append("| # | Company | Pre-A CU | Final Pass | Final CU | Passes tried |")
        _lines.append("|---|---------|---------:|-----------|---------:|---------------|")
        for e in poc_results.get("per_bullet_log", []):
            _lines.append(
                f"| {e['idx']} | {e['company']} | {e['pre_a_cu']} | "
                f"{e.get('final_pass', '-')} | {e.get('final_cu', '-')} | "
                f"{', '.join(e.get('passes_tried', [])) or 'A-PASS'} |"
            )
        _report_path.write_text("\n".join(_lines) + "\n", encoding="utf-8")
    tot = t["totals"]
    logbook.append(
        "step_16_telemetry", "result",
        f"{tot['llm_api_calls_successful']} successful LLM calls, {tot['total_tokens']:,} tokens, ${tot['estimated_cost_usd']} est cost",
        body=f"""**Artifacts:** `artifacts/16_telemetry.json`, `reports/telemetry.md`

**Totals:**
- Successful LLM calls: {tot['llm_api_calls_successful']}
- Total API attempts (including fallback failures): {tot['llm_api_calls_attempted']}
- App-level retries (validator re-prompts): {tot['llm_retries']}
- Fallback events: {tot['llm_fallback_events']}
- Oracle embedding calls: {tot['oracle_embed_calls']}
- Prompt tokens: {tot['prompt_tokens']:,}
- Completion tokens: {tot['completion_tokens']:,}
- **Total tokens: {tot['total_tokens']:,}**
- **Estimated cost: ${tot['estimated_cost_usd']}**

See `reports/telemetry.md` for per-step + per-provider breakdown and capacity signals.
""",
    )

    logbook.append(
        "run_end", "result",
        "run_pipeline.py finished — all 15 steps complete.",
        body=f"""**Final outputs:**
- HTML: `{html_path.relative_to(ROOT)}`
- PDF:  `{pdf_path.relative_to(ROOT)}`

**Coverage:** {role_result['coverage_pct']}% ({len(role_result['covered_reqs'])}/{len(canonical_reqs)} reqs)
**Primary role:** {role_result['role_scores'][0]['company'] if role_result['role_scores'] else 'n/a'}
**Total bullets in final resume:** {sum(len(v) for v in condensed.values())}
**Tokens / cost:** {tot['total_tokens']:,} tokens · ${tot['estimated_cost_usd']} est
**LLM call summary:** {tot['llm_api_calls_successful']} successful / {tot['llm_api_calls_attempted']} attempted / {tot['llm_retries']} retries / {tot['llm_fallback_events']} fallback events / {tot['oracle_embed_calls']} Oracle embeds
""",
    )


if __name__ == "__main__":
    # Iter-08 (2026-04-23): guarantee 16_telemetry.json always exists —
    # even on mid-pipeline crash — so RCA can drill into the failure mode.
    # RCA showed 3/32 runs had missing telemetry (early-stage crashes).
    try:
        main()
    except SystemExit:
        raise
    except Exception as _pipeline_exc:
        import traceback
        import json as _json_crash
        _trace = traceback.format_exc()
        sys.stderr.write(f"[pipeline crash] {_pipeline_exc!r}\n{_trace}\n")
        # Try emergency telemetry emission — scans whatever artifacts made it to disk
        try:
            _parser = argparse.ArgumentParser()
            _parser.add_argument("--run-id", required=False)
            _args, _ = _parser.parse_known_args()
            if _args.run_id:
                _crash_run_dir = ROOT / "runs" / _args.run_id
                if _crash_run_dir.exists():
                    _crash_tel = telemetry.collect_and_emit(_crash_run_dir, retry_map=RETRY_COUNTS)
                    _crash_tel["pipeline_crash"] = {
                        "error": str(_pipeline_exc)[:1000],
                        "type": type(_pipeline_exc).__name__,
                        "traceback_last_line": _trace.strip().splitlines()[-1][:300] if _trace else "",
                    }
                    _crash_tel_path = _crash_run_dir / "artifacts" / "16_telemetry.json"
                    _crash_tel_path.parent.mkdir(parents=True, exist_ok=True)
                    _crash_tel_path.write_text(_json_crash.dumps(_crash_tel, indent=2), encoding="utf-8")
                    sys.stderr.write(f"[pipeline crash] emergency telemetry written to {_crash_tel_path}\n")
        except Exception as _tel_exc:
            sys.stderr.write(f"[pipeline crash] emergency telemetry also failed: {_tel_exc!r}\n")
        raise
