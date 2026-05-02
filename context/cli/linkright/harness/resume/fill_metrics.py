"""Interactive metric-fill — truth-engine for missing/weak bullet metrics.

Per Satvik 2026-05-02: bullets lacking strong quantifiable claims get
PLACEHOLDERS (X%, Y$M, Z hours) auto-inserted, then surfaced to the user
for explicit review. Placeholders are NOT fabrication — they openly signal
"value pending; user supplies offline" (a common pattern for NDA/privacy).
Per gap, user has 3 choices: provide actual value / keep placeholder / drop
metric entirely. Tool suggests categories + industry ranges; user decides
final state. No number lands on the resume without user choosing it.

Flow:
    1. Read 12_condensed_bullets.json (final bullets)
    2. Score each bullet's metric magnitude tier (scorecard._bullet_magnitude)
    3. Surface bullets at tier <= 0.5 as gaps
    4. Per gap: LLM suggests 3 metric types + industry ranges
    5. User chooses ONE type (or "metric not relevant — skip")
    6. User picks one of 3 paths:
       a. Type actual value → rewrite with that number
       b. Use placeholder (X/Y/Z) → rewrite with placeholder symbol
       c. Cancel — leave bullet alone
    7. Save updated bullets, re-render, re-score, write placeholder log
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

from linkright.config import LINKRIGHT_HOME

RUNS_ROOT = LINKRIGHT_HOME / "runs"

WEAK_METRIC_TIER = 0.5
MISSING_METRIC_TIER = 0.0

PLACEHOLDER_SYMBOLS = ["X", "Y", "Z", "A", "B", "C", "D", "E"]


def _build_placeholder(symbol: str, unit: str) -> str:
    """Compose a placeholder string like 'X%' or '$Y M' or 'Z hours'.

    Truth-engine pattern: openly signal pending value. The recruiter sees
    'X%' and reads it as "value to be supplied" — preferable to fabricating
    a specific number, and a known industry pattern for NDA/confidential work.
    """
    unit = (unit or "").strip()
    if not unit:
        return symbol
    if "%" in unit:
        return f"{symbol}%"
    if "$" in unit:
        # Preserve magnitude marker if present (e.g. "$M", "$K", "$B")
        mag = "".join(c for c in unit if c in "MBK")
        return f"${symbol}{mag}" if mag else f"${symbol}"
    return f"{symbol} {unit}"


def _plain(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def detect_metric_gaps(run_dir: Path) -> list[dict[str, Any]]:
    """Find bullets whose metric tier is weak or absent.

    Returns list of gap records: {company, idx, text_html, text_plain, tier}.
    Lower tier = bigger gap. We surface tier <= 0.5 (raw-int or none).
    """
    from linkright.resume.scorecard import _bullet_magnitude

    cb_path = run_dir / "artifacts" / "12_condensed_bullets.json"
    if not cb_path.exists():
        return []
    cb = json.loads(cb_path.read_text())

    gaps: list[dict[str, Any]] = []
    for company, bullets in cb.items():
        if not isinstance(bullets, list):
            continue
        for idx, b in enumerate(bullets):
            text_html = b.get("text_html", "")
            plain = _plain(text_html)
            tier = _bullet_magnitude(plain)
            if tier <= WEAK_METRIC_TIER:
                gaps.append({
                    "company": company,
                    "idx": idx,
                    "text_html": text_html,
                    "text_plain": plain,
                    "tier": tier,
                    "verb": b.get("verb", ""),
                })
    gaps.sort(key=lambda g: g["tier"])
    return gaps


def suggest_metrics_for_bullet(
    bullet_text: str, jd_keywords: list[str], company: str, role: str,
) -> list[dict[str, str]]:
    """LLM call: propose 3 metric TYPES + industry ranges for this bullet.

    Returns list of suggestions: {metric_type, unit, typical_range, midpoint, rationale}.
    Industry ranges are LLM-estimated; user always confirms with actual value.
    """
    from linkright.llm.direct import tier_chat

    system = (
        "You are a resume metrics advisor. Output ONLY a single JSON object — "
        "no preamble, no markdown fences, no explanation."
    )
    user = (
        f"A resume bullet is missing a strong quantifiable metric. "
        f"Suggest exactly 3 DIFFERENT metric types that could naturally fit it.\n\n"
        f"BULLET: {bullet_text}\n"
        f"COMPANY: {company}\n"
        f"ROLE LEVEL: {role}\n"
        f"JD PRIORITIES: {', '.join(jd_keywords[:8])}\n\n"
        f"For each suggestion, give:\n"
        f"  - metric_type: short label (e.g., 'revenue impact', 'time saved', "
        f"'user reach', 'cost reduction', 'efficiency gain', 'NPS lift', 'cycle-time cut')\n"
        f"  - unit: concrete unit ('$M', '%', 'hours', 'users', 'days')\n"
        f"  - typical_range: industry-average range a candidate at this level might achieve "
        f"(e.g., '10-30%', '$0.5M-$5M', '20-40 hours/week')\n"
        f"  - midpoint: single number to default to if user accepts (e.g., '20%', '$2M')\n"
        f"  - rationale: 1 short sentence why this metric fits THIS bullet\n\n"
        f"Output JSON ONLY:\n"
        f'{{"suggestions": [{{"metric_type": "...", "unit": "...", "typical_range": "...", '
        f'"midpoint": "...", "rationale": "..."}}, ..., ...]}}'
    )

    text, _ = tier_chat(
        system=system, user=user, klass="C",
        intent="fill_metrics_suggest", max_tokens=600,
    )
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        parsed = json.loads(text)
        suggestions = parsed.get("suggestions", [])[:3]
        return [s for s in suggestions if isinstance(s, dict)]
    except Exception as exc:
        print(f"  ! LLM suggestion parse failed: {exc}; raw={text[:150]}",
              file=sys.stderr)
        return []


def apply_metric_to_bullet(
    bullet_text: str, metric_type: str, metric_value: str, role: str,
) -> Optional[str]:
    """LLM call: rewrite bullet to naturally incorporate user-confirmed metric.

    Preserves XYZ format (Impact-Measure-Action) and existing bold tags. No
    other fabrication. Returns rewritten text_html, or None on failure.
    """
    from linkright.llm.direct import tier_chat

    system = (
        "You are a resume bullet rewriter. Output ONLY the rewritten bullet "
        "as HTML (with <b> tags preserved around the strongest claim). "
        "No preamble, no markdown."
    )
    user = (
        f"Rewrite this bullet to naturally incorporate the user-confirmed metric. "
        f"Preserve XYZ format (Impact, Measure, Action). Bold the impact phrase "
        f"that includes the metric. Don't fabricate any OTHER numbers or claims.\n\n"
        f"ORIGINAL: {bullet_text}\n\n"
        f"METRIC TO ADD: {metric_value} ({metric_type})\n"
        f"ROLE LEVEL: {role}\n\n"
        f"Output: ONE bullet, HTML with <b> tags, 100-120 chars."
    )

    text, _ = tier_chat(
        system=system, user=user, klass="B",
        intent="fill_metrics_apply", max_tokens=300,
    )
    text = text.strip().strip('"').strip("'")
    if text.startswith("```"):
        text = re.sub(r"^```(?:html)?\s*|\s*```$", "", text, flags=re.S)
    if not text:
        return None
    if "<b>" not in text:
        text = f"<b>{text}</b>" if len(text) < 60 else text
    return text


def _format_suggestion_choice(s: dict[str, str]) -> str:
    return (f"{s.get('metric_type','?')} ({s.get('unit','?')}) "
            f"— typical {s.get('typical_range','?')} | {s.get('rationale','')}")


def run_fill_metrics(run_id: Optional[str] = None, dry_run: bool = False) -> dict:
    """Interactive metric-fill pipeline. See module docstring."""
    import questionary
    from harness.resume.improve import re_render
    from harness.resume.scorecard_context import build_context
    from linkright.resume.scorecard import ResumeScorecard

    if not run_id:
        candidates = [d for d in RUNS_ROOT.iterdir()
                      if d.is_dir() and not d.name.startswith("hyp_")]
        if not candidates:
            return {"error": "no runs found"}
        run_dir = max(candidates, key=lambda p: p.stat().st_mtime)
    else:
        run_dir = RUNS_ROOT / run_id
    if not run_dir.exists():
        return {"error": f"run not found: {run_dir}"}

    print(f"=== Fill Metrics: {run_dir.name} ===", file=sys.stderr)

    ctx_before = build_context(run_dir)
    sc_before = ResumeScorecard(run_id=run_dir.name)
    sc_before.score(ctx_before)
    md_before = next((r.score for r in sc_before.results if r.name == "metric_density"), 0.0)
    print(f"\nBefore — overall: {sc_before.overall_score:.1f} ({sc_before.overall_grade}), "
          f"metric_density: {md_before:.1f}\n", file=sys.stderr)

    gaps = detect_metric_gaps(run_dir)
    print(f"Found {len(gaps)} weak/missing-metric bullet(s):\n", file=sys.stderr)
    for g in gaps:
        print(f"  [{g['company']}#{g['idx']}, tier={g['tier']:.1f}] {g['text_plain']}",
              file=sys.stderr)
    print()

    if not gaps:
        return {"gaps": 0, "before_score": sc_before.overall_score, "filled": 0}
    if dry_run:
        return {"gaps": len(gaps), "dry_run": True}

    strat = json.loads((run_dir / "artifacts" / "07_jd_parse_strategy.json").read_text())
    parsed_p12 = strat["parsed"] if "parsed" in strat else strat
    jd_keywords = parsed_p12.get("jd_keywords", []) or []
    role = (parsed_p12.get("career_level") or "mid").upper()

    cb_path = run_dir / "artifacts" / "12_condensed_bullets.json"
    cb = json.loads(cb_path.read_text())
    filled = 0
    placeholders_used: list[dict[str, str]] = []
    actuals_used: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    placeholder_idx = 0

    for g in gaps:
        print(f"\n─── Gap {filled + 1} of {len(gaps)} ───", file=sys.stderr)
        print(f"Company: {g['company']}", file=sys.stderr)
        print(f"Bullet:  {g['text_plain']}\n", file=sys.stderr)

        suggestions = suggest_metrics_for_bullet(
            g["text_plain"], jd_keywords, g["company"], role,
        )
        if not suggestions:
            print("  ! No suggestions returned by LLM — skipping.", file=sys.stderr)
            skipped.append({"company": g["company"], "idx": g["idx"],
                           "reason": "no_llm_suggestions"})
            continue

        choices = [_format_suggestion_choice(s) for s in suggestions]
        choices.append("⏭  Metric not relevant — skip this bullet")
        pick = questionary.select(
            "Which metric type fits best?",
            choices=choices,
        ).ask()
        if pick is None or pick.startswith("⏭"):
            print("  Skipped (metric not relevant per user).", file=sys.stderr)
            skipped.append({"company": g["company"], "idx": g["idx"],
                           "reason": "user_marked_not_relevant"})
            continue

        chosen = suggestions[choices.index(pick)]
        metric_type = chosen.get("metric_type", "metric")
        unit = chosen.get("unit", "")
        midpoint = str(chosen.get("midpoint", ""))
        typical = chosen.get("typical_range", "")
        print(f"\n  Industry typical: {typical}", file=sys.stderr)

        value_choice = questionary.select(
            "How would you like to fill this metric?",
            choices=[
                f"📊 Provide actual value (recommended if you have it)",
                f"📝 Use placeholder ({_build_placeholder(PLACEHOLDER_SYMBOLS[placeholder_idx % len(PLACEHOLDER_SYMBOLS)], unit)}) — fill offline later",
                "⏭  Cancel — don't add this metric",
            ],
        ).ask()
        if value_choice is None or value_choice.startswith("⏭"):
            print("  Cancelled.", file=sys.stderr)
            skipped.append({"company": g["company"], "idx": g["idx"],
                           "reason": "user_cancelled_at_value_step"})
            continue

        is_placeholder = value_choice.startswith("📝")
        if is_placeholder:
            symbol = PLACEHOLDER_SYMBOLS[placeholder_idx % len(PLACEHOLDER_SYMBOLS)]
            value = _build_placeholder(symbol, unit)
            placeholder_idx += 1
        else:
            value = questionary.text(
                f"Your actual {metric_type} value "
                f"(industry typical: {typical}, midpoint suggestion: {midpoint}):",
                default=midpoint,
            ).ask()
            if value is None or not value.strip():
                print("  Cancelled (no value).", file=sys.stderr)
                skipped.append({"company": g["company"], "idx": g["idx"],
                               "reason": "user_skipped_at_actual_value"})
                continue
            value = value.strip()

        new_html = apply_metric_to_bullet(g["text_plain"], metric_type, value, role)
        if not new_html:
            print("  ! LLM rewrite failed — skipping.", file=sys.stderr)
            skipped.append({"company": g["company"], "idx": g["idx"],
                           "reason": "llm_rewrite_failed"})
            continue

        old_html = cb[g["company"]][g["idx"]]["text_html"]
        cb[g["company"]][g["idx"]]["text_html"] = new_html
        cb[g["company"]][g["idx"]]["improved_by"] = (
            cb[g["company"]][g["idx"]].get("improved_by", "") + ";fill_metrics"
        )
        if is_placeholder:
            cb[g["company"]][g["idx"]]["placeholder"] = {
                "symbol": value, "metric_type": metric_type,
                "unit": unit, "typical_range": typical,
            }
            placeholders_used.append({
                "company": g["company"], "idx": g["idx"],
                "placeholder": value, "metric_type": metric_type,
                "typical_range": typical,
            })
            print(f"  ✓ Placeholder inserted: {value}", file=sys.stderr)
        else:
            actuals_used.append({
                "company": g["company"], "idx": g["idx"],
                "actual_value": value, "metric_type": metric_type,
            })
            print(f"  ✓ Actual value inserted: {value}", file=sys.stderr)
        print(f"    OLD: {_plain(old_html)}", file=sys.stderr)
        print(f"    NEW: {_plain(new_html)}", file=sys.stderr)
        filled += 1

    placeholder_log = run_dir / "artifacts" / "12b_metric_fill_log.json"
    placeholder_log.write_text(json.dumps({
        "filled": filled,
        "placeholders": placeholders_used,
        "actuals": actuals_used,
        "skipped": skipped,
    }, indent=2))

    if filled == 0:
        print("\nNo metrics filled. Exiting without re-render.", file=sys.stderr)
        return {"gaps": len(gaps), "filled": 0,
                "before_score": sc_before.overall_score,
                "placeholders": 0, "actuals": 0, "skipped": len(skipped)}

    cb_path.write_text(json.dumps(cb, indent=2))
    print(f"\n✓ Wrote {filled} metric-filled bullet(s) to 12_condensed_bullets.json",
          file=sys.stderr)
    print(f"  Placeholders: {len(placeholders_used)}, "
          f"Actuals: {len(actuals_used)}, Skipped: {len(skipped)}", file=sys.stderr)
    if placeholders_used:
        print(f"\n📝 {len(placeholders_used)} placeholder(s) pending — fill offline & re-run "
              f"`linkright resume fill-metrics` when ready", file=sys.stderr)

    re_render(run_dir)

    ctx_after = build_context(run_dir)
    sc_after = ResumeScorecard(run_id=run_dir.name)
    sc_after.score(ctx_after)
    md_after = next((r.score for r in sc_after.results if r.name == "metric_density"), 0.0)
    delta = sc_after.overall_score - sc_before.overall_score
    print(f"\nAfter — overall: {sc_after.overall_score:.1f} ({sc_after.overall_grade}), "
          f"metric_density: {md_after:.1f}", file=sys.stderr)
    print(f"  Δ overall: {delta:+.1f}, Δ metric_density: {md_after - md_before:+.1f}",
          file=sys.stderr)

    sc_after.write(run_dir)

    return {
        "gaps": len(gaps),
        "filled": filled,
        "placeholders": len(placeholders_used),
        "actuals": len(actuals_used),
        "skipped": len(skipped),
        "placeholder_log": str(placeholder_log),
        "before_score": sc_before.overall_score,
        "after_score": sc_after.overall_score,
        "before_metric_density": md_before,
        "after_metric_density": md_after,
        "delta": delta,
    }
