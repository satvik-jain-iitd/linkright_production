"""Profile-logic helpers — UAT Cluster D (#25, #26, #27, #28, #31, #32).

These six bugs all touch the nugget pipeline at different stages, so the
helpers live in one file to keep the implementation auditable as a single
unit. Importing modules:

  - pipeline.py    → persist() + parse_and_extract() use classify + entity_resolve
  - render.py      → show_profile() uses sort_by_priority + class_of for the
                     two-pool split (facts vs experience/skill)
  - enrich.py      → extract_from_answer() uses is_fluff_metric() + sort
  - audit.py       → audit_nuggets() uses all helpers (re-classify + fluff + sort)
  - cli.py         → profile audit / profile create / profile enrich glue

# Rationale by bug:

## #25 — Nugget pool pollution
Static facts (Education degrees, Skills lists) were stored interleaved with
work_experience achievement nuggets, polluting retrieval at tailor time
(an "MBA" nugget would surface for a JD asking for "machine learning"
because vector cosine matched on "education-y" tokens). The fix is to
classify each nugget as `fact` / `experience` / `skill` and split the
retrieval tier at render + downstream consumers.

## #26 — Priority sort
Newly-enriched P0 nuggets were appending to the bottom of
nuggets.jsonl / highlights.jsonl, so `profile show` rendered them last
under their company even though P0 should lead. Fix: stable sort by
(priority bucket, original-insertion-order) at every read site.

## #27 — Entity extraction failure
Groq 70B occasionally outputs "company: none" even when the company name
appears in the raw text under the immediately-preceding ### header. The
deterministic fallback walks the parsed companies list and checks
"answer" substring overlap; if exactly one company matches, fill it in.

## #28 — Gap-filling loop
After extraction, work_experience nuggets missing role / company
should trigger an interactive follow-up rather than be silently dropped
(current behaviour drops missing-company; missing-role keeps the row but
renders as "(role unspecified)"). The helper flags gap targets; the CLI
decides whether to prompt (TTY) or warn (--yes / non-TTY).
Note: dates are NOT in the nugget-extract schema, so they are not
checked here — that surface lives on `parsed.experiences[]`.

## #31 — Fluff metric detection
Vague nuggets like "Increased business value by 100%" pass the current
"has a number + a %" check, but the noun ("business value") is unfalsifiable.
Detector matches well-known fluff nouns and rejects when paired with a
suspiciously-round number (100%, 200%, "10x", "significantly").

## #32 — Audit / cleanup phase
On-demand re-pass over existing nuggets that re-classifies, re-resolves
entities, flags fluff, and re-sorts. Idempotent; never deletes — only
demotes priority (fluff → P3) and tags `_audit_flags`. User runs after
multiple enrich sessions to clean accumulated noise.
"""

from __future__ import annotations

import re
from typing import Optional


# ─────────────────────────────────────────────────────────────────────
# #25 — Classification: fact / experience / skill
# ─────────────────────────────────────────────────────────────────────

# Atomic "fact" types are static reference data — should not enter the
# retrieval ranking pool. They render in their own section ("Facts" /
# Education / Certifications) and feed the resume header / education-block
# pipeline, not the bullet ranking.
_FACT_TYPES: frozenset[str] = frozenset({
    "education", "certification", "award", "language",
    "publication", "interest", "course", "voluntary",
    "organisation", "summary",
})

# "Experience" types contribute to bullet retrieval (the JD-aligned scoring
# pool that selects which achievements appear in the tailored resume).
_EXPERIENCE_TYPES: frozenset[str] = frozenset({
    "work_experience", "independent_project",
})

# "Skill" types are a separate tier — they feed the skills block, not the
# bullet block. Mixing them into experience retrieval surfaces low-context
# tokens ("Python") that match every tech JD spuriously.
_SKILL_TYPES: frozenset[str] = frozenset({"skill"})


