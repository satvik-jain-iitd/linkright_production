"""`linkright resume` subcommand group.

Subcommands:
  tailor  — resume + JD → tailored HTML/PDF + scorecard
  score   — compute scorecard for an existing PDF against a JD
  batch   — tailor across a directory of JDs
  iterate — open the B1-B9 iteration loop (harness-driven)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import click

from ..config import Config
from ..cli_aliases import AliasedGroup
from .brand import brand_cmd
from .lib.preflight import require_profile, require_llm_key, require_tailor_run


@click.group(cls=AliasedGroup, name="resume")
def resume_group() -> None:
    """Pillar 1 — Resume tailoring + scoring.

    \b
    Quick aliases (subcommand level — long names also work):
      t  → tailor      crit / c → critique     prac / p → practice
      s  → score       fill / f → fill-metrics plan / r → strategy-review
      imp / i → improve

    Tip: prefix matching works (git-style). `linkright resume tail` →
    tailor when no other tail* exists.
    """


def _read_quality_metrics(run_dir: Path) -> dict:
    """Read JD coverage, width hit-rate, and below-threshold bullet count from pipeline artifacts.

    Returns a dict with keys:
      jd_coverage_pct      — float or None
      jd_covered           — int (covered req count)
      jd_total             — int (total req count)
      width_hit_pct        — float or None
      width_hit_bullets    — int (bullets in target band)
      width_total_bullets  — int (total bullets)
      below_threshold_count — int (bullets flagged _below_threshold by S5.5 gate)
    """
    result: dict = {
        "jd_coverage_pct": None,
        "jd_covered": 0,
        "jd_total": 0,
        "width_hit_pct": None,
        "width_hit_bullets": 0,
        "width_total_bullets": 0,
        "below_threshold_count": 0,
    }
    # JD coverage — from 06_role_scores.json
    role_scores_path = run_dir / "artifacts" / "06_role_scores.json"
    if role_scores_path.exists():
        try:
            data = json.loads(role_scores_path.read_text())
            pct = data.get("coverage_pct")
            covered = data.get("covered_reqs", [])
            gaps = data.get("gaps", [])
            if pct is not None:
                result["jd_coverage_pct"] = float(pct)
                result["jd_covered"] = len(covered) if isinstance(covered, list) else 0
                result["jd_total"] = result["jd_covered"] + (len(gaps) if isinstance(gaps, list) else 0)
        except Exception:
            pass

    # Width hit-rate — from 16_telemetry.json width_poc block
    telemetry_path = run_dir / "artifacts" / "16_telemetry.json"
    if telemetry_path.exists():
        try:
            tel = json.loads(telemetry_path.read_text())
            poc = tel.get("width_poc") or {}
            hit_pct = poc.get("pct_bullets_at_target")
            total = poc.get("total_bullets")
            if hit_pct is not None and total is not None:
                result["width_hit_pct"] = float(hit_pct)
                result["width_total_bullets"] = int(total)
                result["width_hit_bullets"] = round(int(total) * float(hit_pct) / 100)
        except Exception:
            pass

    # S5.5 — below-threshold bullet count — from 11_ranked_bullets.json
    ranked_path = run_dir / "artifacts" / "11_ranked_bullets.json"
    if ranked_path.exists():
        try:
            ranked = json.loads(ranked_path.read_text())
            count = sum(
                1
                for bullets in ranked.values()
                for b in bullets
                if b.get("_below_threshold")
            )
            result["below_threshold_count"] = count
        except Exception:
            pass

    return result


def _fmt_metric_value(value_str: str, pct: float, warn_color: str = "#FF5733") -> str:
    """Wrap value_str in warning color markup when pct < 80, else return plain."""
    if pct < 80.0:
        return f"[{warn_color}]{value_str}[/]"
    return value_str


def _render_success_card(run_dir: Path, started_at: float) -> None:
    """Print the end-of-tailor success summary card."""
    from linkright.ui import success_card, TEAL
    duration = time.monotonic() - started_at
    mins, secs = divmod(int(duration), 60)
    duration_str = f"{mins}m {secs:02d}s" if mins else f"{secs}s"

    pdf_path = run_dir / "artifacts" / "15_final_resume.pdf"
    if pdf_path.exists():
        # AC3: bold filename on first line, dimmed full path on second line.
        # The newline is handled by success_card() which indents continuation
        # lines to the value column — no mid-word wrap occurs because each
        # line segment is a self-contained Rich Text span (no spaces to break
        # on, and overflow="fold" is the fallback for absurdly long paths).
        pdf_line = pdf_path.name + "\n" + str(pdf_path)
    else:
        pdf_line = "(PDF not produced — see logs/pipeline.log)"

    fields = [("PDF", pdf_line), ("Took", duration_str)]

    scorecard_path = run_dir / "scorecard.json"
    if scorecard_path.exists():
        try:
            data = json.loads(scorecard_path.read_text())
            score = data.get("overall_score")
            grade = data.get("overall_grade", "")
            if score is not None:
                score_str = f"{score:.1f}/100  ({grade})" if grade else f"{score:.1f}/100"
                fields.insert(1, ("Score", score_str))
        except Exception:
            pass

    # S4.4 — surface JD coverage % and width hit-rate as quality signals
    metrics = _read_quality_metrics(run_dir)
    if metrics["jd_coverage_pct"] is not None:
        cov_pct = metrics["jd_coverage_pct"]
        cov_str = f"{metrics['jd_covered']}/{metrics['jd_total']} reqs ({cov_pct:.1f}%)"
        fields.append(("JD Coverage", _fmt_metric_value(cov_str, cov_pct)))
    if metrics["width_hit_pct"] is not None:
        wid_pct = metrics["width_hit_pct"]
        wid_str = f"{metrics['width_hit_bullets']}/{metrics['width_total_bullets']} bullets ({wid_pct:.1f}%)"
        fields.append(("Width hits", _fmt_metric_value(wid_str, wid_pct)))

    # S5.5 — warn when bullets flagged below BRS threshold
    if metrics["below_threshold_count"] > 0:
        n = metrics["below_threshold_count"]
        fields.append((
            "Quality",
            f"[#FF5733]⚠  {n} bullet{'s' if n != 1 else ''} below quality threshold — consider manual review[/]",
        ))

    opener = {"darwin": "open", "linux": "xdg-open", "win32": "start"}.get(sys.platform, "open")
    next_steps = [
        ("linkright critique", "LLM review — 5 actionable issues + fix UI"),
        ("linkright fill",     "Resolve missing-metric gaps (interactive)"),
        ("linkright practice", "Interview prep cards from your resume"),
    ]
    if pdf_path.exists():
        next_steps.append((f'{opener} "{pdf_path}"', "Open PDF"))

    success_card(
        title=f"Resume Tailored  —  {run_dir.name}",
        fields=fields,
        next_steps=next_steps,
        accent=TEAL,
    )


@resume_group.command("tailor")
@click.option("--resume", "-r", "resume_path", type=click.Path(exists=True, path_type=Path), required=False, default=None,
              help="(optional) Resume PDF or career_signals.yaml — prompted if omitted")
@click.option("--jd", "-j", "jd_path", type=click.Path(exists=True, path_type=Path), required=False, default=None,
              help="(optional) Job description markdown file — prompted if omitted")
@click.option("--mode", default=None, help="Skill mode: product_manager | swe | ds | designer | generic")
@click.option("--llm-mode", type=click.Choice(["agent", "direct", "mcp"]), default=None,
              help="LLM routing: agent (MCP, default) | direct (user's key) | mcp (alias)")
@click.option("--yes", is_flag=True, help="Skip interactive confirmations")
@click.option("--run-id", default=None, help="Override run id (defaults to timestamp)")
@click.option("--no-cache", is_flag=True, help="Skip the ~/.linkright/profile/ cache; force fresh parse+extract+embed.")
@click.option("--deterministic", is_flag=True,
              help="Pin temperature=0 + seed across all LLM calls. Pairs with hypothesis-test for variance reduction.")
@click.option("--seed", default=42, type=int, help="Seed for deterministic mode (default 42). Honoured by Groq/Cerebras/OpenRouter; Gemini ignores.")
@click.option("--no-pause", "no_pause", is_flag=True, help="Skip phase-boundary review checkpoints (CI / non-interactive mode).")
def tailor(resume_path: Path | None, jd_path: Path | None, mode: str | None, llm_mode: str | None, yes: bool, run_id: str | None, no_cache: bool, deterministic: bool, seed: int, no_pause: bool) -> None:
    """Tailor your resume for a job description (typically 2-4 minutes).

    Run with no flags to be prompted interactively. Pass flags to skip prompts.

    \b
    Quick start:
      linkright tailor                       (prompted for resume + JD)
      linkright tailor -r resume.pdf -j jd.md   (power-user: skip prompts)

    The command parses your resume + JD, retrieves matching career nuggets,
    drafts bullets via LLM, scores + ranks, and renders a final PDF.
    """
    require_profile()
    require_llm_key(llm_mode or Config.load().default_llm_mode)
    # Bare-command UX: auto-use profile resume when available; prompt only as fallback.
    if resume_path is None:
        from linkright.profile.pipeline import _profile_dir as _pdir_fn
        _pdir = _pdir_fn()
        _profile_pdf = _pdir / "inputs" / "resume.pdf"
        _profile_md  = _pdir / "inputs" / "resume.md"
        if _profile_pdf.exists():
            resume_path = _profile_pdf
            click.echo(f"✓ Using profile resume: {resume_path}")
        elif _profile_md.exists():
            resume_path = _profile_md
            click.echo(f"✓ Using profile resume: {resume_path}")
        else:
            from linkright.prompts import prompt_for_existing_path
            resume_path = prompt_for_existing_path(
                "Path to your resume (PDF or .md):",
                must_be_file=True,
                flag_hint="-r/--resume",
            )
    _temp_jd_path: Path | None = None
    if jd_path is None:
        from linkright.prompts import prompt_for_jd_input
        from linkright.jobsearch.cli import _try_auth_headers as _try_auth
        _allow_discovery = _try_auth() is not None
        kind, value = prompt_for_jd_input(flag_hint="-j/--jd", allow_discovery=_allow_discovery)
        if kind == "file":
            jd_path = value
        elif kind == "discovery":
            from linkright.jobsearch.cli import (
                _pick_discovery_id_interactive,
                _resolve_id,
                _http,
                _auth_headers,
                _LINKRIGHT_API,
            )
            discovery_id = _pick_discovery_id_interactive("Pick a saved job to tailor for:")
            if not discovery_id:
                click.echo("Cancelled.", err=True)
                sys.exit(1)
            resolved_id = _resolve_id(discovery_id)
            click.echo(f"Fetching JD for discovery {resolved_id[:8]}...", nl=False)
            try:
                with _http() as client:
                    resp = client.get(
                        f"{_LINKRIGHT_API}/api/discoveries/{resolved_id}",
                        headers=_auth_headers(),
                    )
            except Exception as exc:
                raise click.ClickException(f"Network error fetching JD: {exc}")
            if resp.status_code != 200:
                raise click.ClickException(f"API error {resp.status_code}: {resp.text[:200]}")
            disc = resp.json().get("discovery") or {}
            jd_text = disc.get("jd_text") or ""
            if not jd_text:
                raise click.ClickException(
                    "JD text not available for this discovery. "
                    "Try a different job or paste the JD instead."
                )
            click.echo(" done.")
            import tempfile
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
            tmp.write(
                f"# {disc.get('title', 'Job Description')} — {disc.get('company_name', '')}\n\n"
                f"**Location**: {disc.get('location', 'Unknown')}\n"
                f"**URL**: {disc.get('job_url', '')}\n\n"
                + jd_text
            )
            tmp.close()
            jd_path = Path(tmp.name)
            _temp_jd_path = jd_path
            click.echo(f"  Staged discovery JD → {jd_path}")
        else:  # paste — stage pasted text to a temp .md so existing copy works
            import tempfile
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
            tmp.write(value)
            tmp.close()
            jd_path = Path(tmp.name)
            _temp_jd_path = jd_path  # track for cleanup after copy below
            click.echo(f"  Staged pasted JD → {jd_path}")

    _started_at = time.monotonic()
    cfg = Config.load()
    llm_mode = llm_mode or cfg.default_llm_mode
    mode = mode or cfg.default_skill_mode
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")

    if deterministic:
        os.environ["LR_DETERMINISTIC"] = "1"
        os.environ["LR_SEED"] = str(seed)
        click.echo(f"Deterministic mode ON (seed={seed}) — temperature pinned to 0 across all LLM calls.")

    if no_pause:
        os.environ["LR_NO_PAUSE"] = "1"
        click.echo("Pause checkpoints disabled (--no-pause).")

    run_dir = cfg.runs_dir() / run_id
    (run_dir / "inputs").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    # Stage inputs — orchestrator expects inputs/{resume.pdf|resume.md,jd.md}
    if resume_path.suffix.lower() == ".pdf":
        shutil.copy(resume_path, run_dir / "inputs" / "resume.pdf")
    elif resume_path.suffix.lower() in (".md", ".markdown"):
        shutil.copy(resume_path, run_dir / "inputs" / "resume.md")
    else:
        shutil.copy(resume_path, run_dir / "inputs" / resume_path.name)
    shutil.copy(jd_path, run_dir / "inputs" / "jd.md")
    if _temp_jd_path is not None:
        # Clean up the prompt-staged temp file — the canonical copy lives
        # under run_dir/inputs/ now.
        try:
            _temp_jd_path.unlink()
        except OSError:
            pass

    # Profile-cache pre-populate: if ~/.linkright/profile/ exists AND its
    # embedder tier matches the active tier, copy the per-step artifacts
    # into run_dir so orchestrator's step_00..03 cache guards short-circuit
    # (saves 30-60 sec of LLM + embed work per run).
    cache_used = False
    if not no_cache:
        from linkright.profile.pipeline import _profile_dir, load_metadata
        from linkright.resume.lib.embedder import _detect_tier
        profile_dir = _profile_dir()
        meta = load_metadata(profile_dir)
        if meta:
            active_tier = _detect_tier()
            if meta.get("embedder_tier") == active_tier:
                profile_artifacts = profile_dir / "artifacts"
                cached_files = ["00_resume_raw_text.txt", "01_resume_parsed.json",
                                "02_nuggets_extracted.json", "03_nuggets_embedded.jsonl"]
                copied = []
                for fname in cached_files:
                    src = profile_artifacts / fname
                    if src.exists():
                        shutil.copy(src, run_dir / "artifacts" / fname)
                        copied.append(fname)
                if copied:
                    cache_used = True
                    click.echo(f"✓ Profile cache hit — reusing {len(copied)} artifacts from ~/.linkright/profile/ "
                               f"(saves ~30-60s of parse + extract + embed work).")
            else:
                click.echo(f"⚠ Profile embedder tier ({meta.get('embedder_tier')}) ≠ active tier "
                           f"({active_tier}); skipping cache (rebuild profile to align).")

    click.echo(f"Run ID: {run_id}")
    click.echo(f"Output: {run_dir}")
    click.echo(f"LLM mode: {llm_mode}  •  Skill mode: {mode}")
    if no_cache:
        click.echo("Cache: --no-cache flag set, fresh extraction.")

    if llm_mode in ("direct", "agent", "mcp"):
        # 2026-05-01: agent/mcp modes share the same orchestrator path as direct.
        # The dispatch difference lives inside `linkright.llm.direct.chat_with_fallback`
        # (and sibling functions) which check LR_LLM_MODE and route through the user's
        # chosen CLI subprocess (`agent_chat`) when set to "agent". This means agent-mode
        # reuses all 16 pipeline steps + telemetry + scorecard wiring without duplication.
        if llm_mode in ("agent", "mcp"):
            os.environ["LR_LLM_MODE"] = "agent"
            # Route to the backend picked by the user in `linkright setup`.
            # Env var takes priority — only set if the user hasn't already overridden.
            if not os.environ.get("LR_AGENT_BACKEND") and getattr(cfg, "agent_backend", None):
                os.environ["LR_AGENT_BACKEND"] = cfg.agent_backend
            backend = os.environ.get("LR_AGENT_BACKEND", "claude")
            click.echo(f"Agent mode active — '{backend}' CLI subprocess handles LLM calls (no API keys needed).")
        # Delegate to the 16-step pipeline
        from . import orchestrator
        orchestrator.RUN_DIR = run_dir
        orchestrator.ARTIFACTS = run_dir / "artifacts"
        orchestrator.INPUTS = run_dir / "inputs"
        orchestrator.LOG_PATH = run_dir / "logs" / "pipeline.log"
        orchestrator.ARTIFACTS.mkdir(parents=True, exist_ok=True)
        orchestrator.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Orchestrator's main() expects argparse; we invoke the lower-level run
            # primitives individually when an entry exists, else fall back to main.
            if hasattr(orchestrator, "run"):
                orchestrator.run(run_id=run_id)
            else:
                # Shim: call main() via argv
                old_argv = sys.argv
                sys.argv = ["orchestrator.py", "--run-id", run_id]
                try:
                    orchestrator.main()
                finally:
                    sys.argv = old_argv
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001
            click.echo(f"Pipeline error: {e}", err=True)
            raise click.Abort()
        _render_success_card(run_dir, _started_at)
    else:
        raise click.BadParameter(f"Unknown llm-mode: {llm_mode}")


@resume_group.command("verify")
@click.argument("run_id", required=False, default=None)
@click.option("--strict", is_flag=True, help="Exit non-zero if any canary fails.")
def verify_cmd(run_id: str | None, strict: bool) -> None:
    """Run canary checks on a completed `tailor` run.

    Run with no arg to be prompted from a picker of recent runs. Pass a
    RUN_ID to skip the prompt.

    Catches silent failure modes (0% coverage despite exit 0, telemetry $0
    when LLM ran, all-zero cosines indicating broken embedder, etc.).
    """
    import sys as _sys
    # Make harness package importable (lives beside src/, not inside it).
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.canaries import run_all, format_report
    cfg = Config.load()

    # Bare-command UX: pick from recent runs.
    if run_id is None:
        runs_dir = cfg.runs_dir()
        if not runs_dir.exists():
            click.echo("No runs found yet — try `linkright resume tailor` first.", err=True)
            _sys.exit(1)
        candidates = sorted(
            [d for d in runs_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )[:20]
        if not candidates:
            click.echo("No runs found yet — try `linkright resume tailor` first.", err=True)
            _sys.exit(1)
        from linkright.prompts import prompt_for_id_from_list
        run_id = prompt_for_id_from_list(
            candidates,
            label_fn=lambda d: f"{d.name}  ({datetime.fromtimestamp(d.stat().st_mtime).strftime('%Y-%m-%d %H:%M')})",
            id_fn=lambda d: d.name,
            message="Pick a run to verify:",
            flag_hint="RUN_ID",
        )
        if run_id is None:
            click.echo("Cancelled.", err=True)
            _sys.exit(1)

    run_dir = cfg.runs_dir() / run_id
    if not run_dir.exists():
        click.echo(f"Run dir not found: {run_dir}", err=True)
        _sys.exit(1)
    all_passed, results = run_all(run_dir=run_dir)
    click.echo(format_report(results))
    if strict and not all_passed:
        _sys.exit(2)


@resume_group.command("score")
@click.option("--pdf", "pdf_path", type=click.Path(exists=True, path_type=Path), required=False, default=None,
              help="(optional) PDF resume to score — prompted if omitted")
@click.option("--jd", "jd_path", type=click.Path(exists=True, path_type=Path), required=False, default=None,
              help="(optional) Job description — prompted if omitted")
def score(pdf_path: Path | None, jd_path: Path | None) -> None:
    """Score an existing PDF against a JD using the resume scorecard (stub).

    Run with no flags to be prompted. Pass --pdf and --jd to skip prompts.
    """
    if pdf_path is None:
        from linkright.prompts import prompt_for_existing_path
        pdf_path = prompt_for_existing_path(
            "Path to the PDF resume to score:",
            must_be_file=True,
            flag_hint="--pdf",
        )
    _temp_jd_path: Path | None = None
    if jd_path is None:
        from linkright.prompts import prompt_for_jd_input
        kind, value = prompt_for_jd_input(flag_hint="--jd")
        if kind == "file":
            jd_path = value
        else:  # paste — stage to temp .md
            import tempfile
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
            tmp.write(value)
            tmp.close()
            jd_path = Path(tmp.name)
            _temp_jd_path = jd_path

    click.echo(f"Scorecard stub — pdf={pdf_path.name}, jd={jd_path.name}")
    click.echo("Resume scorecard harness: harness/resume/ (to be wired).")
    if _temp_jd_path is not None:
        try:
            _temp_jd_path.unlink()
        except OSError:
            pass


@resume_group.command("batch")
@click.option("--resume", "-r", "resume_path", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--jds", "jds_dir", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
@click.option("--parallel", default=3, type=int)
def batch(resume_path: Path, jds_dir: Path, parallel: int) -> None:
    """Tailor resume across a directory of JDs (parallel)."""
    jds = sorted(jds_dir.glob("*.md"))
    click.echo(f"Found {len(jds)} JDs; would tailor with parallel={parallel}")
    click.echo("(Batch runner uses asyncio.gather + per-run subprocess — implemented after direct-mode ships.)")


@resume_group.command("iterate")
@click.option("--run-id", default=None, help="Run id under ~/.linkright/runs/ (defaults to latest)")
@click.option("--max-iterations", default=3, type=int, help="Max B1-B9 loops (informational)")
def iterate(run_id: str | None, max_iterations: int) -> None:
    """Open the B1-B9 iteration loop: pick worst dim → propose fix → re-run."""
    # Make the top-level `harness` package importable (lives beside src/, not inside it)
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.iterate import run_iterate
    run_iterate(run_id=run_id, max_iterations=max_iterations)


@resume_group.command("improve")
@click.option("--run-id", default=None, help="Run id (defaults to latest non-hypothesis run)")
@click.option("--target-dim", default=None,
              help="Scorecard dim to improve. If unset, picks weakest. MVP: width_hit_rate only.")
@click.option("--dry-run", is_flag=True,
              help="Identify deficiencies but don't actually call LLM for refinement.")
def improve_cmd(run_id: str | None, target_dim: str | None, dry_run: bool) -> None:
    """REFINE existing bullets — NOT regenerate from scratch.

    Use this when your tailored resume is mostly good but one specific
    dimension needs polish (e.g., bullets too long, bullets too short).
    Reads the latest tailor run, identifies what's off vs the target
    dim, runs targeted LLM refinement on ONLY that dimension —
    preserves everything else (metrics, bolds, verbs).

    Currently supports `width_hit_rate` (bullets outside [108, 118]
    char band get trimmed/expanded). Other dims coming.
    """
    require_profile()
    require_tailor_run()
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.improve import run_improve
    result = run_improve(run_id=run_id, target_dim=target_dim, dry_run=dry_run)
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)


@resume_group.command("fill-metrics")
@click.option("--run-id", default=None,
              help="Run id under ~/.linkright/runs/ (defaults to latest non-hypothesis run)")
@click.option("--dry-run", is_flag=True,
              help="Detect gaps and print, but skip user prompts + LLM rewrites.")
def fill_metrics_cmd(run_id: str | None, dry_run: bool) -> None:
    """Interactive metric-filler — replace weak bullets with concrete numbers.

    For each bullet that counts things ('Built 5 features') instead of
    measuring impact ('Built 5 features that drove 30% adoption'), the
    tool:
      1. Suggests 3 metric types (e.g., cost reduction, time saved,
         user reach) with industry-typical ranges.
      2. You pick a type (or mark "not relevant" to skip).
      3. You pick a fill mode:
           a. Provide your actual value (e.g., '18%')
           b. Use a placeholder ('X%', 'Y$M', 'Z hours') — fill offline
           c. Cancel — leave bullet alone
      4. Bullet rewritten with your value; resume re-rendered + re-scored.

    Placeholders are NOT fabrication — they openly signal "value pending"
    (a common pattern for NDA / privacy / mid-process candidates). The
    tool coaches WHAT metrics matter; YOU supply the actual numbers.
    Tool never invents values.
    """
    require_profile()
    require_tailor_run()
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.fill_metrics import run_fill_metrics
    result = run_fill_metrics(run_id=run_id, dry_run=dry_run)
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)


@resume_group.command("practice")
@click.option("--run-id", default=None,
              help="Run id under ~/.linkright/runs/ (defaults to latest non-hypothesis run)")
@click.option("--non-interactive", is_flag=True,
              help="Print the full prep packet without prompting (for piping/review).")
def practice_cmd(run_id: str | None, non_interactive: bool) -> None:
    """Walk through interview-practice cards from your tailored resume.

    For every bullet in your latest resume, shows:
      - the competency signal it conveys
      - 2 recruiter screening questions this bullet best answers
      - STAR (Situation / Task / Action / Result) seed template,
        with Action pre-filled from the bullet
      - prompt to type your answer (saved as your audit log)

    Bridges Pillar 1 (resume) ↔ Pillar 3 (interview prep) — every
    bullet becomes a baseline narrative for HR-screening / Round 1
    questions that almost-always come up.
    """
    require_profile()
    require_tailor_run()
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.practice import run_practice
    result = run_practice(run_id=run_id, interactive=not non_interactive)
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)


@resume_group.command("strategy-review")
@click.option("--run-id", default=None,
              help="Run id under ~/.linkright/runs/ (defaults to latest non-hypothesis run)")
def strategy_review_cmd(run_id: str | None) -> None:
    """Review the bullet plan BEFORE final generation.

    The bullet-plan step is the most consequential decision in the
    tailor pipeline — it determines which experiences from your career
    get prioritized, in what order, and how many bullets each role
    gets. This command surfaces that plan for you to inspect and edit
    BEFORE the LLM writes the verbose bullets.

    Workflow:
      1. Run `linkright resume tailor` once — pipeline retrieves
         nuggets per role, builds a draft plan
      2. Run THIS command — review per-role nugget plan; pick which
         become bullets
      3. Future tailor runs read your confirmed plan and override the
         auto-retrieval
    """
    require_profile()
    require_tailor_run()
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.strategy_review import run_strategy_review
    result = run_strategy_review(run_id=run_id)
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)


@resume_group.command("critique")
@click.option("--run-id", default=None,
              help="Run id under ~/.linkright/runs/ (defaults to latest non-hypothesis run)")
def critique_cmd(run_id: str | None) -> None:
    """LLM critique of your tailored resume + interactive fixes.

    Reads your rendered resume + JD. An LLM critic identifies up to 5
    actionable issues (weak phrasings, generic skills, missing JD
    coverage, illogical bullets, etc.). For each issue you pick:
      - Apply: take the LLM's suggested fix
      - Manual edit: opens the bullet in $EDITOR
      - Skip: leave it alone

    Run this right after `linkright tailor` to catch problems before
    you ship. Pairs naturally with `linkright fill` (metric gaps) and
    `linkright practice` (interview prep cards).
    """
    require_profile()
    require_tailor_run()
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.critique import run_critique
    result = run_critique(run_id=run_id)
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)


@resume_group.command("hypothesis-test")
@click.option("--resume", "-r", "resume_path", type=click.Path(exists=True, path_type=Path), required=True,
              help="Path to resume PDF (or pre-existing profile staged file).")
@click.option("--jd", "-j", "jd_path", type=click.Path(exists=True, path_type=Path), required=True,
              help="Path to job description markdown.")
@click.option("--hypothesis", required=True,
              help="One-line description of the hypothesis being tested. Logged to CONTINUOUS_RCA_LOG.md.")
@click.option("--variant-env", "variant_env_pairs", multiple=True,
              help="key=value env var override applied to variant arm only. "
                   "May be specified multiple times. "
                   "Common: LR_TIER_OVERRIDE_<step|intent>=<provider>.")
@click.option("--target-dim", "target_dims", multiple=True,
              help="Scorecard dim(s) the variant should improve (e.g. keyword_coverage). "
                   "If unset, falls back to overall_score.")
@click.option("--n", default=3, type=int, help="Runs per arm (default 3 → 6 total pipelines).")
@click.option("--seed", default=42, type=int, help="Seed base. Each run uses seed+i.")
@click.option("--skip-baseline", is_flag=True,
              help="Run only the variant arm; assumes a baseline arm was run earlier under the same hypothesis_id.")
def hypothesis_test_cmd(resume_path, jd_path, hypothesis, variant_env_pairs,
                        target_dims, n, seed, skip_baseline) -> None:
    """K baseline + K variant runs (deterministic mode) → median + stdev → KEEP/REVERT/INCONCLUSIVE.

    Single-command 99% iteration loop primitive. Each arm runs ``n`` pipelines
    with `LR_DETERMINISTIC=1`, scores via ResumeScorecard, computes per-dim
    median + stdev, applies the decision rule, and appends a YAML block to
    ``harness/CONTINUOUS_RCA_LOG.md``.

    Decision rule:
      KEEP        any --target-dim improved ≥ 2× pooled_stdev AND no other
                  dim regressed > 1× stdev
      REVERT      any target dim regressed ≥ 1× stdev
                  OR any non-target dim regressed ≥ 1× stdev
      INCONCLUSIVE no target improvement above noise band → suggest higher --n

    Exit codes: 0 KEEP, 1 REVERT, 2 INCONCLUSIVE.
    """
    import sys as _sys
    _HARNESS_PARENT = Path(__file__).resolve().parents[3]
    if str(_HARNESS_PARENT) not in _sys.path:
        _sys.path.insert(0, str(_HARNESS_PARENT))
    from harness.resume.hypothesis_test import run_hypothesis_test

    variant_env: dict[str, str] = {}
    for pair in variant_env_pairs:
        if "=" not in pair:
            click.echo(f"Invalid --variant-env: {pair!r} (expected key=value)", err=True)
            sys.exit(2)
        k, v = pair.split("=", 1)
        variant_env[k.strip()] = v.strip()

    result = run_hypothesis_test(
        resume_path=resume_path,
        jd_path=jd_path,
        hypothesis=hypothesis,
        variant_env=variant_env,
        target_dims=list(target_dims),
        n=n,
        seed_base=seed,
        skip_baseline=skip_baseline,
    )

    if result["verdict"] == "REVERT":
        sys.exit(1)
    if result["verdict"] == "INCONCLUSIVE":
        sys.exit(2)


# ── Subcommand aliases (registered after all commands are defined) ──────────
# Industry pattern: high-frequency commands get short aliases; long names
# always stay valid. `linkright resume t` ≡ `linkright resume tailor`.

resume_group.add_command(brand_cmd)

resume_group.add_aliases({
    # tailor / t
    "t":      "tailor",
    # brand / b — optional company-branded design (post-tailor step)
    "b":      "brand",
    # improve / imp / i
    "imp":    "improve",
    "i":      "improve",
    # critique / crit / c
    "crit":   "critique",
    "c":      "critique",
    # practice / prac / p
    "prac":   "practice",
    "p":      "practice",
    # score / s
    "s":      "score",
    # fill-metrics / fill / f
    "fill":   "fill-metrics",
    "f":      "fill-metrics",
    # strategy-review / plan / review / r
    "plan":   "strategy-review",
    "review": "strategy-review",
    "r":      "strategy-review",
    # iterate / iter
    "iter":   "iterate",
    # verify / v
    "v":      "verify",
    # hypothesis-test / ht
    "ht":     "hypothesis-test",
})
