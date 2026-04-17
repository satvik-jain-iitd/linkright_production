"""Module 3: Phase 4c bullet condensing prompt tests.

Tests current vs proposed Phase 4c prompt:
- Uses verbose paragraphs from Module 2 (phase4a_output_cache) as input.
- Falls back to canned synthetic paragraphs if M2 hasn't run.
- Evaluates: char count compliance, metric preservation, circular phrasing,
  bold-tag preservation.

Report: reports/phase_4c_comparison_{timestamp}.md
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def _bold_keywords(s: str) -> set[str]:
    return set(re.findall(r"<b>([^<]+)</b>", s))


def _metrics(s: str) -> set[str]:
    """Extract numbers with units: percentages, dollars, plain counts."""
    out = set()
    for m in re.finditer(r"\$\d+(?:\.\d+)?[KMB]?|\d+(?:,\d+)+|\d+(?:\.\d+)?%|\d+(?:\.\d+)?\+?(?=\s|$)", s):
        out.add(m.group(0).strip())
    return out


def _circular(s: str) -> list[str]:
    """Detect content words appearing 3+ times (circular phrasing)."""
    stripped = _strip_html(s).lower()
    tokens = re.findall(r"\w+", stripped)
    stopwords = {
        "the", "a", "an", "of", "to", "in", "by", "for", "with", "on",
        "through", "from", "and", "or", "at", "as", "is", "was", "be", "been",
        "via", "that", "this", "it", "its", "into",
    }
    from collections import Counter
    cnt = Counter(t for t in tokens if t not in stopwords and len(t) > 2)
    return [w for w, c in cnt.items() if c >= 3]


def _canned_paragraphs() -> list[dict]:
    """Fallback paragraphs when Module 2 hasn't run."""
    return [
        {
            "paragraph_index": 0,
            "text_html": "<b>Reduced speed-to-market by 70%</b>, from 10 days to 3 days, by leading an 18-member scrum team across 10 consecutive zero-spillover PIs at American Express, delivering 60+ features without any direct supervision.",
            "verb": "Reduced",
            "xyz": {"x_impact": "70% speed-to-market reduction", "y_measure": "10→3 days", "z_action": "led 18-member scrum across 10 PIs"},
        },
        {
            "paragraph_index": 1,
            "text_html": "<b>Achieved 80% AI-assisted story drafting adoption</b>, measured by sprint-planning user stories drafted via AI tools, by driving ChatGPT Enterprise rollout across the team and demoing Shipquick to VPs.",
            "verb": "Drove",
            "xyz": {"x_impact": "80% AI adoption", "y_measure": "user stories drafted", "z_action": "rolled out ChatGPT Enterprise"},
        },
        {
            "paragraph_index": 2,
            "text_html": "<b>Grew Use Case Hub adoption from 35% to 85%</b> across 1,500+ SME SaaS clients at Sprinklr, by prioritizing 10 use cases across 3 MVPs using product adoption data and building a 'Listen, Learn, Act' framework.",
            "verb": "Grew",
            "xyz": {"x_impact": "35→85% adoption growth", "y_measure": "1,500+ SME clients", "z_action": "prioritized via adoption data"},
        },
        {
            "paragraph_index": 3,
            "text_html": "<b>Delivered $1.2M TCV pipeline contribution</b> from a $9M+ Q4 FY24 Walmart Spark Driver Support engagement, by analyzing 100K+ contact center calls with unsupervised ML clustering and designing a custom L1/L2/L3 issue taxonomy.",
            "verb": "Delivered",
            "xyz": {"x_impact": "$1.2M TCV", "y_measure": "$9M+ pipeline", "z_action": "analyzed 100K+ calls with ML"},
        },
    ]


def _build_user_prompt(paragraphs: list[dict]) -> str:
    lines = []
    for i, p in enumerate(paragraphs):
        lines.append(
            f"PARAGRAPH {i} (verb: {p.get('verb','?')}): \"{p.get('text_html','')}\""
        )
    paragraphs_section = "\n\n".join(lines)
    return (
        "## Paragraphs to Condense\n\n"
        f"{paragraphs_section}\n\n"
        "Condense each paragraph to 95-110 rendered characters. "
        "Preserve <b> tags, verbs, and metrics exactly."
    )