def class_of(nugget: dict) -> str:
    """Return one of: 'fact', 'experience', 'skill'.

    Reads `type` field; defaults to 'experience' when the type is unknown,
    so legacy nuggets without a class field don't silently disappear from
    the bullet pool. The `nugget_class` field, when present, takes
    precedence — backfill writes it once, then later reads short-circuit.
    """
    explicit = (nugget.get("nugget_class") or "").strip().lower()
    if explicit in ("fact", "experience", "skill"):
        return explicit
    t = (nugget.get("type") or "").strip().lower()
    if t in _FACT_TYPES:
        return "fact"
    if t in _SKILL_TYPES:
        return "skill"
    # work_experience, independent_project, and anything unrecognised → experience.
    # Defaulting to "experience" preserves retrieval for legacy nuggets while
    # an "Other" type would risk silent omission from JD scoring.
    return "experience"


def classify_in_place(nuggets: list[dict]) -> int:
    """Stamp every nugget with `nugget_class` if missing. Returns count
    of rows touched (used by tests + audit telemetry)."""
    n = 0
    for nug in nuggets:
        if not (nug.get("nugget_class") or "").strip():
            nug["nugget_class"] = class_of(nug)
            n += 1
    return n


# ─────────────────────────────────────────────────────────────────────
# #26 — Priority sort
# ─────────────────────────────────────────────────────────────────────

_PRIORITY_RANK: dict[str, int] = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def priority_key(nugget: dict) -> int:
    """Return 0 (P0) … 3 (P3). Unknown / missing importance → 4 (sorts last)."""
    imp = (nugget.get("importance") or "").strip().upper()
    return _PRIORITY_RANK.get(imp, 4)


def sort_by_priority(nuggets: list[dict]) -> list[dict]:
    """Stable sort by priority ASC (P0 → P3 → unknown).

    STABLE ordering is critical — within the same priority bucket we
    preserve insertion order. Without stability, callers that append a
    new P0 to nuggets.jsonl would see the new row jump above existing
    P0s on next render, surprising users who learn "newer = lower".

    Does not mutate input; returns a new list.
    """
    return sorted(nuggets, key=priority_key)


# ─────────────────────────────────────────────────────────────────────
# #27 — Entity-resolution fallback for "unknown" company / role
# ─────────────────────────────────────────────────────────────────────

# Strings the LLM uses to signal "I don't know". Treat all as missing.
_UNKNOWN_SET: frozenset[str] = frozenset({
    "", "none", "null", "unknown", "n/a", "na", "tbd",
})


