"""Module 2: Phase 4a verbose paragraph prompt tests.

Tests the current vs proposed Phase 4a prompt on real Satvik data:
- Uses retrieval results from Module 1 (cached in session)
- Generates 4 paragraphs per JD × company using both prompt variants
- Evaluates: hallucination, JD keyword coverage, rigid-formula detection

Report: reports/phase_4a_comparison_{timestamp}.md
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.tools.hybrid_retrieval import hybrid_retrieve, format_nuggets_for_llm


# Hallucinations specific to Satvik's real profile (he's 3 yrs exp, in India)
HALLUCINATION_PATTERNS = [
    (r"\b\d+\+?\s*years?\b", "years claim"),
    (r"\bNew York\b", "fabricated location"),
    (r"\bUSA\b", "fabricated USA"),
    (r"\bSan Francisco\b", "fabricated location"),
]


def _tokenize(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"\w+", s) if len(w) >= 3}


def _keyword_coverage(keywords: list[str], text: str) -> tuple[float, list[str]]:
    """Returns (coverage_frac, matched_keywords)."""
    if not keywords:
        return 0.0, []
    text_lower = text.lower()
    tokens = _tokenize(text)
    matched = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in text_lower:
            matched.append(kw)
            continue
        kw_tokens = _tokenize(kw)
        if kw_tokens and kw_tokens.issubset(tokens):
            matched.append(kw)
    return len(matched) / len(keywords), matched


def _extract_hallucinations(text: str) -> list[tuple[str, str]]:
    """Returns list of (match_text, pattern_label) for fabrications."""
    hits = []
    for pat, label in HALLUCINATION_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            hits.append((m.group(0), label))
    return hits


def _build_user_prompt(
    jd: dict,
    company_name: str,
    company_title: str,
    company_dates: str,
    company_chunks: str,
    bullet_count: int,
) -> str:
    """Replicates PHASE_4A_VERBOSE_USER template."""
    jd_keywords_compact = json.dumps(jd["keywords"], separators=(",", ":"))
    req_lines = "\n".join(
        f"r{i+1}: {r} [P{(i % 2)}]" for i, r in enumerate(jd["requirements"])
    )
    return (
        f"## JD Keywords\n{jd_keywords_compact}\n\n"
        f"## JD Requirements (to reference in covers_requirements)\n{req_lines}\n\n"
        f"## Company: {company_name}\n"
        f"Title: {company_title}\n"
        f"Date: {company_dates}\n"
        f"Team: —\n\n"
        f"## Relevant Career Context\n{company_chunks}\n\n"
        f"Write {bullet_count} XYZ achievement paragraphs for this company. "
        "Lead with IMPACT, not action. Include verbose_context for each. ZERO verb repetition."
    )


def _substitute_system(system_template: str, strategy: str, strategy_desc: str,
                        career_level: str, bullet_count: int, used_verbs: list[str]) -> str:
    """Fill the system prompt template — matching orchestrator's variable set."""
    return (
        system_template
        .replace("{{strategy}}", strategy)
        .replace("{{strategy_description}}", strategy_desc)
        .replace("{{career_level}}", career_level)
        .replace("{{bullet_count}}", str(bullet_count))
        .replace("{{used_verbs}}", json.dumps(used_verbs))
    )


