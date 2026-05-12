"""Sprint 7 Width Optimization POC — 5-pass waterfall.

Goal: for each condensed bullet, hit 95-100% of the line width budget without
fabricating metrics or losing JD keywords. If all bullets land in [95%, 100%],
apply CSS `text-align: justify` for natural column-fill rendering. Telemetry
captures per-pass success rates + LLM cost.

Passes:
  A — width-aware condense (already in step_12; we just measure)
  B — bold emphasis + color highlight on metrics + JD keywords (deterministic)
  C — synonym swap via prod's SYNONYM_BANK (deterministic)
  D — LLM rephrase via Cerebras qwen-235B (constrained)
  E — accept with warning (best-effort)

Reuses prod infrastructure via sys.path injection:
  - repo/worker/app/data/synonym_bank.py::SYNONYM_BANK
  - repo/worker/app/tools/suggest_synonyms.py (not used directly to avoid async
    plumbing — we re-implement the simple matching inline)

Env gate: ENABLE_WIDTH_POC=1 to activate. Otherwise no-op.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

# ── SYNONYM_BANK now lives inside linkright.resume.data (ported from prod) ──
try:
    from ..data.synonym_bank import SYNONYM_BANK  # type: ignore
except Exception:
    SYNONYM_BANK = {"expand": [], "trim": []}

# W2-A: use real Roboto advance-width tables for accurate bold measurement.
# ROBOTO_REGULAR_WEIGHTS and ROBOTO_BOLD_WEIGHTS are per-glyph dicts; digit=1.000 baseline.
# Same source as prod's suggest_synonyms.py::_calculate_word_width.
try:
    from ..data.roboto_weights import (  # type: ignore
        ROBOTO_REGULAR_WEIGHTS,
        ROBOTO_BOLD_WEIGHTS,
        REGULAR_DEFAULT,
        BOLD_DEFAULT,
    )
except Exception:
    ROBOTO_REGULAR_WEIGHTS = {}
    ROBOTO_BOLD_WEIGHTS = {}
    REGULAR_DEFAULT = 1.000
    BOLD_DEFAULT = 1.052


def _char_width(c: str, bold: bool = False) -> float:
    """W2-A: real Roboto advance-width lookup (replaces heuristic).

    Bold glyphs typically 5-9% wider; digits = 1.000 baseline.
    """
    if bold:
        return ROBOTO_BOLD_WEIGHTS.get(c, BOLD_DEFAULT)
    return ROBOTO_REGULAR_WEIGHTS.get(c, REGULAR_DEFAULT)


def measure_width_cu(html: str) -> float:
    """Return width in character units (rough). Measures rendered text (strips tags),
    but accounts for bold via <b> detection."""
    total = 0.0
    # Split into bold + regular runs
    pos = 0
    for m in re.finditer(r"<b[^>]*>(.*?)</b>", html, flags=re.DOTALL | re.IGNORECASE):
        # Chars before this bold run — regular
        regular_text = re.sub(r"<[^>]+>", "", html[pos:m.start()])
        for c in regular_text:
            total += _char_width(c, bold=False)
        # Bold content
        bold_text = re.sub(r"<[^>]+>", "", m.group(1))
        for c in bold_text:
            total += _char_width(c, bold=True)
        pos = m.end()
    # Tail
    tail = re.sub(r"<[^>]+>", "", html[pos:])
    for c in tail:
        total += _char_width(c, bold=False)
    return round(total, 2)


# ── Pass B: deterministic bold + highlight on metrics + JD keywords ──────────

_METRIC_PATTERNS = [
    re.compile(r"\b(\d+(?:[.,]\d+)?%?(?:[xX])?)\b"),
    re.compile(r"[$₹€£]\s*\d+[\d,.]*(?:[KkMmBb]n?)?"),
    re.compile(r"\b\d+\s*(years?|hrs?|days?|weeks?|months?|customers?|users?|teams?|accounts?|markets?)\b", re.IGNORECASE),
    re.compile(r"\b\d+:\d+\b"),  # ratios
    re.compile(r"\b\d+[KkMmBb]\+?\b"),
]


def _is_already_bold(html: str, start: int, end: int) -> bool:
    """Check if [start, end) substring is inside an existing <b>...</b>."""
    # Find all bold ranges
    for bm in re.finditer(r"<b[^>]*>.*?</b>", html, flags=re.DOTALL | re.IGNORECASE):
        if bm.start() <= start < bm.end():
            return True
    return False


def apply_bold_highlight(html: str, jd_keywords: list[str]) -> tuple[str, int, int]:
    """Pass B: wrap metrics and JD keywords in <b> tags.
    Returns (new_html, bolded_metrics_count, bolded_keywords_count).
    """
    bolded_metrics = 0
    bolded_keywords = 0

    # Pass B.1 — metrics (wrapped in <b><span class="metric-highlight">...</span></b>)
    # We do it with a single pass + offset tracking to avoid double-processing.
    for pat in _METRIC_PATTERNS:
        def _repl_metric(m: re.Match) -> str:
            nonlocal bolded_metrics
            text = m.group(0)
            # Skip if already in a bold context
            if _is_already_bold(html, m.start(), m.end()):
                return text
            bolded_metrics += 1
            return f'<b><span class="metric-highlight">{text}</span></b>'
        new_html = pat.sub(_repl_metric, html)
        html = new_html

    # Pass B.2 — JD keywords (wrapped in plain <b>)
    # Sort descending by length so longer matches win (e.g., "multi-tenancy" before "tenancy")
    kws = sorted([k.strip() for k in jd_keywords if k and len(k.strip()) >= 3], key=len, reverse=True)
    for kw in kws[:25]:  # cap to top 25 keywords
        # Word-boundary case-insensitive match, not inside existing bold
        escaped = re.escape(kw)
        pat = re.compile(rf"\b({escaped})\b", re.IGNORECASE)
        def _repl_kw(m: re.Match) -> str:
            nonlocal bolded_keywords
            if _is_already_bold(html, m.start(), m.end()):
                return m.group(0)
            bolded_keywords += 1
            return f"<b>{m.group(0)}</b>"
        html = pat.sub(_repl_kw, html)

    return html, bolded_metrics, bolded_keywords


# ── Pass C: synonym swap using prod SYNONYM_BANK ─────────────────────────────

def apply_synonym_swap(html: str, target_min: float, target_max: float, max_swaps: int = 3) -> tuple[str, int, bool]:
    """Pass C: try up to max_swaps synonym replacements (outside <b> tags).
    Returns (new_html, swaps_applied, in_target).
    """
    swaps_applied = 0
    for _ in range(max_swaps):
        cu = measure_width_cu(html)
        if target_min <= cu <= target_max:
            return html, swaps_applied, True
        target_mid = (target_min + target_max) / 2.0
        direction = "trim" if cu > target_mid else "expand"
        pairs = SYNONYM_BANK.get(direction, [])

        # Plain text WITHOUT bold content (so we don't swap inside <b>)
        plain_text_with_holes = re.sub(r"<b[^>]*>.*?</b>", " " * 10, html, flags=re.DOTALL | re.IGNORECASE)
        plain_text_with_holes = re.sub(r"<[^>]+>", "", plain_text_with_holes)

        # Find candidate token replacements
        candidates: list[tuple[str, str, float, float]] = []  # (orig, repl, delta, dist_to_target)
        for orig, repl, delta in pairs:
            # Only consider if orig appears in plain_text (outside bold)
            if re.search(rf"\b{re.escape(orig)}\b", plain_text_with_holes, re.IGNORECASE):
                new_cu = cu + delta
                candidates.append((orig, repl, delta, abs(new_cu - target_mid)))
        if not candidates:
            return html, swaps_applied, target_min <= cu <= target_max
        candidates.sort(key=lambda t: t[3])
        orig, repl, _d, _dist = candidates[0]

        # Apply swap in HTML BUT only outside <b> regions.
        def _swap_outside_bold(s: str) -> str:
            # Split html into (non_bold, bold, non_bold, bold, ...) chunks
            out = []
            last = 0
            for m in re.finditer(r"<b[^>]*>.*?</b>", s, flags=re.DOTALL | re.IGNORECASE):
                chunk = s[last:m.start()]
                swapped = re.sub(rf"\b{re.escape(orig)}\b", repl, chunk, count=1, flags=re.IGNORECASE)
                out.append(swapped)
                out.append(s[m.start():m.end()])
                last = m.end()
            tail = s[last:]
            tail = re.sub(rf"\b{re.escape(orig)}\b", repl, tail, count=1, flags=re.IGNORECASE)
            out.append(tail)
            return "".join(out)

        new_html = _swap_outside_bold(html)
        if new_html == html:
            break  # no actual change (edge case)
        html = new_html
        swaps_applied += 1
    return html, swaps_applied, target_min <= measure_width_cu(html) <= target_max


# ── Pass D: LLM rephrase (Cerebras qwen-235B) ─────────────────────────────────

def _call_oracle_rephrase(bullet_html: str, target_min: float, target_max: float, cu: float) -> Optional[str]:
    """Try Oracle /lifeos/rewrite (llama3.2:1b, local, FREE).

    Strategy:
      1. Strip HTML bold tags → plain text
      2. Extract original metrics + keywords (what was bolded) for invariant check
      3. Call Oracle with plain text + system prompt
      4. Strip conversational wrappers from response
      5. Verify invariants (metrics + keywords present in rewrite, verbatim)
      6. Re-apply bold tags via regex (Pass B style)
      7. Return bold-re-applied HTML, or None if failed
    """
    import os as _os
    import httpx as _httpx

    oracle_url = _os.environ.get("ORACLE_BACKEND_URL", "")
    oracle_secret = _os.environ.get("ORACLE_BACKEND_SECRET", "")
    if not oracle_url or not oracle_secret:
        return None

    # Extract original bolded content (the invariants)
    original_bolds = re.findall(r"<b[^>]*>(.*?)</b>", bullet_html, flags=re.DOTALL | re.IGNORECASE)
    # Strip HTML tags
    plain = re.sub(r"<[^>]+>", "", bullet_html)

    action = "shorten" if cu > target_max else "lengthen"
    delta = ((target_min + target_max) / 2.0) - cu
    # 2026-04-22 rewrite per user's directive: Pass D is a WIDTH-ONLY TUNER.
    # It may ONLY modify filler/glue words. XYZ (impact verb, metrics, context nouns)
    # MUST survive verbatim. The prompt is explicit about what can and cannot change.
    # Allowed edit magnitude scales with delta — for small nudges (±5 chars) keep
    # it light; for larger trims (15-30 chars) allow more aggressive filler removal
    # while still preserving XYZ.
    if action == "lengthen":
        edit_instr = (
            "You may ADD 3-10 filler words — specifically: articles (a, an, the), "
            "clarifying adjectives drawn from context (enterprise, production, cross-functional), "
            "connectors (while, through, across), or a short prepositional phrase. "
            "Do NOT add new facts, numbers, tools, or proper nouns."
        )
    else:
        edit_instr = (
            "You may REMOVE up to 15 filler words — specifically: redundant articles (the, a, an), "
            "adverbs (successfully, effectively, consistently, reliably), weak adjectives "
            "(various, multiple, several, key, important), filler phrases "
            "(in order to, as part of, with the goal of), and repeated prepositions. "
            "You may also collapse 'X by doing Y, which achieved Z' into a tighter 'X through Y achieving Z'. "
            "Do NOT remove any metric, percentage, proper noun, the main impact verb, or any word inside <b>...</b>."
        )
    # Target word-count change scales with delta — 1 CU ≈ 0.2 words
    words_to_change = max(3, int(abs(delta) * 0.25))  # e.g. delta=60 → ~15 words
    # 2026-04-23 fix: gemma3:1b tends to undershoot when asked to lengthen
    # (lands 3-5 chars short of target), so bias target toward top-of-band
    # when lengthening. When shortening, bias toward midpoint (LLMs over-trim).
    if action == "lengthen":
        target_chars = int(target_max)  # aim for ~101; LLM likely lands ~96-98
    else:
        target_chars = int(target_min + 2)  # aim for ~98; LLM likely lands ~94-97
    current_chars = len(plain)
    system = (
        f"You are a precision width tuner. Your ONLY job is to {action} this bullet by about "
        f"{abs(delta):.0f} characters (roughly {words_to_change} words {action}er) while "
        f"PRESERVING every meaningful element.\n\n"
        f"# CURRENT vs TARGET\n"
        f"Current plain-text length: {current_chars} characters\n"
        f"Target plain-text length:  {target_chars} characters (range {target_min:.0f}-{target_max:.0f})\n"
        f"Delta needed:              {'+' if action == 'lengthen' else ''}{-abs(delta) if action == 'shorten' else int(abs(delta))} characters\n\n"
        f"# WHAT YOU MUST NOT CHANGE (XYZ preservation — zero tolerance)\n"
        f"1. X (Impact/Outcome): the leading verb and outcome noun — keep VERBATIM.\n"
        f"2. Y (Measurement): every number, percentage, $, K, M, B, ratio — keep VERBATIM.\n"
        f"3. Z (Action / Specific Contribution): the phrase describing what the candidate PERSONALLY DID — keep VERBATIM. Proper nouns / domain acronyms — keep VERBATIM.\n"
        f"4. Every <b>...</b> span's content — keep VERBATIM (don't touch what's inside bold).\n\n"
        f"# WHAT YOU MAY CHANGE (filler only)\n"
        f"{edit_instr}\n\n"
        f"# CREATIVE SHORTENING TECHNIQUES (apply JUDICIOUSLY when basic filler removal isn't enough)\n"
        f"When basic filler removal isn't enough to hit the target, you may apply these context-sensitive "
        f"substitutions. Each has a SAFE-USE rule — if you can't verify the rule, DON'T apply:\n\n"
        f"1. \"and\" → \"&\"\n"
        f"   ✅ Apply between common nouns: \"sales and marketing\" → \"sales & marketing\"\n"
        f"   ❌ DO NOT in proper nouns, company names, or Oxford-comma series\n"
        f"   ❌ DO NOT if \"and\" connects two full clauses (\"I built X and shipped Y\")\n\n"
        f"2. \"percent\" → \"%\"\n"
        f"   ✅ Apply only when directly after a number: \"50 percent\" → \"50%\"\n"
        f"   ❌ DO NOT in prose: \"a small percent of users\" stays as-is\n\n"
        f"3. Number words → digits (0-10 only, metric contexts only)\n"
        f"   ✅ \"three markets\" → \"3 markets\", \"seven engineers\" → \"7 engineers\"\n"
        f"   ❌ DO NOT in proverb/idiom: \"three principles\", \"seven-figure deal\"\n\n"
        f"4. \"per [unit]\" → \"/[unit]\"\n"
        f"   ✅ After a number: \"40 hours per month\" → \"40 hrs/mo\", \"$5 per hour\" → \"$5/hr\"\n"
        f"   ❌ DO NOT if no number: \"once per month\" stays as-is\n\n"
        f"5. \"approximately\" → \"~\"\n"
        f"   ✅ Before a number: \"approximately 100 users\" → \"~100 users\"\n"
        f"   ❌ DO NOT in prose without a number\n\n"
        f"6. \"million\"/\"thousand\"/\"billion\" → \"M\"/\"K\"/\"B\"\n"
        f"   ✅ Right after a number: \"5 million downloads\" → \"5M downloads\"\n"
        f"   ❌ DO NOT in prose: \"thousands of users\" stays as-is\n\n"
        f"7. Compound verb phrase reductions (safe universally):\n"
        f"   \"was responsible for\" → \"led\"\n"
        f"   \"in charge of\" → \"led\"\n"
        f"   \"played a role in\" → \"drove\"\n"
        f"   \"had the opportunity to\" → \"got to\"\n"
        f"   \"made contributions to\" → \"contributed to\"\n\n"
        f"8. Tech acronyms (expand if lengthening, contract if shortening):\n"
        f"   \"artificial intelligence\" ⟷ \"AI\"\n"
        f"   \"machine learning\" ⟷ \"ML\"\n"
        f"   \"user interface\" ⟷ \"UI\"\n"
        f"   \"user experience\" ⟷ \"UX\"\n\n"
        f"HARD RULE: never apply ANY of these inside <b>...</b> content. Bold is frozen.\n\n"
        f"# OUTPUT PURITY — zero tolerance\n"
        f"- NEVER emit commentary: no \"Note:\", no \"Here's\", no \"Sure,\", no explanations.\n"
        f"- NEVER emit HTML comments: no <!-- ... -->\n"
        f"- NEVER wrap in code fences, quotes, or labels.\n"
        f"- Output EXACTLY the adjusted bullet text and NOTHING else.\n\n"
        f"# INTERNAL REASONING STEPS (do this in your head before returning)\n"
        f"Step 1: List every word in the input. Classify each as KEEP (metric/verb/noun/bold content) or FILLER (article/adverb/weak adjective).\n"
        f"Step 2: Count the FILLER words. You have this many words of budget to {action}.\n"
        f"Step 3: Draft the adjusted bullet by {'removing' if action == 'shorten' else 'adding'} filler words only.\n"
        f"Step 4: Count plain-text characters of your draft. Target: {target_chars} chars.\n"
        f"Step 5: If off target by > 5 chars, adjust filler ONE MORE time. If still off, return best attempt.\n\n"
        f"# VALIDATION\n"
        f"Your output will be REJECTED if it changes any metric, verb, proper noun, or bold content. "
        f"Your output MUST differ from the input by about {words_to_change} words in total count "
        f"(either adding or removing filler as instructed). Echoing is REJECTED.\n"
        f"Target plain-text length: {target_min:.0f}-{target_max:.0f} chars. COUNT BEFORE RETURNING.\n\n"
        f"Return ONLY the adjusted bullet — no preamble, no quotes, no explanation, no reasoning visible."
    )

    def _oracle_call(_system: str, _temperature: float, _timeout: float = 20.0) -> Optional[str]:
        """Oracle gemma3:1b primary (free local). Gemini-best-tier reserved for hard
        fallback only — per user directive 'more power is not the answer'."""
        try:
            resp = _httpx.post(
                f"{oracle_url.rstrip('/')}/lifeos/rewrite",
                headers={"Authorization": f"Bearer {oracle_secret}", "Content-Type": "application/json"},
                json={"prompt": plain, "system": _system, "temperature": _temperature},
                timeout=_timeout,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return (data.get("text") or "").strip()
        except Exception:
            return None

    def _clean_response(_txt: str) -> str:
        """Strip conversational wrappers + take first substantive line."""
        _txt = re.sub(
            r"^(Here('s| is)|Here's a|Here is a|I've|I have|Let me|Or,?|Alternatively).*?[:\n]\s*",
            "",
            _txt,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        lines = [l.strip().strip('"\u201c\u201d') for l in _txt.split("\n") if l.strip()]
        return lines[0] if lines else ""

    def _is_echo(orig: str, new: str) -> bool:
        """True if new is essentially identical to orig (≥90% word overlap at same length)."""
        orig_words = orig.lower().split()
        new_words = new.lower().split()
        if not orig_words or not new_words:
            return False
        if len(orig_words) == len(new_words):
            overlap = sum(1 for o, n in zip(orig_words, new_words) if o == n)
            return overlap / len(orig_words) >= 0.9
        return False

    # Attempt 1: standard prompt at temperature 0.1
    raw = _oracle_call(system, 0.1)
    if raw is None:
        return None
    rewritten = _clean_response(raw)

    if not rewritten or len(rewritten) < 20:
        return None

    # Attempt 2: if echo detected, retry at higher temp with explicit anti-echo instruction.
    # Shorter timeout (15s) — if Oracle needed > 20s for attempt 1 (cold-load), we've already
    # paid that; retry should be fast. Skip retry if no budget.
    if _is_echo(plain, rewritten):
        retry_system = (
            system
            + "\n\nYour previous response was nearly identical to the input. "
            "You MUST produce a MATERIALLY different rewrite with a different word count. "
            "The number of words in your response MUST differ from the original by at least 3."
        )
        raw2 = _oracle_call(retry_system, 0.3, _timeout=15.0)
        if raw2:
            rewritten2 = _clean_response(raw2)
            if rewritten2 and len(rewritten2) >= 20 and not _is_echo(plain, rewritten2):
                rewritten = rewritten2

    # Iter-04 (2026-04-23): Attempt 3/4 — char-count feedback retry.
    # If the rewritten plain-char length is off-target by >3 chars, retry up to 2 more
    # times with EXPLICIT feedback of actual vs target chars. Small models respond much
    # better to concrete numeric feedback than abstract "shorter/longer" goals.
    target_mid = (target_min + target_max) / 2.0
    for retry_attempt in range(2):  # max 2 additional retries = 4 total LLM calls
        cur_chars = len(rewritten)
        off_by = abs(cur_chars - target_mid)
        if off_by <= 3.0:
            break  # close enough — accept
        direction = "SHORTEN" if cur_chars > target_mid else "LENGTHEN"
        delta_now = int(abs(cur_chars - target_mid))
        feedback = (
            f"\n\n# CHAR-COUNT FEEDBACK (attempt {retry_attempt + 2})\n"
            f"Your last output was {cur_chars} plain-text characters.\n"
            f"Target range: {target_min:.0f}-{target_max:.0f} chars (midpoint {target_mid:.0f}).\n"
            f"You are OFF by {delta_now} chars. You must {direction} by EXACTLY "
            f"{delta_now} chars in this attempt. Count as you write.\n"
            f"If {direction} = SHORTEN: remove another 1-3 filler words (articles, adverbs, weak adjectives).\n"
            f"If {direction} = LENGTHEN: add 1-3 filler words (articles, clarifying adjectives, connectives).\n"
            f"All other rules from the original instructions STILL APPLY: preserve metrics, "
            f"proper nouns, and bold content. Return ONLY the adjusted bullet."
        )
        raw_retry = _oracle_call(system + feedback, 0.2 + 0.1 * retry_attempt, _timeout=15.0)
        if not raw_retry:
            break
        rewritten_retry = _clean_response(raw_retry)
        if rewritten_retry and len(rewritten_retry) >= 20 and not _is_echo(plain, rewritten_retry):
            # Only accept if it moved closer to target
            new_off_by = abs(len(rewritten_retry) - target_mid)
            if new_off_by < off_by:
                rewritten = rewritten_retry

    # Invariant check: every original bold content must appear verbatim in rewrite
    for bold_content in original_bolds:
        bold_plain = re.sub(r"<[^>]+>", "", bold_content).strip()
        if bold_plain and bold_plain.lower() not in rewritten.lower():
            return None  # metric or keyword lost → reject

    # XYZ-preservation check (2026-04-22 per user directive):
    # Pass D may only modify filler. Extract every digit-containing token + every
    # capitalized multi-word proper noun from the original — all must survive.
    _METRIC_TOKENS = re.compile(r"\b\d[\d,.:]*(?:[%xX+]|[KkMmBb]\+?)?\b|[$₹€£]\s*\d[\d,.]*(?:[KkMmBb]n?)?")
    orig_metric_tokens = set(m.group(0).lower() for m in _METRIC_TOKENS.finditer(plain))
    new_metric_tokens = set(m.group(0).lower() for m in _METRIC_TOKENS.finditer(rewritten))
    if not orig_metric_tokens.issubset(new_metric_tokens):
        # A metric was dropped or mutated — reject
        return None

    # Leading verb check: first word of original ≈ first word of rewrite (case-insensitive)
    orig_words = plain.split()
    new_words = rewritten.split()
    if orig_words and new_words:
        orig_first = orig_words[0].lower().strip(".,:")
        new_first = new_words[0].lower().strip(".,:")
        if orig_first != new_first:
            # Leading verb changed — reject (XYZ X component violated)
            return None

    # Re-apply bold tags to metrics + keywords (simple regex match)
    out = rewritten
    for bold_content in original_bolds:
        bold_plain = re.sub(r"<[^>]+>", "", bold_content).strip()
        if bold_plain:
            # Case-insensitive replace first occurrence, wrap in <b>
            pat = re.compile(rf"\b{re.escape(bold_plain)}\b", re.IGNORECASE)
            out = pat.sub(f"<b>{bold_plain}</b>", out, count=1)

    return out


def apply_llm_rephrase(html: str, target_min: float, target_max: float, llm_module) -> tuple[str, int, int, int, bool]:
    """Pass D: try Oracle first (free llama3.2:1b), fall back to Cerebras on fail.

    Returns (new_html, llm_calls, prompt_tokens, completion_tokens, in_target).

    Env knobs:
      - LLM_REPHRASE_PROVIDER=oracle|cerebras|auto (default: auto = oracle-first)
    """
    provider_pref = os.environ.get("LLM_REPHRASE_PROVIDER", "auto").lower()

    # Pass D-0: Oracle (free, local)
    if provider_pref in ("auto", "oracle"):
        cu_initial = measure_width_cu(html)
        result = _call_oracle_rephrase(html, target_min, target_max, cu_initial)
        if result:
            new_cu = measure_width_cu(result)
            if target_min <= new_cu <= target_max:
                # Oracle success — zero billed tokens (local model)
                return result, 1, 0, 0, True
        if provider_pref == "oracle":
            # User restricted to Oracle only
            return html, 1 if result else 0, 0, 0, False
    cu = measure_width_cu(html)
    if target_min <= cu <= target_max:
        return html, 0, 0, 0, True
    action = "shorten" if cu > target_max else "lengthen"
    delta = (target_min + target_max) / 2.0 - cu

    system = (
        "You are a resume width micro-editor. Rewrite the bullet below to fit the "
        f"exact width range [{target_min:.1f}, {target_max:.1f}] character units when "
        f"rendered. Current width is {cu:.1f} CU (need to {action} by {abs(delta):.1f}).\n\n"
        "HARD RULES — violation means rejection:\n"
        "1. Preserve every <b>...</b> tag and its content VERBATIM. No edits inside bold.\n"
        "2. The action verb at the start of the bullet must not change.\n"
        "3. Do not introduce new facts, metrics, or domain terms not in the original.\n"
        "4. Adjust articles (a/the), determiners, connectives, and unbolded adjectives only.\n\n"
        "Return ONLY the rewritten bullet HTML — no JSON, no commentary, no quotes."
    )
    user = html

    prompt_tokens = completion_tokens = 0
    llm_calls = 0
    best_html = html
    best_diff = abs(cu - (target_min + target_max) / 2.0)

    for attempt in range(2):
        try:
            # Iter-06 (2026-04-23): Cerebras 8B primary (2200 tok/s, free tier).
            # Pass D is filler-word-only rewrite — 8B sufficient, massive speed win
            # over Oracle (800ms-2s) or Cerebras qwen-235B (2-5s). Fall back to qwen
            # on rate-limit for the hardest cases that 8B struggles with.
            try:
                resp_text, usage = llm_module.cerebras_8b_chat(
                    system=system, user=user, temperature=0.1, max_tokens=500
                )
            except Exception as _e_c8:
                if "429" in str(_e_c8) or "rate" in str(_e_c8).lower():
                    resp_text, usage = llm_module.cerebras_qwen_chat(
                        system=system, user=user, temperature=0.1, max_tokens=500
                    )
                else:
                    raise
            llm_calls += 1
            prompt_tokens += usage.get("prompt_tokens", 0) or 0
            completion_tokens += usage.get("completion_tokens", 0) or 0
        except Exception:
            break

        # Strip accidental code-fence wrapping
        clean = resp_text.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        clean = clean.strip()

        # Validate bold content preserved
        orig_bolds = re.findall(r"<b[^>]*>(.*?)</b>", html, flags=re.DOTALL | re.IGNORECASE)
        new_bolds = re.findall(r"<b[^>]*>(.*?)</b>", clean, flags=re.DOTALL | re.IGNORECASE)
        if set(orig_bolds) != set(new_bolds):
            # Bold invariant violated; reject
            if attempt == 0:
                user = html + f"\n\nRETRY: your previous response modified or dropped bold content. Preserve <b>...</b> tags EXACTLY."
                continue
            break

        new_cu = measure_width_cu(clean)
        diff = abs(new_cu - (target_min + target_max) / 2.0)
        if diff < best_diff:
            best_diff = diff
            best_html = clean
        if target_min <= new_cu <= target_max:
            return clean, llm_calls, prompt_tokens, completion_tokens, True

        # Not in range; retry once with error hint
        if attempt == 0:
            user = html + f"\n\nRETRY: your previous response was {new_cu:.1f} CU; need [{target_min:.1f}, {target_max:.1f}]."

    return best_html, llm_calls, prompt_tokens, completion_tokens, False


# ── Orchestrator: 5-pass waterfall per bullet ─────────────────────────────────

def width_poc_optimize_bullets(
    condensed_by_company: dict,
    jd_keywords: list[str],
    target_min: float = 96.33,  # 95% of cv-a4-mid-career raw_budget 101.4 (Part 1.1)
    target_max: float = 101.4,  # 100%
    llm_module=None,
) -> tuple[dict, dict]:
    """Run the 5-pass waterfall on all condensed bullets.

    Args:
        condensed_by_company: {company_name: [{'text_html': ..., ...}, ...]}
        jd_keywords: list of keywords for Pass B
        target_min/max: width budget in character units
        llm_module: e2e_diagnostic_run.lib.llm module (for cerebras_chat)

    Returns:
        (optimized_condensed_by_company, poc_results)
        poc_results has the telemetry rollup.
    """
    t0 = time.time()

    by_pass_counts = {
        "A_condense_only": 0,
        "B_bold_highlight": 0,
        "C_synonym_swap": 0,
        "D_llm_rephrase": 0,
        "E_accepted_with_warning": 0,
    }
    per_bullet_log: list[dict] = []
    total_llm_calls = total_prompt_tok = total_completion_tok = 0

    result: dict = {}
    for company, bullets in condensed_by_company.items():
        opt_bullets = []
        for idx, b in enumerate(bullets):
            html = b.get("text_html", "")
            entry = {
                "company": company,
                "idx": idx,
                "pre_a_cu": measure_width_cu(html),
                "passes_tried": [],
                "final_pass": None,
            }
            # Part 1.2 reorder: Pass B (bold + color-highlight) applied UNCONDITIONALLY
            # as formatting, not conditionally. Measurement happens post-B.
            html_b, n_metrics, n_keywords = apply_bold_highlight(html, jd_keywords)
            entry["post_b_cu"] = measure_width_cu(html_b)
            entry["bolded_metrics"] = n_metrics
            entry["bolded_keywords"] = n_keywords
            entry["passes_tried"].append("B_formatting_applied")

            # Check if post-B width already in target — if so, "A+B" succeeded
            if target_min <= entry["post_b_cu"] <= target_max:
                by_pass_counts["B_bold_highlight"] += 1
                entry["final_pass"] = "B"
                entry["final_cu"] = entry["post_b_cu"]
                opt_bullets.append({**b, "text_html": html_b})
                per_bullet_log.append(entry)
                continue

            # Pass C — synonym swap
            html_c, swaps, in_range_c = apply_synonym_swap(html_b, target_min, target_max)
            entry["post_c_cu"] = measure_width_cu(html_c)
            entry["synonym_swaps"] = swaps
            if in_range_c:
                by_pass_counts["C_synonym_swap"] += 1
                entry["final_pass"] = "C"
                entry["final_cu"] = entry["post_c_cu"]
                opt_bullets.append({**b, "text_html": html_c})
                per_bullet_log.append(entry)
                continue
            entry["passes_tried"].append("C")

            # Pass D — LLM rephrase (if llm_module provided)
            if llm_module is not None:
                html_d, d_calls, d_pt, d_ct, in_range_d = apply_llm_rephrase(html_c, target_min, target_max, llm_module)
                entry["post_d_cu"] = measure_width_cu(html_d)
                entry["d_llm_calls"] = d_calls
                total_llm_calls += d_calls
                total_prompt_tok += d_pt
                total_completion_tok += d_ct
                if in_range_d:
                    by_pass_counts["D_llm_rephrase"] += 1
                    entry["final_pass"] = "D"
                    entry["final_cu"] = entry["post_d_cu"]
                    opt_bullets.append({**b, "text_html": html_d})
                    per_bullet_log.append(entry)
                    continue
                entry["passes_tried"].append("D")
                final_html = html_d  # best-effort from D
            else:
                final_html = html_c

            # Iter-07 (2026-04-23): Pass F — HARD-TRIM guarantee.
            # If bullet is still over target_max (wraps to 2nd line), apply
            # deterministic word-drop from the END until <= target_max. Preserves
            # leading verb + bold spans (we never touch content inside <b>...</b>).
            # This guarantees step_13 "no wraps" — a HARD FLOOR for 99% target.
            pre_f_cu = measure_width_cu(final_html)
            if pre_f_cu > target_max + 1.0:  # +1 tolerance for measurement noise
                from re import finditer as _finditer, DOTALL as _DOTALL
                # Split into tokens: non-bold text + intact <b>...</b> spans
                tokens: list[tuple[str, bool]] = []  # (text, is_bold)
                pos = 0
                for m in _finditer(r"<b[^>]*>.*?</b>", final_html, flags=_DOTALL):
                    if m.start() > pos:
                        tokens.append((final_html[pos:m.start()], False))
                    tokens.append((m.group(0), True))
                    pos = m.end()
                if pos < len(final_html):
                    tokens.append((final_html[pos:], False))
                # Drop non-bold words from END until width fits.
                # Preserve leading/trailing whitespace to keep inline rendering correct.
                # Iter-08 fix: skip EMPTY non-bold tokens (they have nothing to drop) —
                # previously caused 25-iteration no-op burn when Pass F hit a bullet
                # with all-bold + empty-filler structure.
                attempts_f = 0
                while attempts_f < 25 and measure_width_cu("".join(t for t, _ in tokens)) > target_max:
                    made_progress = False
                    for i in range(len(tokens) - 1, -1, -1):
                        txt, is_bold = tokens[i]
                        if is_bold:
                            continue
                        leading = txt[:len(txt) - len(txt.lstrip())]
                        core = txt.strip(".,;: \n")
                        words = core.split()
                        if not words:
                            # Empty non-bold chunk — nothing to drop here, try next token
                            continue
                        if len(words) <= 1:
                            tokens[i] = ("", False)
                        else:
                            new_core = " ".join(words[:-1])
                            trailing = ". " if txt.rstrip().endswith(".") else " "
                            tokens[i] = (leading + new_core + trailing, False)
                        made_progress = True
                        break
                    if not made_progress:
                        break  # nothing left to drop anywhere
                    attempts_f += 1
                final_html_f = "".join(t for t, _ in tokens).rstrip(", ")
                if not final_html_f.endswith((".", "!", "?")):
                    final_html_f = final_html_f.rstrip() + "."
                entry["post_f_cu"] = measure_width_cu(final_html_f)
                entry["hard_trim_applied"] = True
                entry["hard_trim_drops"] = attempts_f
                final_html = final_html_f

            # Iter-08 (2026-04-23): Pass F-WIDEN — symmetric hard-floor for UNDER bullets.
            # If bullet is still below target_min (CU< target_min - 1), use SYNONYM_BANK
            # "expand" pairs to swap short words for longer equivalents. Deterministic,
            # no LLM spend. Preserves bold content + leading verb.
            pre_widen_cu = measure_width_cu(final_html)
            if pre_widen_cu < target_min - 1.0:  # -1 tolerance
                import re as _re_w
                expand_pairs = SYNONYM_BANK.get("expand", [])
                widen_attempts = 0
                widened_html = final_html
                while widen_attempts < 15 and measure_width_cu(widened_html) < target_min:
                    swap_applied = False
                    # Split at bold boundaries — only swap in non-bold regions
                    non_bold_portions: list[tuple[int, int, str]] = []  # (start, end, content)
                    pos = 0
                    for m in _re_w.finditer(r"<b[^>]*>.*?</b>", widened_html, flags=_re_w.DOTALL):
                        if m.start() > pos:
                            non_bold_portions.append((pos, m.start(), widened_html[pos:m.start()]))
                        pos = m.end()
                    if pos < len(widened_html):
                        non_bold_portions.append((pos, len(widened_html), widened_html[pos:]))
                    # Try each expand pair until one fires
                    for orig_word, replacement, _delta in expand_pairs:
                        pat = _re_w.compile(rf"\b{_re_w.escape(orig_word)}\b", _re_w.IGNORECASE)
                        for start, end, chunk in non_bold_portions:
                            if pat.search(chunk):
                                new_chunk = pat.sub(replacement, chunk, count=1)
                                widened_html = widened_html[:start] + new_chunk + widened_html[end:]
                                swap_applied = True
                                break
                        if swap_applied:
                            break
                    if not swap_applied:
                        break  # no more expandable words
                    widen_attempts += 1
                entry["post_widen_cu"] = measure_width_cu(widened_html)
                entry["hard_widen_applied"] = True
                entry["hard_widen_swaps"] = widen_attempts
                # Only keep widen if it actually improved (moved closer to target_min)
                if measure_width_cu(widened_html) > pre_widen_cu:
                    final_html = widened_html

            # Pass E — accept (with warning if still off target after Pass F)
            by_pass_counts["E_accepted_with_warning"] += 1
            entry["final_pass"] = "E"
            entry["final_cu"] = measure_width_cu(final_html)
            opt_bullets.append({**b, "text_html": final_html})
            per_bullet_log.append(entry)

        result[company] = opt_bullets

    total_bullets = sum(len(v) for v in condensed_by_company.values())
    total_in_target = (
        by_pass_counts["A_condense_only"]
        + by_pass_counts["B_bold_highlight"]
        + by_pass_counts["C_synonym_swap"]
        + by_pass_counts["D_llm_rephrase"]
    )
    pct_at_target = round(100.0 * total_in_target / max(total_bullets, 1), 2)

    # Cerebras rates per 1M tokens (plan spec)
    input_cost = (total_prompt_tok / 1_000_000) * 0.60
    output_cost = (total_completion_tok / 1_000_000) * 1.20
    est_cost = round(input_cost + output_cost, 6)

    # Part 1.3: post-loop all-in-range check → apply_justify decision.
    # Also Addendum C: dual classification 95-100% vs 97-100% from the same run.
    # 2026-04-22: apply_justify uses a LENIENT acceptance band [target_min - 1, target_max + 7]
    # ≈ [95.33, 108.4] CU. Reason: visually, a bullet at 94-108 CU fills the line cleanly
    # and justify CSS looks natural. The strict [96.33, 101.4] window rejected bullets that
    # were visually indistinguishable from target. The lenient band is used ONLY for the
    # justify decision; the strict window is still reported as `pct_bullets_at_target`.
    raw_budget = target_max  # assume target_max == raw_budget (100%)
    stricter_min = 0.97 * raw_budget
    lenient_min = target_min - 1.0
    lenient_max = target_max + 7.0
    in_95_100 = sum(1 for e in per_bullet_log if target_min <= e.get("final_cu", 0) <= target_max)
    in_97_100 = sum(1 for e in per_bullet_log if stricter_min <= e.get("final_cu", 0) <= target_max)
    in_lenient = sum(1 for e in per_bullet_log if lenient_min <= e.get("final_cu", 0) <= lenient_max)
    all_in_range = (in_95_100 == total_bullets) and total_bullets > 0
    # Justify applied when ≥ 85% of bullets land in the lenient band.
    # Not 100% because one outlier bullet shouldn't kill visually-clean justify.
    all_in_lenient_pct = in_lenient / max(total_bullets, 1)
    apply_justify = all_in_lenient_pct >= 0.85 and total_bullets > 0

    poc_results = {
        "enabled": True,
        "total_bullets": total_bullets,
        "by_pass": {
            name: {"succeeded": count, "pct": round(100 * count / max(total_bullets, 1), 2)}
            for name, count in by_pass_counts.items()
        },
        "llm_calls_for_width": total_llm_calls,
        "tokens_for_width": {
            "prompt": total_prompt_tok,
            "completion": total_completion_tok,
            "total": total_prompt_tok + total_completion_tok,
        },
        "est_cost_for_width_usd": est_cost,
        "pct_bullets_at_target": pct_at_target,
        "target_range_cu": [target_min, target_max],
        "wall_time_s": round(time.time() - t0, 2),
        "hit_rates": {
            "at_95_to_100pct": round(100.0 * in_95_100 / max(total_bullets, 1), 2),
            "at_97_to_100pct": round(100.0 * in_97_100 / max(total_bullets, 1), 2),
            "at_lenient_band": round(100.0 * in_lenient / max(total_bullets, 1), 2),
        },
        "all_in_range": all_in_range,
        "apply_justify": apply_justify,
        "per_bullet_log": per_bullet_log,
    }
    return result, poc_results


def is_enabled() -> bool:
    """Check env flag."""
    return os.environ.get("ENABLE_WIDTH_POC", "").lower() in ("1", "true", "yes")
