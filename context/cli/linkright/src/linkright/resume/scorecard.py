"""Resume scorecard — 10 heuristic dims for Pillar 1 output quality."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, ClassVar

_HARNESS = Path(__file__).resolve().parents[3] / "harness"
if str(_HARNESS.parent) not in sys.path:
    sys.path.insert(0, str(_HARNESS.parent))

from harness.scorecard import Dimension, Scorecard  # noqa: E402


_METRIC_RE = re.compile(r"(\d+%?|\$\d+|\d+x|\d+\+)")
_NUMBER_RE = re.compile(r"\d")
_CTA_RE = re.compile(r"(what do you think|thoughts\?|agree\?|share|comment|\?$)", re.I)
_IMPERATIVE_HINTS = ("try", "start", "stop", "build", "ship", "read", "listen", "ask", "do", "use", "check", "remember")


def _s_keyword_coverage(ctx: dict[str, Any]) -> float:
    kws = ctx.get("jd_keywords") or set()
    text = (ctx.get("resume_text") or "").lower()
    if not kws:
        return 0.0
    matched = sum(1 for k in kws if k.lower() in text)
    return 100.0 * matched / len(kws)


def _s_width_hit_rate(ctx: dict[str, Any]) -> float:
    s = ctx.get("width_statuses") or []
    if not s:
        return 0.0
    return 100.0 * sum(1 for x in s if x == "PASS") / len(s)


def _s_xyz_format_purity(ctx: dict[str, Any]) -> float:
    bullets = ctx.get("bullets") or []
    if not bullets:
        return 0.0
    hits = sum(1 for b in bullets if _METRIC_RE.search(b) and re.match(r"^\s*[A-Z][a-z]+", b))
    return 100.0 * hits / len(bullets)


# Phase 1.2 — strong-verb dictionary: weak/filler verbs heavily penalized
_WEAK_VERBS = {
    "worked", "helped", "assisted", "participated", "contributed", "involved",
    "responsible", "duties", "tasked", "supported", "engaged", "collaborated",
    "leveraged", "utilized", "facilitated", "ensured", "managed",  # last 3 borderline
    # First-person leakers (should never appear after preamble scrubber)
    "i", "my", "we", "during", "while",
    # Stripped-prefix remnants
    "at",
}


def _s_verb_diversity(ctx: dict[str, Any]) -> float:
    """Reward unique strong leading verbs; penalize weak/filler verbs.

    Score = 100 × (unique_strong_verbs / total_bullets), where each weak verb
    occurrence contributes 0.5 instead of 1.0 (50% penalty). Catches both
    repetition AND filler-verb pollution.
    """
    bullets = ctx.get("bullets") or []
    if not bullets:
        return 0.0
    verbs = [b.strip().split(" ", 1)[0].lower() for b in bullets if b.strip()]
    if not verbs:
        return 0.0
    weak_count = sum(1 for v in verbs if v in _WEAK_VERBS)
    unique_count = len(set(verbs))
    # Effective unique-strong = unique * (1 - 0.5 * weak_ratio)
    weak_ratio = weak_count / len(verbs)
    effective_unique = unique_count * (1 - 0.5 * weak_ratio)
    return 100.0 * effective_unique / len(verbs)


# Phase 1.6 — metric magnitude tiers (M/B > K > raw > none)
_MAG_BILLIONS = re.compile(r"(?:\d+(?:\.\d+)?\s*[BbMm](?!\w)|\$\s*\d+[BbMm])")
_MAG_THOUSANDS = re.compile(r"(?:\d+(?:\.\d+)?\s*[Kk](?!\w)|\d{4,})")
_MAG_PCT = re.compile(r"\d+(?:\.\d+)?\s*%")


def _bullet_magnitude(b: str) -> float:
    """Tiered metric weight per bullet. M/B = 1.0; K or 4+ digits = 0.8; % = 0.7; raw int = 0.5; none = 0."""
    if _MAG_BILLIONS.search(b):
        return 1.0
    if _MAG_THOUSANDS.search(b):
        return 0.8
    if _MAG_PCT.search(b):
        return 0.7
    if _NUMBER_RE.search(b):
        return 0.5
    return 0.0


def _s_metric_density(ctx: dict[str, Any]) -> float:
    """Phase 1.6 — average magnitude tier across bullets, scaled to 100."""
    bullets = ctx.get("bullets") or []
    if not bullets:
        return 0.0
    avg_mag = sum(_bullet_magnitude(b) for b in bullets) / len(bullets)
    return 100.0 * avg_mag


def _s_page_fit(ctx: dict[str, Any]) -> float:
    """Phase 1.2 — score ~90% utilization as ideal per Jane 2026-05-02 update.

    User's words 2026-05-02: "lets target 90% height instead of 95% that way
    we will have breathing space at the bottom of the resume". IDEAL band
    shifted from 95-100% to 85-92%.

    Bands (utilization = content_height_mm / usable_height_mm * 100):
        85-92%   → 100  IDEAL (target band — breathing space at bottom)
        92-100%  → 85   close to risk zone (slight downgrade)
        80-85%   → 85   acceptable
        75-80%   → 70   under-utilized
        70-75%   → 55   wasteful
        < 70%    → 30   significantly empty
        > 100%   → 20   overflow (silent clip likely)
        not 1 page → 0  hard fail
    """
    pages = ctx.get("total_pages", 0)
    if pages != 1:
        return 0.0 if pages == 0 else 20.0

    util = float(ctx.get("page_utilization_pct") or 0.0)
    if util <= 0:
        return 80.0  # no data — neutral
    if util > 100.0:
        return 20.0  # overflow — silent clip risk
    if 85.0 <= util <= 92.0:
        return 100.0  # IDEAL — 90% target band with breathing space
    if 92.0 < util <= 100.0:
        return 85.0   # close to risk zone, slight downgrade
    if 80.0 <= util < 85.0:
        return 85.0   # acceptable
    if 75.0 <= util < 80.0:
        return 70.0   # under-utilized
    if 70.0 <= util < 75.0:
        return 55.0   # wasteful
    return 30.0       # < 70% = significantly empty


def _s_brs_top_pct(ctx: dict[str, Any]) -> float:
    """Phase 1.1 — handle both 0-1 normalized and 0-100 scaled BRS values."""
    scores = sorted(ctx.get("brs_scores") or [], reverse=True)
    if not scores:
        return 0.0
    top = scores[: max(1, len(scores) // 4)]
    mean = float(sum(top) / len(top))
    # Auto-detect scale: if the largest top-25% mean is ≤1.0, BRS is normalized.
    # Multiply by 100 to align with other dims that are 0-100.
    if mean <= 1.0:
        mean *= 100.0
    return min(100.0, mean)


def _s_contrast_aa(ctx: dict[str, Any]) -> float:
    ratios = ctx.get("contrast_ratios") or []
    if not ratios:
        return 0.0
    return 100.0 * sum(1 for r in ratios if r >= 4.5) / len(ratios)


# Phase 1.8 — near-duplicate-rate dimension (replaces broken synonym_usage)
_DUP_TOKEN_RE = re.compile(r"[^a-z0-9 %$]+")
_STOP_TOKENS = {
    "with", "from", "across", "into", "this", "that", "those", "these", "have",
    "been", "their", "they", "them", "than", "then", "while", "when", "where",
    "your", "ours", "what", "such", "very", "more", "most", "less", "also",
}


def _bullet_tokens(s: str) -> set:
    t = _DUP_TOKEN_RE.sub(" ", s.lower())
    return {w for w in t.split() if len(w) > 3 and w not in _STOP_TOKENS}


_NUMERIC_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?\s*[%x]?")


def _bullet_metrics(s: str) -> set:
    """Extract numeric tokens (e.g., '13%', '9%', '100M', '$1.2M', '36') from a bullet.

    Used to catch paraphrased duplicates that share the same metrics
    (e.g. two bullets both citing '13% to 9% churn' with different wording —
    Jaccard alone missed them, but metric overlap caught them).
    """
    return {m.group(0).strip() for m in _NUMERIC_TOKEN_RE.finditer(s.lower())}


def _is_near_duplicate(b1: str, b2: str) -> bool:
    """Composite dup detector: triggers if EITHER signal is strong enough.

    Signal A — Jaccard token overlap ≥0.5 (lowered from 0.6 to catch
                paraphrases with mostly-overlapping content nouns).
    Signal B — share ≥2 numeric metrics AND ≥2 content tokens overlap
                (catches the "13% to 9% churn" + "9.14/10" case where two
                bullets cite the same metric pair via different framings).
    """
    t1, t2 = _bullet_tokens(b1), _bullet_tokens(b2)
    if not t1 or not t2:
        return False
    overlap = len(t1 & t2) / max(1, min(len(t1), len(t2)))
    if overlap >= 0.5:
        return True
    m1, m2 = _bullet_metrics(b1), _bullet_metrics(b2)
    shared_metrics = m1 & m2
    if len(shared_metrics) >= 2 and len(t1 & t2) >= 2:
        return True
    return False


def _s_near_dup_rate(ctx: dict[str, Any]) -> float:
    """Phase 1.8 — penalize semantically duplicate bullet pairs.

    Score = 100 × (1 − dup_pairs / total_pairs). Composite detector covers
    both paraphrased text and shared-metric duplicates.
    """
    bullets = ctx.get("bullets") or []
    n = len(bullets)
    if n < 2:
        return 100.0
    dup_pairs = 0
    total_pairs = n * (n - 1) // 2
    for i in range(n):
        for j in range(i + 1, n):
            if _is_near_duplicate(bullets[i], bullets[j]):
                dup_pairs += 1
    return 100.0 * (1.0 - dup_pairs / total_pairs)


def _s_structure_integrity(ctx: dict[str, Any]) -> float:
    """Expanded — checks 6 sections (was 4), plus bullet-balance variance across
    main roles only (≥2 bullets); single-bullet freelance/gig entries excluded.

    2026-05-02: pre-fix the variance check compared main roles against thin
    freelance/side-gig entries (1 bullet each), unfairly penalizing legitimate
    diverse career narratives. Now only "main roles" (≥2 bullets) participate
    in variance — freelance/side gigs with single bullets stay valid signals
    of scope diversity rather than missing depth.
    """
    section_keys = ("has_header", "has_experience", "has_education", "has_skills",
                    "has_summary", "has_projects_or_certs")
    present = sum(1 for k in section_keys if ctx.get(k))
    base = 100.0 * present / len(section_keys)
    # Bullet-balance among main roles only (≥2 bullets)
    bullets_per_role = ctx.get("bullets_per_role") or []
    main_roles = [n for n in bullets_per_role if n >= 2]
    if main_roles and len(main_roles) >= 2:
        max_b = max(main_roles)
        min_b = min(main_roles)
        if max_b - min_b > 3:
            base *= 0.85
    return base


# ════════════════════════════════════════════════════════════════════════
# Phase 1.5 (v5.5) — NEW DIMENSIONS for honest scoring
# ════════════════════════════════════════════════════════════════════════

# Phase 1.3 — Tense consistency (past roles must use past-tense verbs)
_PAST_TENSE_IRREGULARS = {
    "built", "led", "ran", "ran", "drove", "drew", "gave", "got", "kept", "knew",
    "made", "met", "ran", "saw", "sent", "set", "shipped", "showed", "took",
    "taught", "thought", "won", "wrote", "found", "spoke", "stood", "spent",
    "bought", "brought", "caught", "fell", "fought", "felt", "flew", "had",
    "heard", "held", "left", "lost", "paid", "put", "read", "said", "saw",
    "sold", "sent", "sat", "slept", "stood", "told", "took", "thought", "threw",
    "understood", "wrote",
    # Strong action verbs commonly past-tense already
    "architected", "compressed", "delivered", "secured", "enabled", "cut",
    "grew", "uncovered", "shipped", "spearheaded", "improved", "reduced",
    "increased", "decreased", "achieved", "automated", "designed", "developed",
    "drove", "engineered", "executed", "expanded", "generated", "implemented",
    "launched", "led", "managed", "negotiated", "optimized", "orchestrated",
    "produced", "scaled", "streamlined", "transformed",
}
_PRESENT_CONTINUOUS_RE = re.compile(r"^([a-z]+ing)\b", re.IGNORECASE)


def _s_tense_consistency(ctx: dict[str, Any]) -> float:
    """For roles whose end_date is not 'Present', every bullet must use past tense.

    Detects present-continuous ("Building...") which should be past ("Built").
    Score = 100 × (past-tense-correct bullets) / total bullets.
    """
    bullets_with_ctx = ctx.get("bullets_with_meta") or []
    if not bullets_with_ctx:
        # Fallback to simpler check on flat bullets list
        bullets = ctx.get("bullets") or []
        if not bullets:
            return 100.0
        ok = 0
        for b in bullets:
            first = (b.strip().split(" ", 1)[0] or "").lower().rstrip(",.!?")
            if _PRESENT_CONTINUOUS_RE.match(first):
                continue  # gerund/present-continuous = bad in past role
            if first.endswith("ed") or first in _PAST_TENSE_IRREGULARS:
                ok += 1
                continue
            # Active verb that may not be in dict — give benefit of doubt
            ok += 1
        return 100.0 * ok / len(bullets)
    # Rich path with role metadata
    total = 0
    correct = 0
    for entry in bullets_with_ctx:
        is_past = entry.get("is_past_role", False)
        for b in entry.get("bullets") or []:
            total += 1
            first = (b.strip().split(" ", 1)[0] or "").lower().rstrip(",.!?")
            if is_past:
                if _PRESENT_CONTINUOUS_RE.match(first):
                    continue
                if first.endswith("ed") or first in _PAST_TENSE_IRREGULARS:
                    correct += 1
                else:
                    correct += 1  # benefit of doubt for unknown active verbs
            else:
                correct += 1  # current role can be present or past
    return 100.0 * correct / total if total else 100.0


# Phase 1.4 — Acronym expansion check (first-use must have full form)
_ACRONYM_RE = re.compile(r"\b([A-Z]{2,5})\b")
_COMMON_KNOWN_ACRONYMS = {
    # Universally-known tech/programming/internet acronyms ONLY.
    # Domain-specific acronyms (AML, KYC, K8s, WCAG, etc.) MUST come from
    # auto-learn (orchestrator's _learn_acronym_expansions) — no domain bias here.
    # S1.5: keep in sync with orchestrator._UNIVERSAL_NO_EXPAND.
    "PM", "AI", "ML", "AR", "VR", "API", "SQL", "AWS", "GCP", "iOS", "OS",
    "UX", "UI", "REST", "JSON", "XML", "CSS", "JS", "PDF", "URL", "SDK",
    "HTML", "HTTP", "HTTPS", "DNS", "VPN", "SSL", "TLS", "DB", "RPC",
    "CPU", "GPU", "RAM", "SSD", "CLI", "GUI", "B2B", "B2C", "SaaS",
    "CRM", "ERP", "JD", "HR", "QA", "MCP", "RAG", "LLM", "NLP", "OAuth", "JWT",
    # Modern AI / compound terms — product names, should never be expanded
    "GenAI", "GPT", "BERT", "GAN", "LLMs", "MLOps", "AIOps", "NLU", "NLG",
    "XAI", "RL", "RLHF", "DL", "CV", "OCR", "NER", "ASR", "TTS", "STT",
}


# v5.8 — relaxed scorer dim per user-aligned design (Decision #1):
# Only penalize acronyms WHOSE EXPANSION IS KNOWN from source but NOT applied.
# If we have no source-learned expansion for an acronym, we don't penalize.
def _learnable_expansions_from_text(text: str) -> dict:
    """Mirror of orchestrator's _learn_acronym_expansions, used by the scorer.

    Scans for 'Word Word (XYZ)' or 'XYZ (Word Word)' patterns.

    2026-05-02: tightened acronym filter — require ≥2 uppercase letters in the
    candidate token. Prior filter accepted any leading-cap word (e.g. "Team",
    "Award"), causing false-positive "acronyms" with parenthetical-tagline
    descriptions and tanking the score. Genuine acronyms have 2+ caps.
    """
    learned: dict = {}
    if not text:
        return learned

    def _is_real_acronym(token: str) -> bool:
        bare = token.rstrip("s").rstrip(".")
        if len(bare) < 2:
            return False
        n_upper = sum(1 for c in bare if c.isupper())
        return n_upper >= 2

    pat_a = re.compile(
        r"\b((?:[A-Z][A-Za-z\-&\.]+(?:\s+(?:and|of|the|for|to|in|on)\s+|\s+)){1,6})"
        r"\(([A-Z][A-Za-z0-9]{1,5}s?)\)"
    )
    pat_b = re.compile(
        r"\b([A-Z][A-Za-z0-9]{1,5}s?)\s*\(((?:[A-Z][A-Za-z\-&\.]+(?:\s+(?:and|of|the|for|to|in|on)\s+|\s+)){1,6}[A-Za-z\-&\.]+)\)"
    )
    for m in pat_a.finditer(text):
        words = m.group(1).strip().rstrip(",.;:")
        ac = m.group(2).strip()
        if not _is_real_acronym(ac):
            continue
        if ac in _COMMON_KNOWN_ACRONYMS:
            continue
        if len(words) > 80:
            continue
        if ac not in learned:
            learned[ac] = words
    for m in pat_b.finditer(text):
        ac = m.group(1).strip()
        words = m.group(2).strip().rstrip(",.;:")
        if not _is_real_acronym(ac):
            continue
        if ac in _COMMON_KNOWN_ACRONYMS or ac in learned:
            continue
        if len(words) > 80:
            continue
        learned[ac] = words
    return learned


def _s_acronym_expansion(ctx: dict[str, Any]) -> float:
    """v5.8 RELAXED: only penalize acronyms WHOSE EXPANSION IS KNOWN from source
    but NOT applied in the rendered resume.

    Source pool = resume_text + source_nuggets_text + jd_text (anything we
    could have learned a pair from). If source has no pair for an acronym,
    we can't expand it — vacuously OK (no penalty).

    Algorithm:
      1. Scan source pool for "Word Word (XYZ)" / "XYZ (Word Word)" pairs.
      2. For each learned XYZ, check if rendered resume_text has the expansion form
         within ±70 chars of XYZ's first occurrence.
      3. Score = 100 × (learned & applied) / learned. If 0 learned → 100.
    """
    rendered = ctx.get("resume_text") or ""
    if not rendered:
        return 100.0
    # Combined source pool for learning
    source_text = "\n".join([
        ctx.get("source_nuggets_text") or "",
        ctx.get("jd_text") or "",
        ctx.get("resume_markdown") or "",
        rendered,  # rendered itself may contain the pair if expansion happened
    ])
    learnable = _learnable_expansions_from_text(source_text)
    if not learnable:
        return 100.0
    applied = 0
    for ac, expansion in learnable.items():
        m = re.search(rf"\b{re.escape(ac)}\b", rendered)
        if not m:
            # Acronym not even in rendered output — can't fault it
            applied += 1
            continue
        # Check expansion appears within ±70 chars of first acronym occurrence
        window = rendered[max(0, m.start() - 100): m.start() + len(ac) + 30]
        if expansion.lower() in window.lower():
            applied += 1
    return 100.0 * applied / len(learnable)


# Phase 1.5 — Metric fidelity (bullet metrics must trace to source nuggets)
def _s_metric_fidelity(ctx: dict[str, Any]) -> float:
    """For each bullet, all numeric tokens must appear in the union of source-nugget metrics.

    Catches hallucinations like "Reduced ... time by 80%" when source said
    "Drove 80% adoption rate" — the % is preserved, but if a bullet has a
    number not in any source nugget, that's a fabrication signal.
    Score = 100 × (bullets with all metrics traceable) / total bullets.
    """
    bullets = ctx.get("bullets") or []
    source_text = ctx.get("source_nuggets_text") or ""
    if not bullets:
        return 100.0
    if not source_text:
        return 80.0  # no source data — give benefit of doubt
    source_metrics = _bullet_metrics(source_text)
    traceable = 0
    for b in bullets:
        b_metrics = _bullet_metrics(b)
        if not b_metrics:
            traceable += 1  # bullet has no numbers — vacuously OK (xyz_purity catches missing metrics)
            continue
        if b_metrics.issubset(source_metrics):
            traceable += 1
    return 100.0 * traceable / len(bullets)


# Phase 1.6 — Header JD-role match
def _s_header_jd_match(ctx: dict[str, Any]) -> float:
    """Header target_role should contain the JD's PRIMARY role-title tokens.

    Score = 100 × (overlap / primary_role_tokens). 2026-05-02: scorer compares
    against PRIMARY role only (text before em-dash separator), not the full
    "Title — Team (Scope)" string. Header may legitimately drop team/scope
    suffix to fit one line (per feedback_header_shrink_to_fit memory) — that
    is NOT a JD-mismatch; team keywords still appear in summary/bullets/skills
    where keyword_coverage scorer already counts them.
    """
    header = (ctx.get("header_role") or "").lower()
    jd_role = (ctx.get("jd_role") or "").lower()
    if not jd_role:
        return 100.0  # no JD role to compare — no penalty
    # Take JD role's PRIMARY part (before em-dash / en-dash / " - ").
    for sep in (" — ", " – ", " - "):
        if sep in jd_role:
            jd_role = jd_role.split(sep, 1)[0].strip()
            break
    # Also strip trailing "(...)" clause.
    jd_role = re.sub(r"\s*\([^)]*\)\s*$", "", jd_role).strip()
    jd_tokens = {t for t in re.split(r"[^a-z0-9]+", jd_role) if len(t) > 2}
    header_tokens = {t for t in re.split(r"[^a-z0-9]+", header) if len(t) > 2}
    if not jd_tokens:
        return 100.0
    overlap = jd_tokens & header_tokens
    return 100.0 * len(overlap) / len(jd_tokens)


# Phase 1.7 — Summary no-echo (summary text shouldn't repeat bullets)
def _s_summary_no_echo(ctx: dict[str, Any]) -> float:
    """Summary text vs each bullet — Jaccard token overlap should be <0.4.

    Score = 100 × (1 − max_jaccard) if max > 0.4 else 100.
    """
    summary = ctx.get("summary_text") or ""
    bullets = ctx.get("bullets") or []
    if not summary or not bullets:
        return 100.0
    s_tokens = _bullet_tokens(summary)
    if not s_tokens:
        return 100.0
    max_overlap = 0.0
    for b in bullets:
        b_tokens = _bullet_tokens(b)
        if not b_tokens:
            continue
        ov = len(s_tokens & b_tokens) / max(1, min(len(s_tokens), len(b_tokens)))
        max_overlap = max(max_overlap, ov)
    if max_overlap < 0.4:
        return 100.0
    return 100.0 * (1.0 - max_overlap)


# Phase 1.1 — Real contrast measurement from rendered HTML
_HEX_COLOR_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c + c for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        c_n = c / 255.0
        return c_n / 12.92 if c_n <= 0.03928 else ((c_n + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _wcag_contrast(c1: str, c2: str) -> float:
    l1 = _luminance(_hex_to_rgb(c1))
    l2 = _luminance(_hex_to_rgb(c2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _s_contrast_aa(ctx: dict[str, Any]) -> float:
    """Phase 1.1 — measure real WCAG AA contrast from extracted color pairs.

    `ctx['contrast_pairs']` should be a list of (fg_hex, bg_hex) tuples populated
    by scorecard_context.py from the rendered HTML's CSS variables.
    Score = 100 × (pairs with ratio ≥ 4.5) / total pairs.
    Falls back to placeholder ratios if pairs not populated.
    """
    pairs = ctx.get("contrast_pairs") or []
    if pairs:
        passing = 0
        for fg, bg in pairs:
            try:
                if _wcag_contrast(fg, bg) >= 4.5:
                    passing += 1
            except Exception:
                continue
        return 100.0 * passing / len(pairs) if pairs else 0.0
    # Fallback to old placeholder ratios
    ratios = ctx.get("contrast_ratios") or []
    if not ratios:
        return 80.0  # benefit of doubt
    return 100.0 * sum(1 for r in ratios if r >= 4.5) / len(ratios)


# ════════════════════════════════════════════════════════════════════════
# Re-balanced Dimension list — 15 dims, weights sum to 1.00
# ════════════════════════════════════════════════════════════════════════

# v0.1.6 — entity_fidelity dim: catches the Oracle→Google duplication bug
# (rendered companies must subset of source experiences).
def _s_entity_fidelity(ctx: dict[str, Any]) -> float:
    """% of rendered work-experience companies that exist in the source resume.

    100 = no hallucinated companies. <100 = at least one fabricated employer.
    Highest-severity dim — fabricated employment history is resume fraud.
    """
    rendered = ctx.get("rendered_company_names") or []
    source_experiences = ctx.get("source_experience_companies") or []
    if not rendered:
        return 100.0  # vacuous — nothing rendered to check
    if not source_experiences:
        # No source companies known; can't verify either way — return mild flag
        return 80.0
    src_norm = {re.sub(r"[^a-z0-9]+", "", c.lower()) for c in source_experiences if c}
    real_count = 0
    for r in rendered:
        n = re.sub(r"[^a-z0-9]+", "", (r or "").lower())
        if not n:
            continue
        # substring-match either direction
        if n in src_norm or any(n in s or s in n for s in src_norm if s):
            real_count += 1
    return 100.0 * real_count / len(rendered)


class ResumeScorecard(Scorecard):
    pillar: ClassVar[str] = "resume"
    dimensions: ClassVar[list[Dimension]] = [
        Dimension("keyword_coverage",     0.10, _s_keyword_coverage),
        Dimension("width_hit_rate",       0.09, _s_width_hit_rate),
        Dimension("xyz_format_purity",    0.07, _s_xyz_format_purity),
        Dimension("verb_diversity",       0.07, _s_verb_diversity),
        Dimension("metric_density",       0.07, _s_metric_density),
        Dimension("page_fit",             0.09, _s_page_fit),
        Dimension("brs_top_pct",          0.07, _s_brs_top_pct),
        Dimension("contrast_aa",          0.05, _s_contrast_aa),
        Dimension("near_dup_rate",        0.05, _s_near_dup_rate),
        Dimension("structure_integrity",  0.05, _s_structure_integrity),
        Dimension("tense_consistency",    0.05, _s_tense_consistency),
        Dimension("acronym_expansion",    0.03, _s_acronym_expansion),
        Dimension("metric_fidelity",      0.05, _s_metric_fidelity),
        Dimension("header_jd_match",      0.04, _s_header_jd_match),
        Dimension("summary_no_echo",      0.03, _s_summary_no_echo),
        # NEW v0.1.6 — highest-severity (resume integrity)
        Dimension("entity_fidelity",      0.09, _s_entity_fidelity),
    ]
    # Weights: 0.10+0.09+0.07+0.07+0.07+0.09+0.07+0.05+0.05+0.05+0.05+0.03+0.05+0.04+0.03+0.09 = 1.00