async def test_phase4a_per_jd(
    live_sb,
    satvik_user_id,
    target_jds,
    retrieval_cache,
    phase4a_output_cache,
    llm_primary,
    load_variant,
    report_writer,
):
    """A/B test current vs proposed Phase 4a prompt."""
    report_path = report_writer("phase_4a_comparison")

    # Pick one company to focus on — American Express has 9 nuggets, rich context
    company = "American Express"
    company_title = "Senior Associate Product Manager"
    company_dates = "Jul 2024 – Present"
    bullet_count = 4

    current_system = load_variant("phase4a_current")
    proposed_system = load_variant("phase4a_proposed")
    assert current_system, "phase4a_current.txt missing"
    assert proposed_system, "phase4a_proposed.txt missing"

    with report_path.open("w") as f:
        f.write("# Module 2: Phase 4a Verbose Paragraph — A/B Comparison\n\n")
        f.write(f"**Company:** {company}  \n")
        f.write(f"**Title/Dates:** {company_title} | {company_dates}  \n")
        f.write(f"**LLM:** {llm_primary.model_id}  \n")
        f.write(f"**Bullets per JD:** {bullet_count}  \n\n")
        f.write(
            "> Each JD is tested twice: once with the current production prompt, once with "
            "the proposed rewrite (few-shot Google examples + grounding rule + smart keyword "
            "integration). Automated checks detect hallucinations, keyword coverage, and "
            "rigid formula use.\n\n"
        )

        for jd in target_jds:
            jd_id = jd["id"]
            f.write(f"\n---\n\n## {jd['title']} @ {jd['company']} (`{jd_id}`)\n\n")

            # Retrieve context (use cache if Module 1 ran first)
            cache_key = (jd_id, company)
            if cache_key not in retrieval_cache:
                jd_query = " ".join(jd["keywords"][:5])
                effective_query = f"{company} {jd_query}"
                results, method = await hybrid_retrieve(
                    live_sb, satvik_user_id, effective_query,
                    company=company, limit=8,
                )
                retrieval_cache[cache_key] = results
            else:
                results = retrieval_cache[cache_key]

            company_chunks = format_nuggets_for_llm(results)[:5000]
            user_prompt = _build_user_prompt(
                jd, company, company_title, company_dates, company_chunks, bullet_count
            )

            f.write(f"**Retrieved nuggets:** {len(results)}  \n")
            f.write(f"**Context chars:** {len(company_chunks)}  \n\n")

            # Run both variants
            for variant_name, template in (
                ("CURRENT", current_system),
                ("PROPOSED", proposed_system),
            ):
                system = _substitute_system(
                    template,
                    strategy="IMPACT_FIRST",
                    strategy_desc="lead every paragraph with quantified outcome",
                    career_level="mid",
                    bullet_count=bullet_count,
                    used_verbs=[],
                )

                try:
                    resp = await llm_primary.complete(system, user_prompt, temperature=0.4)
                    raw = resp.text.strip()
                    # Strip markdown fences if present
                    if raw.startswith("```"):
                        raw = re.sub(r"^```(?:json)?\s*", "", raw)
                        raw = re.sub(r"\s*```$", "", raw)
                    data = json.loads(raw)
                    paragraphs = data.get("paragraphs", [])
                except Exception as e:
                    f.write(f"\n### ❌ {variant_name} — LLM call failed\n\n{e}\n\n")
                    continue

                phase4a_output_cache[(jd_id, company, variant_name)] = paragraphs

                f.write(f"\n### {variant_name} variant — {len(paragraphs)} paragraphs\n\n")

                # Per-paragraph evaluation
                f.write("| # | Verb | Chars | Starts <b>? | Hallucinations | JD kw hit | Paragraph (preview 250ch) |\n")
                f.write("|---|---|---|---|---|---|---|\n")

                all_hallucinations = []
                all_verbs = []
                combined_text = ""

                for i, p in enumerate(paragraphs, 1):
                    text_html = p.get("text_html", "")
                    verb = p.get("verb", "")
                    combined_text += " " + text_html
                    all_verbs.append(verb)

                    # Strip HTML tags for char count
                    stripped = re.sub(r"<[^>]+>", "", text_html)
                    char_count = len(stripped)

                    hallucinations = _extract_hallucinations(text_html)
                    all_hallucinations.extend(hallucinations)
                    halluc_str = ", ".join(f"{h[0]}({h[1]})" for h in hallucinations) or "—"

                    starts_bold = "✅" if text_html.strip().startswith("<b>") else "❌"

                    _, matched_kws = _keyword_coverage(jd["keywords"], text_html)
                    kw_str = f"{len(matched_kws)}"

                    preview = text_html[:250].replace("|", "\\|").replace("\n", " ")
                    f.write(f"| {i} | {verb} | {char_count} | {starts_bold} | {halluc_str} | {kw_str} | {preview} |\n")

                # Aggregate metrics
                cov, matched = _keyword_coverage(jd["keywords"], combined_text)
                unique_verbs = len(set(all_verbs)) == len(all_verbs)

                f.write(f"\n**Metrics:** total chars={len(combined_text)}, "
                        f"JD kw coverage={cov:.0%} ({len(matched)}/{len(jd['keywords'])} matched), "
                        f"unique verbs={unique_verbs}, hallucinations={len(all_hallucinations)}\n\n")

                if all_hallucinations:
                    f.write(f"**⚠️ Hallucinations detected:**\n")
                    for text, label in all_hallucinations:
                        f.write(f"- `{text}` ({label})\n")
                    f.write("\n")

                # Rigid formula detector — count paragraphs starting with "<b>N%" or "<b>$N"
                rigid_openers = sum(
                    1 for p in paragraphs
                    if re.match(r"<b>\s*[\d.]+[%$]?", p.get("text_html", ""))
                )
                f.write(f"**Rigid openers (start with <b>number%>):** "
                        f"{rigid_openers}/{len(paragraphs)}\n\n")

                # Full text for review
                f.write("<details><summary>Full paragraphs (click to expand)</summary>\n\n")
                for i, p in enumerate(paragraphs, 1):
                    f.write(f"\n**P{i}** ({p.get('verb','?')}):  \n")
                    f.write(f"{p.get('text_html','')}\n\n")
                    if "verbose_context" in p:
                        f.write(f"<br>*verbose_context*: {p['verbose_context'][:400]}…\n\n")
                f.write("</details>\n\n")

            # Comparison summary for this JD
            f.write("#### 🆚 Variant comparison\n\n")
            cur_paras = phase4a_output_cache.get((jd_id, company, "CURRENT"), [])
            pro_paras = phase4a_output_cache.get((jd_id, company, "PROPOSED"), [])

            def _halluc_count(paras):
                total = 0
                for p in paras:
                    total += len(_extract_hallucinations(p.get("text_html", "")))
                return total

            def _kw_cov(paras, kws):
                combined = " ".join(p.get("text_html", "") for p in paras)
                cov, _ = _keyword_coverage(kws, combined)
                return cov

            f.write("| Metric | Current | Proposed | Winner |\n")
            f.write("|---|---|---|---|\n")
            f.write(f"| Paragraphs returned | {len(cur_paras)} | {len(pro_paras)} | — |\n")
            f.write(f"| Hallucinations | {_halluc_count(cur_paras)} | {_halluc_count(pro_paras)} | "
                    f"{'PROPOSED' if _halluc_count(pro_paras) < _halluc_count(cur_paras) else 'tie/CURRENT'} |\n")
            f.write(f"| JD kw coverage | {_kw_cov(cur_paras, jd['keywords']):.0%} | "
                    f"{_kw_cov(pro_paras, jd['keywords']):.0%} | "
                    f"{'PROPOSED' if _kw_cov(pro_paras, jd['keywords']) > _kw_cov(cur_paras, jd['keywords']) else 'tie/CURRENT'} |\n")

        # Overall summary
        f.write("\n---\n\n## Overall Summary\n\n")
        total_cur_halluc = sum(
            sum(len(_extract_hallucinations(p.get("text_html",""))) for p in phase4a_output_cache.get((jd["id"], company, "CURRENT"), []))
            for jd in target_jds
        )
        total_pro_halluc = sum(
            sum(len(_extract_hallucinations(p.get("text_html",""))) for p in phase4a_output_cache.get((jd["id"], company, "PROPOSED"), []))
            for jd in target_jds
        )
        f.write(f"- **Total hallucinations (CURRENT):** {total_cur_halluc}\n")
        f.write(f"- **Total hallucinations (PROPOSED):** {total_pro_halluc}\n")
        f.write(f"- **Hallucination reduction:** {total_cur_halluc - total_pro_halluc}\n\n")

        f.write("### Manual Review Slots\n\n")
        f.write(
            "For each JD above, inspect the paragraphs and rate both variants:\n"
            "- Natural English vs robotic formula\n"
            "- Grounded in context vs inventing details\n"
            "- JD keyword integration feels natural vs forced\n\n"
            "Overall verdict (fill in):\n"
            "- PROPOSED prompt is clearly better: ☐\n"
            "- PROPOSED is marginal/mixed: ☐\n"
            "- CURRENT is better (revert proposed): ☐\n"
        )

    print(f"\n[Module 2] Report written: {report_path}")
    assert report_path.exists()
