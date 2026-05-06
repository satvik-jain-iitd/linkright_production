"""End-of-pipeline critique step — Truth Engine Layer 3.

Per Jane 2026-05-02 (memory feedback_end_of_pipeline_critique_step):
After step_15 PDF render, run an LLM critique pass that:
  1. Reads the rendered resume HTML + JD
  2. Lists ≤5 actionable issues with severity
  3. Per issue: 3 fix options including "manual edit by user"
  4. User picks; tool applies the chosen fix
  5. Re-render + re-score
  6. Persist audit trail

Closes the Truth Engine loop:
  Layer 1 (start):  contact verify (profile/pipeline.py:contact_verify_loop)
  Layer 2 (mid):    fill-metrics actual-vs-placeholder (fill_metrics.py)
  Layer 3 (end):    critique review (THIS module)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from linkright.config import LINKRIGHT_HOME

RUNS_ROOT = LINKRIGHT_HOME / "runs"


def _strip_html(html: str) -> str:
    """Plain text from HTML for LLM context (cuts CSS, scripts, comments)."""
    h = re.sub(r"<style[^>]*>.*?</style>", "", html or "", flags=re.S | re.I)
    h = re.sub(r"<script[^>]*>.*?</script>", "", h, flags=re.S | re.I)
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    h = re.sub(r"\s+", " ", h).strip()
    return h


def _invoke_critic_llm(rendered_text: str, jd_text: str) -> list[dict]:
    """Call LLM critic. Returns list of issue dicts. Class D (judgment).

    Robust JSON parsing — extracts JSON block even if LLM emits prose around it.
    Returns empty list on parse failure (caller handles gracefully).
    """
    from linkright.llm.direct import tier_chat

    system = (
        "You are a senior resume critic with 10+ years of recruiting experience. "
        "Read a rendered resume + the target JD. Identify up to 5 ACTIONABLE issues "
        "that hurt the candidate's shortlist chances. Output JSON ONLY — no preamble, "
        "no markdown fences, no commentary."
    )
    user = (
        f"=== RESUME (rendered, plain text) ===\n{rendered_text[:6000]}\n\n"
        f"=== JOB DESCRIPTION ===\n{jd_text[:2000]}\n\n"
        f"Identify up to 5 issues. Each issue MUST:\n"
        f"  - Cite a specific word/phrase/section (location field)\n"
        f"  - Be objectively wrong or weak (not stylistic preference)\n"
        f"  - Have CONCRETE fixes (specific text replacements, not vague advice)\n"
        f"\n"
        f"Output JSON shape:\n"
        f'{{"issues": [\n'
        f'  {{"id": 1,\n'
        f'    "severity": "HIGH" | "MEDIUM" | "LOW",\n'
        f'    "location": "Skills section" or "Bullet 3 of <Company> role" etc.,\n'
        f'    "issue": "1-sentence description",\n'
        f'    "fix_a": "specific replacement text or action",\n'
        f'    "fix_b": "alternative replacement (different angle)",\n'
        f'    "rationale": "why this hurts shortlist chances"}},\n'
        f"  ...\n"
        f"]}}\n\n"
        f"Focus on: weak phrasings, generic skills, missing JD-keyword coverage, "
        f"wrong tense, illogical sentences, redundancy, unclear metrics, "
        f"non-actionable verbs (\"worked on\", \"helped\", \"assisted\"), "
        f"verbose construction, JD-misalignments."
    )
    try:
        text, _usage = tier_chat(
            system=system, user=user, klass="D",
            intent="step_16b_critique_review", max_tokens=2000,
        )
    except Exception as e:
        print(f"  ! LLM critique failed: {type(e).__name__}: {e}", file=sys.stderr)
        return []

    text = text.strip()
    # Strip markdown fences if LLM ignored instruction
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)

    # Try direct parse
    try:
        parsed = json.loads(text)
    except Exception:
        # Robust: find first {...} block
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            print(f"  ! Critique LLM returned unparseable text: {text[:200]}", file=sys.stderr)
            return []
        try:
            parsed = json.loads(m.group(0))
        except Exception as e:
            print(f"  ! Critique JSON parse failed: {e}", file=sys.stderr)
            return []

    issues = parsed.get("issues", []) if isinstance(parsed, dict) else []
    return [i for i in issues if isinstance(i, dict)]


def _format_severity(sev: str) -> str:
    sev = (sev or "").upper()
    return {"HIGH": "🔴 HIGH", "MEDIUM": "🟡 MED", "LOW": "🟢 LOW"}.get(sev, sev)


def _apply_text_replacement(run_dir: Path, search: str, replacement: str) -> bool:
    """Naive text replacement across condensed bullets + summary.

    Returns True if a change was made. The fix LLM emits the text to find +
    text to replace; we search the relevant artifacts and apply.
    """
    if not search or not replacement:
        return False
    changed = False

    # Try 12_condensed_bullets.json
    bullets_path = run_dir / "artifacts" / "12_condensed_bullets.json"
    if bullets_path.exists():
        cb = json.loads(bullets_path.read_text())
        for co, bullets in cb.items():
            if not isinstance(bullets, list):
                continue
            for b in bullets:
                old = b.get("text_html", "")
                if search in old:
                    b["text_html"] = old.replace(search, replacement, 1)
                    b["improved_by"] = (b.get("improved_by", "") + ";critique_fix").strip(";")
                    changed = True
        if changed:
            bullets_path.write_text(json.dumps(cb, indent=2))
            return True

    # Try summary
    sum_path = run_dir / "artifacts" / "09_professional_summary.html"
    if sum_path.exists():
        old = sum_path.read_text()
        if search in old:
            sum_path.write_text(old.replace(search, replacement, 1))
            return True

    return False


def _open_in_editor(file_path: Path) -> None:
    """Open the HTML or bullets JSON in user's $EDITOR for manual edit."""
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"
    try:
        subprocess.call([editor, str(file_path)])
    except Exception as e:
        print(f"  ! Failed to launch {editor}: {e}. File path: {file_path}",
              file=sys.stderr)