async def test_phase4c_condense(
    target_jds,
    phase4a_output_cache,
    llm_condenser,
    llm_primary,
    load_variant,
    report_writer,
):
    """A/B test current vs proposed Phase 4c prompt across available paragraph sets."""
    report_path = report_writer("phase_4c_comparison")

    current_system = load_variant("phase4c_current")
    proposed_system = load_variant("phase4c_proposed")
    assert current_system, "phase4c_current.txt missing"
    assert proposed_system, "phase4c_proposed.txt missing"

    # Prefer real M2 outputs; fall back to canned
    paragraph_sets = []
    for jd in target_jds:
        for variant in ("PROPOSED", "CURRENT"):
            paras = phase4a_output_cache.get((jd["id"], "American Express", variant))
            if paras:
                paragraph_sets.append((f"{jd['id']}__m2_{variant}", paras))

    if not paragraph_sets:
        paragraph_sets.append(("canned_synthetic", _canned_paragraphs()))

    with report_path.open("w") as f:
        f.write("# Module 3: Phase 4c Bullet Condense — A/B Comparison\n\n")
        f.write(f"**Condenser LLM (primary):** {llm_condenser.model_id}  \n")
        f.write(f"**Fallback LLM:** {llm_primary.model_id}  \n")
        f.write(f"**Paragraph sets tested:** {len(paragraph_sets)}  \n\n")
        f.write(
            "> Each paragraph set is condensed with CURRENT and PROPOSED Phase 4c prompts. "
            "Automated checks: char count compliance (95-110), bold preservation, metric "
            "preservation, circular-phrasing detection.\n\n"
        )

        for set_name, paragraphs in paragraph_sets:
            f.write(f"\n---\n\n## Set: `{set_name}` ({len(paragraphs)} paragraphs)\n\n")
            user_prompt = _build_user_prompt(paragraphs).replace(
                "{paragraph_count}", str(len(paragraphs))
            )

            for variant_name, template in (
                ("CURRENT", current_system),
                ("PROPOSED", proposed_system),
            ):
                system = template.replace("{paragraph_count}", str(len(paragraphs)))

                try:
                    resp = await llm_condenser.complete(system, user_prompt, temperature=0.2)
                    raw = resp.text.strip()
                    if raw.startswith("```"):
                        raw = re.sub(r"^```(?:json)?\s*", "", raw)
                        raw = re.sub(r"\s*```$", "", raw)
                    data = json.loads(raw)
                    bullets = data.get("bullets", [])
                except Exception as e:
                    f.write(f"\n### ❌ {variant_name} — LLM call failed\n\n{e}\n\n")
                    continue

                f.write(f"\n### {variant_name} variant — {len(bullets)} bullets\n\n")
                f.write("| # | Src | Bullet | Chars | 95-110? | <b>? | Metrics lost | Circular words |\n")
                f.write("|---|---|---|---|---|---|---|---|\n")

                pass_count = 0
                for b in bullets:
                    idx = b.get("paragraph_index", -1)
                    if idx < 0 or idx >= len(paragraphs):
                        continue
                    src = paragraphs[idx].get("text_html", "")
                    out = b.get("text_html", "")

                    chars = len(_strip_html(out))
                    in_range = 95 <= chars <= 110
                    if in_range:
                        pass_count += 1

                    starts_bold = bool(out.strip().startswith("<b>"))
                    src_metrics = _metrics(_strip_html(src))
                    out_metrics = _metrics(_strip_html(out))
                    metrics_lost = src_metrics - out_metrics

                    circ_words = _circular(out)

                    src_preview = _strip_html(src)[:60].replace("|", "\\|")
                    out_preview = out[:200].replace("|", "\\|").replace("\n", " ")

                    f.write(
                        f"| {idx} | {src_preview}… | {out_preview} | {chars} | "
                        f"{'✅' if in_range else '❌'} | {'✅' if starts_bold else '❌'} | "
                        f"{', '.join(metrics_lost) if metrics_lost else '—'} | "
                        f"{', '.join(circ_words) if circ_words else '—'} |\n"
                    )

                f.write(f"\n**Pass rate (95-110 chars):** {pass_count}/{len(bullets)}\n\n")

        # Overall summary
        f.write("\n---\n\n## Manual Review Slots\n\n")
        f.write(
            "Open the bullets above and rate:\n"
            "- Does CURRENT produce circular phrasing (same word 3+ times)?\n"
            "- Does PROPOSED reduce circular phrasing?\n"
            "- Does PROPOSED read more naturally / varied?\n\n"
            "Verdict:\n"
            "- PROPOSED clearly better: ☐\n"
            "- Tied / marginal: ☐\n"
            "- CURRENT better: ☐\n"
        )

    print(f"\n[Module 3] Report written: {report_path}")
    assert report_path.exists()
