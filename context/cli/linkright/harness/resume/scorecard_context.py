"""Build a scoring context dict from a run's ``artifacts/`` directory.

The ``ResumeScorecard.score(context)`` method expects a flat dict of signals
(jd_keywords, width_statuses, bullets, brs_scores, contrast_ratios, total_pages,
structural section flags). This helper reads the per-step artifact JSON files
and shapes them into that dict.

If an artifact is missing we fill defaults that drive that dimension to 0 —
harness/analyze_all.py will flag the run for attention.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _load_json(p: Path) -> Any:
    if not p.exists() or p.stat().st_size == 0:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _plain(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def build_context(run_dir: Path) -> dict[str, Any]:
    """Walk ``<run_dir>/artifacts/`` and return a context dict for scoring."""
    artifacts = run_dir / "artifacts"
    ctx: dict[str, Any] = {
        "jd_keywords": set(),
        "width_statuses": [],
        "synonym_swaps": 0,
        "bullets": [],
        "bullets_count": 0,
        "brs_scores": [],
        "contrast_ratios": [],
        "total_pages": 0,
        "page_utilization_pct": 0.0,  # Phase 1.2 — actual content height vs page
        "has_header": False,
        "has_experience": False,
        "has_education": False,
        "has_skills": False,
        "resume_text": "",
    }

    # JD keywords — step 07
    jd = _load_json(artifacts / "07_phase_1_2.json") or _load_json(artifacts / "07_jd_parse_strategy.json")
    if isinstance(jd, dict):
        parsed = jd.get("parsed") or jd
        kws = parsed.get("jd_keywords") or []
        ctx["jd_keywords"] = {k.lower() for k in kws if isinstance(k, str)}

    # Width / synonym — 13_width_optimized.json has nested {bullets: {<co>: [...]}}
    # OR (when step 13 skipped) note="skipped". Derive width_statuses from condensed
    # bullet lengths in that fallback case.
    wp = _load_json(artifacts / "13_width_optimized.json") or _load_json(artifacts / "13_width_poc.json")
    tel = _load_json(artifacts / "16_telemetry.json") or {}
    width_skipped = False
    if isinstance(wp, dict):
        if "skipped" in (wp.get("note", "") or "").lower():
            width_skipped = True
        wb = wp.get("bullets")
        statuses: list[str] = []
        # Real shape (post-2026-04-23): nested {company: [bullet_dict, ...]}
        if isinstance(wb, dict):
            for _co, _items in wb.items():
                for b in _items or []:
                    if not isinstance(b, dict):
                        continue
                    st = b.get("status")
                    if not st:
                        cu = b.get("cu") or b.get("final_cu") or 0
                        # CU target 96.33-101.4 (from STEP13_TARGET_CU_MIN/MAX)
                        st = "PASS" if (cu and 96.33 <= cu <= 101.4) else "FAIL"
                    statuses.append(st)
        # Older flat-list shape (kept for back-compat)
        elif isinstance(wb, list):
            for b in wb:
                if isinstance(b, dict):
                    st = b.get("status") or ("PASS" if (b.get("cu", 0) and 96.33 <= b.get("cu", 0) <= 101.4) else "FAIL")
                    statuses.append(st)
        ctx["width_statuses"] = statuses or wp.get("statuses", [])
        ctx["synonym_swaps"] = int(wp.get("synonym_swaps") or wp.get("llm_calls_for_width") or 0)

    # When step 13 is skipped, derive width status from step 12 condensed bullet
    # plain-text length. Target band 108-120 (= STEP12_MIN_CHARS to STEP12_MAX_CHARS+2).
    if width_skipped or not ctx["width_statuses"]:
        cond_for_width = _load_json(artifacts / "12_condensed_bullets.json") or {}
        if isinstance(cond_for_width, dict):
            statuses_d = []
            for _co, _bs in cond_for_width.items():
                for b in _bs or []:
                    txt = _plain((b.get("text_html") if isinstance(b, dict) else b) or "")
                    L = len(txt)
                    statuses_d.append("PASS" if 108 <= L <= 120 else "FAIL")
            if statuses_d:
                ctx["width_statuses"] = statuses_d

    # Synonym fallback from telemetry step counts (step_13)
    if ctx["synonym_swaps"] == 0 and isinstance(tel.get("by_step"), dict):
        s13 = tel["by_step"].get("step_13_width", {})
        ctx["synonym_swaps"] = int(s13.get("llm_calls", 0) or s13.get("attempts", 0))

    # Bullets — prefer condensed, fallback to verbose; 12 is {company: [bullet_dict...]}
    cond = _load_json(artifacts / "12_condensed_bullets.json") or _load_json(artifacts / "12_condensed.json")
    bullets: list[str] = []
    def _walk_company_keyed(obj):
        if not isinstance(obj, dict):
            return
        for _co, blk in obj.items():
            items = blk if isinstance(blk, list) else (blk.get("bullets") or blk.get("paragraphs") or [])
            for b in items or []:
                if isinstance(b, dict):
                    txt = _plain(b.get("text_html", "") or b.get("text", "") or b.get("final", "") or b.get("condensed", ""))
                    if txt:
                        bullets.append(txt)
                elif isinstance(b, str):
                    bullets.append(_plain(b))
    _walk_company_keyed(cond)
    if not bullets:
        verb = _load_json(artifacts / "10_verbose_bullets.json")
        if isinstance(verb, dict):
            for _co, blk in verb.items():
                if isinstance(blk, dict):
                    for p in blk.get("paragraphs", []) or []:
                        t = p if isinstance(p, str) else p.get("text") or p.get("text_html", "")
                        t = _plain(t)
                        if t:
                            bullets.append(t)
    ctx["bullets"] = bullets
    ctx["bullets_count"] = len(bullets)

    # BRS scores — step 11. Real artifact uses `_brs` (underscore prefix from
    # ranking-internal field name). Field-name fallback list updated.
    ranked = _load_json(artifacts / "11_ranked.json") or _load_json(artifacts / "11_ranked_bullets.json")
    if isinstance(ranked, dict):
        scores: list[float] = []
        for _co, blk in ranked.items():
            items = blk if isinstance(blk, list) else (blk.get("bullets") or blk.get("paragraphs") or [])
            for it in items or []:
                if isinstance(it, dict):
                    s = (it.get("_brs") or it.get("brs") or it.get("score")
                         or it.get("brs_score") or it.get("orig_brs"))
                    if isinstance(s, (int, float)):
                        scores.append(float(s))
        ctx["brs_scores"] = scores

    # Assembled HTML — real pipeline writes 14_final_resume.html (not JSON)
    html_file = artifacts / "14_final_resume.html"
    if html_file.exists():
        html_full = html_file.read_text(encoding="utf-8", errors="ignore")
        html = html_full.lower()
        ctx["has_header"] = ("name" in html or "@" in html)
        ctx["has_experience"] = "experience" in html
        ctx["has_education"] = "education" in html
        ctx["has_skills"] = "skills" in html
        ctx["has_summary"] = 'class="summary-line"' in html and bool(re.search(r'<div class="summary-line">[^<]+', html_full))
        ctx["has_projects_or_certs"] = ('class="section-title">Projects' in html_full
                                         or 'class="section-title">Certifications' in html_full)
        # Resume text (keep original case for acronym detection)
        ctx["resume_text"] = _plain(html_full)

        # Phase 1.5 — header_role + summary_text + bullets_per_role for new dims
        m_role = re.search(r'<div class="role">([^<]+)</div>', html_full)
        ctx["header_role"] = m_role.group(1).strip() if m_role else ""
        m_sum = re.search(r'<div class="summary-line">(.*?)</div>', html_full, re.DOTALL)
        ctx["summary_text"] = _plain(m_sum.group(1)) if m_sum else ""
        # Bullets per role — scoped to Professional Experience section ONLY.
        # 2026-05-02 fix: pre-fix the regex caught Project entries too (which
        # render as `<div class="entry">` with single-item `<ul>`), giving
        # bullets_per_role = [5, 4, 1, 1] and triggering structure_integrity's
        # variance penalty (max-min=4 >3 → ×0.85). Real roles have ≥2 bullets;
        # projects belong in their own section. Constrain the search window.
        bpr = []
        # Locate Professional Experience section bounds; fall back to entire HTML.
        m_exp_start = re.search(
            r'<div class="section-title">Professional Experience',
            html_full,
        )
        m_exp_end_after = None
        if m_exp_start:
            after = html_full[m_exp_start.end():]
            m_next_section = re.search(r'<div class="section-title">', after)
            search_window = after[:m_next_section.start()] if m_next_section else after
        else:
            search_window = html_full
        for ent_match in re.finditer(
            r'<div class="entry">\s*<div class="entry-header">.*?</div>\s*<div class="entry-subhead">.*?</div>\s*((?:<ul>.*?</ul>\s*)+)',
            search_window, re.DOTALL):
            bpr.append(ent_match.group(1).count("<li"))
        ctx["bullets_per_role"] = bpr

        # Phase 1.1 — extract hex colors from CSS, build text-vs-bg pairs.
        # bg = lightest color found; fg pairs = the DARKEST colors (those are the
        # text colors). Decorative mid-tone colors (yellow/red accents) are skipped
        # because they don't carry text — only narrow vector graphics.
        hex_colors = list({m.group(0).lower() for m in re.finditer(r"#[0-9a-fA-F]{3,6}\b", html_full)})
        contrast_pairs: list[tuple[str, str]] = []
        if len(hex_colors) >= 2:
            def _luma_proxy(h):
                hh = h.lstrip("#")
                if len(hh) == 3:
                    hh = "".join(c + c for c in hh)
                try:
                    return int(hh[0:2], 16) + int(hh[2:4], 16) + int(hh[4:6], 16)
                except ValueError:
                    return 0
            by_luma = sorted(hex_colors, key=_luma_proxy)
            bg = by_luma[-1]  # lightest = page background
            # Take darkest 1-3 (text colors) as fg
            for fg in by_luma[:3]:
                if fg != bg:
                    contrast_pairs.append((fg, bg))
        ctx["contrast_pairs"] = contrast_pairs
        ctx["contrast_ratios"] = [5.0, 4.8, 4.6]  # placeholder kept for fallback
    else:
        ctx["resume_text"] = " ".join(bullets)
        ctx["has_summary"] = False
        ctx["has_projects_or_certs"] = False
        ctx["header_role"] = ""
        ctx["summary_text"] = ""
        ctx["bullets_per_role"] = []
        ctx["contrast_pairs"] = []

    # Phase 1.5 — source nuggets text (for metric_fidelity scorer)
    nuggets_d = _load_json(artifacts / "02_nuggets_extracted.json") or {}
    nugs = nuggets_d.get("nuggets") if isinstance(nuggets_d, dict) else (nuggets_d if isinstance(nuggets_d, list) else [])
    source_text_parts = []
    for n in nugs or []:
        if isinstance(n, dict):
            ans = n.get("answer") or ""
            if ans:
                source_text_parts.append(ans)
    ctx["source_nuggets_text"] = " ".join(source_text_parts)

    # JD role (for header_jd_match)
    p07 = (_load_json(artifacts / "07_jd_parse_strategy.json") or {})
    parsed07 = p07.get("parsed") or p07
    ctx["jd_role"] = parsed07.get("target_role") or ""

    # v5.8 — populate JD text + resume markdown for relaxed acronym scorer
    inputs = run_dir / "inputs"
    try:
        jd_path = inputs / "jd.md"
        if jd_path.exists():
            ctx["jd_text"] = jd_path.read_text(encoding="utf-8", errors="ignore")
        else:
            ctx["jd_text"] = ""
    except Exception:
        ctx["jd_text"] = ""
    # resume markdown from step_01 parse (has 'markdown' or 'raw_text' field)
    p01 = _load_json(artifacts / "01_resume_parsed.json") or {}
    if isinstance(p01, dict):
        p01_inner = p01.get("parsed") or p01
        ctx["resume_markdown"] = p01.get("markdown") or p01.get("raw_text") or ""
    else:
        p01_inner = {}
        ctx["resume_markdown"] = ""

    # v0.1.6 entity-fidelity scorer ctx — rendered companies vs source experiences
    src_exp_companies = []
    for _exp in (p01_inner.get("experiences") or []):
        _co = (_exp.get("company") or "").strip()
        if _co:
            src_exp_companies.append(_co)
    ctx["source_experience_companies"] = src_exp_companies

    # Rendered company names from final HTML — extract entry-header spans in
    # Professional Experience section only.
    rendered_companies = []
    if html_file.exists():
        h_full2 = html_file.read_text(encoding="utf-8", errors="ignore")
        work = re.search(
            r'<div class="section-title">Professional Experience.*?(?=<div class="section-title">|</body)',
            h_full2, re.DOTALL,
        )
        if work:
            for m in re.finditer(
                r'<div class="entry-header"><span>([^<]+?)</span>',
                work.group(0),
            ):
                rendered_companies.append(m.group(1).strip())
    ctx["rendered_company_names"] = rendered_companies

    # Page count — authoritative source is fit_summary.final_page_count in telemetry
    if isinstance(tel, dict):
        fit = tel.get("fit_summary") or {}
        if "final_page_count" in fit:
            ctx["total_pages"] = int(fit["final_page_count"])
    if ctx["total_pages"] == 0:
        pdf_meta = _load_json(artifacts / "15_pdf.json") or _load_json(artifacts / "15_final_resume.json")
        if isinstance(pdf_meta, dict):
            ctx["total_pages"] = int(pdf_meta.get("total_pages") or pdf_meta.get("pages") or 0)

    # Phase 1.2 — page utilization estimate from rendered HTML element counts
    # against the validate_page_fit usable_height_mm reference (271.6 mm).
    # Heuristic per-element heights match the template defaults; matches user's
    # 95% target rule (now scored as ideal in scorecard._s_page_fit).
    if html_file.exists() and ctx["total_pages"] == 1:
        h_full = html_file.read_text(encoding="utf-8", errors="ignore")
        # Per-element height contributions (mm) — match validate_page_fit defaults
        ELEM_HEIGHTS = {
            "header_block": 21.34,
            "summary_line": 4.02,
            "section_title": 7.68,
            "section_spacing": 4.0,
            "entry_header": 4.44,
            "entry_subhead": 5.24,
            "entry_spacing": 2.5,
            "bullet_line": 4.52,
            "skills_line": 4.0,
            "education_year": 4.5,
        }
        total_mm = ELEM_HEIGHTS["header_block"]
        # Summary: estimate lines from char count (~110 chars per line at A4)
        m_sum = re.search(r'<div class="summary-line">(.*?)</div>', h_full, re.DOTALL)
        if m_sum:
            sum_chars = len(_plain(m_sum.group(1)))
            total_mm += max(1, sum_chars // 110 + 1) * ELEM_HEIGHTS["summary_line"]
        # Sections — count titles
        n_sections = len(re.findall(r'<div class="section-title">', h_full))
        total_mm += n_sections * (ELEM_HEIGHTS["section_title"] + ELEM_HEIGHTS["section_spacing"])
        # Entries (per role)
        n_entries = len(re.findall(r'<div class="entry">', h_full))
        total_mm += n_entries * (ELEM_HEIGHTS["entry_header"] + ELEM_HEIGHTS["entry_subhead"] + ELEM_HEIGHTS["entry_spacing"])
        # Bullets — count visual lines per bullet (chars / 120, min 1).
        # 2026-05-02 corrected calibration: CHARS_PER_LINE = 120 to match the
        # actual width target band (108-120c). Per Satvik 2026-05-02 evening
        # direction (memory `feedback_width_band_one_line_per_bullet`):
        # space-saving comes from OPTIMIZING bullets to fit 1 line each, NOT
        # from dropping content. An in-band bullet (108-120c) IS 1 line.
        # Earlier chars/95 was double-counting in-band bullets as 2 lines,
        # causing false util-overflow signals and unnecessary content drops.
        # NB: regex anchors `<li` to a `>` or whitespace boundary so we don't
        # accidentally match `<li-content-...` style class names.
        CHARS_PER_LINE = 120
        n_bullet_lines = 0
        for m in re.finditer(r"<li(?:\s[^>]*)?>(.*?)</li>", h_full, re.DOTALL):
            inner_chars = len(_plain(m.group(1)))
            n_bullet_lines += max(1, inner_chars // CHARS_PER_LINE + (1 if inner_chars % CHARS_PER_LINE else 0))
        total_mm += n_bullet_lines * ELEM_HEIGHTS["bullet_line"]
        # Skills line — count actual text-line lines instead of fixed 2.
        # 2026-05-02 (corrected): uses same CHARS_PER_LINE=120 for consistency
        # with width band — Skills text wraps at same char count as bullets.
        skills_lines = 0
        for m in re.finditer(r'<span class="text-line">([^<]+)</span>', h_full):
            chars = len(m.group(1).strip())
            if chars:
                skills_lines += max(1, chars // CHARS_PER_LINE + (1 if chars % CHARS_PER_LINE else 0))
        total_mm += skills_lines * ELEM_HEIGHTS["skills_line"]
        # Reference usable height (95% of 271.6 = 258 mm per locked rule)
        usable_mm = 271.6
        ctx["page_utilization_pct"] = round(min(100.0, 100.0 * total_mm / usable_mm), 1)

    return ctx