def run_critique(run_id: Optional[str] = None) -> dict:
    """Interactive end-of-pipeline critique. See module docstring."""
    import questionary
    from rich.console import Console
    from rich.panel import Panel

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

    console = Console()
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]🔍 Critique Review — Truth Engine Layer 3[/]\n"
        f"[dim]Run: {run_dir.name}[/]\n"
        f"LLM critic surfaces top 5 actionable issues. Per issue: pick auto-fix, "
        f"manual edit, or skip.",
        border_style="cyan",
    ))

    html_path = run_dir / "artifacts" / "14_final_resume.html"
    jd_path = run_dir / "inputs" / "jd.md"
    if not html_path.exists():
        return {"error": f"missing rendered HTML at {html_path}"}
    rendered = _strip_html(html_path.read_text(encoding="utf-8", errors="ignore"))
    jd_text = jd_path.read_text(encoding="utf-8", errors="ignore") if jd_path.exists() else ""

    console.print("\n[dim]Calling LLM critic (klass=D, ~5-10s)...[/]\n")
    issues = _invoke_critic_llm(rendered, jd_text)

    audit: dict = {
        "run_id": run_dir.name,
        "issues_found": len(issues),
        "issue_log": [],
    }

    if not issues:
        console.print("[yellow]No actionable issues identified by critic. "
                      "Either the resume is clean or LLM call failed — check stderr.[/]")
        audit_path = run_dir / "artifacts" / "16b_critique.json"
        audit_path.write_text(json.dumps(audit, indent=2))
        return audit

    console.print(f"[bold]Found {len(issues)} actionable issue(s):[/]\n")
    for issue in issues:
        console.print(f"  {_format_severity(issue.get('severity'))} "
                      f"[{issue.get('location', '?')}] {issue.get('issue', '?')}")
    console.print()

    applied_count = 0
    skipped_count = 0
    manual_count = 0

    for i, issue in enumerate(issues, 1):
        console.print(f"\n[bold]── Issue {i} of {len(issues)} ──[/]")
        console.print(f"  Severity: {_format_severity(issue.get('severity'))}")
        console.print(f"  Location: {issue.get('location', '?')}")
        console.print(f"  Problem:  {issue.get('issue', '?')}")
        console.print(f"  Why:      [dim]{issue.get('rationale', '')}[/]")

        fix_a = issue.get("fix_a", "").strip()
        fix_b = issue.get("fix_b", "").strip()

        choices = []
        if fix_a:
            choices.append(f"📝 Apply Fix A: {fix_a[:80]}{'...' if len(fix_a) > 80 else ''}")
        if fix_b:
            choices.append(f"📝 Apply Fix B: {fix_b[:80]}{'...' if len(fix_b) > 80 else ''}")
        choices.append("✏️  Manual edit (open in editor)")
        choices.append("⏭  Skip — leave as-is")

        try:
            pick = questionary.select(
                "How to resolve?",
                choices=choices,
            ).ask()
        except KeyboardInterrupt:
            console.print("[red]Aborted by user. Audit log saved up to this point.[/]")
            break

        if pick is None or pick.startswith("⏭"):
            skipped_count += 1
            audit["issue_log"].append({**issue, "action": "skipped"})
            continue

        if pick.startswith("✏️"):
            # Open bullets JSON for editing (most actionable target)
            bullets_path = run_dir / "artifacts" / "12_condensed_bullets.json"
            target = bullets_path if bullets_path.exists() else html_path
            console.print(f"\n  Opening {target.name} in $EDITOR (fallback: nano)...")
            _open_in_editor(target)
            manual_count += 1
            audit["issue_log"].append({**issue, "action": "manual_edited",
                                        "edited_file": str(target)})
            continue

        # Auto-fix path — extract the chosen fix's full text from issue
        chosen_fix = fix_a if pick.startswith("📝 Apply Fix A") else fix_b
        # Heuristic: if fix is a "find → replace" pair (e.g., "X → Y"), split.
        # Otherwise, surface the fix to user as guidance + open editor.
        m_arrow = re.search(r"(.+?)\s*[→\-]>?\s*(.+)", chosen_fix)
        if m_arrow:
            search = m_arrow.group(1).strip().strip('"').strip("'")
            replacement = m_arrow.group(2).strip().strip('"').strip("'")
            applied = _apply_text_replacement(run_dir, search, replacement)
            if applied:
                applied_count += 1
                audit["issue_log"].append({**issue, "action": "auto_applied",
                                            "search": search, "replacement": replacement})
                console.print(f"  [green]✓ Applied: '{search[:40]}' → '{replacement[:40]}'[/]")
            else:
                console.print(f"  [yellow]· Auto-fix didn't find search text. "
                              f"Falling back to manual edit.[/]")
                bullets_path = run_dir / "artifacts" / "12_condensed_bullets.json"
                target = bullets_path if bullets_path.exists() else html_path
                _open_in_editor(target)
                manual_count += 1
                audit["issue_log"].append({**issue, "action": "manual_edited_after_auto_miss",
                                            "edited_file": str(target)})
        else:
            console.print(f"  [yellow]· Fix is not a find/replace pair. "
                          f"Opening editor for manual application.[/]")
            console.print(f"  [dim]Suggested change: {chosen_fix}[/]")
            bullets_path = run_dir / "artifacts" / "12_condensed_bullets.json"
            target = bullets_path if bullets_path.exists() else html_path
            _open_in_editor(target)
            manual_count += 1
            audit["issue_log"].append({**issue, "action": "manual_edited",
                                        "guidance": chosen_fix,
                                        "edited_file": str(target)})

    audit["applied"] = applied_count
    audit["manual_edited"] = manual_count
    audit["skipped"] = skipped_count

    audit_path = run_dir / "artifacts" / "16b_critique.json"
    audit_path.write_text(json.dumps(audit, indent=2))

    console.print(f"\n[bold]Critique complete:[/]")
    console.print(f"  Applied auto-fixes:  {applied_count}")
    console.print(f"  Manual edits:        {manual_count}")
    console.print(f"  Skipped:             {skipped_count}")

    if applied_count > 0 or manual_count > 0:
        console.print("\n[dim]Re-rendering + re-scoring...[/]")
        from harness.resume.improve import re_render
        from harness.resume.scorecard_context import build_context
        from linkright.resume.scorecard import ResumeScorecard

        re_render(run_dir)
        ctx = build_context(run_dir)
        sc = ResumeScorecard(run_id=run_dir.name)
        sc.score(ctx)
        sc.write(run_dir)
        audit["after_score"] = sc.overall_score
        audit["after_grade"] = sc.overall_grade
        audit_path.write_text(json.dumps(audit, indent=2))
        console.print(f"  [green]New score: {sc.overall_score:.1f} ({sc.overall_grade})[/]")

    return audit
