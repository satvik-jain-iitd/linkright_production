"""Deep Root-Cause Analysis — per-step audit across all diagnostic runs.

Pure read-only. Walks every run dir matching `runs/run_*`, evaluates each
pipeline step's output against an explicit expectation contract, and emits:

  runs/deep_rca_<date>.json   — machine-readable scorecard + metrics
  runs/deep_rca_<date>.md     — scorecard grid + narrative per FAIL
  runs/run_04_*/PASS_E_POSTMORTEM.md — per-bullet Pass-E analysis (run_04 only)

Verdicts:
  ✅ PASS       — matches expectation
  ⚠  WARN       — shape OK, quality off
  ❌ FAIL       — structural break / empty / missing critical field
  ⏸  BLOCKED   — step never ran (artifact missing entirely)
  —             — step not applicable to this run

Each step check returns (verdict, short_reason, metrics_dict).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Callable, Optional

from ._paths import RUNS_ROOT as RUNS, ensure_runs_root  # noqa: E402

ROOT = Path(__file__).resolve().parent
ensure_runs_root()
DATE_TAG = dt.date.today().isoformat()


# ─── Verdict helpers ─────────────────────────────────────────────────────────

def _load_json(p: Path) -> Optional[dict | list]:
    if not p.exists() or p.stat().st_size == 0:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


# ─── Per-step check functions ────────────────────────────────────────────────
# Each returns (verdict, reason, metrics)

def check_00_raw(run: Path) -> tuple[str, str, dict]:
    p = run / "artifacts" / "00_resume_raw_text.txt"
    if not p.exists():
        return "⏸", "file missing", {}
    text = p.read_text(encoding="utf-8", errors="ignore")
    n = len(text)
    # TODO: hardcoded user-specific company markers removed. Restore as
    # profile-derived check in follow-up PR (read expected companies from
    # profile metadata).
    if n < 2000:
        return "❌", f"too short: {n} chars", {"chars": n}
    return "✅", f"{n} chars", {"chars": n}


def check_01_parsed(run: Path) -> tuple[str, str, dict]:
    d = _load_json(run / "artifacts" / "01_resume_parsed.json")
    if d is None:
        return "⏸", "missing/empty", {}
    parsed = d.get("parsed") or d
    exp = parsed.get("experiences") or parsed.get("companies") or []
    if not isinstance(exp, list):
        return "❌", "no experiences/companies list", {}
    if len(exp) < 3:
        return "⚠", f"only {len(exp)} companies parsed", {"companies": len(exp)}
    return "✅", f"{len(exp)} companies parsed", {"companies": len(exp)}


def check_02_nuggets(run: Path) -> tuple[str, str, dict]:
    d = _load_json(run / "artifacts" / "02_nuggets_extracted.json")
    if d is None:
        return "⏸", "missing/empty", {}
    nug = d.get("nuggets", []) if isinstance(d, dict) else []
    n = len(nug)
    if n == 0:
        return "❌", "zero nuggets extracted", {"count": 0}
    required = ("company", "role", "importance", "answer")
    bad = [i for i, x in enumerate(nug) if not all(k in x for k in required)]
    ans_lens = [len((x.get("answer") or "").strip()) for x in nug]
    avg_ans = sum(ans_lens) / len(ans_lens) if ans_lens else 0
    companies = set((x.get("company") or "").strip() for x in nug if x.get("company"))
    metrics = {"count": n, "avg_ans_len": round(avg_ans, 1), "companies": len(companies), "missing_fields": len(bad)}
    if bad:
        return "❌", f"{len(bad)} nuggets missing required fields", metrics
    if n < 8:
        return "⚠", f"low count {n}", metrics
    if avg_ans < 30:
        return "⚠", f"avg answer short ({avg_ans:.0f} chars)", metrics
    return "✅", f"{n} nuggets, {len(companies)} companies, avg ans {avg_ans:.0f}c", metrics


def check_03_embedded(run: Path) -> tuple[str, str, dict]:
    rows = _load_jsonl(run / "artifacts" / "03_nuggets_embedded.jsonl")
    if not rows:
        return "⏸", "missing/empty", {}
    # Compare vs step 02 count
    step02 = _load_json(run / "artifacts" / "02_nuggets_extracted.json") or {}
    nug_count = len(step02.get("nuggets", []) if isinstance(step02, dict) else [])
    dim_set = set()
    latencies = []
    for r in rows:
        # dim might be under meta.dim or at top level 'embedding_len'
        dim = None
        if isinstance(r, dict):
            if r.get("embedding_len"):
                dim = r["embedding_len"]
            elif isinstance(r.get("meta"), dict):
                dim = r["meta"].get("dim")
            elif r.get("embedding"):
                dim = len(r["embedding"]) if isinstance(r["embedding"], list) else None
            lat = (r.get("meta") or {}).get("latency_s")
            if lat is not None:
                latencies.append(lat)
        if dim:
            dim_set.add(dim)
    metrics = {"rows": len(rows), "nug_count": nug_count, "dims": sorted(dim_set), "latency_samples": len(latencies), "latency_sum": round(sum(latencies), 1)}
    if len(rows) != nug_count:
        return "❌", f"row mismatch: {len(rows)} embedded vs {nug_count} nuggets", metrics
    if dim_set and 768 not in dim_set:
        return "❌", f"wrong dim: {dim_set}", metrics
    if dim_set and len(dim_set) > 1:
        return "⚠", f"mixed dims: {dim_set}", metrics
    return "✅", f"{len(rows)} rows @ dim 768", metrics


def check_05_jd_req_embed(run: Path) -> tuple[str, str, dict]:
    p = run / "artifacts" / "05_jd_req_embeddings.jsonl"
    if not p.exists():
        return "—", "not produced by this run", {}
    rows = _load_jsonl(p)
    if not rows:
        return "❌", "empty file", {"rows": 0}
    return "✅", f"{len(rows)} req embeddings", {"rows": len(rows)}


def check_06_role_scores(run: Path) -> tuple[str, str, dict]:
    d = _load_json(run / "artifacts" / "06_role_scores.json")
    if d is None:
        return "⏸", "missing/empty", {}
    covered = d.get("coverage_pct")
    role_scores = d.get("role_scores") or {}
    gaps = d.get("gaps") or []
    metrics = {"coverage_pct": covered, "gaps": len(gaps), "dims_scored": len(role_scores)}
    if covered is None:
        return "⚠", "no coverage_pct field", metrics
    return "✅", f"coverage {covered}%, {len(gaps)} gaps", metrics


def check_07_jd(run: Path) -> tuple[str, str, dict]:
    d = _load_json(run / "artifacts" / "07_jd_parse_strategy.json")
    if d is None:
        return "⏸", "missing/empty", {}
    p = d.get("parsed") or d
    reqs = p.get("requirements") or []
    kws = p.get("jd_keywords") or []
    metrics = {"requirements": len(reqs), "jd_keywords": len(kws), "target_role": p.get("target_role")}
    if len(reqs) == 0:
        return "❌", "zero requirements parsed", metrics
    if len(reqs) < 5:
        return "⚠", f"only {len(reqs)} requirements", metrics
    if len(kws) < 5:
        return "⚠", f"only {len(kws)} keywords", metrics
    return "✅", f"{len(reqs)} reqs, {len(kws)} keywords", metrics


def check_08_retrieval(run: Path) -> tuple[str, str, dict]:
    d = _load_json(run / "artifacts" / "08_relevant_nuggets_per_company.json")
    if d is None:
        return "⏸", "missing/empty", {}
    ret = d.get("retrieved", {}) if isinstance(d, dict) else {}
    if not ret:
        return "❌", "no retrieval results", {}
    per_co = {co: len(nugs) for co, nugs in ret.items() if isinstance(nugs, list)}
    min_n = min(per_co.values()) if per_co else 0
    empty_cos = [co for co, n in per_co.items() if n == 0]
    metrics = {"companies": len(per_co), "per_co": per_co, "min": min_n, "empty": empty_cos}
    if not per_co:
        return "❌", "no companies in retrieval", metrics
    if empty_cos:
        return "❌", f"{len(empty_cos)} companies got 0 nuggets: {empty_cos}", metrics
    if min_n < 3:
        return "⚠", f"low min: {min_n} nuggets in smallest company", metrics
    return "✅", f"{len(per_co)} companies, min {min_n} nuggets", metrics


def check_09_summary(run: Path) -> tuple[str, str, dict]:
    p = run / "artifacts" / "09_professional_summary.html"
    if not p.exists():
        return "⏸", "missing", {}
    html = p.read_text(encoding="utf-8")
    plain = re.sub(r"<[^>]+>", "", html).strip()
    n = len(plain)
    metrics = {"plain_chars": n}
    if n < 80:
        return "⚠", f"summary too short ({n} chars)", metrics
    if n > 400:
        return "⚠", f"summary long ({n} chars)", metrics
    return "✅", f"{n} chars", metrics


def check_10_verbose(run: Path) -> tuple[str, str, dict]:
    """Step 10 verbose bullets — critical Phase 4a output.
    Detects the fabricated_atom_id issue we saw in run_03 + run_04_noon."""
    d = _load_json(run / "artifacts" / "10_verbose_bullets.json")
    if d is None:
        return "⏸", "missing/empty", {}
    kept = {}
    dropped = {}
    reasons = []
    for co, blk in d.items():
        if isinstance(blk, dict):
            p = blk.get("paragraphs", [])
            dr = blk.get("dropped", [])
            kept[co] = len(p)
            dropped[co] = len(dr)
            for d_entry in dr:
                r = d_entry.get("reason") or d_entry.get("error")
                if r:
                    reasons.append(r)
    total_kept = sum(kept.values())
    total_dropped = sum(dropped.values())
    drop_rate = total_dropped / max(total_kept + total_dropped, 1)
    empty_companies = [co for co, n in kept.items() if n == 0]
    metrics = {
        "kept_total": total_kept,
        "dropped_total": total_dropped,
        "drop_rate": round(drop_rate, 2),
        "empty_companies": empty_companies,
        "drop_reasons": list(set(reasons)),
    }
    if total_kept == 0:
        return "❌", f"zero bullets kept (all dropped: {reasons[:3]})", metrics
    if empty_companies:
        return "❌", f"empty companies: {empty_companies}", metrics
    if drop_rate > 0.3:
        return "⚠", f"high drop rate {drop_rate*100:.0f}% ({reasons[:2]})", metrics
    return "✅", f"{total_kept} kept, {total_dropped} dropped", metrics


def check_11_ranked(run: Path) -> tuple[str, str, dict]:
    d = _load_json(run / "artifacts" / "11_ranked_bullets.json")
    if d is None:
        return "⏸", "missing/empty", {}
    totals = {}
    for co, blk in d.items():
        if isinstance(blk, list):
            totals[co] = len(blk)
        elif isinstance(blk, dict):
            totals[co] = len(blk.get("bullets", []) or blk.get("paragraphs", []))
    total = sum(totals.values())
    if total == 0:
        return "❌", "zero ranked bullets", {"per_co": totals}
    return "✅", f"{total} ranked across {len(totals)} companies", {"per_co": totals, "total": total}


def check_12_condensed(run: Path) -> tuple[str, str, dict]:
    d = _load_json(run / "artifacts" / "12_condensed_bullets.json")
    if d is None:
        return "⏸", "missing/empty", {}
    total = 0
    with_bold = 0
    verb_first = 0
    char_dist = []
    for co, blist in d.items():
        if not isinstance(blist, list):
            continue
        for b in blist:
            if not isinstance(b, dict):
                continue
            total += 1
            txt = b.get("text_html", "") or ""
            char_dist.append(len(re.sub(r"<[^>]+>", "", txt)))
            if "<b>" in txt.lower() or "<strong>" in txt.lower():
                with_bold += 1
            plain = re.sub(r"<[^>]+>", "", txt).strip()
            first = plain.split()[0] if plain.split() else ""
            if first.endswith(("ed", "ied", "t", "n")) or first.lower() in {"led", "drove", "built", "grew", "won", "saved"}:
                verb_first += 1
    metrics = {
        "total_bullets": total,
        "with_bold_pct": round(with_bold / max(total, 1) * 100, 1),
        "verb_first_pct": round(verb_first / max(total, 1) * 100, 1),
        "avg_chars": round(sum(char_dist) / max(len(char_dist), 1), 1) if char_dist else 0,
    }
    if total == 0:
        return "❌", "zero bullets", metrics
    if metrics["with_bold_pct"] < 50:
        return "⚠", f"only {metrics['with_bold_pct']:.0f}% bullets have <b>", metrics
    if metrics["verb_first_pct"] < 60:
        return "⚠", f"only {metrics['verb_first_pct']:.0f}% verb-first", metrics
    return "✅", f"{total} bullets, {metrics['with_bold_pct']:.0f}% bold, avg {metrics['avg_chars']:.0f}c", metrics


def check_13_width(run: Path) -> tuple[str, str, dict]:
    """Uses 16_telemetry.json::width_poc block (the "skipped" 13_* file
    is intentional in this harness — real data lives in telemetry)."""
    tel = _load_json(run / "artifacts" / "16_telemetry.json") or {}
    wp = tel.get("width_poc") or {}
    if not wp or not wp.get("enabled"):
        # Width POC was off for this run
        return "—", "POC disabled for this run", {"enabled": False}
    hit = (wp.get("hit_rates") or {}).get("at_95_to_100pct", 0)
    aj = wp.get("apply_justify")
    bp = wp.get("by_pass") or {}
    pe = (bp.get("E_accepted_with_warning") or {}).get("succeeded", 0)
    pd = (bp.get("D_llm_rephrase") or {}).get("succeeded", 0)
    total = wp.get("total_bullets", 0)
    metrics = {
        "total_bullets": total,
        "hit_rate_95_100": hit,
        "apply_justify": aj,
        "pass_d_success": pd,
        "pass_e_fallback": pe,
        "target_range": wp.get("target_range_cu"),
        "llm_calls": wp.get("llm_calls_for_width"),
    }
    if total == 0:
        return "❌", "zero bullets optimized", metrics
    if hit < 50:
        return "❌", f"hit rate only {hit:.0f}% (target ≥50%)", metrics
    if not aj:
        return "⚠", f"{hit:.0f}% hit but justify not applied", metrics
    return "✅", f"hit {hit:.0f}%, justify={aj}", metrics


def check_14_html(run: Path) -> tuple[str, str, dict]:
    p = run / "artifacts" / "14_final_resume.html"
    if not p.exists():
        return "⏸", "missing", {}
    html = p.read_text(encoding="utf-8")
    n = len(html)
    # Cheap tag-balance check for <b>
    b_open = len(re.findall(r"<b(?:\s[^>]*)?>", html, flags=re.I))
    b_close = len(re.findall(r"</b>", html, flags=re.I))
    li_count = len(re.findall(r"<li[\s>]", html, flags=re.I))
    metrics = {"chars": n, "b_open": b_open, "b_close": b_close, "li_count": li_count}
    if n < 1000:
        return "⚠", f"final HTML short ({n} chars)", metrics
    if b_open != b_close:
        return "❌", f"<b> tag mismatch: open={b_open} close={b_close}", metrics
    return "✅", f"{n} chars, {li_count} bullets, tags balanced", metrics


def check_15_pdf(run: Path) -> tuple[str, str, dict]:
    p = run / "artifacts" / "15_final_resume.pdf"
    if not p.exists():
        return "⏸", "no PDF produced", {}
    size_kb = p.stat().st_size / 1024
    metrics = {"size_kb": round(size_kb, 1)}
    if size_kb < 50:
        return "❌", f"PDF too small ({size_kb:.0f} KB)", metrics
    if size_kb > 500:
        return "⚠", f"PDF large ({size_kb:.0f} KB) — may indicate >1 page", metrics
    return "✅", f"{size_kb:.0f} KB", metrics


def check_16_telemetry(run: Path) -> tuple[str, str, dict]:
    d = _load_json(run / "artifacts" / "16_telemetry.json")
    if d is None:
        return "⏸", "missing/empty", {}
    totals = d.get("totals") or {}
    providers = d.get("by_provider") or {}
    wall = d.get("wall_time_s")
    metrics = {
        "wall_time_s": wall,
        "providers": sorted(providers.keys()),
        "llm_api_calls": totals.get("llm_api_calls_successful"),
        "oracle_embed_calls": totals.get("oracle_embed_calls"),
        "total_tokens": totals.get("total_tokens"),
        "est_cost_usd": totals.get("estimated_cost_usd"),
    }
    if wall is None:
        return "❌", "no wall_time_s", metrics
    if not providers:
        return "⚠", "empty by_provider dict", metrics
    return "✅", f"wall {wall:.0f}s, providers={sorted(providers.keys())}, oracle_embed={metrics['oracle_embed_calls']}", metrics


CHECKS: list[tuple[str, Callable]] = [
    ("00", check_00_raw),
    ("01", check_01_parsed),
    ("02", check_02_nuggets),
    ("03", check_03_embedded),
    ("05", check_05_jd_req_embed),
    ("06", check_06_role_scores),
    ("07", check_07_jd),
    ("08", check_08_retrieval),
    ("09", check_09_summary),
    ("10", check_10_verbose),
    ("11", check_11_ranked),
    ("12", check_12_condensed),
    ("13", check_13_width),
    ("14", check_14_html),
    ("15", check_15_pdf),
    ("16", check_16_telemetry),
]


# ─── Pass-E postmortem for run_04 ────────────────────────────────────────────

def pass_e_postmortem(run_dirs: list[Path]) -> list[dict]:
    rows = []
    for run in run_dirs:
        if "run_04" not in run.name or "aggregate" in run.name:
            continue
        rep = run / "reports" / "width_poc_results.md"
        if not rep.exists():
            continue
        text = rep.read_text(encoding="utf-8")
        # Table format: | # | Company | Pre-A CU | Final Pass | Final CU | Passes tried |
        for line in text.splitlines():
            m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([\d.]+)\s*\|\s*(\w+)\s*\|\s*([\d.]+)\s*\|\s*([^|]*?)\s*\|", line)
            if not m:
                continue
            idx, co, pre_a, final_pass, final_cu, passes = m.groups()
            rows.append({
                "run": run.name.replace("run_04_2026-04-22_", ""),
                "company": co.strip(),
                "bullet_idx": int(idx),
                "pre_a_cu": float(pre_a),
                "final_pass": final_pass,
                "final_cu": float(final_cu),
                "passes_tried": passes.strip(),
                "cu_delta": round(float(final_cu) - float(pre_a), 2),
            })
    return rows


# ─── Scorecard aggregation ───────────────────────────────────────────────────

VERDICT_ORDER = {"✅": 0, "—": 1, "⚠": 2, "❌": 3, "⏸": 4}


def main():
    run_dirs = sorted(
        d for d in RUNS.iterdir()
        if d.is_dir() and d.name.startswith("run_") and "aggregate" not in d.name
    )
    print(f"Analyzing {len(run_dirs)} runs")

    scorecard: dict[str, dict[str, tuple[str, str, dict]]] = {}
    for run in run_dirs:
        scorecard[run.name] = {}
        for step_id, fn in CHECKS:
            try:
                scorecard[run.name][step_id] = fn(run)
            except Exception as exc:
                scorecard[run.name][step_id] = ("❌", f"check crashed: {exc}", {})

    # Pass-E postmortem
    pe_rows = pass_e_postmortem(run_dirs)

    # ── JSON output ──
    out_json = RUNS / f"deep_rca_{DATE_TAG}.json"
    out_json.write_text(json.dumps({
        "date": DATE_TAG,
        "runs_analyzed": len(run_dirs),
        "scorecard": {
            run: {step: {"verdict": v[0], "reason": v[1], "metrics": v[2]} for step, v in steps.items()}
            for run, steps in scorecard.items()
        },
        "pass_e_postmortem": pe_rows,
    }, indent=2, default=str), encoding="utf-8")

    # ── Markdown scorecard ──
    md = [f"# Deep RCA — {DATE_TAG}\n"]
    md.append(f"**Runs analyzed:** {len(run_dirs)}\n")
    md.append("## Scorecard\n")
    # Header
    header_row = "| Run | " + " | ".join(s for s, _ in CHECKS) + " |"
    sep_row = "|---|" + "|".join(["---"] * len(CHECKS)) + "|"
    md.extend([header_row, sep_row])
    for run, steps in scorecard.items():
        short = run.replace("run_", "").replace("_2026-04-2", "-")[:36]
        cells = [steps[s][0] for s, _ in CHECKS]
        md.append(f"| `{short}` | " + " | ".join(cells) + " |")

    md.append("\n## Verdicts — one-line reasons\n")
    md.append("| Run | Step | Verdict | Reason |")
    md.append("|---|:-:|:-:|---|")
    for run, steps in scorecard.items():
        short = run.replace("run_", "").replace("_2026-04-2", "-")[:36]
        for step_id, _ in CHECKS:
            v, r, _ = steps[step_id]
            if v != "✅" and v != "—":
                md.append(f"| `{short}` | {step_id} | {v} | {r} |")

    md.append("\n## Key metrics per step (for deeper inspection)\n")
    for run, steps in scorecard.items():
        short = run.replace("run_", "")[:50]
        md.append(f"\n### `{short}`\n")
        for step_id, _ in CHECKS:
            v, r, m = steps[step_id]
            if m:
                kv = ", ".join(f"{k}={v}" for k, v in list(m.items())[:6])
                md.append(f"- **{step_id}** {v} — {r}    _{kv}_")
            else:
                md.append(f"- **{step_id}** {v} — {r}")

    # Pass-E postmortem
    if pe_rows:
        md.append("\n## Pass-E Postmortem (run_04 bullets that fell to accept-with-warning)\n")
        md.append("| Run | # | Company | Pre-A CU | Final Pass | Final CU | Δ | Passes tried |")
        md.append("|---|--:|---|--:|:-:|--:|--:|---|")
        for r in pe_rows:
            md.append(
                f"| `{r['run'][:20]}` | {r['bullet_idx']} | {r['company']} | "
                f"{r['pre_a_cu']} | {r['final_pass']} | {r['final_cu']} | "
                f"{r['cu_delta']:+.2f} | {r['passes_tried']} |"
            )

        # Summary: of Pass-E bullets, how many had Pass D attempted vs not?
        pe_only = [r for r in pe_rows if r["final_pass"] == "E"]
        d_attempted = [r for r in pe_only if "D" in r["passes_tried"]]
        md.append(
            f"\n**Pass-E summary**: {len(pe_only)} bullets ended in Pass E. "
            f"{len(d_attempted)} of those had Pass D attempted (LLM rephrase made but result out of target)."
        )

    out_md = RUNS / f"deep_rca_{DATE_TAG}.md"
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"\nWrote:\n  {out_json}\n  {out_md}")
    print("\n=== Top-line verdict counts ===")
    counts = {"✅": 0, "⚠": 0, "❌": 0, "⏸": 0, "—": 0}
    for _, steps in scorecard.items():
        for _, (v, _, _) in steps.items():
            counts[v] = counts.get(v, 0) + 1
    for v, c in counts.items():
        print(f"  {v} {c}")


if __name__ == "__main__":
    main()