def _is_missing(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in _UNKNOWN_SET


def resolve_entity(
    nugget: dict,
    parsed: Optional[dict] = None,
    raw_text: str = "",
) -> dict:
    """Return a copy of `nugget` with `company` / `role` filled when a
    confident deterministic match is available.

    Heuristic (in order):
      1. If `company` is missing but the nugget's `answer` mentions a
         company name from `parsed["companies"]` verbatim — use it.
      2. If exactly one company in `parsed` has a matching role substring
         in `nugget.answer` — fill both.
      3. If `raw_text` is provided + the answer contains a token that
         appears in raw_text immediately AFTER an "at <X>" / "@ <X>"
         pattern — fill company.

    Never overwrites a non-missing value (avoids LLM regression risk).
    Marked with `_entity_resolved_by` flag for audit-trail visibility.
    """
    out = dict(nugget)
    if not _is_missing(out.get("company")) and not _is_missing(out.get("role")):
        return out

    answer_l = (out.get("answer") or out.get("nugget_text") or "").lower()
    if not answer_l:
        return out

    parsed_companies = (parsed or {}).get("companies", []) or []

    # Strategy 1+2: parsed companies cross-reference.
    if _is_missing(out.get("company")):
        for comp in parsed_companies:
            name = (comp.get("name") or "").strip()
            if not name:
                continue
            if name.lower() in answer_l:
                out["company"] = name
                # Try role too while we have the company match.
                role = (comp.get("title") or "").strip()
                if role and _is_missing(out.get("role")):
                    if role.lower() in answer_l:
                        out["role"] = role
                out["_entity_resolved_by"] = "parsed_companies"
                return out

    # Strategy 3: "at <Company>" / "@ <Company>" pattern in raw text.
    if _is_missing(out.get("company")) and raw_text:
        # Find "at <CapitalizedWord(s)>" in the nugget answer; verify it
        # appears in the raw resume text (no fabrication).
        m = re.search(r"\bat\s+([A-Z][\w&.\- ]{1,40})", out.get("answer") or "")
        if m:
            candidate = m.group(1).strip().rstrip(".,;)")
            # Trim multi-word match at first non-Title-Case word so we don't
            # capture "American Express building", just "American Express".
            tokens = candidate.split()
            trimmed = []
            for tok in tokens:
                if tok and (tok[0].isupper() or tok in {"&", "of", "the"}):
                    trimmed.append(tok)
                else:
                    break
            candidate = " ".join(trimmed)
            if candidate and candidate.lower() in raw_text.lower():
                out["company"] = candidate
                out["_entity_resolved_by"] = "raw_text_pattern"

    return out


# ─────────────────────────────────────────────────────────────────────
# #28 — Gap-filling target detection
# ─────────────────────────────────────────────────────────────────────

# Fields that, when missing on a work_experience nugget, justify a
# user follow-up. role/company are the only LLM-emitted-per-nugget
# fields recruiter-critical enough to surface.
#
# NOTE — "dates" deliberately NOT included:
# The NUGGET_EXTRACT_MD prompt (resume/lib/prompts.py:80-87) emits a
# fixed schema of {type, company, role, importance, answer, tags,
# leadership} — there is NO per-nugget date field. Including "dates"
# here produced spurious "missing dates" warnings on EVERY
# work_experience nugget after `profile create` (round-1 BLOCK
# CRITICAL #1: 5-gap cap was always saturated with date-flags,
# turning the new gap-fill signal into noise). Dates live on the
# parsed-resume experience entries (parsed.experiences[].start_date)
# — verifying them is a different surface (role-level, not
# nugget-level) and belongs in a future date-audit pass.
_GAP_FIELDS: tuple[str, ...] = ("company", "role")


def gap_filling_targets(nuggets: list[dict]) -> list[dict]:
    """Return a list of {nugget_index, missing: [fields]} for nuggets
    that need follow-up. Only flags work_experience class — facts and
    skills have different curation flows.

    Caller decides whether to prompt the user (TTY) or just log
    (non-TTY / --yes). Bounded: max 5 gaps surfaced per pipeline run
    so the user never faces a 30-question inquisition.

    Only checks `company` + `role` — the two fields the nugget-extract
    LLM emits per nugget (see prompts.py:NUGGET_EXTRACT_MD). Dates are
    NOT checked: they don't exist on the nugget schema, so a date
    check here would false-positive on every row.
    """
    targets: list[dict] = []
    for nug in nuggets:
        if class_of(nug) != "experience":
            continue
        # Skip independent projects — company is conventionally absent.
        if (nug.get("type") or "").lower() == "independent_project":
            continue
        missing: list[str] = []
        for field in _GAP_FIELDS:
            if _is_missing(nug.get(field)):
                missing.append(field)
        if missing:
            targets.append({
                "nugget_index": nug.get("nugget_index"),
                "answer_preview": (nug.get("answer") or nug.get("nugget_text") or "")[:120],
                "missing": missing,
            })
        if len(targets) >= 5:
            break
    return targets


# ─────────────────────────────────────────────────────────────────────
# #31 — Fluff-metric detection
# ─────────────────────────────────────────────────────────────────────

# Nouns that are vague / unfalsifiable when paired with a number. Real
# metrics name a concrete object: "revenue", "users", "latency", etc.
_FLUFF_NOUNS: frozenset[str] = frozenset({
    "business value", "stakeholder value", "shareholder value",
    "synergy", "synergies", "alignment", "engagement",
    "productivity", "efficiency", "effectiveness",
    "morale", "culture", "buy-in", "buy in",
    "visibility", "awareness", "ownership",
    "value-add", "value add", "added value",
    "innovation", "thought leadership",
    "team performance",  # too broad without a sub-metric
})

# Vague intensity words that signal hand-waving even without a noun.
_FLUFF_INTENSIFIERS: frozenset[str] = frozenset({
    "significantly", "drastically", "substantially",
    "tremendously", "vastly", "immensely",
})

# Suspiciously round percentages that almost always indicate a guess.
# 100% (exact doubling), 200%, 1000% on a fluff noun are the giveaways.
_SUSPICIOUS_PERCENTS_RE = re.compile(r"\b(100|150|200|300|500|1000)%")

# "Nx" multipliers paired with a fluff noun (10x productivity, 5x value).
_MULTIPLIER_RE = re.compile(r"\b(\d{1,3})\s*x\b", re.IGNORECASE)


def is_fluff_metric(text: str) -> bool:
    """Return True if `text` reads like a vague / unfalsifiable metric.

    Two-signal rule — must have BOTH a fluff noun (or intensifier) AND
    either a suspicious round-number OR a multiplier. This avoids false
    positives on legitimate sentences like:
      "Shipped 100% test coverage in Q3" (no fluff noun → keep)
      "Drove engagement campaign across 6 markets" (no number → keep)
      "Increased revenue 100% YoY" (concrete noun "revenue" → keep)

    Catches the documented offender:
      "Increased business value by 100%" → fluff_noun ('business value')
                                            AND suspicious 100% → flag.
    """
    if not text:
        return False
    low = text.lower()

    has_fluff_noun = any(noun in low for noun in _FLUFF_NOUNS)
    has_intensifier = any(adv in low for adv in _FLUFF_INTENSIFIERS)
    if not (has_fluff_noun or has_intensifier):
        return False

    if _SUSPICIOUS_PERCENTS_RE.search(low):
        return True
    if _MULTIPLIER_RE.search(low):
        return True
    # Intensifier-only (no number, no multiplier) is suspicious enough
    # when paired with a fluff noun.
    if has_intensifier and has_fluff_noun:
        return True
    return False


# ─────────────────────────────────────────────────────────────────────
# #32 — Audit / cleanup phase
# ─────────────────────────────────────────────────────────────────────

def audit_nuggets(
    nuggets: list[dict],
    parsed: Optional[dict] = None,
    raw_text: str = "",
) -> dict:
    """Re-run classification + entity resolution + fluff detection over
    existing nuggets. Mutates the list in place — sets `nugget_class`,
    `company`/`role` (only when blank), and adds `_audit_flags` (list)
    when a row was demoted or marked.

    Returns a counts dict: { classified, entity_resolved, fluff_demoted,
                             reprioritised, total }.

    Idempotent: re-running is a no-op when nothing changed. We NEVER
    delete a nugget — only demote priority to P3 and tag the flag.
    User retains full control to override / re-edit via enrich + truth
    engine.
    """
    counts = {
        "classified": 0,
        "entity_resolved": 0,
        "fluff_demoted": 0,
        "reprioritised": 0,
        "total": len(nuggets),
    }

    for nug in nuggets:
        # Backfill class.
        if not (nug.get("nugget_class") or "").strip():
            nug["nugget_class"] = class_of(nug)
            counts["classified"] += 1

        # Entity resolution (only if missing).
        if _is_missing(nug.get("company")) or _is_missing(nug.get("role")):
            resolved = resolve_entity(nug, parsed=parsed, raw_text=raw_text)
            if resolved.get("company") and _is_missing(nug.get("company")):
                nug["company"] = resolved["company"]
                counts["entity_resolved"] += 1
            if resolved.get("role") and _is_missing(nug.get("role")):
                nug["role"] = resolved["role"]
            if resolved.get("_entity_resolved_by"):
                nug["_entity_resolved_by"] = resolved["_entity_resolved_by"]

        # Fluff detection on the answer text.
        text = (nug.get("answer") or nug.get("nugget_text") or "")
        if is_fluff_metric(text):
            flags = nug.get("_audit_flags") or []
            if "fluff_metric" not in flags:
                flags.append("fluff_metric")
                nug["_audit_flags"] = flags
                # Demote priority — never below P3, never delete.
                cur = (nug.get("importance") or "").strip().upper()
                if cur in ("P0", "P1", "P2"):
                    nug["importance"] = "P3"
                    counts["reprioritised"] += 1
                counts["fluff_demoted"] += 1

    return counts
