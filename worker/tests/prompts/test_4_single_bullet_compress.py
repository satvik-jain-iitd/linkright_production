"""Module 4: Single-bullet click-to-compress prompt tests.

Tests a NEW prompt (single_bullet_compress_v1.txt) designed for the future
click-to-compress UI feature — user picks one bullet, chooses target width,
system rewrites it at that width.

For each test bullet × target width (110/95/80):
- Call Oracle 1B
- Call Groq 70B
- Compare output quality, metric preservation, length compliance

Report: reports/single_bullet_compress_{timestamp}.md
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"

TARGET_WIDTHS = [110, 95, 80]


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def _metrics(s: str) -> set[str]:
    out = set()
    for m in re.finditer(r"\$\d+(?:\.\d+)?[KMB]?|\d+(?:,\d+)+|\d+(?:\.\d+)?%|\d+(?:\.\d+)?\+?(?=\s|$)", s):
        out.add(m.group(0).strip())
    return out


def _bold_keywords(s: str) -> set[str]:
    return set(re.findall(r"<b>([^<]+)</b>", s))


async def _run_one(llm, system_prompt: str, bullet: dict, target: int):
    """Returns (compressed_text, char_count, raw_json) or (None, None, error_str)."""
    user = (
        f"## Original bullet (current: {bullet['current_chars']} chars)\n"
        f"{bullet['bullet_html']}\n\n"
        f"## Target width\n{target} chars\n\n"
        f"## Verbose context (for re-phrasing reference)\n"
        f"{bullet['verbose_context']}\n\n"
        "Compress to target width. Return JSON: "
        '{"compressed_bullet": "<b>...</b>...", "chars": N, "notes": "what was cut/restructured"}'
    )
    try:
        resp = await llm.complete(system_prompt, user, temperature=0.2)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        out = data.get("compressed_bullet", "")
        return out, len(_strip_html(out)), data
    except Exception as e:
        return None, None, str(e)


async def test_single_bullet_compress(
    llm_compressor,
    load_variant,
    report_writer,
):
    """Evaluate Oracle 1B vs Groq 70B on the single-bullet compress prompt."""
    report_path = report_writer("single_bullet_compress")

    system = load_variant("single_bullet_compress_v1")
    assert system, "single_bullet_compress_v1.txt missing"

    with open(FIXTURES_DIR / "compress_test_bullets.json") as f:
        bullets = json.load(f)

    oracle = llm_compressor.get("oracle")
    groq = llm_compressor.get("groq")

    with report_path.open("w") as f:
        f.write("# Module 4: Single-Bullet Click-to-Compress — Oracle 1B vs Groq 70B\n\n")
        f.write(f"**Bullets tested:** {len(bullets)}  \n")
        f.write(f"**Target widths:** {TARGET_WIDTHS}  \n")
        f.write(f"**Oracle available:** {'yes (' + oracle.model_id + ')' if oracle else 'NO — skipped'}  \n")
        f.write(f"**Groq model:** {groq.model_id}  \n\n")
        f.write(
            "> For each bullet at each target width, we run the prompt on Oracle 1B "
            "(cheap/fast) and Groq 70B (higher quality). Compare outputs on accuracy, "
            "metric preservation, natural language.\n\n"
        )

        stats: dict[str, list[int]] = {"oracle_passes": [], "groq_passes": []}

        for bullet in bullets:
            f.write(f"\n---\n\n## Bullet: `{bullet['id']}`\n\n")
            f.write(f"**Original ({bullet['current_chars']} chars):**  \n")
            f.write(f"{bullet['bullet_html']}\n\n")
            src_metrics = _metrics(_strip_html(bullet["bullet_html"]))
            src_bold = _bold_keywords(bullet["bullet_html"])
            f.write(f"*Source metrics:* `{sorted(src_metrics)}`  \n")
            f.write(f"*Source bold spans:* `{sorted(src_bold)}`  \n\n")

            f.write("| Target | LLM | Chars | In range ±3 | Metrics preserved | Bold preserved | Output |\n")
            f.write("|---|---|---|---|---|---|---|\n")

            for target in TARGET_WIDTHS:
                for llm_name, llm in (("Oracle", oracle), ("Groq", groq)):
                    if llm is None:
                        f.write(f"| {target} | {llm_name} | — | — | — | — | (skipped) |\n")
                        continue

                    out, chars, data = await _run_one(llm, system, bullet, target)

                    if out is None:
                        f.write(f"| {target} | {llm_name} | ERROR | — | — | — | `{str(data)[:80]}` |\n")
                        continue

                    in_range = abs(chars - target) <= 3
                    out_metrics = _metrics(_strip_html(out))
                    metrics_preserved = src_metrics.issubset(out_metrics)
                    out_bold = _bold_keywords(out)
                    bold_preserved = len(out_bold) > 0

                    if in_range and metrics_preserved:
                        stats[f"{llm_name.lower()}_passes"].append(1)
                    else:
                        stats[f"{llm_name.lower()}_passes"].append(0)

                    preview = out[:180].replace("|", "\\|").replace("\n", " ")
                    f.write(
                        f"| {target} | {llm_name} | {chars} | "
                        f"{'✅' if in_range else '❌'} | "
                        f"{'✅' if metrics_preserved else '❌ ' + str(src_metrics - out_metrics)} | "
                        f"{'✅' if bold_preserved else '❌'} | "
                        f"{preview} |\n"
                    )

        # Summary
        f.write("\n---\n\n## Summary\n\n")
        total_tests = len(bullets) * len(TARGET_WIDTHS)
        if oracle:
            oracle_passes = sum(stats["oracle_passes"])
            f.write(f"- **Oracle 1B pass rate:** {oracle_passes}/{total_tests} "
                    f"({oracle_passes/total_tests:.0%})\n")
        groq_passes = sum(stats["groq_passes"])
        f.write(f"- **Groq 70B pass rate:** {groq_passes}/{total_tests} "
                f"({groq_passes/total_tests:.0%})\n\n")

        f.write("### Decision\n\n")
        f.write(
            "- If Oracle 1B passes ≥70% → use Oracle in production (cheap, fast)\n"
            "- If Oracle 1B passes <70% but Groq ≥70% → use Groq in production\n"
            "- If both <70% → iterate prompt (draft v2)\n\n"
            "Verdict (fill in):\n"
            "- Oracle 1B sufficient: ☐\n"
            "- Use Groq 70B instead: ☐\n"
            "- Prompt needs v2: ☐\n"
        )

    print(f"\n[Module 4] Report written: {report_path}")
    assert report_path.exists()
